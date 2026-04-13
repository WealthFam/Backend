import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

# Global lock for DuckDB writes to prevent "database is locked" errors
# during concurrent mutations across different threads/tasks.
db_write_lock = threading.Lock()

# DuckDB is primarily a synchronous in-process database.
# We will use the standard synchronous engine.
# In FastAPI, we can use `def` route handlers (instead of `async def`) 
# to run these in a threadpool, preventing event loop blocking.

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "config": {
            "checkpoint_threshold": "10MB"
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