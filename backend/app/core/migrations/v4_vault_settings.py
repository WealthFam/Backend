from sqlalchemy import text

def apply(connection, helpers):
    """v4: Document Vault and App Settings"""
    rebuild_table = helpers['rebuild_table']
    safe_add_column = helpers['safe_add_column']
    
    # 1. Expense Group Integration in Transactions
    safe_add_column("transactions", "expense_group_id", "VARCHAR")
    safe_add_column("pending_transactions", "expense_group_id", "VARCHAR")

    # 2. Alerts Icon Fix
    alert_cols = ["id", "tenant_id", "user_id", "title", "body", "category", "icon", "is_read", "created_at", "expires_at"]
    rebuild_table("alerts", """CREATE TABLE IF NOT EXISTS alerts (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, user_id VARCHAR,
        title VARCHAR NOT NULL, body VARCHAR NOT NULL, category VARCHAR DEFAULT 'INFO',
        icon VARCHAR, is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    )""", alert_cols)

    # 3. Document Vault Rebuild
    vault_cols = ["id", "tenant_id", "owner_id", "filename", "file_type", "file_path", "file_size", "mime_type", "thumbnail_path", "transaction_id", "parent_id", "is_folder", "is_shared", "description", "gdrive_file_id", "last_synced_at", "current_version", "created_at", "updated_at"]
    rebuild_table("document_vault", """CREATE TABLE IF NOT EXISTS document_vault (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, owner_id VARCHAR,
        filename VARCHAR NOT NULL, file_type VARCHAR DEFAULT 'OTHER', file_path VARCHAR,
        file_size NUMERIC(15, 0) DEFAULT 0, mime_type VARCHAR, thumbnail_path VARCHAR,
        transaction_id VARCHAR, parent_id VARCHAR, is_folder BOOLEAN DEFAULT FALSE,
        is_shared BOOLEAN DEFAULT TRUE, description VARCHAR, gdrive_file_id VARCHAR,
        last_synced_at TIMESTAMP, current_version INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    )""", vault_cols)

    # 4. Vault Utility Tables
    connection.execute(text("""
    CREATE TABLE IF NOT EXISTS document_versions (
        id VARCHAR PRIMARY KEY, document_id VARCHAR NOT NULL, version_number INTEGER NOT NULL,
        file_path VARCHAR NOT NULL, file_size NUMERIC(15, 0) NOT NULL,
        filename VARCHAR NOT NULL, thumbnail_path VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS vault_sync_history (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, status VARCHAR NOT NULL,
        message VARCHAR, items_processed INTEGER DEFAULT 0, error_details VARCHAR,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    """))

    # 5. Misc Tables
    connection.execute(text("""
    CREATE TABLE IF NOT EXISTS expense_groups (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, name VARCHAR NOT NULL,
        description VARCHAR, is_active BOOLEAN DEFAULT TRUE NOT NULL,
        start_date TIMESTAMP, end_date TIMESTAMP, budget NUMERIC(15, 2) DEFAULT 0,
        icon VARCHAR, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id)
    );
    CREATE TABLE IF NOT EXISTS app_settings (
        id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, key VARCHAR NOT NULL,
        value VARCHAR NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(tenant_id) REFERENCES tenants (id), UNIQUE(tenant_id, key)
    );
    """))
