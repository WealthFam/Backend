import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

def safe_add_column(connection, table: str, col: str, col_type: str):
    """Adds a column to a table only if it doesn't already exist."""
    try:
        # Check if column exists
        cols = connection.execute(text(f"PRAGMA table_info('{table}')")).fetchall()
        col_names = [c[1] for c in cols]
        
        if col not in col_names:
            logger.info(f"Adding missing column {col} to table {table}...")
            # Detect DuckDB vs General SQLAlchemy usage
            final_type = col_type if "DECIMAL" not in col_type.upper() else col_type
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {final_type}"))
            logger.info(f"Successfully added {col} to {table}.")
        else:
            # Column exists, skip
            pass
    except Exception as e:
        logger.warning(f"Could not add column {col} to {table}: {e}")

def rebuild_table(connection, table_name: str, create_sql: str, columns: list):
    """
    Handles DuckDB's strict dependency locking by performing a table swap.
    1. Renames old table to _old
    2. Creates new table
    3. Copies data from existing columns
    4. Drops old table
    """
    try:
        # Check if table exists
        existing = connection.execute(text(f"SELECT count(*) FROM information_schema.tables WHERE table_name = '{table_name}'")).scalar()
        if not existing:
            # Simple path: table doesn't exist, just create it
            connection.execute(text(create_sql))
            return

        logger.info(f"Rebuilding table {table_name} to update schema...")
        
        # 1. Rename existing
        connection.execute(text(f"ALTER TABLE {table_name} RENAME TO {table_name}_old"))
        
        # 2. Create new
        connection.execute(text(create_sql))
        
        # 3. Detect which columns we can safely copy
        existing_cols = [r[1] for r in connection.execute(text(f"PRAGMA table_info('{table_name}_old')")).fetchall()]
        cols_to_copy = [c for c in columns if c in existing_cols]
        
        if cols_to_copy:
            col_str = ", ".join(cols_to_copy)
            connection.execute(text(f"INSERT INTO {table_name} ({col_str}) SELECT {col_str} FROM {table_name}_old"))
            logger.info(f"Copied data for columns: {col_str}")
        
        # 4. Drop old
        connection.execute(text(f"DROP TABLE {table_name}_old"))
        logger.info(f"Rebuild of {table_name} complete.")
        
    except Exception as e:
        logger.error(f"FAILED to rebuild table {table_name}: {e}")
        # Try to recover if we were mid-swap
        try:
            connection.execute(text(f"ALTER TABLE {table_name}_old RENAME TO {table_name}"))
        except:
            pass
        raise e
