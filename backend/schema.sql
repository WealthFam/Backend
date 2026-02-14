-- Auto-generated schema from Backend SQLAlchemy models
-- Dialect: DuckDB (compatible with PostgreSQL syntax mostly)

-- 1. Tenants & Users
CREATE TABLE tenants (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	full_name VARCHAR,
	avatar VARCHAR,
	role VARCHAR DEFAULT 'ADULT' NOT NULL, 
	dob DATE,
	pan_number VARCHAR,
	scopes VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_user_tenant ON users (tenant_id);

-- 2. Finance Core
CREATE TABLE accounts (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	owner_id VARCHAR, 
	name VARCHAR NOT NULL, 
	type VARCHAR NOT NULL, 
	currency VARCHAR NOT NULL, 
	account_mask VARCHAR,
	balance NUMERIC(15, 2) DEFAULT 0.0,
	credit_limit NUMERIC(15, 2),
	last_synced_balance NUMERIC(15, 2),
	last_synced_at TIMESTAMP WITHOUT TIME ZONE,
	last_synced_limit NUMERIC(15, 2),
	billing_day NUMERIC(2, 0),
	due_day NUMERIC(2, 0),
	is_verified BOOLEAN DEFAULT TRUE NOT NULL,
	import_config VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);
CREATE INDEX ix_accounts_tenant_owner ON accounts (tenant_id, owner_id);

CREATE TABLE categories (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	icon VARCHAR, 
	color VARCHAR DEFAULT '#3B82F6',
	type VARCHAR DEFAULT 'expense',
	parent_id VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(parent_id) REFERENCES categories (id)
);

CREATE TABLE loans (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	account_id VARCHAR NOT NULL, 
	principal_amount NUMERIC(15, 2) NOT NULL, 
	interest_rate NUMERIC(5, 2) NOT NULL, 
	start_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	tenure_months NUMERIC(5, 0) NOT NULL, 
	emi_amount NUMERIC(15, 2) NOT NULL, 
	emi_date NUMERIC(2, 0) NOT NULL, 
	loan_type VARCHAR DEFAULT 'OTHER' NOT NULL,
	bank_account_id VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id),
	UNIQUE(account_id)
);
CREATE INDEX ix_loans_tenant ON loans (tenant_id);

CREATE TABLE transactions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	account_id VARCHAR NOT NULL, 
	type VARCHAR NOT NULL DEFAULT 'DEBIT',
	amount NUMERIC(15, 2) NOT NULL, 
	date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	description VARCHAR, 
	recipient VARCHAR, 
	category VARCHAR, 
	tags VARCHAR, 
	external_id VARCHAR, 
	content_hash VARCHAR,
	is_transfer BOOLEAN DEFAULT FALSE NOT NULL,
	linked_transaction_id VARCHAR,
	source VARCHAR NOT NULL DEFAULT 'MANUAL',
	latitude DECIMAL(10, 8),
	longitude DECIMAL(11, 8),
	location_name VARCHAR,
	expense_group_id VARCHAR,
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	is_emi BOOLEAN DEFAULT FALSE NOT NULL,
	loan_id VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(loan_id) REFERENCES loans (id),
	FOREIGN KEY(expense_group_id) REFERENCES expense_groups (id)
);
CREATE INDEX ix_transactions_query ON transactions (tenant_id, account_id, date);
CREATE INDEX ix_transactions_category ON transactions (tenant_id, category);

-- Expense Groups
CREATE TABLE expense_groups (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR,
	is_active BOOLEAN DEFAULT TRUE NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    budget DECIMAL(15, 2) DEFAULT 0,
    icon VARCHAR,
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_expense_groups_tenant ON expense_groups (tenant_id);

-- 3. Ingestion & Automation (Rules, Budgets, Recurring)
CREATE TABLE category_rules (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	keywords VARCHAR NOT NULL, 
	priority NUMERIC(5, 0) DEFAULT 0, 
	is_transfer BOOLEAN DEFAULT FALSE NOT NULL,
	to_account_id VARCHAR,
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE TABLE budgets (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	amount_limit NUMERIC(15, 2) NOT NULL, 
	period VARCHAR DEFAULT 'MONTHLY', 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_budgets_lookup ON budgets (tenant_id, category);

CREATE TABLE recurring_transactions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	amount NUMERIC(15, 2) NOT NULL, 
	type VARCHAR NOT NULL DEFAULT 'DEBIT', 
	category VARCHAR, 
	account_id VARCHAR NOT NULL, 
	frequency VARCHAR DEFAULT 'MONTHLY' NOT NULL, 
	start_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	next_run_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_active BOOLEAN DEFAULT TRUE NOT NULL, 
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	last_run_date TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_recurring_lookup ON recurring_transactions (tenant_id, account_id, next_run_date);

-- 4. Mutual Funds
CREATE TABLE mutual_funds_meta (
	scheme_code VARCHAR NOT NULL, 
	scheme_name VARCHAR NOT NULL, 
	isin_growth VARCHAR, 
	isin_reinvest VARCHAR, 
	fund_house VARCHAR, 
	category VARCHAR, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (scheme_code)
);


CREATE TABLE investment_goals (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	target_amount NUMERIC(15, 2) NOT NULL, 
	target_date TIMESTAMP WITHOUT TIME ZONE, 
	icon VARCHAR DEFAULT '🎯', 
	color VARCHAR DEFAULT '#3b82f6', 
	is_completed BOOLEAN DEFAULT FALSE, 
	owner_id VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(owner_id) REFERENCES users (id)
);
CREATE INDEX ix_investment_goals_tenant ON investment_goals (tenant_id);

CREATE TABLE goal_assets (
    id VARCHAR NOT NULL,
    tenant_id VARCHAR NOT NULL,
    goal_id VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    name VARCHAR,
    manual_amount NUMERIC(15, 2),
    interest_rate NUMERIC(5, 2),
    linked_account_id VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY(tenant_id) REFERENCES tenants (id),
    FOREIGN KEY(goal_id) REFERENCES investment_goals (id),
    FOREIGN KEY(linked_account_id) REFERENCES accounts (id)
);
CREATE INDEX ix_goal_assets_lookup ON goal_assets (tenant_id, goal_id);

CREATE TABLE mutual_fund_holdings (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	scheme_code VARCHAR NOT NULL, 
	folio_number VARCHAR, 
	units NUMERIC(15, 4) DEFAULT 0, 
	average_price NUMERIC(15, 4) DEFAULT 0, 
	current_value NUMERIC(15, 2), 
	last_nav NUMERIC(15, 4), 
	user_id VARCHAR,
	goal_id VARCHAR,
	last_updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(scheme_code) REFERENCES mutual_funds_meta (scheme_code),
	FOREIGN KEY(user_id) REFERENCES users (id),
	FOREIGN KEY(goal_id) REFERENCES investment_goals (id)
);
CREATE INDEX ix_mf_holdings_lookup ON mutual_fund_holdings (tenant_id, scheme_code);

CREATE TABLE mutual_fund_orders (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	holding_id VARCHAR, 
	scheme_code VARCHAR NOT NULL, 
	type VARCHAR DEFAULT 'BUY' NOT NULL, 
	amount NUMERIC(15, 2) NOT NULL, 
	units NUMERIC(15, 4) NOT NULL, 
	nav NUMERIC(15, 4) NOT NULL, 
	order_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	folio_number VARCHAR,
	status VARCHAR DEFAULT 'COMPLETED', 
	external_id VARCHAR, 
	import_source VARCHAR DEFAULT 'MANUAL', 
	user_id VARCHAR,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(scheme_code) REFERENCES mutual_funds_meta (scheme_code),
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE INDEX ix_mf_orders_lookup ON mutual_fund_orders (tenant_id, scheme_code, order_date);
CREATE INDEX ix_mf_orders_folio ON mutual_fund_orders (folio_number);

CREATE TABLE portfolio_timeline_cache (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	snapshot_date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	portfolio_hash VARCHAR NOT NULL, 
	portfolio_value NUMERIC(15, 2) NOT NULL, 
	invested_value NUMERIC(15, 2) NOT NULL, 
	benchmark_value NUMERIC(15, 2), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_timeline_cache_lookup ON portfolio_timeline_cache (tenant_id, portfolio_hash, snapshot_date);

-- 5. Email & Ingestion Configuration
CREATE TABLE email_configurations (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	password VARCHAR NOT NULL, 
	imap_server VARCHAR DEFAULT 'imap.gmail.com', 
	folder VARCHAR DEFAULT 'INBOX', 
	is_active BOOLEAN DEFAULT TRUE, 
	auto_sync_enabled BOOLEAN DEFAULT FALSE, 
	last_sync_at TIMESTAMP WITHOUT TIME ZONE, 
	cas_last_sync_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_email_configs_tenant ON email_configurations (tenant_id);

CREATE TABLE email_sync_logs (
	id VARCHAR NOT NULL, 
	config_id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	status VARCHAR DEFAULT 'running', 
	items_processed NUMERIC(10, 0) DEFAULT 0, 
	message VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(config_id) REFERENCES email_configurations (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_email_logs_lookup ON email_sync_logs (tenant_id, config_id);

CREATE TABLE pending_transactions (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	account_id VARCHAR NOT NULL, 
	amount NUMERIC(15, 2) NOT NULL, 
	date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	description VARCHAR, 
	recipient VARCHAR, 
	category VARCHAR, 
	source VARCHAR NOT NULL, 
	raw_message VARCHAR, 
	content_hash VARCHAR,
	external_id VARCHAR, 
	is_transfer BOOLEAN DEFAULT FALSE NOT NULL,
	to_account_id VARCHAR,
	balance_is_synced BOOLEAN DEFAULT FALSE NOT NULL,
	latitude DECIMAL(10, 8),
	longitude DECIMAL(11, 8),
	location_name VARCHAR,
	expense_group_id VARCHAR,
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(expense_group_id) REFERENCES expense_groups (id)
);
CREATE INDEX ix_pending_txns_lookup ON pending_transactions (tenant_id, account_id);

CREATE TABLE unparsed_messages (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	source VARCHAR NOT NULL, 
	raw_content VARCHAR NOT NULL, 
	content_hash VARCHAR,
	subject VARCHAR, 
	sender VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE TABLE parsing_patterns (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	pattern_type VARCHAR DEFAULT 'regex', 
	pattern_value VARCHAR NOT NULL, 
	mapping_config VARCHAR NOT NULL, 
	is_active BOOLEAN DEFAULT TRUE, 
	description VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

-- 6. AI & Mobile
CREATE TABLE ai_configurations (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	provider VARCHAR DEFAULT 'gemini', 
	model_name VARCHAR DEFAULT 'gemini-pro', 
	api_key VARCHAR, 
	is_enabled BOOLEAN DEFAULT TRUE, 
	prompts_json VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE TABLE ai_call_cache (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	content_hash VARCHAR NOT NULL, 
	provider VARCHAR NOT NULL, 
	model_name VARCHAR NOT NULL, 
	response_json VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_ai_call_cache_content_hash ON ai_call_cache (content_hash);

CREATE TABLE mobile_devices (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
    user_id VARCHAR,
	device_name VARCHAR NOT NULL, 
	device_id VARCHAR NOT NULL, 
	fcm_token VARCHAR, 
	is_approved BOOLEAN DEFAULT FALSE, 
	is_enabled BOOLEAN DEFAULT TRUE, 
	is_ignored BOOLEAN DEFAULT FALSE, 
	last_seen_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
    FOREIGN KEY(user_id) REFERENCES users (id),
    UNIQUE(device_id)
);
CREATE INDEX ix_mobile_devices_tenant ON mobile_devices (tenant_id);

CREATE TABLE ingestion_events (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	device_id VARCHAR, 
	event_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	message VARCHAR, 
	data_json TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_ingestion_events_tenant_device ON ingestion_events (tenant_id, device_id);

CREATE TABLE ignored_patterns (
	id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	pattern VARCHAR NOT NULL, 
	source VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_ignored_patterns_tenant ON ignored_patterns (tenant_id);
CREATE TABLE balance_snapshots (
	id VARCHAR NOT NULL, 
	account_id VARCHAR NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	balance NUMERIC(15, 2) NOT NULL, 
	timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	source VARCHAR DEFAULT 'MANUAL', 
	PRIMARY KEY (id), 
	FOREIGN KEY(account_id) REFERENCES accounts (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);
CREATE INDEX ix_balance_snapshots_account ON balance_snapshots (account_id);
CREATE INDEX ix_balance_snapshots_tenant ON balance_snapshots (tenant_id);
