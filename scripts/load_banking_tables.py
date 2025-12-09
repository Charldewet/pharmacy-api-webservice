#!/usr/bin/env python3
"""
Load and verify the banking and ledger tables for PharmaSight Financial Layer.

This script:
1. Creates the banking and ledger tables if they don't exist
2. Verifies that all tables, enums, indexes, and triggers are correctly set up

Usage:
    python scripts/load_banking_tables.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def create_banking_tables(conn):
    """Create the banking and ledger tables if they don't exist"""
    print("Creating banking and ledger tables...")
    
    banking_schema_file = Path(__file__).parent.parent / "schema_banking.sql"
    
    if not banking_schema_file.exists():
        print(f"❌ Error: Schema file not found at {banking_schema_file}")
        return False
    
    with open(banking_schema_file, 'r') as f:
        schema_sql = f.read()
    
    try:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            conn.commit()
        
        print("✓ Banking and ledger tables created successfully")
        print()
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False


def verify_tables(conn):
    """Verify that all tables, enums, indexes, and triggers exist"""
    print("Verifying banking and ledger tables...")
    print()
    
    expected_tables = [
        'bank_accounts',
        'bank_import_batches',
        'bank_transactions',
        'bank_import_errors',
        'ledger_entries'
    ]
    
    expected_enums = [
        ('bank_import_status', ['IMPORTED', 'CLASSIFIED_PARTIAL', 'CLASSIFIED_COMPLETE', 'POSTED_TO_LEDGER']),
        ('ledger_source', ['PHARMASIGHT', 'BANK', 'MANUAL'])
    ]
    
    issues = []
    
    with conn.cursor() as cur:
        # Check tables exist
        for table_name in expected_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'pharma' 
                    AND table_name = %s
                )
            """, (table_name,))
            
            if cur.fetchone()['exists']:
                print(f"✓ Table 'pharma.{table_name}' exists")
            else:
                issues.append(f"❌ Table 'pharma.{table_name}' does not exist")
        
        print()
        
        # Check enums exist
        for enum_name, expected_values in expected_enums:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_type 
                    WHERE typname = %s
                    AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pharma')
                )
            """, (enum_name,))
            
            if cur.fetchone()['exists']:
                print(f"✓ Enum type 'pharma.{enum_name}' exists")
                
                # Check enum values
                cur.execute("""
                    SELECT enumlabel 
                    FROM pg_enum 
                    WHERE enumtypid = (
                        SELECT oid FROM pg_type 
                        WHERE typname = %s
                        AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pharma')
                    )
                    ORDER BY enumsortorder
                """, (enum_name,))
                
                actual_values = [row['enumlabel'] for row in cur.fetchall()]
                if set(actual_values) == set(expected_values):
                    print(f"  ✓ Enum values correct: {', '.join(actual_values)}")
                else:
                    issues.append(f"❌ Enum '{enum_name}' has incorrect values. Expected: {expected_values}, Got: {actual_values}")
            else:
                issues.append(f"❌ Enum type 'pharma.{enum_name}' does not exist")
        
        print()
        
        # Check indexes for each table
        table_indexes = {
            'bank_accounts': ['idx_bank_accounts_pharmacy', 'idx_bank_accounts_active'],
            'bank_import_batches': [
                'idx_bank_import_batches_bank_account',
                'idx_bank_import_batches_pharmacy',
                'idx_bank_import_batches_period',
                'idx_bank_import_batches_status'
            ],
            'bank_transactions': [
                'idx_bank_transactions_batch',
                'idx_bank_transactions_bank_account',
                'idx_bank_transactions_pharmacy',
                'idx_bank_transactions_date',
                'idx_bank_transactions_external_id'
            ],
            'bank_import_errors': [
                'idx_bank_import_errors_batch'
            ],
            'ledger_entries': [
                'idx_ledger_entries_pharmacy',
                'idx_ledger_entries_date',
                'idx_ledger_entries_debit_account',
                'idx_ledger_entries_credit_account',
                'idx_ledger_entries_pharmacy_date',
                'idx_ledger_entries_source',
                'idx_ledger_entries_source_ref'
            ]
        }
        
        for table_name, expected_indexes in table_indexes.items():
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'pharma' 
                AND tablename = %s
            """, (table_name,))
            
            actual_indexes = {row['indexname'] for row in cur.fetchall()}
            expected_set = set(expected_indexes)
            
            missing = expected_set - actual_indexes
            if missing:
                issues.append(f"❌ Table '{table_name}' missing indexes: {missing}")
            else:
                print(f"✓ Table '{table_name}' has all expected indexes ({len(expected_indexes)} indexes)")
        
        print()
        
        # Check triggers
        expected_triggers = {
            'bank_accounts': ['trigger_update_bank_account_updated_at'],
            'bank_transactions': ['trigger_update_bank_transaction_updated_at'],
            'ledger_entries': ['trigger_update_ledger_entry_updated_at']
        }
        
        for table_name, expected_triggers_list in expected_triggers.items():
            cur.execute("""
                SELECT tgname 
                FROM pg_trigger 
                WHERE tgrelid = (
                    SELECT oid FROM pg_class 
                    WHERE relname = %s 
                    AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pharma')
                )
                AND tgisinternal = false
            """, (table_name,))
            
            actual_triggers = {row['tgname'] for row in cur.fetchall()}
            expected_set = set(expected_triggers_list)
            
            missing = expected_set - actual_triggers
            if missing:
                issues.append(f"❌ Table '{table_name}' missing triggers: {missing}")
            else:
                print(f"✓ Table '{table_name}' has all expected triggers")
        
        print()
    
    if issues:
        print("=" * 60)
        print("⚠️  VERIFICATION ISSUES FOUND:")
        print("=" * 60)
        for issue in issues:
            print(issue)
        return False
    else:
        print("=" * 60)
        print("✓ ALL VERIFICATIONS PASSED!")
        print("=" * 60)
        return True


def main():
    """Main execution function"""
    print("=" * 60)
    print("PHARMASIGHT BANKING & LEDGER TABLES - SETUP & VERIFICATION")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            # Step 1: Create tables
            if not create_banking_tables(conn):
                print("❌ Failed to create tables")
                sys.exit(1)
            
            # Step 2: Verify tables
            if not verify_tables(conn):
                print("❌ Verification failed")
                sys.exit(1)
            
            print()
            print("=" * 60)
            print("✓ SETUP COMPLETE!")
            print("=" * 60)
            print()
            print("The banking and ledger tables are now ready for use.")
            print("You can now use the banking and ledger API endpoints:")
            print("  - POST /bank-accounts")
            print("  - GET /bank-accounts/pharmacies/{pharmacy_id}")
            print("  - POST /ledger-entries")
            print("  - GET /ledger-entries/pharmacies/{pharmacy_id}")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

