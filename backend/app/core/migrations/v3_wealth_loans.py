from sqlalchemy import text

def apply(connection, helpers):
    """v3: Wealth Management and Loan Tracking"""
    rebuild_table = helpers['rebuild_table']
    safe_add_column = helpers['safe_add_column']
    
    # 1. Loan Integration in Transactions
    safe_add_column("transactions", "loan_id", "VARCHAR")
    safe_add_column("transactions", "is_emi", "BOOLEAN DEFAULT FALSE")

    # 2. Portfolio Rebuild (Ensuring all names match models.py)
    mf_cols = ["id", "tenant_id", "scheme_code", "folio_number", "units", "average_price", "current_value", "last_nav", "user_id", "goal_id", "last_updated_at"]
    
    # Fail-safe column rename for migration path
    existing_cols = [r[1] for r in connection.execute(text("PRAGMA table_info('mutual_fund_holdings')")).fetchall()]
    if "nav" in existing_cols and "last_nav" not in existing_cols:
        connection.execute(text("ALTER TABLE mutual_fund_holdings RENAME COLUMN nav TO last_nav"))
    if "last_updated" in existing_cols and "last_updated_at" not in existing_cols:
        connection.execute(text("ALTER TABLE mutual_fund_holdings RENAME COLUMN last_updated TO last_updated_at"))

    rebuild_table("mutual_fund_holdings", """CREATE TABLE IF NOT EXISTS mutual_fund_holdings (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, 
        scheme_code VARCHAR NOT NULL, folio_number VARCHAR,
        units NUMERIC(15, 4) DEFAULT 0, average_price NUMERIC(15, 4) DEFAULT 0,
        current_value NUMERIC(15, 2) DEFAULT 0, last_nav NUMERIC(15, 4) DEFAULT 0,
        user_id VARCHAR, goal_id VARCHAR, 
        last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    )""", mf_cols)

    connection.execute(text("""
    CREATE TABLE IF NOT EXISTS mutual_fund_orders (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, holding_id VARCHAR,
        scheme_code VARCHAR NOT NULL, type VARCHAR DEFAULT 'BUY',
        amount NUMERIC(15, 2) NOT NULL, units NUMERIC(15, 4) NOT NULL,
        nav NUMERIC(15, 4) NOT NULL, order_date TIMESTAMP NOT NULL,
        folio_number VARCHAR, status VARCHAR DEFAULT 'COMPLETED',
        external_id VARCHAR, import_source VARCHAR DEFAULT 'MANUAL',
        user_id VARCHAR, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS mutual_fund_sync_logs (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP,
        status VARCHAR DEFAULT 'running', num_funds_updated INTEGER DEFAULT 0,
        error_message VARCHAR, FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS investment_goals (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
        target_amount NUMERIC(15, 2) NOT NULL, target_date TIMESTAMP,
        icon VARCHAR DEFAULT '🎯', color VARCHAR DEFAULT '#3b82f6',
        is_completed BOOLEAN DEFAULT FALSE, owner_id VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS goal_assets (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, goal_id VARCHAR NOT NULL,
        type VARCHAR NOT NULL, name VARCHAR, manual_amount NUMERIC(15, 2),
        interest_rate NUMERIC(5, 2), linked_account_id VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id), FOREIGN KEY(goal_id) REFERENCES investment_goals (id)
    );
    CREATE TABLE IF NOT EXISTS portfolio_timeline_cache (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, snapshot_date TIMESTAMP NOT NULL,
        portfolio_hash VARCHAR NOT NULL, portfolio_value NUMERIC(15, 2) NOT NULL,
        invested_value NUMERIC(15, 2) NOT NULL, benchmark_value NUMERIC(15, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS loans (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, account_id VARCHAR NOT NULL UNIQUE,
        principal_amount NUMERIC(15, 2) NOT NULL, interest_rate NUMERIC(5, 2) NOT NULL,
        start_date TIMESTAMP NOT NULL, tenure_months INTEGER NOT NULL,
        emi_amount NUMERIC(15, 2) NOT NULL, emi_date INTEGER NOT NULL,
        loan_type VARCHAR DEFAULT 'OTHER' NOT NULL, bank_account_id VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    """))
