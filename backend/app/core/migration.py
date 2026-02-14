import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)
from sqlalchemy.engine import Engine

def run_auto_migrations(engine: Engine):
    """
    Runs auto-migration logic to ensure the database schema matches the code expectations.
    This is designed for DuckDB which doesn't have robust Alembic support for all operations.
    
    NOTE: This function blocks and may raise exceptions if the DB is locked.
    The service manager (Systemd/Docker) should handle restarts in case of Lock errors.
    """
    try:
        with engine.connect() as connection:
            logger.info("Running auto-migration for mobile features...")
            
            # Helper to add columns safely
            def safe_add_column(table, col, type_def):
                try:
                    # DuckDB supports ADD COLUMN IF NOT EXISTS in newer versions
                    # but we can also check existence to be sure
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {type_def}"))
                except Exception as e:
                    logger.info(f"DEBUG: safe_add_column potential issue: {e}")
                    # If it failed because it already exists, we are fine. 
                    # If it failed for another reason, we might want to know, but 
                    # we don't want to abort the whole migration if possible.

            # 1. Add columns to existing tables since CREATE TABLE IF NOT EXISTS won't add them
            safe_add_column("pending_transactions", "latitude", "DECIMAL(10, 8)")
            safe_add_column("pending_transactions", "longitude", "DECIMAL(11, 8)")
            safe_add_column("pending_transactions", "location_name", "VARCHAR")
            safe_add_column("pending_transactions", "created_at", "TIMESTAMP")
            safe_add_column("pending_transactions", "is_transfer", "BOOLEAN DEFAULT FALSE")
            safe_add_column("pending_transactions", "to_account_id", "VARCHAR")

            # 1b. Add columns to CONFIRMED transactions table (for auto-ingest)
            safe_add_column("transactions", "latitude", "DECIMAL(10, 8)")
            safe_add_column("transactions", "longitude", "DECIMAL(11, 8)")
            safe_add_column("transactions", "location_name", "VARCHAR")
            safe_add_column("transactions", "is_transfer", "BOOLEAN DEFAULT FALSE")
            safe_add_column("transactions", "linked_transaction_id", "VARCHAR")

            # 2. Add mobile_devices table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS mobile_devices (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                user_id VARCHAR,
                device_name VARCHAR NOT NULL,
                device_id VARCHAR NOT NULL UNIQUE,
                fcm_token VARCHAR,
                is_approved BOOLEAN DEFAULT FALSE,
                is_enabled BOOLEAN DEFAULT TRUE,
                is_ignored BOOLEAN DEFAULT FALSE,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                FOREIGN KEY(user_id) REFERENCES users (id)
            );
            """))
            
            safe_add_column("mobile_devices", "user_id", "VARCHAR")
            safe_add_column("mobile_devices", "is_enabled", "BOOLEAN DEFAULT TRUE")
            safe_add_column("mobile_devices", "is_ignored", "BOOLEAN DEFAULT FALSE")
            
            # 3. Add unparsed_messages table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS unparsed_messages (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                raw_content VARCHAR NOT NULL,
                subject VARCHAR,
                sender VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))
            
            # 4. Add ingestion_events table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ingestion_events (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                device_id VARCHAR,
                event_type VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                message VARCHAR,
                data_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 5. Add email_configurations table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS email_configurations (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                user_id VARCHAR,
                email VARCHAR NOT NULL,
                password VARCHAR NOT NULL,
                imap_server VARCHAR DEFAULT 'imap.gmail.com',
                folder VARCHAR DEFAULT 'INBOX',
                is_active BOOLEAN DEFAULT TRUE,
                auto_sync_enabled BOOLEAN DEFAULT FALSE,
                last_sync_at TIMESTAMP,
                cas_last_sync_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 6. Category Type Migration
            safe_add_column("categories", "type", "VARCHAR DEFAULT 'expense'")
            
            # 7. Add email_sync_logs table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS email_sync_logs (
                id VARCHAR PRIMARY KEY,
                config_id VARCHAR NOT NULL,
                tenant_id VARCHAR NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status VARCHAR DEFAULT 'running',
                items_processed NUMERIC(10, 0) DEFAULT 0,
                message VARCHAR,
                FOREIGN KEY(config_id) REFERENCES email_configurations (id),
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))
            
            # 8. Deduplication Feature
            safe_add_column("transactions", "content_hash", "VARCHAR")
            safe_add_column("pending_transactions", "content_hash", "VARCHAR")
            safe_add_column("unparsed_messages", "content_hash", "VARCHAR")

            # 9. Ignore Patterns (Noise Reduction)
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ignored_patterns (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                pattern VARCHAR NOT NULL,
                source VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 10. Exclude from reports flag
            safe_add_column("transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            safe_add_column("pending_transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            safe_add_column("recurring_transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            safe_add_column("category_rules", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            
            # 11. Loans Table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS loans (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                account_id VARCHAR NOT NULL UNIQUE,
                principal_amount NUMERIC(15, 2) NOT NULL,
                interest_rate NUMERIC(5, 2) NOT NULL,
                start_date TIMESTAMP NOT NULL,
                tenure_months NUMERIC(5, 0) NOT NULL,
                emi_amount NUMERIC(15, 2) NOT NULL,
                emi_date NUMERIC(2, 0) NOT NULL,
                loan_type VARCHAR DEFAULT 'OTHER' NOT NULL,
                bank_account_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                FOREIGN KEY(account_id) REFERENCES accounts (id)
            );
            """))

            # 12. Add loan_type to loans if exists (backward compat)
            safe_add_column("loans", "loan_type", "VARCHAR DEFAULT 'OTHER'")

            # 13. Add EMI flag to transactions
            safe_add_column("transactions", "is_emi", "BOOLEAN DEFAULT FALSE")
            safe_add_column("transactions", "loan_id", "VARCHAR")

            # 14. Expense Groups & Subcategories
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS expense_groups (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                description VARCHAR,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            safe_add_column("categories", "parent_id", "VARCHAR")
            safe_add_column("transactions", "expense_group_id", "VARCHAR")
            safe_add_column("pending_transactions", "expense_group_id", "VARCHAR")

            # 14b. Add Date Range to Expense Groups
            safe_add_column("expense_groups", "start_date", "TIMESTAMP")
            safe_add_column("expense_groups", "end_date", "TIMESTAMP")
            safe_add_column("expense_groups", "budget", "DECIMAL(15, 2) DEFAULT 0")

            # 15. Investment Goals
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS investment_goals (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                target_amount NUMERIC(15, 2) NOT NULL,
                target_date TIMESTAMP,
                icon VARCHAR DEFAULT '🎯',
                color VARCHAR DEFAULT '#3b82f6',
                is_completed BOOLEAN DEFAULT FALSE,
                owner_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                FOREIGN KEY(owner_id) REFERENCES users (id)
            );
            """))

            safe_add_column("investment_goals", "owner_id", "VARCHAR")

            # 16. Link Holdings to Goals
            safe_add_column("mutual_fund_holdings", "goal_id", "VARCHAR")

            # 17. Expense Group Icons
            safe_add_column("expense_groups", "icon", "VARCHAR")

            # 18. Goal Assets (Flexible Linking)
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS goal_assets (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                goal_id VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                name VARCHAR,
                manual_amount NUMERIC(15, 2),
                interest_rate NUMERIC(5, 2),
                linked_account_id VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                FOREIGN KEY(goal_id) REFERENCES investment_goals (id),
                FOREIGN KEY(linked_account_id) REFERENCES accounts (id)
            );
            """))

            # 19. Benchmark Simulation (Absolute Corpus)
            safe_add_column("portfolio_timeline_cache", "benchmark_value", "NUMERIC(15, 2)")


            # Explicitly commit the transaction!
            connection.commit()
            logger.info("Auto-migration complete.")
            
    except Exception as e:
        # Re-raise lock errors or critical failures so the app doesn't start in a bad state
        logger.info(f"CRITICAL: Migration failed: {e}")
        raise e
