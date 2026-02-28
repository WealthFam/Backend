from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from parser.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """
    Initialize the database tables.
    DuckDB with SQLAlchemy requires explicit creation if not using migrations.
    """
    # 1. SQLAlchemy auto-create (Best effort for ORM models)
    Base.metadata.create_all(bind=engine)

    # 2. Run explicit migrations for DuckDB stability
    from parser.db.migration import run_auto_migrations
    run_auto_migrations(engine)
    
    # 3. OPTIONAL: Run schema.sql if you want to enforce raw SQL definitions or views not in ORM
    # schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "schema.sql")
    # if os.path.exists(schema_path):
    #     try:
    #         with open(schema_path, "r") as f:
    #             sql_script = f.read()
    #             with engine.connect() as conn:
    #                 # conn.execute(text(sql_script)) # Requires sqlalchemy.text
    #                 pass
    #     except Exception as e:
    #         print(f"Schema SQL execution failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
