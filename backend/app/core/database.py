from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from backend.app.core.config import settings

# DuckDB is primarily a synchronous in-process database.
# We will use the standard synchronous engine.
# In FastAPI, we can use `def` route handlers (instead of `async def`) 
# to run these in a threadpool, preventing event loop blocking.

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"read_only": False}, 
    # Use NullPool for DuckDB to ensure locks are released immediately after use.
    poolclass=NullPool
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
