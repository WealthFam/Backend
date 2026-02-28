from sqlalchemy import text
import logging
logger = logging.getLogger(__name__)
from sqlalchemy.engine import Engine

def run_auto_migrations(engine: Engine):
    """
    Runs auto-migration logic to ensure the parser database schema matches the models.
    """
    try:
        with engine.connect() as connection:
            print("Running Parser Service migrations...")
            
            # Helper to add columns safely (handling TIMESTAMPTZ for sqlite/duckdb locally vs postgres in prod)
            def safe_add_column(table, col, type_def):
                try:
                    # SQLite/DuckDB doesn't natively love 'TIMESTAMPTZ' syntax in ALTER statements the same way Postgres does
                    # We normalize it for local dev vs prod
                    final_type = type_def
                    if engine.dialect.name in ['sqlite', 'duckdb']:
                        final_type = type_def.replace('TIMESTAMPTZ', 'TIMESTAMP')
                    
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {final_type}"))
                except Exception as e:
                    logger.info(f"DEBUG: safe_add_column potential issue on {table}.{col}: {e}")

            # 1. Create merchant_aliases table if not exists
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS merchant_aliases (
                id VARCHAR PRIMARY KEY,
                pattern VARCHAR NOT NULL UNIQUE,
                alias VARCHAR NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            """))
            
            # 2. Add tenant_id to all tables
            safe_add_column("request_logs", "tenant_id", "VARCHAR DEFAULT 'system_tenant'")
            safe_add_column("file_parsing_configs", "tenant_id", "VARCHAR DEFAULT 'system_tenant'")
            safe_add_column("ai_configs", "tenant_id", "VARCHAR DEFAULT 'system_tenant'")
            safe_add_column("pattern_rules", "tenant_id", "VARCHAR DEFAULT 'system_tenant'")
            safe_add_column("merchant_aliases", "tenant_id", "VARCHAR DEFAULT 'system_tenant'")
            safe_add_column("ai_call_cache", "tenant_id", "VARCHAR DEFAULT 'system_tenant'")

            # 3. Update pattern_rules with AI fields and new columns
            safe_add_column("pattern_rules", "is_ai_generated", "BOOLEAN DEFAULT FALSE")
            safe_add_column("pattern_rules", "confidence", "JSON")
            safe_add_column("pattern_rules", "date_format", "VARCHAR")

            # 4. Create ai_call_cache table if not exists
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_call_cache (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                content_hash VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                response_json JSON NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            """))
            # Index for performance
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_call_cache_content_hash ON ai_call_cache (content_hash);"))

            # Explicitly commit if needed (DuckDB depends on connection mode)
            connection.commit()
            print("Parser Service migrations complete.")
            
            # --- Single Tenant Migration ---
            # Automatically migrate old 'system_tenant' records to the actual active tenant ID
            try:
                from parser.db.migrate_tenant import migrate_to_single_tenant
                migrate_to_single_tenant(engine)
            except Exception as outer_e:
                print(f"Non-critical: Single tenant migration skipped or failed: {outer_e}")
                
    except Exception as e:
        print(f"CRITICAL: Parser migration failed: {e}")
        raise e
