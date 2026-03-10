import duckdb
import os
import sys
import shutil

def vacuum(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    
    print(f"\n{'='*40}")
    print(f"Shrinking {path}...")
    size_before = os.path.getsize(path)
    
    export_dir = path + "_export"
    rebuild_path = path + ".rebuild"
    
    try:
        # 1. Setup clean export directory
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir)
        os.makedirs(export_dir)
        
        if os.path.exists(rebuild_path): 
            os.remove(rebuild_path)
        
        # 2. Export the database to Parquet files
        print(f"  Exporting to {export_dir}...")
        try:
            con = duckdb.connect(path, read_only=True)
            con.execute(f"EXPORT DATABASE '{export_dir}' (FORMAT PARQUET);")
            con.close()
        except Exception as conn_err:
            print(f"  FAILED to connect to {path}. Usually indicates WAL corruption.")
            print(f"  Error details: {conn_err}")
            raise conn_err
        
        # 3. Import into a fresh new database file to eliminate fragmentation
        print(f"  Importing into new file: {rebuild_path}...")
        con = duckdb.connect(rebuild_path)
        con.execute(f"IMPORT DATABASE '{export_dir}';")
        con.close()
        
        # 4. Final verification and swap
        size_after = os.path.getsize(rebuild_path)
        reduction = (size_before - size_after) / (1024 * 1024)
        print(f"  Success!")
        print(f"  Size Reduction: {size_before/1024/1024:.1f}MB -> {size_after/1024/1024:.1f}MB")
        print(f"  Reclaimed space: {reduction:.1f}MB")
        
        # Swap the old bloated file with the new clean one
        os.replace(rebuild_path, path)
        print("  Database file swapped successfully.")
        
        # Cleanup temporary export artifacts
        shutil.rmtree(export_dir)

    except Exception as e:
        print(f"  ERROR during vacuum of {path}: {e}")
        # Clean up partial work on failure to avoid leaving junk
        if os.path.exists(rebuild_path): os.remove(rebuild_path)
        if os.path.exists(export_dir): shutil.rmtree(export_dir)

if __name__ == "__main__":
    # Check environment variables first (for containerized environments)
    # Strip 'duckdb:///' prefix if present
    env_targets = [
        os.environ.get('PARSER_DATABASE_URL', '').replace('duckdb:///', ''),
        os.environ.get('APP_DATABASE_URL', '').replace('duckdb:///', '')
    ]
    
    # Filter out empty or common defaults
    env_targets = [t for t in env_targets if t and t.endswith('.duckdb')]
    
    if env_targets:
        targets = env_targets
    else:
        # Fallback to standard local paths
        targets = [
            'data/ingestion_engine_parser.duckdb',
            'data/family_finance_v3.duckdb'
        ]
    
    for target in targets:
        # Ensure path is absolute if it starts with /
        vacuum(target)
    
    print("\nMaintenance Complete.")
