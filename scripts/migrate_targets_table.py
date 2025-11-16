#!/usr/bin/env python3
"""
Migrate the pharmacy_targets table to match the new schema:
- Rename target_date to date
- Add created_by_user_id column

Usage:
    python scripts/migrate_targets_table.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def migrate_targets_table():
    """Migrate the pharmacy_targets table to new schema"""
    
    print("=" * 60)
    print("MIGRATING PHARMACY_TARGETS TABLE")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Check current structure
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'pharma' 
                    AND table_name = 'pharmacy_targets'
                    ORDER BY ordinal_position
                """)
                columns = [row['column_name'] for row in cur.fetchall()]
                print(f"Current columns: {', '.join(columns)}")
                print()
                
                # Check if migration is needed
                needs_rename = 'target_date' in columns and 'date' not in columns
                needs_user_id = 'created_by_user_id' not in columns
                
                if not needs_rename and not needs_user_id:
                    print("✓ Table already matches the new schema")
                    print("  - Column 'date' exists")
                    print("  - Column 'created_by_user_id' exists")
                    return
                
                # Check for existing data
                cur.execute("SELECT COUNT(*) as count FROM pharma.pharmacy_targets")
                row_count = cur.fetchone()['count']
                
                if row_count > 0:
                    print(f"⚠️  Warning: Table contains {row_count} rows")
                    print("   Migration will preserve existing data")
                    print()
                
                # Step 1: Add created_by_user_id column if missing
                if needs_user_id:
                    print("Adding column 'created_by_user_id'...")
                    cur.execute("""
                        ALTER TABLE pharma.pharmacy_targets
                        ADD COLUMN IF NOT EXISTS created_by_user_id bigint 
                        REFERENCES pharma.users(user_id) ON DELETE SET NULL
                    """)
                    conn.commit()
                    print("✓ Column 'created_by_user_id' added")
                    print()
                
                # Step 2: Rename target_date to date if needed
                if needs_rename:
                    print("Renaming column 'target_date' to 'date'...")
                    # First, drop the unique constraint if it exists
                    cur.execute("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_schema = 'pharma' 
                        AND table_name = 'pharmacy_targets'
                        AND constraint_type = 'UNIQUE'
                    """)
                    constraints = [row['constraint_name'] for row in cur.fetchall()]
                    
                    for constraint_name in constraints:
                        print(f"  Dropping constraint '{constraint_name}'...")
                        cur.execute(f"ALTER TABLE pharma.pharmacy_targets DROP CONSTRAINT IF EXISTS {constraint_name}")
                    
                    # Rename the column
                    cur.execute("ALTER TABLE pharma.pharmacy_targets RENAME COLUMN target_date TO date")
                    
                    # Recreate the unique constraint
                    print("  Recreating unique constraint...")
                    cur.execute("""
                        ALTER TABLE pharma.pharmacy_targets
                        ADD CONSTRAINT pharmacy_targets_pharmacy_id_date_key 
                        UNIQUE (pharmacy_id, date)
                    """)
                    
                    conn.commit()
                    print("✓ Column renamed to 'date'")
                    print()
                
                # Step 3: Ensure indexes exist with correct names
                print("Checking indexes...")
                cur.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE schemaname = 'pharma' 
                    AND tablename = 'pharmacy_targets'
                """)
                existing_indexes = [row['indexname'] for row in cur.fetchall()]
                
                if 'idx_pharmacy_targets_pharmacy_date' not in existing_indexes:
                    print("  Creating index 'idx_pharmacy_targets_pharmacy_date'...")
                    cur.execute("""
                        CREATE INDEX idx_pharmacy_targets_pharmacy_date 
                        ON pharma.pharmacy_targets(pharmacy_id, date)
                    """)
                    conn.commit()
                    print("  ✓ Index created")
                else:
                    print("  ✓ Index 'idx_pharmacy_targets_pharmacy_date' exists")
                
                if 'idx_pharmacy_targets_date' not in existing_indexes:
                    print("  Creating index 'idx_pharmacy_targets_date'...")
                    cur.execute("""
                        CREATE INDEX idx_pharmacy_targets_date 
                        ON pharma.pharmacy_targets(date)
                    """)
                    conn.commit()
                    print("  ✓ Index created")
                else:
                    print("  ✓ Index 'idx_pharmacy_targets_date' exists")
                
                print()
                print("=" * 60)
                print("✓ MIGRATION COMPLETE!")
                print("=" * 60)
                print()
                print("The pharmacy_targets table is now ready to use.")
                print("You can now use the targets API endpoints:")
                print("  - GET /admin/pharmacies/{pharmacy_id}/targets")
                print("  - POST /admin/pharmacies/{pharmacy_id}/targets")
                print("  - DELETE /admin/pharmacies/{pharmacy_id}/targets/{date}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    migrate_targets_table()

