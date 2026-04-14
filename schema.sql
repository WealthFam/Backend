-- Auto-generated schema from Backend SQLAlchemy models
-- Unified Schema for DuckDB
-- Dialect: DuckDB

-- 1. Tenants & Users
CREATE TABLE IF NOT EXISTS tenants (
	id VARCHAR PRIMARY KEY,
	name VARCHAR NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	email VARCHAR UNIQUE NOT NULL,
	password_hash VARCHAR NOT NULL,
	full_name VARCHAR,
	avatar VARCHAR,
	role VARCHAR DEFAULT 'ADULT' NOT NULL,
	dob TIMESTAMP,
	pan_number VARCHAR,
	scopes VARCHAR,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS user_tokens (
	id VARCHAR PRIMARY KEY, 
	user_id VARCHAR NOT NULL, 
	token_jti VARCHAR UNIQUE NOT NULL, 
	expires_at TIMESTAMP NOT NULL, 
	is_revoked BOOLEAN DEFAULT FALSE, 
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS tenant_settings (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	key VARCHAR NOT NULL,
	value VARCHAR,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

-- 2. Finance Core
CREATE TABLE IF NOT EXISTS accounts (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	owner_id VARCHAR,
	name VARCHAR NOT NULL,
	type VARCHAR NOT NULL,
	currency VARCHAR DEFAULT 'INR',
	account_mask VARCHAR,
	balance NUMERIC(15, 2) DEFAULT 0.0,
	credit_limit NUMERIC(15, 2),
	last_synced_balance NUMERIC(15, 2),
	last_synced_at TIMESTAMP,
	last_synced_limit NUMERIC(15, 2),
	billing_day INTEGER,
	due_day INTEGER,
	is_verified BOOLEAN DEFAULT TRUE NOT NULL,
	import_config VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS categories (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	icon VARCHAR,
	color VARCHAR DEFAULT '#3B82F6',
	type VARCHAR DEFAULT 'expense',
	parent_id VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS loans (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	account_id VARCHAR NOT NULL UNIQUE,
	principal_amount NUMERIC(15, 2) NOT NULL,
	interest_rate NUMERIC(5, 2) NOT NULL,
	start_date TIMESTAMP NOT NULL,
	tenure_months INTEGER NOT NULL,
	emi_amount NUMERIC(15, 2) NOT NULL,
	emi_date INTEGER NOT NULL,
	loan_type VARCHAR DEFAULT 'OTHER' NOT NULL,
	bank_account_id VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS transactions (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	account_id VARCHAR NOT NULL,
	type VARCHAR NOT NULL DEFAULT 'DEBIT',
	amount NUMERIC(15, 2) NOT NULL,
	date TIMESTAMP NOT NULL,
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
	expense_group_id VARCHAR,
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	is_emi BOOLEAN DEFAULT FALSE NOT NULL,
	loan_id VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS expense_groups (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	description VARCHAR,
	is_active BOOLEAN DEFAULT TRUE NOT NULL,
	start_date TIMESTAMP,
	end_date TIMESTAMP,
	budget NUMERIC(15, 2) DEFAULT 0,
	icon VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

-- 3. Ingestion & Automation (Rules, Budgets, Recurring)
CREATE TABLE IF NOT EXISTS category_rules (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	category VARCHAR NOT NULL,
	keywords VARCHAR NOT NULL,
	priority INTEGER DEFAULT 0,
	is_transfer BOOLEAN DEFAULT FALSE NOT NULL,
	to_account_id VARCHAR,
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS budgets (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	category VARCHAR NOT NULL,
	amount_limit NUMERIC(15, 2) NOT NULL,
	period VARCHAR DEFAULT 'MONTHLY',
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS recurring_transactions (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	name VARCHAR NOT NULL,
	amount NUMERIC(15, 2) NOT NULL,
	type VARCHAR NOT NULL DEFAULT 'DEBIT',
	category VARCHAR,
	account_id VARCHAR NOT NULL,
	frequency VARCHAR DEFAULT 'MONTHLY' NOT NULL,
	start_date TIMESTAMP NOT NULL,
	next_run_date TIMESTAMP NOT NULL,
	is_active BOOLEAN DEFAULT TRUE NOT NULL,
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	last_run_date TIMESTAMP,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

-- 4. Mutual Funds
CREATE TABLE IF NOT EXISTS mutual_funds_meta (
	scheme_code VARCHAR PRIMARY KEY,
	scheme_name VARCHAR NOT NULL,
	isin_growth VARCHAR,
	isin_reinvest VARCHAR,
	fund_house VARCHAR,
	category VARCHAR,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

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
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

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
	FOREIGN KEY (tenant_id) REFERENCES tenants (id),
	FOREIGN KEY (goal_id) REFERENCES investment_goals (id)
);

CREATE TABLE IF NOT EXISTS mutual_fund_holdings (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	scheme_code VARCHAR NOT NULL,
	folio_number VARCHAR,
	units NUMERIC(15, 4) DEFAULT 0,
	average_price NUMERIC(15, 4) DEFAULT 0,
	current_value NUMERIC(15, 2) DEFAULT 0,
	last_nav NUMERIC(15, 4) DEFAULT 0,
	user_id VARCHAR,
	goal_id VARCHAR,
	last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id),
	FOREIGN KEY (scheme_code) REFERENCES mutual_funds_meta (scheme_code)
);

CREATE TABLE IF NOT EXISTS mutual_fund_orders (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	holding_id VARCHAR,
	scheme_code VARCHAR NOT NULL,
	type VARCHAR DEFAULT 'BUY',
	amount NUMERIC(15, 2) NOT NULL,
	units NUMERIC(15, 4) NOT NULL,
	nav NUMERIC(15, 4) NOT NULL,
	order_date TIMESTAMP NOT NULL,
	folio_number VARCHAR,
	status VARCHAR DEFAULT 'COMPLETED',
	external_id VARCHAR,
	import_source VARCHAR DEFAULT 'MANUAL',
	user_id VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS portfolio_timeline_cache (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	snapshot_date TIMESTAMP NOT NULL,
	portfolio_hash VARCHAR NOT NULL,
	portfolio_value NUMERIC(15, 2) NOT NULL,
	invested_value NUMERIC(15, 2) NOT NULL,
	benchmark_value NUMERIC(15, 2),
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS mutual_fund_sync_logs (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	completed_at TIMESTAMP,
	status VARCHAR DEFAULT 'running',
	num_funds_updated INTEGER DEFAULT 0,
	error_message VARCHAR,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

-- 5. Ingestion Configuration
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
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS email_sync_logs (
	id VARCHAR PRIMARY KEY,
	config_id VARCHAR NOT NULL,
	tenant_id VARCHAR NOT NULL,
	started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	completed_at TIMESTAMP,
	status VARCHAR DEFAULT 'running',
	items_processed INTEGER DEFAULT 0,
	message VARCHAR,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS pending_transactions (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	account_id VARCHAR NOT NULL,
	amount NUMERIC(15, 2) NOT NULL,
	date TIMESTAMP NOT NULL,
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
	expense_group_id VARCHAR,
	exclude_from_reports BOOLEAN DEFAULT FALSE NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS unparsed_messages (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	source VARCHAR NOT NULL,
	raw_content VARCHAR NOT NULL,
	content_hash VARCHAR,
	subject VARCHAR,
	sender VARCHAR,
	latitude DECIMAL(10, 8),
	longitude DECIMAL(11, 8),
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS parsing_patterns (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	pattern_type VARCHAR DEFAULT 'regex',
	pattern_value VARCHAR NOT NULL,
	mapping_config VARCHAR NOT NULL,
	is_active BOOLEAN DEFAULT TRUE,
	description VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

-- 6. AI & Mobile
CREATE TABLE IF NOT EXISTS ai_configurations (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	provider VARCHAR DEFAULT 'gemini',
	model_name VARCHAR DEFAULT 'gemini-pro',
	api_key VARCHAR,
	is_enabled BOOLEAN DEFAULT TRUE,
	prompts_json VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS ai_call_cache (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	content_hash VARCHAR NOT NULL,
	provider VARCHAR NOT NULL,
	model_name VARCHAR NOT NULL,
	response_json VARCHAR NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS mobile_devices (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	user_id VARCHAR,
	device_name VARCHAR NOT NULL,
	device_id VARCHAR UNIQUE NOT NULL,
	fcm_token VARCHAR,
	is_approved BOOLEAN DEFAULT FALSE,
	is_enabled BOOLEAN DEFAULT TRUE,
	is_ignored BOOLEAN DEFAULT FALSE,
	last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS ingestion_events (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	device_id VARCHAR,
	event_type VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	message VARCHAR,
	data_json VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS spam_filters (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	sender VARCHAR,
	subject VARCHAR,
	source VARCHAR,
	count_blocked INTEGER DEFAULT 0,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS ai_insight_cache (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	insight_type VARCHAR NOT NULL,
	content VARCHAR NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

-- 7. Document Vault
CREATE TABLE IF NOT EXISTS document_vault (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	owner_id VARCHAR,
	filename VARCHAR NOT NULL,
	file_type VARCHAR DEFAULT 'OTHER',
	file_path VARCHAR,
	file_size NUMERIC(15, 0) DEFAULT 0,
	mime_type VARCHAR,
	thumbnail_path VARCHAR,
	transaction_id VARCHAR,
	parent_id VARCHAR,
	is_folder BOOLEAN DEFAULT FALSE NOT NULL,
	is_shared BOOLEAN DEFAULT TRUE NOT NULL,
	description VARCHAR,
	gdrive_file_id VARCHAR,
	last_synced_at TIMESTAMP,
	current_version INTEGER DEFAULT 1,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS document_versions (
	id VARCHAR PRIMARY KEY,
	document_id VARCHAR NOT NULL,
	version_number INTEGER NOT NULL,
	file_path VARCHAR NOT NULL,
	file_size NUMERIC(15, 0) NOT NULL,
	filename VARCHAR NOT NULL,
	thumbnail_path VARCHAR,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vault_sync_history (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	message VARCHAR,
	items_processed INTEGER DEFAULT 0,
	error_details VARCHAR,
	started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	completed_at TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

-- 8. Notifications & Settings
CREATE TABLE IF NOT EXISTS alerts (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	user_id VARCHAR,
	title VARCHAR NOT NULL,
	body VARCHAR NOT NULL,
	category VARCHAR DEFAULT 'INFO',
	icon VARCHAR,
	is_read BOOLEAN DEFAULT FALSE,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	expires_at TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS app_settings (
	id VARCHAR PRIMARY KEY,
	tenant_id VARCHAR NOT NULL,
	key VARCHAR NOT NULL,
	value VARCHAR NOT NULL,
	updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (tenant_id) REFERENCES tenants (id),
	UNIQUE(tenant_id, key)
);

-- 9. Migration History
CREATE TABLE IF NOT EXISTS migration_history (
	version_id VARCHAR PRIMARY KEY,
	applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);