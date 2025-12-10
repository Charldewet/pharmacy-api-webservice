#!/usr/bin/env python3
"""
Load and verify the management financials schema.
Adds report_category column to accounts table for P&L reporting.

Usage:
    python scripts/load_management_financials_schema.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def apply_schema(conn):
    """Apply the management financials schema"""
    print("Applying management financials schema...")
    
    schema_file = Path(__file__).parent.parent / "schema_management_financials.sql"
    
    if not schema_file.exists():
        print(f"❌ Error: Schema file not found at {schema_file}")
        return False
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    try:
        with conn.cursor() as cur:
            # Execute the schema SQL
            cur.execute(schema_sql)
            conn.commit()
        
        print("✓ Management financials schema applied successfully")
        print()
        return True
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False


def verify_schema(conn):
    """Verify that the report_category column exists"""
    print("Verifying schema...")
    
    with conn.cursor() as cur:
        # Check if report_category column exists
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'pharma'
              AND table_name = 'accounts'
              AND column_name = 'report_category'
        """)
        
        column = cur.fetchone()
        
        if column:
            print(f"✓ Column 'report_category' exists")
            print(f"  - Type: {column['data_type']}")
            print(f"  - Nullable: {column['is_nullable']}")
        else:
            print("❌ Column 'report_category' not found")
            return False
        
        # Check index
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'pharma'
              AND tablename = 'accounts'
              AND indexname = 'idx_accounts_report_category'
        """)
        
        index = cur.fetchone()
        
        if index:
            print(f"✓ Index 'idx_accounts_report_category' exists")
        else:
            print("⚠ Index 'idx_accounts_report_category' not found (optional)")
        
        print()
        return True


def main():
    """Main function"""
    print("=" * 60)
    print("MANAGEMENT FINANCIALS SCHEMA SETUP")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            if not apply_schema(conn):
                print("❌ Failed to apply schema")
                return 1
            
            if not verify_schema(conn):
                print("❌ Schema verification failed")
                return 1
            
            print("✅ Management financials schema setup complete!")
            print()
            print("Next steps:")
            print("1. Update accounts with report_category values:")
            print("   - revenue: Income accounts (4000-4999)")
            print("   - cogs: Cost of sales accounts (5000-5999)")
            print("   - expenses: Operating expense accounts (6000-6999)")
            print("   - other_income: Other income accounts (7500-7999)")
            print("   - other_expenses: Other expense accounts")
            print("2. Test the API endpoints:")
            print("   GET /pharmacies/{id}/management-statement?year=YYYY&month=MM")
            print("   GET /pharmacies/{id}/management-statement/trend?from=YYYY-MM&to=YYYY-MM")
            return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
