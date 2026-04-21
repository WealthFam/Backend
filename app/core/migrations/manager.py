import logging
from sqlalchemy import text
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
    
    # 3. Run one-time data repairs (Self-healing)
    run_data_repair_v1_mf(engine)
    
    # 4. Seed benchmark rules
    seed_benchmark_rules(engine)
    
    logger.info("Schema sync completed.")

def run_data_repair_v1_mf(engine: Engine):
    """
    [2026-04-18] Self-healing logic for Mutual Fund holdings.
    Identifies tenants with 0 invested_value and triggers a recalculation.
    """
    from sqlalchemy import text
    try:
        # 1. Identify affected tenants (where holdings have 0 invested but potentially have orders)
        with engine.connect() as conn:
            query = text("""
                SELECT DISTINCT tenant_id 
                FROM mutual_fund_holdings 
                WHERE invested_value = 0 OR invested_value IS NULL OR average_price IS NULL
            """)
            tenants = [row[0] for row in conn.execute(query).fetchall()]
        
        if not tenants:
            return

        logger.info(f"Detected {len(tenants)} tenants requiring Mutual Fund data repair...")
        
        # 2. Lazy imports to avoid circular dependencies
        from backend.app.core.database import SessionLocal
        from backend.app.modules.finance.services.mutual_funds import MutualFundService
        
        # 3. Trigger repair for each tenant
        for t_id in tenants:
            try:
                with SessionLocal() as db:
                    count = MutualFundService.recalculate_holdings(db, t_id)
                    logger.info(f"✅ Data repair completed for tenant {t_id}: Processed {count} orders.")
            except Exception as e:
                logger.error(f"❌ Failed to repair data for tenant {t_id}: {e}")
                
    except Exception as e:
        logger.warning(f"Skipping Mutual Fund data repair: {e}")

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
    
    # [2026-04-15] Add missing latitude and longitude columns to ingestion and transactions
    utils.safe_add_column(connection, "unparsed_messages", "latitude", "DECIMAL(10, 8)")
    utils.safe_add_column(connection, "unparsed_messages", "longitude", "DECIMAL(11, 8)")
    utils.safe_add_column(connection, "pending_transactions", "latitude", "DECIMAL(10, 8)")
    utils.safe_add_column(connection, "pending_transactions", "longitude", "DECIMAL(11, 8)")
    utils.safe_add_column(connection, "transactions", "latitude", "DECIMAL(10, 8)")
    utils.safe_add_column(connection, "transactions", "longitude", "DECIMAL(11, 8)")
    
    # [2026-04-15] Add missing mutual fund columns 
    utils.safe_add_column(connection, "mutual_fund_holdings", "average_price", "DECIMAL(15, 4)")
    utils.safe_add_column(connection, "mutual_fund_holdings", "current_value", "DECIMAL(15, 2)")
    utils.safe_add_column(connection, "mutual_fund_holdings", "last_nav", "DECIMAL(15, 4)")
    utils.safe_add_column(connection, "mutual_fund_holdings", "user_id", "VARCHAR")
    utils.safe_add_column(connection, "mutual_fund_holdings", "goal_id", "VARCHAR")
    
    # [2026-04-15] Legacy patches migrated from upgrade_mf_schema.py
    utils.safe_add_column(connection, "mutual_fund_orders", "transaction_hash", "VARCHAR")
    utils.safe_add_column(connection, "portfolio_timeline_cache", "benchmark_value", "DOUBLE")

    # [2026-04-18] Fix 0 invested metrics 
    utils.safe_add_column(connection, "mutual_fund_holdings", "invested_value", "DECIMAL(15, 2) DEFAULT 0")

    # [2026-04-17] Hardened fix for account creation snapshots
    utils.safe_add_column(connection, "balance_snapshots", "credit_limit", "DECIMAL(15, 2)")

    
    # [2026-04-21] Add Mutual Fund Benchmarks table (Harmonized Schema)
    # We drop and recreate once to ensure column names are synchronized (benchmark_symbol, benchmark_label)
    # This is safe as BenchmarkService automatically repopulates these mappings on first run.
    connection.execute(text("DROP TABLE IF EXISTS mutual_fund_benchmarks"))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS mutual_fund_benchmarks (
            id VARCHAR PRIMARY KEY,
            category VARCHAR UNIQUE,
            benchmark_symbol VARCHAR,
            benchmark_label VARCHAR,
            is_default BOOLEAN DEFAULT FALSE,
            styling_color VARCHAR,
            styling_style VARCHAR,
            styling_dash_array VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    # [2026-04-21] Add multi-benchmark support to cache
    utils.safe_add_column(connection, "mutual_fund_holdings", "is_deleted", "BOOLEAN DEFAULT FALSE")
    utils.safe_add_column(connection, "portfolio_timeline_cache", "benchmarks_json", "TEXT")
    utils.safe_add_column(connection, "mutual_fund_holdings", "deleted_at", "TIMESTAMP")
    utils.safe_add_column(connection, "mutual_fund_orders", "is_deleted", "BOOLEAN DEFAULT FALSE")
    utils.safe_add_column(connection, "mutual_fund_orders", "deleted_at", "TIMESTAMP")

    # [2026-04-21] Align benchmark field names
    utils.safe_rename_column(connection, "mutual_fund_benchmarks", "benchmark_scheme_code", "benchmark_symbol")
    utils.safe_rename_column(connection, "mutual_fund_benchmarks", "benchmark_name", "benchmark_label")

    # [2026-04-21] Add Mutual Fund Benchmark Rules table
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS mutual_fund_benchmark_rules (
            id VARCHAR PRIMARY KEY,
            priority INTEGER DEFAULT 0,
            keyword VARCHAR NOT NULL,
            benchmark_symbol VARCHAR NOT NULL,
            benchmark_label VARCHAR NOT NULL,
            styling_color VARCHAR,
            styling_style VARCHAR DEFAULT 'solid',
            styling_dash_array VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # TODO: Add schema evolution logic here as the app grows.
    pass

def seed_benchmark_rules(engine: Engine):
    """
    Seeds the mutual_fund_benchmark_rules table with initial heuristics.
    """
    from sqlalchemy import text
    from uuid import uuid4
    
    rules = [
        # priority, keyword, symbol, label, color, dash
        (10, "small cap", "147703", "Nifty Smallcap 250 Index", "#F43F5E", "5,5"),
        (20, "mid cap", "147701", "Nifty Midcap 150 Index", "#F59E0B", "5,5"),
        (30, "large cap", "120716", "Nifty 50 Index", "#10B981", "5,5"),
        (40, "bluechip", "120716", "Nifty 50 Index", "#10B981", "5,5"),
        (50, "index", "120716", "Nifty 50 Index", "#10B981", "5,5"),
        (100, "", "120716", "Nifty 50 Index", "#10B981", "5,5") # Default fallback
    ]
    
    with engine.begin() as conn:
        # Check if any rules exist
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM mutual_fund_benchmark_rules")).scalar()
            if count == 0:
                logger.info("Seeding initial Mutual Fund benchmark rules...")
                for priority, keyword, symbol, label, color, dash in rules:
                    conn.execute(text("""
                        INSERT INTO mutual_fund_benchmark_rules 
                        (id, priority, keyword, benchmark_symbol, benchmark_label, styling_color, styling_dash_array)
                        VALUES (:id, :priority, :keyword, :symbol, :label, :color, :dash)
                    """), {
                        "id": str(uuid4()),
                        "priority": priority,
                        "keyword": keyword,
                        "symbol": symbol,
                        "label": label,
                        "color": color,
                        "dash": dash
                    })
        except Exception as e:
            logger.warning(f"Skipping benchmark rules seeding: {e}")
