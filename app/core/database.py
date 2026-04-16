import logging
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Global re-entrant lock for DuckDB writes to prevent deadlocks during nested service calls.
db_write_lock = threading.RLock()

# DuckDB is primarily a synchronous in-process database.
# We will use the standard synchronous engine.
# In FastAPI, we can use `def` route handlers (instead of `async def`) 
# to run these in a threadpool, preventing event loop blocking.

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "config": {
            "checkpoint_threshold": "2MB"
        }
    },
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def force_checkpoint():
    """
    Manually triggers a DuckDB checkpoint to merge the WAL into the main file.
    Can be called periodically or during shutdown.
    """
    try:
        with engine.connect() as connection:
            logger.info("Executing PRAGMA force_checkpoint...")
            connection.execute(text("PRAGMA force_checkpoint;"))
        return True
    except Exception as e:
        logger.error(f"❌ Error during DuckDB checkpoint: {e}")
        return False

def shutdown_db():
    """
    Gracefully shuts down the database by forcing a checkpoint 
    and disposing the engine. This prevents WAL corruption.
    """
    logger.info("--- Initializing Backend Database Graceful Shutdown ---")
    
    # 1. Force a checkpoint to merge WAL into main database file
    force_checkpoint()
            
    # 2. Dispose the engine to release file locks
    try:
        logger.info("Disposing Backend engine...")
        engine.dispose()
        logger.info("✅ Backend Database shutdown complete.")
    except Exception as e:
        logger.error(f"❌ Error during engine disposal: {e}")