#!/usr/bin/env python3
"""
Create the pharmacy_targets table if it doesn't exist.

Usage:
    python scripts/create_targets_table.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def create_targets_table():
    """Create the pharmacy_targets table if it doesn't exist"""
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS pharma.pharmacy_targets (
      id                bigserial PRIMARY KEY,
      pharmacy_id       integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
      date              date NOT NULL,
      target_value      numeric(12, 2) NOT NULL CHECK (target_value >= 0),
      created_at        timestamptz NOT NULL DEFAULT now(),
      updated_at        timestamptz NOT NULL DEFAULT now(),
      created_by_user_id bigint REFERENCES pharma.users(user_id) ON DELETE SET NULL,
      UNIQUE(pharmacy_id, date)
    );
    """
    
    create_indexes_sql = """
    CREATE INDEX IF NOT EXISTS idx_pharmacy_targets_pharmacy_date ON pharma.pharmacy_targets(pharmacy_id, date);
    CREATE INDEX IF NOT EXISTS idx_pharmacy_targets_date ON pharma.pharmacy_targets(date);
    """
    
    check_table_sql = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'pharma' 
        AND table_name = 'pharmacy_targets'
    );
    """
    
    print("=" * 60)
    print("CREATING PHARMACY_TARGETS TABLE")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Check if table already exists
                cur.execute(check_table_sql)
                result = cur.fetchone()
                table_exists = result[0] if isinstance(result, tuple) else result['exists']
                
                if table_exists:
                    print("✓ Table 'pharma.pharmacy_targets' already exists")
                    print()
                    print("Checking indexes...")
                    
                    # Check indexes
                    cur.execute("""
                        SELECT indexname 
                        FROM pg_indexes 
                        WHERE schemaname = 'pharma' 
                        AND tablename = 'pharmacy_targets'
                    """)
                    existing_indexes = [row['indexname'] if isinstance(row, dict) else row[0] for row in cur.fetchall()]
                    
                    if 'idx_pharmacy_targets_pharmacy_date' in existing_indexes:
                        print("✓ Index 'idx_pharmacy_targets_pharmacy_date' exists")
                    else:
                        print("⚠ Creating missing index 'idx_pharmacy_targets_pharmacy_date'...")
                        cur.execute("CREATE INDEX idx_pharmacy_targets_pharmacy_date ON pharma.pharmacy_targets(pharmacy_id, date);")
                        conn.commit()
                        print("✓ Index created")
                    
                    if 'idx_pharmacy_targets_date' in existing_indexes:
                        print("✓ Index 'idx_pharmacy_targets_date' exists")
                    else:
                        print("⚠ Creating missing index 'idx_pharmacy_targets_date'...")
                        cur.execute("CREATE INDEX idx_pharmacy_targets_date ON pharma.pharmacy_targets(date);")
                        conn.commit()
                        print("✓ Index created")
                    
                    print()
                    print("Table is ready to use!")
                    return
                
                # Create table
                print("Creating table 'pharma.pharmacy_targets'...")
                cur.execute(create_table_sql)
                conn.commit()
                print("✓ Table created successfully")
                
                # Create indexes
                print()
                print("Creating indexes...")
                cur.execute(create_indexes_sql)
                conn.commit()
                print("✓ Indexes created successfully")
                
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
    create_targets_table()

