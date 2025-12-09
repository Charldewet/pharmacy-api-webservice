#!/usr/bin/env python3
"""
Verify that the accounts table is correctly set up with all data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def verify_table_structure(conn):
    """Verify the accounts table structure"""
    print("=" * 70)
    print("VERIFYING TABLE STRUCTURE")
    print("=" * 70)
    print()
    
    with conn.cursor() as cur:
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'pharma' 
                AND table_name = 'accounts'
            )
        """)
        table_exists = cur.fetchone()['exists']
        
        if not table_exists:
            print("❌ Table 'pharma.accounts' does not exist!")
            return False
        
        print("✓ Table 'pharma.accounts' exists")
        
        # Check columns
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'pharma' 
            AND table_name = 'accounts'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        print("\nTable columns:")
        expected_columns = {
            'id', 'code', 'name', 'type', 'category', 'parent_account_id',
            'is_active', 'display_order', 'notes', 'created_at', 'updated_at'
        }
        actual_columns = {col['column_name'] for col in columns}
        
        for col in columns:
            marker = "✓" if col['column_name'] in expected_columns else "?"
            print(f"  {marker} {col['column_name']:20} {col['data_type']:20} nullable={col['is_nullable']}")
        
        missing = expected_columns - actual_columns
        if missing:
            print(f"\n❌ Missing columns: {missing}")
            return False
        
        # Check enum type
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM pg_type 
                WHERE typname = 'account_type'
                AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pharma')
            )
        """)
        enum_exists = cur.fetchone()['exists']
        
        if enum_exists:
            print("\n✓ Enum type 'pharma.account_type' exists")
            
            # Check enum values
            cur.execute("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = (
                    SELECT oid FROM pg_type 
                    WHERE typname = 'account_type'
                    AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pharma')
                )
                ORDER BY enumsortorder
            """)
            enum_values = [row['enumlabel'] for row in cur.fetchall()]
            print(f"  Enum values: {', '.join(enum_values)}")
        else:
            print("\n❌ Enum type 'pharma.account_type' does not exist!")
            return False
        
        # Check indexes
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'pharma' 
            AND tablename = 'accounts'
            ORDER BY indexname
        """)
        indexes = [row['indexname'] for row in cur.fetchall()]
        
        print(f"\n✓ Found {len(indexes)} indexes:")
        for idx in indexes:
            print(f"  - {idx}")
        
        # Check trigger
        cur.execute("""
            SELECT tgname 
            FROM pg_trigger 
            WHERE tgrelid = (
                SELECT oid FROM pg_class 
                WHERE relname = 'accounts' 
                AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pharma')
            )
            AND tgisinternal = false
        """)
        triggers = [row['tgname'] for row in cur.fetchall()]
        
        print(f"\n✓ Found {len(triggers)} triggers:")
        for trig in triggers:
            print(f"  - {trig}")
        
        print()
        return True


def verify_account_data(conn):
    """Verify account data"""
    print("=" * 70)
    print("VERIFYING ACCOUNT DATA")
    print("=" * 70)
    print()
    
    with conn.cursor() as cur:
        # Total count
        cur.execute("SELECT COUNT(*) as total FROM pharma.accounts")
        total = cur.fetchone()['total']
        print(f"Total accounts: {total}")
        
        # Count by type
        cur.execute("""
            SELECT type::text as account_type, COUNT(*) as count
            FROM pharma.accounts
            GROUP BY type
            ORDER BY type
        """)
        type_counts = cur.fetchall()
        
        print("\nAccounts by type:")
        for row in type_counts:
            print(f"  {row['account_type']:20} {row['count']:3}")
        
        # Count by category
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM pharma.accounts
            GROUP BY category
            ORDER BY count DESC
            LIMIT 10
        """)
        category_counts = cur.fetchall()
        
        print("\nTop categories:")
        for row in category_counts:
            print(f"  {row['category']:30} {row['count']:3}")
        
        # Sample accounts from each major type
        print("\nSample accounts:")
        for account_type in ['ASSET', 'INCOME', 'COGS', 'EXPENSE', 'LIABILITY', 'EQUITY']:
            cur.execute("""
                SELECT code, name, category
                FROM pharma.accounts
                WHERE type::text = %s
                ORDER BY display_order
                LIMIT 3
            """, (account_type,))
            samples = cur.fetchall()
            if samples:
                print(f"\n  {account_type}:")
                for s in samples:
                    print(f"    {s['code']} - {s['name']} ({s['category']})")
        
        # Check required core accounts
        print("\nRequired core accounts:")
        required = [
            ('4000', 'Sales – Dispensary', 'INCOME'),
            ('4010', 'Sales – Front Shop', 'INCOME'),
            ('5000', 'Cost of Sales – Merchandise', 'COGS'),
            ('6200', 'Salaries & Wages', 'EXPENSE'),
            ('6100', 'Rent – Premises', 'EXPENSE'),
            ('7000', 'Interest Paid – Loans', 'FINANCE_COST'),
        ]
        
        all_found = True
        for code, name, account_type in required:
            cur.execute("""
                SELECT code, name, type::text as type_str
                FROM pharma.accounts
                WHERE code = %s AND type::text = %s
            """, (code, account_type))
            account = cur.fetchone()
            if account:
                print(f"  ✓ {code} - {account['name']}")
            else:
                print(f"  ❌ {code} - {name} ({account_type}) - NOT FOUND")
                all_found = False
        
        print()
        return all_found


def main():
    """Main verification"""
    print()
    print("=" * 70)
    print("ACCOUNTS TABLE VERIFICATION")
    print("=" * 70)
    print()
    
    try:
        with get_conn() as conn:
            # Verify structure
            structure_ok = verify_table_structure(conn)
            if not structure_ok:
                print("❌ Structure verification failed!")
                sys.exit(1)
            
            # Verify data
            data_ok = verify_account_data(conn)
            if not data_ok:
                print("❌ Data verification failed!")
                sys.exit(1)
            
            print("=" * 70)
            print("✓ ALL VERIFICATIONS PASSED!")
            print("=" * 70)
            print()
            print("The accounts table is correctly set up and ready for use.")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

