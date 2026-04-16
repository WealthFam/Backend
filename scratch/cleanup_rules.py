import json
import duckdb
import os

db_path = r"c:\Users\oksbw\.gemini\antigravity\scratch\data\family_finance_v3.duckdb"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = duckdb.connect(db_path)
try:
    print("Identifying broken category_rules...")
    rules = conn.execute("SELECT id, name, keywords FROM category_rules").fetchall()
    
    fixed_count = 0
    for row in rules:
        rid, name, keywords = row
        try:
            json.loads(keywords)
        except Exception:
            print(f"Fixing rule: {name} (ID: {rid})")
            print(f"  Old keywords: {keywords}")
            
            # Heuristic fix: if it looks like [Some Text], convert to ["Some Text"]
            new_keywords = "[]"
            if keywords.startswith("[") and keywords.endswith("]"):
                content = keywords[1:-1].strip()
                if content:
                    new_keywords = json.dumps([content])
            else:
                # If no brackets, maybe it's just raw text?
                if keywords.strip():
                    new_keywords = json.dumps([keywords.strip()])
            
            print(f"  New keywords: {new_keywords}")
            conn.execute("UPDATE category_rules SET keywords = ? WHERE id = ?", [new_keywords, rid])
            fixed_count += 1
            
    if fixed_count > 0:
        print(f"\nSuccessfully fixed {fixed_count} rules.")
    else:
        print("\nNo rules needed fixing (all are valid JSON).")

finally:
    conn.close()
