import logging
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Separate write lock for the market database to prevent contention with primary DB
market_db_write_lock = threading.RLock()

market_engine = create_engine(
    settings.MARKET_DATABASE_URL,
    connect_args={
        "config": {
            "checkpoint_threshold": "2MB"
        }
    },
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_pre_ping=True
)

MarketSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=market_engine)

MarketBase = declarative_base()

def get_market_db():
    db = MarketSessionLocal()
    try:
        yield db
    finally:
        db.close()

def force_market_checkpoint():
    """
    Manually triggers a DuckDB checkpoint for the market database.
    """
    try:
        with market_engine.connect() as connection:
            logger.info("Executing PRAGMA force_checkpoint on Market DB...")
            connection.execute(text("PRAGMA force_checkpoint;"))
        return True
    except Exception as e:
        logger.error(f"❌ Error during Market DuckDB checkpoint: {e}")
        return False
