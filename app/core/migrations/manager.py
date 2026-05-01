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
    
    # DuckDB can be sensitive to multiple DDL operations on the same table within a single transaction.
    # We pass the engine to apply_patches to allow it to manage transaction boundaries.
    apply_patches(engine)
    
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

def apply_patches(engine: Engine):
    """
    PLACEHOLDER FOR FUTURE SCHEMA EVOLUTION.
    
    Each patch is executed in its own isolated transaction to satisfy DuckDB's 
    strict requirement for clear transaction boundaries during DDL operations.
    """
    
    logger.info("Applying ad-hoc schema patches...")

    # DuckDB Hardening: Force a checkpoint before starting patches to ensure
    # all previous operations (like metadata.create_all) are fully flushed.
    with engine.begin() as connection:
        connection.execute(text("PRAGMA force_checkpoint;"))

    # [2026-04-14] Fix column name mismatch in mutual_fund_holdings
    with engine.begin() as connection:
        utils.safe_rename_column(connection, "mutual_fund_holdings", "last_updated", "last_updated_at")
    
    # [2026-04-15] Add missing latitude and longitude columns
    for table in ["unparsed_messages", "pending_transactions", "transactions"]:
        with engine.begin() as connection:
            utils.safe_add_column(connection, table, "latitude", "DECIMAL(10, 8)")
        with engine.begin() as connection:
            utils.safe_add_column(connection, table, "longitude", "DECIMAL(11, 8)")
    
    # [2026-04-15] Add missing mutual fund columns 
    for col, col_type in [
        ("average_price", "DECIMAL(15, 4)"),
        ("current_value", "DECIMAL(15, 2)"),
        ("last_nav", "DECIMAL(15, 4)"),
        ("user_id", "VARCHAR"),
        ("goal_id", "VARCHAR"),
        ("invested_value", "DECIMAL(15, 2) DEFAULT 0") # [2026-04-18]
    ]:
        with engine.begin() as connection:
            utils.safe_add_column(connection, "mutual_fund_holdings", col, col_type)
    
    # [2026-04-15] Legacy patches
    with engine.begin() as connection:
        utils.safe_add_column(connection, "mutual_fund_orders", "transaction_hash", "VARCHAR")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "portfolio_timeline_cache", "benchmark_value", "DOUBLE")

    # [2026-04-17] Hardened fix for account creation snapshots
    with engine.begin() as connection:
        utils.safe_add_column(connection, "balance_snapshots", "credit_limit", "DECIMAL(15, 2)")

    # [2026-04-21] Add Mutual Fund Benchmarks table
    # We split drop and create to avoid transaction conflicts
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS mutual_fund_benchmarks"))
    
    with engine.begin() as connection:
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
    with engine.begin() as connection:
        utils.safe_add_column(connection, "mutual_fund_holdings", "is_deleted", "BOOLEAN DEFAULT FALSE")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "portfolio_timeline_cache", "benchmarks_json", "TEXT")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "mutual_fund_holdings", "deleted_at", "TIMESTAMP")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "mutual_fund_orders", "is_deleted", "BOOLEAN DEFAULT FALSE")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "mutual_fund_orders", "deleted_at", "TIMESTAMP")

    # [2026-04-21] Align benchmark field names (Idempotent renames)
    with engine.begin() as connection:
        utils.safe_rename_column(connection, "mutual_fund_benchmarks", "benchmark_scheme_code", "benchmark_symbol")
    with engine.begin() as connection:
        utils.safe_rename_column(connection, "mutual_fund_benchmarks", "benchmark_name", "benchmark_label")

    # [2026-04-21] Add Mutual Fund Benchmark Rules table
    with engine.begin() as connection:
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

    # [2026-04-28] Add User enhancements (ORM create_all handles the new tables)
    with engine.begin() as connection:
        utils.safe_add_column(connection, "users", "phone_number", "VARCHAR")

    # [2026-04-29] Decouple Statement Sync from General Email Sync
    with engine.begin() as connection:
        utils.safe_add_column(connection, "email_configurations", "statement_last_sync_at", "TIMESTAMP")

    # [2026-04-29] Statement Enhancements (Soft-delete & Email source)
    with engine.begin() as connection:
        utils.safe_add_column(connection, "statements", "email_sender", "VARCHAR")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "statements", "is_deleted", "BOOLEAN DEFAULT FALSE")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "statements", "deleted_at", "TIMESTAMP")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "statement_transactions", "is_deleted", "BOOLEAN DEFAULT FALSE")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "statement_transactions", "deleted_at", "TIMESTAMP")
    
    # [2026-04-30] Transaction Soft-delete Support
    with engine.begin() as connection:
        utils.safe_add_column(connection, "transactions", "is_deleted", "BOOLEAN DEFAULT FALSE")
    with engine.begin() as connection:
        utils.safe_add_column(connection, "transactions", "deleted_at", "TIMESTAMP")

    # [2026-05-01] Extended Soft-delete Support
    for table in ["accounts", "loans", "investment_goals", "expense_groups", "recurring_transactions", "budgets"]:
        with engine.begin() as connection:
            utils.safe_add_column(connection, table, "is_deleted", "BOOLEAN DEFAULT FALSE")
        with engine.begin() as connection:
            utils.safe_add_column(connection, table, "deleted_at", "TIMESTAMP")

    # [2026-05-01] Statement Failure Reason Support
    with engine.begin() as connection:
        utils.safe_add_column(connection, "statements", "failure_reason", "VARCHAR")

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
