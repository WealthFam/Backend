from sqlalchemy import text

def apply(connection, helpers):
    """v2: GPS Features and SMS Triage"""
    safe_add_column = helpers['safe_add_column']

    # 1. Unparsed Messages table (Ensuring GPS columns exist)
    connection.execute(text("""
    CREATE TABLE IF NOT EXISTS unparsed_messages (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, source VARCHAR NOT NULL,
        raw_content VARCHAR NOT NULL, content_hash VARCHAR, subject VARCHAR,
        sender VARCHAR, latitude DECIMAL(10, 8), longitude DECIMAL(11, 8),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    """))
    # Fail-safe adds
    safe_add_column("unparsed_messages", "latitude", "DECIMAL(10, 8)")
    safe_add_column("unparsed_messages", "longitude", "DECIMAL(11, 8)")

    # 2. Transaction Extensions (GPS, Reporting, Source)
    safe_add_column("transactions", "latitude", "DECIMAL(10, 8)")
    safe_add_column("transactions", "longitude", "DECIMAL(11, 8)")
    safe_add_column("transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")
    safe_add_column("transactions", "source", "VARCHAR DEFAULT 'MANUAL'")
    safe_add_column("transactions", "is_transfer", "BOOLEAN DEFAULT FALSE")
    safe_add_column("transactions", "linked_transaction_id", "VARCHAR")

    # 3. Pending Transactions extensions
    safe_add_column("pending_transactions", "latitude", "DECIMAL(10, 8)")
    safe_add_column("pending_transactions", "longitude", "DECIMAL(11, 8)")
    safe_add_column("pending_transactions", "is_transfer", "BOOLEAN DEFAULT FALSE")
    safe_add_column("pending_transactions", "to_account_id", "VARCHAR")
    safe_add_column("pending_transactions", "balance_is_synced", "BOOLEAN DEFAULT FALSE")
    safe_add_column("pending_transactions", "exclude_from_reports", "BOOLEAN DEFAULT FALSE")

    # 4. Parsing Helpers
    connection.execute(text("""
    CREATE TABLE IF NOT EXISTS parsing_patterns (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL,
        pattern_type VARCHAR DEFAULT 'regex', pattern_value VARCHAR NOT NULL,
        mapping_config VARCHAR NOT NULL, is_active BOOLEAN DEFAULT TRUE,
        description VARCHAR, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS ai_configurations (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL,
        provider VARCHAR DEFAULT 'gemini', model_name VARCHAR DEFAULT 'gemini-pro',
        api_key VARCHAR, is_enabled BOOLEAN DEFAULT TRUE,
        prompts_json VARCHAR, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    """))
