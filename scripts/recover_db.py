import os
import duckdb
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def recover_database(db_path):
    if not os.path.exists(db_path):
        logger.warning(f"Database file not found: {db_path}")
        return False

    wal_path = f"{db_path}.wal"
    backup_wal = f"{wal_path}.corrupted_{int(os.path.getmtime(db_path))}"

    logger.info(f"--- Attempting recovery for {db_path} ---")

    # 1. Check if WAL exists
    if os.path.exists(wal_path):
        logger.info(f"Detected WAL file: {wal_path}")
        try:
            # Try to open normally first (maybe it's not actually corrupted)
            con = duckdb.connect(db_path)
            con.close()
            logger.info("Database opened successfully. No action needed.")
            return True
        except Exception as e:
            logger.error(f"Failed to open database with WAL: {e}")
            logger.info(f"Moving corrupted WAL to {backup_wal}...")
            shutil.move(wal_path, backup_wal)
    else:
        logger.info("No WAL file found. Checking database integrity...")

    # 2. Attempt to open without WAL
    try:
        con = duckdb.connect(db_path)
        logger.info("Database opened successfully without WAL.")
        
        # 3. Force a checkpoint to stabilize the file
        logger.info("Executing CHECKPOINT...")
        con.execute("CHECKPOINT;")
        
        # 4. Simple integrity check
        logger.info("Running integrity check (counting tables)...")
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
        logger.info(f"Found {len(tables)} tables.")
        
        con.close()
        logger.info(f"SUCCESS: Recovery complete for {db_path}")
        return True
    except Exception as e:
        logger.error(f"CRITICAL: Failed to recover main database file {db_path}: {e}")
        return False

if __name__ == "__main__":
    db_paths = [
        os.environ.get('PARSER_DATABASE_URL', '/data/ingestion_engine_parser.duckdb').replace('duckdb:///', ''),
        os.environ.get('APP_DATABASE_URL', '/data/family_finance_v3.duckdb').replace('duckdb:///', '')
    ]

    success_count = 0
    for path in db_paths:
        if recover_database(path):
            success_count += 1

    if success_count == len(db_paths):
        logger.info("\nALL DATABASES RECOVERED SUCCESSFULLY.")
    elif success_count > 0:
        logger.warning("\nPARTIAL RECOVERY COMPLETED.")
    else:
        logger.error("\nRECOVERY FAILED FOR ALL DATABASES.")
