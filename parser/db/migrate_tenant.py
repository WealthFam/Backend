from sqlalchemy.engine import Engine
from sqlalchemy import text

def migrate_to_single_tenant(parser_engine: Engine):
    """
    Migration script to auto-map 'system_tenant' records in the parser DB
    to the single active tenant ID.
    
    Instead of connecting to the main backend DB (which causes DuckDB lock errors),
    this queries the parser DB itself. Once the user performs any action (like 
    parsing a file or syncing an email), their real tenant_id is saved. 
    This script finds that single real tenant_id and retroactively applies it 
    to all old data.
    """
    print("Checking for single-tenant migration within Parser DB...")
                
    try:
        with parser_engine.connect() as parser_conn:
            # 1. Find if there's exactly ONE real tenant_id in request_logs or pattern_rules
            # We skip 'system_tenant' and nulls
            query = text("""
                SELECT DISTINCT tenant_id 
                FROM request_logs 
                WHERE tenant_id IS NOT NULL AND tenant_id != 'system_tenant'
                UNION
                SELECT DISTINCT tenant_id 
                FROM pattern_rules 
                WHERE tenant_id IS NOT NULL AND tenant_id != 'system_tenant'
            """)
            
            results = parser_conn.execute(query).fetchall()
            
            if not results:
                print("Skipping tenant migration: No real tenant ID found yet. (Perform an action in the app first).")
                return
                
            if len(results) > 1:
                print("Skipping tenant migration: Multiple tenants found. This script is only for single-tenant environments.")
                return
                
            single_tenant_id = results[0][0]
            print(f"Found active tenant ID in Parser DB: {single_tenant_id}")

            # 2. Update all parser tables
            tables_to_update = [
                "request_logs", 
                "file_parsing_configs", 
                "ai_configs", 
                "pattern_rules", 
                "merchant_aliases",
                "ai_call_cache"
            ]
            
            updated_count = 0
            for table in tables_to_update:
                try:
                    res = parser_conn.execute(
                        text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id = 'system_tenant' OR tenant_id IS NULL"), 
                        {"tid": single_tenant_id}
                    )
                    if res.rowcount > 0:
                        updated_count += 1
                        print(f"  Updated {res.rowcount} rows in {table}")
                except Exception as e:
                    print(f"  Warning: could not update {table}: {e}")
                    
            parser_conn.commit()
            if updated_count > 0:
                print(f"Successfully migrated data to tenant '{single_tenant_id}'.")
            else:
                print("No old 'system_tenant' data needed migration.")
            
    except Exception as e:
        print(f"Error during tenant migration: {e}")
