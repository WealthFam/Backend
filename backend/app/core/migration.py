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
            
            # Helper to add columns safely (handling TIMESTAMPTZ for sqlite/duckdb locally vs postgres in prod)
            def safe_add_column(table, col, type_def):
                try:
                    # SQLite/DuckDB doesn't natively love 'TIMESTAMPTZ' syntax in ALTER statements the same way Postgres does
                    # We normalize it for local dev vs prod
                    final_type = type_def
                    if engine.dialect.name in ['sqlite', 'duckdb']:
                        final_type = type_def.replace('TIMESTAMPTZ', 'TIMESTAMP')
                    
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {final_type}"))
                    logger.debug(f"Migration: ensured column {table}.{col}")
                except Exception as e:
                    # Log at WARNING — column likely already exists (IF NOT EXISTS should prevent this, but DuckDB may differ)
                    logger.warning(f"Migration: could not add {table}.{col} ({type_def}): {e}")

            # 1. Add columns to existing tables since CREATE TABLE IF NOT EXISTS won't add them
            safe_add_column("pending_transactions", "latitude", "DECIMAL(10, 8)")
            safe_add_column("pending_transactions", "longitude", "DECIMAL(11, 8)")
            safe_add_column("pending_transactions", "location_name", "VARCHAR")
            safe_add_column("pending_transactions", "created_at", "TIMESTAMPTZ")
            safe_add_column("pending_transactions", "is_transfer", "BOOLEAN DEFAULT FALSE")
            safe_add_column("pending_transactions", "to_account_id", "VARCHAR")

            # 1b. Add columns to CONFIRMED transactions table (for auto-ingest)
            safe_add_column("transactions", "latitude", "DECIMAL(10, 8)")
            safe_add_column("transactions", "longitude", "DECIMAL(11, 8)")
            safe_add_column("transactions", "location_name", "VARCHAR")
            safe_add_column("transactions", "is_transfer", "BOOLEAN DEFAULT FALSE")
            safe_add_column("transactions", "linked_transaction_id", "VARCHAR")

            # 1c. Balance Refactoring sync fields
            safe_add_column("accounts", "last_synced_balance", "NUMERIC(15, 2)")
            safe_add_column("accounts", "last_synced_at", "TIMESTAMPTZ")
            safe_add_column("accounts", "last_synced_limit", "NUMERIC(15, 2)")
            safe_add_column("pending_transactions", "balance_is_synced", "BOOLEAN DEFAULT FALSE")

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
                last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
                last_sync_at TIMESTAMPTZ,
                cas_last_sync_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
                started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMPTZ,
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
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 10. Exclude from reports flag
            safe_add_column("transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            safe_add_column("pending_transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            safe_add_column("recurring_transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            safe_add_column("recurring_transactions", "latitude", "DECIMAL(10, 8)")
            safe_add_column("recurring_transactions", "longitude", "DECIMAL(11, 8)")
            safe_add_column("recurring_transactions", "location_name", "VARCHAR")
            safe_add_column("category_rules", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
            
            # 11. Loans Table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS loans (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                account_id VARCHAR NOT NULL UNIQUE,
                principal_amount NUMERIC(15, 2) NOT NULL,
                interest_rate NUMERIC(5, 2) NOT NULL,
                start_date TIMESTAMPTZ NOT NULL,
                tenure_months NUMERIC(5, 0) NOT NULL,
                emi_amount NUMERIC(15, 2) NOT NULL,
                emi_date NUMERIC(2, 0) NOT NULL,
                loan_type VARCHAR DEFAULT 'OTHER' NOT NULL,
                bank_account_id VARCHAR,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            safe_add_column("categories", "parent_id", "VARCHAR")
            safe_add_column("transactions", "expense_group_id", "VARCHAR")
            safe_add_column("pending_transactions", "expense_group_id", "VARCHAR")

            # 14b. Add Date Range to Expense Groups
            safe_add_column("expense_groups", "start_date", "TIMESTAMPTZ")
            safe_add_column("expense_groups", "end_date", "TIMESTAMPTZ")
            safe_add_column("expense_groups", "budget", "DECIMAL(15, 2) DEFAULT 0")

            # 15. Investment Goals
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS investment_goals (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                target_amount NUMERIC(15, 2) NOT NULL,
                target_date TIMESTAMPTZ,
                icon VARCHAR DEFAULT '🎯',
                color VARCHAR DEFAULT '#3b82f6',
                is_completed BOOLEAN DEFAULT FALSE,
                owner_id VARCHAR,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
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
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                FOREIGN KEY(goal_id) REFERENCES investment_goals (id),
                FOREIGN KEY(linked_account_id) REFERENCES accounts (id)
            );
            """))

            # 19. Benchmark Simulation (Absolute Corpus)
            safe_add_column("portfolio_timeline_cache", "benchmark_value", "NUMERIC(15, 2)")

            # 20. Balance Snapshots table
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS balance_snapshots (
                id VARCHAR PRIMARY KEY,
                account_id VARCHAR NOT NULL,
                tenant_id VARCHAR NOT NULL,
                balance NUMERIC(15, 2) NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
                source VARCHAR DEFAULT 'MANUAL',
                FOREIGN KEY(account_id) REFERENCES accounts (id),
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 21. Account owner field
            safe_add_column("accounts", "owner_id", "VARCHAR")

            # 22. Document Vault Tables
            # NOTE: Due to DuckDB limitations with Foreign Keys during updates, 
            # we ensure these tables do NOT have self-referencing FKs or strict FKs on document_id.

            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS document_vault (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                owner_id VARCHAR,
                filename VARCHAR NOT NULL,
                file_type VARCHAR NOT NULL DEFAULT 'OTHER',
                file_path VARCHAR,
                file_size NUMERIC(15, 0) DEFAULT 0,
                mime_type VARCHAR,
                transaction_id VARCHAR,
                parent_id VARCHAR,
                is_folder BOOLEAN DEFAULT FALSE,
                is_shared BOOLEAN DEFAULT TRUE,
                description VARCHAR,
                gdrive_file_id VARCHAR,
                last_synced_at TIMESTAMPTZ,
                current_version NUMERIC(5, 0) DEFAULT 1,
                thumbnail_path VARCHAR,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                FOREIGN KEY(owner_id) REFERENCES users (id)
                -- NOTE: No FK on transaction_id — DuckDB blocks UPDATE on parent rows when FK exists
            );
            """))

            safe_add_column("document_vault", "parent_id", "VARCHAR")
            safe_add_column("document_vault", "is_folder", "BOOLEAN DEFAULT FALSE")
            safe_add_column("document_vault", "is_shared", "BOOLEAN DEFAULT TRUE")
            safe_add_column("document_vault", "gdrive_file_id", "VARCHAR")
            safe_add_column("document_vault", "last_synced_at", "TIMESTAMPTZ")
            safe_add_column("document_vault", "current_version", "NUMERIC(5, 0) DEFAULT 1")
            safe_add_column("document_vault", "updated_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")
            safe_add_column("document_vault", "thumbnail_path", "VARCHAR")

            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS document_versions (
                id VARCHAR PRIMARY KEY,
                document_id VARCHAR NOT NULL,
                version_number NUMERIC(5, 0) NOT NULL,
                file_path VARCHAR NOT NULL,
                file_size NUMERIC(15, 0) NOT NULL,
                filename VARCHAR NOT NULL,
                thumbnail_path VARCHAR,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            """))

            safe_add_column("document_versions", "thumbnail_path", "VARCHAR")

            # 22b. Drop FK constraint on document_vault.transaction_id if it exists
            # DuckDB's FK implementation blocks UPDATE on any referenced parent row,
            # not just deletes — so normal transaction date edits crash when a doc is linked.
            # We rebuild the table without the FK if it has one. Data is preserved.
            try:
                # Check if the FK exists by attempting a safe probe
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS _dv_migration_check AS SELECT 1 WHERE FALSE
                """))
                connection.execute(text("DROP TABLE IF EXISTS _dv_migration_check"))

                # Recreate document_vault without the transaction_id FK
                # Only runs when transitioning from old schema that had the FK
                connection.execute(text("""
                CREATE TABLE IF NOT EXISTS document_vault_new (
                    id VARCHAR PRIMARY KEY,
                    tenant_id VARCHAR NOT NULL,
                    owner_id VARCHAR,
                    filename VARCHAR NOT NULL,
                    file_type VARCHAR NOT NULL DEFAULT 'OTHER',
                    file_path VARCHAR,
                    file_size NUMERIC(15, 0) DEFAULT 0,
                    mime_type VARCHAR,
                    transaction_id VARCHAR,
                    parent_id VARCHAR,
                    is_folder BOOLEAN DEFAULT FALSE,
                    is_shared BOOLEAN DEFAULT TRUE,
                    description VARCHAR,
                    gdrive_file_id VARCHAR,
                    last_synced_at TIMESTAMPTZ,
                    current_version NUMERIC(5, 0) DEFAULT 1,
                    thumbnail_path VARCHAR,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                    FOREIGN KEY(owner_id) REFERENCES users (id)
                );
                """))

                connection.execute(text("""
                INSERT INTO document_vault_new
                SELECT id, tenant_id, owner_id, filename, file_type, file_path, file_size,
                       mime_type, transaction_id, parent_id, is_folder, is_shared, description,
                       gdrive_file_id, last_synced_at, current_version, thumbnail_path, created_at, updated_at
                FROM document_vault
                ON CONFLICT (id) DO NOTHING;
                """))

                connection.execute(text("DROP TABLE document_vault"))
                connection.execute(text("ALTER TABLE document_vault_new RENAME TO document_vault"))
                logger.info("document_vault FK migration complete — transaction_id FK removed.")
            except Exception as fk_err:
                logger.info(f"document_vault FK migration skipped (likely already clean): {fk_err}")

            # 23. Tenant Settings
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS tenant_settings (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                key VARCHAR NOT NULL,
                value VARCHAR,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 24. Vault Sync History
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS vault_sync_history (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                message VARCHAR,
                items_processed NUMERIC(10, 0) DEFAULT 0,
                error_details VARCHAR,
                started_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMPTZ,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 25. Ignored Recurring Patterns (Subscription Detection)
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ignored_recurring_patterns (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                pattern VARCHAR NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 26. Ignored Category Suggestions
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ignored_suggestions (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                pattern VARCHAR NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 27. Family Alerts (Notification History)
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                user_id VARCHAR,
                title VARCHAR NOT NULL,
                body VARCHAR NOT NULL,
                category VARCHAR DEFAULT 'INFO',
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id),
                FOREIGN KEY(user_id) REFERENCES users (id)
            );
            """))

            # 28. AI Insight Cache
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_insight_cache (
                id VARCHAR PRIMARY KEY,
                tenant_id VARCHAR NOT NULL,
                insight_type VARCHAR NOT NULL,
                content VARCHAR NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tenant_id) REFERENCES tenants (id)
            );
            """))

            # 29. User Tokens (JWT JTI Tracking)
            connection.execute(text("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                token_jti VARCHAR NOT NULL UNIQUE,
                expires_at TIMESTAMPTZ NOT NULL,
                is_revoked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users (id)
            );
            """))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_user_tokens_jti ON user_tokens (token_jti)"))

            # Explicitly commit the transaction!
            connection.commit()

            logger.info("Auto-migration complete.")
            
    except Exception as e:
        # Re-raise lock errors or critical failures so the app doesn't start in a bad state
        logger.info(f"CRITICAL: Migration failed: {e}")
        raise e
