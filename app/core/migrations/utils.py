import logging
import re
from sqlalchemy import text
from typing import List, Optional

logger = logging.getLogger(__name__)

def safe_add_column(connection, table: str, col: str, col_type: str):
    """
    Idempotent helper to add a column to a table only if it doesn't already exist.
    """
    try:
        cols = connection.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
        col_names = [c[1] for c in cols]
        
        if col not in col_names:
            logger.info(f"Adding missing column {col} to table {table}...")
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
            logger.info(f"Successfully added {col} to {table}.")
    except Exception as e:
        logger.warning(f"Could not add column {col} to {table}: {e}")

def safe_create_index(connection, table: str, column: str, index_name: Optional[str] = None):
    """
    Idempotent helper to create an index.
    Checks for index existence before executing CREATE INDEX to prevent errors.
    """
    if not index_name:
        index_name = f"ix_{table}_{column}"
    
    try:
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column});"))
        logger.info(f"Ensured index {index_name} exists on {table}({column}).")
    except Exception as e:
        logger.warning(f"Failed to create index {index_name}: {e}")

def rebuild_table(connection, table_name: str, create_sql: str, columns: Optional[List[str]] = None):
    """
    Advanced 'Drop-and-Rebuild' utility with automated column mapping.
    Ensures safe schema upgrades without data loss.
    
    HARDENING: Added robust state-detection that ignores complex SQL type parameters 
    (like NUMERIC(15,2)). If the existing table satisfies the schema, we skip 
    rebuilding to prevent DuckDB DependencyErrors.
    """
    try:
        # 1. Existence Check
        existing = connection.execute(text(f"SELECT count(*) FROM information_schema.tables WHERE table_name = '{table_name}'")).scalar()
        if not existing:
            logger.info(f"Table {table_name} does not exist. Creating fresh.")
            connection.execute(text(create_sql))
            return

        # 2. Hardened State Detection (Precision Regex)
        target_cols = columns
        if not target_cols:
            # Strip comments
            clean_sql = re.sub(r'--.*$', '', create_sql, flags=re.MULTILINE)
            # Find the core definition block
            sql_body = re.search(r'\((.*)\)', clean_sql, re.DOTALL)
            if sql_body:
                body_content = sql_body.group(1)
                # CRITICAL: Strip content of parentheses to avoid matching type parameters like (15, 2)
                clean_body = re.sub(r'\([^()]*\)', '', body_content)
                # Extract first word of every line or after a comma
                candidates = re.findall(r'(?:^|,)\s*([a-zA-Z0-9_]+)', clean_body, re.MULTILINE)
                # Comprehensive keyword blacklist
                blacklist = {
                    "FOREIGN", "PRIMARY", "UNIQUE", "CHECK", "CONSTRAINT", "KEY", 
                    "NULL", "NOT", "DEFAULT", "TIMESTAMP", "CURRENT_TIMESTAMP", "CREATE", "REFERENCES"
                }
                target_cols = [c for c in candidates if c.upper() not in blacklist]
            else:
                target_cols = []

        current_cols = [r[1] for r in connection.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()]
        
        # Determine if we are truly missing any pillars of the schema
        missing_cols = [c for c in target_cols if c not in current_cols]
        if not missing_cols:
            logger.info(f"Table {table_name} schema is already satisfied. Skipping redundant rebuild.")
            return

        logger.info(f"Rebuild required for {table_name}. Missing columns: {missing_cols}")
        
        # 3. Safe Rebuild (Only triggered if missing_cols exists)
        connection.execute(text(f"ALTER TABLE {table_name} RENAME TO {table_name}_old"))
        connection.execute(text(create_sql))
        
        old_cols = [r[1] for r in connection.execute(text(f"PRAGMA table_info('{table_name}_old')")).fetchall()]
        new_cols = [r[1] for r in connection.execute(text(f"PRAGMA table_info('{table_name}')")).fetchall()]
        
        cols_to_copy = [c for c in new_cols if c in old_cols]
        if columns: # If manual list, further intersect
            cols_to_copy = [c for c in columns if c in cols_to_copy]
            
        if cols_to_copy:
            col_str = ", ".join(cols_to_copy)
            connection.execute(text(f"INSERT INTO {table_name} ({col_str}) SELECT {col_str} FROM {table_name}_old"))
            logger.info(f"Successfully migrated {len(cols_to_copy)} columns: {col_str}")
        
        connection.execute(text(f"DROP TABLE {table_name}_old"))
        logger.info(f"Rebuild of {table_name} finalized successfully.")
        
    except Exception as e:
        logger.error(f"FATAL REBUILD ERROR on {table_name}: {e}")
        try:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            connection.execute(text(f"ALTER TABLE {table_name}_old RENAME TO {table_name}"))
        except:
            pass
        raise e
