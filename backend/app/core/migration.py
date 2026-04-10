import logging
import importlib
from sqlalchemy import text
from sqlalchemy.engine import Engine
from backend.app.core.migrations.utils import safe_add_column, rebuild_table

logger = logging.getLogger(__name__)

# List of all modular migrations in order
MIGRATIONS = [
    "v1_baseline",
    "v2_gps_sms",
    "v3_wealth_loans",
    "v4_vault_settings"
]

def run_auto_migrations(engine: Engine):
    """
    Modular Orchestrator for DuckDB Migrations.
    Tracks versioning and dynamically runs scripts from the migrations/ folder.
    """
    logger.info("Main orchestrator: Starting auto-migrations...")
    
    with engine.begin() as connection:
        # 1. Initialize migration history table (Force VARCHAR for modular versions)
        helpers_internal = {
            'rebuild_table': lambda table, sql, cols: rebuild_table(connection, table, sql, cols)
        }
        helpers_internal['rebuild_table']("migration_history", """
            CREATE TABLE IF NOT EXISTS migration_history (
                version_id VARCHAR PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """, ["version_id", "applied_at"])
        
        # 2. Get applied versions
        applied = [r[0] for r in connection.execute(text("SELECT version_id FROM migration_history")).fetchall()]
        
        # 3. Helpers to pass to scripts
        helpers = {
            'safe_add_column': lambda table, col, col_type: safe_add_column(connection, table, col, col_type),
            'rebuild_table': lambda table, sql, cols: rebuild_table(connection, table, sql, cols)
        }
        
        # 4. Run pending migrations
        for version in MIGRATIONS:
            if version not in applied:
                logger.info(f"---> Applying Migration: {version}")
                try:
                    # Dynamically import the migration script
                    module = importlib.import_module(f"backend.app.core.migrations.{version}")
                    module.apply(connection, helpers)
                    
                    # Record success
                    connection.execute(
                        text("INSERT INTO migration_history (version_id) VALUES (:v)"),
                        {"v": version}
                    )
                    logger.info(f"Migration {version} SUCCESS.")
                    
                except Exception as e:
                    logger.error(f"!!! MIGRATION {version} FAILED: {e}")
                    logger.exception(e)
                    # We don't catch here so the startup fails early if a migration is broken
                    raise e

    logger.info("Main orchestrator: All migrations complete.")
