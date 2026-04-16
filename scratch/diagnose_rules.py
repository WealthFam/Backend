import json
import duckdb
import os

db_path = r"c:\Users\oksbw\.gemini\antigravity\scratch\data\family_finance_v3.duckdb"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = duckdb.connect(db_path)
try:
    print("Checking category_rules table...")
    rules = conn.execute("SELECT id, name, keywords, tenant_id FROM category_rules").fetchall()
    
    broken_count = 0
    for row in rules:
        rid, name, keywords, tenant_id = row
        try:
            json.loads(keywords)
        except Exception as e:
            print(f"\n[BROKEN RULE FOUND]")
            print(f"ID: {rid}")
            print(f"Name: {name}")
            print(f"Keywords: '{keywords}'")
            print(f"Error: {e}")
            broken_count += 1
            
    if broken_count == 0:
        print("\nNo broken JSON found in category_rules keywords.")
    else:
        print(f"\nTotal broken rules: {broken_count}")

finally:
    conn.close()
