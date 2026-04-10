from sqlalchemy import text

def apply(connection, helpers):
    """v1: Baseline Core Schema - Comprehensive Audit"""
    
    connection.execute(text("""
    -- 1. Identity & Config
    CREATE TABLE IF NOT EXISTS tenants (
        id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, email VARCHAR UNIQUE NOT NULL,
        password_hash VARCHAR NOT NULL, full_name VARCHAR, avatar VARCHAR, 
        dob TIMESTAMP, pan_number VARCHAR, role VARCHAR DEFAULT 'ADULT',
        scopes VARCHAR, FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS user_tokens (
        id VARCHAR PRIMARY KEY, user_id VARCHAR NOT NULL, token_jti VARCHAR UNIQUE NOT NULL,
        expires_at TIMESTAMP NOT NULL, is_revoked BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users (id)
    );
    CREATE TABLE IF NOT EXISTS tenant_settings (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, key VARCHAR NOT NULL,
        value VARCHAR, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );

    -- 2. Financial Foundations
    CREATE TABLE IF NOT EXISTS accounts (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, owner_id VARCHAR,
        name VARCHAR NOT NULL, type VARCHAR NOT NULL, currency VARCHAR DEFAULT 'INR',
        account_mask VARCHAR, balance NUMERIC(15, 2) DEFAULT 0,
        credit_limit NUMERIC(15, 2), billing_day INTEGER, due_day INTEGER,
        is_verified BOOLEAN DEFAULT TRUE, import_config VARCHAR,
        last_synced_balance NUMERIC(15, 2), last_synced_at TIMESTAMP, last_synced_limit NUMERIC(15, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS balance_snapshots (
        id VARCHAR PRIMARY KEY, account_id VARCHAR NOT NULL, tenant_id VARCHAR NOT NULL,
        balance NUMERIC(15, 2) NOT NULL, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source VARCHAR DEFAULT 'MANUAL', FOREIGN KEY(account_id) REFERENCES accounts (id),
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS categories (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
        icon VARCHAR, color VARCHAR DEFAULT '#3B82F6', type VARCHAR DEFAULT 'expense',
        parent_id VARCHAR, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS budgets (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, category VARCHAR NOT NULL,
        amount_limit NUMERIC(15, 2) NOT NULL, period VARCHAR DEFAULT 'MONTHLY',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS category_rules (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
        category VARCHAR NOT NULL, keywords VARCHAR NOT NULL, priority INTEGER DEFAULT 0,
        is_transfer BOOLEAN DEFAULT FALSE, to_account_id VARCHAR, 
        exclude_from_reports BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );

    -- 3. Ingestion & Sync
    CREATE TABLE IF NOT EXISTS email_configurations (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, user_id VARCHAR,
        email VARCHAR NOT NULL, password VARCHAR NOT NULL, imap_server VARCHAR DEFAULT 'imap.gmail.com',
        folder VARCHAR DEFAULT 'INBOX', is_active BOOLEAN DEFAULT TRUE,
        auto_sync_enabled BOOLEAN DEFAULT FALSE, last_sync_at TIMESTAMP, 
        cas_last_sync_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS email_sync_logs (
        id VARCHAR PRIMARY KEY, config_id VARCHAR NOT NULL, tenant_id VARCHAR NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP,
        status VARCHAR DEFAULT 'running', items_processed INTEGER DEFAULT 0,
        message VARCHAR, FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS mobile_devices (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, user_id VARCHAR,
        device_name VARCHAR NOT NULL, device_id VARCHAR UNIQUE NOT NULL,
        fcm_token VARCHAR, is_approved BOOLEAN DEFAULT FALSE,
        is_enabled BOOLEAN DEFAULT TRUE, is_ignored BOOLEAN DEFAULT FALSE,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS ai_call_cache (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, content_hash VARCHAR NOT NULL,
        provider VARCHAR NOT NULL, model_name VARCHAR NOT NULL, response_json VARCHAR NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS ingestion_events (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, device_id VARCHAR,
        event_type VARCHAR NOT NULL, status VARCHAR NOT NULL, message VARCHAR,
        data_json VARCHAR, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS spam_filters (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, sender VARCHAR,
        subject VARCHAR, source VARCHAR, count_blocked INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );

    -- 4. Mutual Fund Metadata (Static)
    CREATE TABLE IF NOT EXISTS mutual_funds_meta (
        scheme_code VARCHAR PRIMARY KEY, scheme_name VARCHAR NOT NULL,
        isin_growth VARCHAR, isin_reinvest VARCHAR, fund_house VARCHAR,
        category VARCHAR, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """))
