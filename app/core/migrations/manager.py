import logging
from sqlalchemy.engine import Engine
from . import utils

logger = logging.getLogger(__name__)

def run_schema_sync(engine: Engine):
    """
    Simplified Schema Scaffholding.
    
    This replaces the complex migration versioning system with a simple hooks-based approach.
    1. Base.metadata.create_all() handles the initial table creation.
    2. Any ad-hoc SQL or schema patches (like adding columns to existing tables) 
       should be placed in the 'apply_patches' function below.
    """
    logger.info("Initializing Schema Sync Scaffholding...")
    
    with engine.begin() as connection:
        apply_patches(connection)
    
    logger.info("Schema sync completed.")

def apply_patches(connection):
    """
    PLACEHOLDER FOR FUTURE SCHEMA EVOLUTION.
    
    If you need to add a column, create an index, or rebuild a table in the future,
    add the logic here using the 'utils' helpers.
    
    Example:
    utils.safe_add_column(connection, "users", "new_feature_enabled", "BOOLEAN DEFAULT FALSE")
    """
    
    # -------------------------------------------------------------------------
    # SCAFFOLD: Put future ad-hoc migrations below this line
    # -------------------------------------------------------------------------
    
    logger.info("Applying ad-hoc schema patches...")
    
    # [2026-04-14] Fix column name mismatch in mutual_fund_holdings
    utils.safe_rename_column(connection, "mutual_fund_holdings", "last_updated", "last_updated_at")
    
    # TODO: Add schema evolution logic here as the app grows.
    pass
