#!/usr/bin/env python3
"""
Load and verify the chart of accounts for PharmaSight Management Accounts.

This script:
1. Creates the accounts table if it doesn't exist
2. Loads the seed accounts data
3. Verifies that all required accounts exist
4. Checks for data integrity (unique codes, valid types, etc.)

Usage:
    python scripts/load_accounts.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

# Required core accounts that must exist
REQUIRED_CORE_ACCOUNTS = [
    ('4000', 'Sales – Dispensary', 'INCOME'),
    ('4010', 'Sales – Front Shop', 'INCOME'),
    ('5000', 'Cost of Sales – Merchandise', 'COGS'),
    ('6200', 'Salaries & Wages', 'EXPENSE'),
    ('6100', 'Rent – Premises', 'EXPENSE'),
    ('7000', 'Interest Paid – Loans', 'FINANCE_COST'),
]

VALID_ACCOUNT_TYPES = [
    'ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'COGS', 
    'EXPENSE', 'FINANCE_COST', 'OTHER_INCOME', 'TAX'
]


def create_accounts_table(conn):
    """Create the accounts table and enum type if they don't exist"""
    print("Creating accounts table and enum type...")
    
    with conn.cursor() as cur:
        # Create enum type if it doesn't exist
        cur.execute("""
            DO $$ BEGIN
                CREATE TYPE pharma.account_type AS ENUM (
                    'ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'COGS',
                    'EXPENSE', 'FINANCE_COST', 'OTHER_INCOME', 'TAX'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        
        # Create accounts table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pharma.accounts (
                id                bigserial PRIMARY KEY,
                code              varchar(10) NOT NULL UNIQUE,
                name              text NOT NULL,
                type              pharma.account_type NOT NULL,
                category          text NOT NULL,
                parent_account_id bigint REFERENCES pharma.accounts(id) ON DELETE SET NULL,
                is_active         boolean NOT NULL DEFAULT true,
                display_order     integer NOT NULL DEFAULT 0,
                notes             text,
                created_at        timestamptz NOT NULL DEFAULT now(),
                updated_at        timestamptz NOT NULL DEFAULT now()
            );
        """)
        
        # Create indexes
        indexes = [
            ("idx_accounts_code", "CREATE INDEX IF NOT EXISTS idx_accounts_code ON pharma.accounts(code)"),
            ("idx_accounts_type", "CREATE INDEX IF NOT EXISTS idx_accounts_type ON pharma.accounts(type)"),
            ("idx_accounts_category", "CREATE INDEX IF NOT EXISTS idx_accounts_category ON pharma.accounts(category)"),
            ("idx_accounts_parent", "CREATE INDEX IF NOT EXISTS idx_accounts_parent ON pharma.accounts(parent_account_id)"),
            ("idx_accounts_active", "CREATE INDEX IF NOT EXISTS idx_accounts_active ON pharma.accounts(is_active)"),
            ("idx_accounts_display_order", "CREATE INDEX IF NOT EXISTS idx_accounts_display_order ON pharma.accounts(display_order)"),
        ]
        
        for idx_name, idx_sql in indexes:
            cur.execute(idx_sql)
        
        # Create trigger function and trigger
        cur.execute("""
            CREATE OR REPLACE FUNCTION pharma.update_account_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        cur.execute("""
            DROP TRIGGER IF EXISTS trigger_update_account_updated_at ON pharma.accounts;
            CREATE TRIGGER trigger_update_account_updated_at
                BEFORE UPDATE ON pharma.accounts
                FOR EACH ROW
                EXECUTE FUNCTION pharma.update_account_updated_at();
        """)
        
        conn.commit()
        print("✓ Accounts table created successfully")
        print()


def load_seed_data(conn):
    """Load seed accounts data from seed_accounts.sql"""
    print("Loading seed accounts data...")
    
    seed_file = Path(__file__).parent.parent / "seed_accounts.sql"
    
    if not seed_file.exists():
        print(f"❌ Error: Seed file not found at {seed_file}")
        return False
    
    with open(seed_file, 'r') as f:
        seed_sql = f.read()
    
    try:
        with conn.cursor() as cur:
            cur.execute(seed_sql)
            conn.commit()
        
        print("✓ Seed data loaded successfully")
        print()
        return True
    except Exception as e:
        print(f"❌ Error loading seed data: {e}")
        conn.rollback()
        return False


def verify_accounts(conn):
    """Verify accounts data integrity"""
    print("Verifying accounts data...")
    print()
    
    issues = []
    
    with conn.cursor() as cur:
        # Check for duplicate codes
        cur.execute("""
            SELECT code, COUNT(*) as count
            FROM pharma.accounts
            GROUP BY code
            HAVING COUNT(*) > 1
        """)
        duplicates = cur.fetchall()
        if duplicates:
            issues.append(f"❌ Found duplicate account codes: {duplicates}")
        else:
            print("✓ All account codes are unique")
        
        # Check for invalid account types
        valid_types_str = "', '".join(VALID_ACCOUNT_TYPES)
        cur.execute(f"""
            SELECT code, name, type::text as type_str
            FROM pharma.accounts
            WHERE type::text NOT IN ('{valid_types_str}')
        """)
        invalid_types = cur.fetchall()
        if invalid_types:
            issues.append(f"❌ Found invalid account types: {invalid_types}")
        else:
            print("✓ All account types are valid")
        
        # Check for required core accounts
        missing_accounts = []
        for code, name, account_type in REQUIRED_CORE_ACCOUNTS:
            cur.execute("""
                SELECT id FROM pharma.accounts
                WHERE code = %s AND type::text = %s
            """, (code, account_type))
            if not cur.fetchone():
                missing_accounts.append((code, name, account_type))
        
        if missing_accounts:
            issues.append(f"❌ Missing required core accounts: {missing_accounts}")
        else:
            print("✓ All required core accounts exist")
        
        # Get account counts by type
        cur.execute("""
            SELECT type::text as account_type, COUNT(*) as count
            FROM pharma.accounts
            GROUP BY type
            ORDER BY type
        """)
        type_counts = cur.fetchall()
        print()
        print("Account counts by type:")
        for row in type_counts:
            print(f"  {row['account_type']}: {row['count']}")
        
        # Get total count
        cur.execute("SELECT COUNT(*) as total FROM pharma.accounts")
        total = cur.fetchone()['total']
        print()
        print(f"Total accounts: {total}")
        print()
        
        # Check for accounts with null or empty codes
        cur.execute("""
            SELECT COUNT(*) as count
            FROM pharma.accounts
            WHERE code IS NULL OR code = ''
        """)
        null_codes = cur.fetchone()['count']
        if null_codes > 0:
            issues.append(f"❌ Found {null_codes} accounts with null or empty codes")
        else:
            print("✓ No null or empty account codes")
        
        # Check for accounts with null names
        cur.execute("""
            SELECT COUNT(*) as count
            FROM pharma.accounts
            WHERE name IS NULL OR name = ''
        """)
        null_names = cur.fetchone()['count']
        if null_names > 0:
            issues.append(f"❌ Found {null_names} accounts with null or empty names")
        else:
            print("✓ No null or empty account names")
    
    if issues:
        print()
        print("=" * 60)
        print("⚠️  VERIFICATION ISSUES FOUND:")
        print("=" * 60)
        for issue in issues:
            print(issue)
        return False
    else:
        print()
        print("=" * 60)
        print("✓ ALL VERIFICATIONS PASSED!")
        print("=" * 60)
        return True


def main():
    """Main execution function"""
    print("=" * 60)
    print("PHARMASIGHT CHART OF ACCOUNTS - SETUP & VERIFICATION")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            # Step 1: Create table
            create_accounts_table(conn)
            
            # Step 2: Load seed data
            if not load_seed_data(conn):
                print("❌ Failed to load seed data")
                sys.exit(1)
            
            # Step 3: Verify accounts
            if not verify_accounts(conn):
                print("❌ Verification failed")
                sys.exit(1)
            
            print()
            print("=" * 60)
            print("✓ SETUP COMPLETE!")
            print("=" * 60)
            print()
            print("The chart of accounts is now ready for use.")
            print("You can query accounts using:")
            print("  SELECT * FROM pharma.accounts WHERE is_active = true ORDER BY display_order;")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

