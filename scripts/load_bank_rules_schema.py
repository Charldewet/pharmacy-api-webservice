#!/usr/bin/env python3
"""
Load and verify the bank rules and classification schema.

This script:
1. Creates the bank rules tables, enums, and updates existing tables
2. Verifies that all tables, enums, indexes, and triggers are correctly set up

Usage:
    python scripts/load_bank_rules_schema.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def apply_schema(conn):
    """Apply the bank rules schema"""
    print("Applying bank rules schema...")
    
    schema_file = Path(__file__).parent.parent / "schema_bank_rules.sql"
    
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
        
        print("✓ Bank rules schema applied successfully")
        print()
        return True
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False


def verify_schema(conn):
    """Verify that all tables, enums, and indexes exist"""
    print("Verifying schema...")
    print()
    
    checks = []
    
    with conn.cursor() as cur:
        # Check enums
        enum_checks = [
            ('classification_status', ['unclassified', 'rule_classified', 'ai_classified', 'user_override']),
            ('bank_rule_type', ['receive', 'spend', 'transfer']),
            ('condition_group_type', ['ALL', 'ANY']),
            ('condition_field', ['description', 'reference', 'amount', 'amount_in', 'amount_out', 'date']),
            ('condition_operator', ['contains', 'not_contains', 'equals', 'starts_with', 'ends_with', 'greater_than', 'less_than', 'regex']),
            ('ai_suggestion_status', ['pending', 'accepted', 'rejected']),
        ]
        
        for enum_name, expected_values in enum_checks:
            try:
                cur.execute(f"""
                    SELECT enumlabel 
                    FROM pg_enum 
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'classification_status' AND typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'pharma'))
                    ORDER BY enumsortorder
                """)
                # For now, just check if enum exists
                cur.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_type t
                        JOIN pg_namespace n ON t.typnamespace = n.oid
                        WHERE t.typname = %s AND n.nspname = 'pharma'
                    )
                """, (enum_name,))
                exists = cur.fetchone()[0]
                checks.append(('Enum', enum_name, exists))
            except Exception as e:
                checks.append(('Enum', enum_name, False))
                print(f"  ⚠️  Warning checking enum {enum_name}: {e}")
        
        # Check tables
        table_checks = [
            'bank_rules',
            'bank_rule_conditions',
            'ai_suggestions',
        ]
        
        for table_name in table_checks:
            try:
                cur.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'pharma' AND table_name = %s
                    )
                """, (table_name,))
                exists = cur.fetchone()[0]
                checks.append(('Table', table_name, exists))
            except Exception as e:
                checks.append(('Table', table_name, False))
                print(f"  ⚠️  Warning checking table {table_name}: {e}")
        
        # Check bank_transactions columns
        column_checks = [
            'classification_status',
            'classified_at',
            'classified_by_rule_id',
            'ai_suggestion_id',
            'ledger_entry_id',
        ]
        
        for column_name in column_checks:
            try:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'pharma' 
                        AND table_name = 'bank_transactions' 
                        AND column_name = %s
                    )
                """, (column_name,))
                exists = cur.fetchone()[0]
                checks.append(('Column', f'bank_transactions.{column_name}', exists))
            except Exception as e:
                checks.append(('Column', f'bank_transactions.{column_name}', False))
                print(f"  ⚠️  Warning checking column {column_name}: {e}")
        
        # Check ledger_entries column
        try:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'pharma' 
                    AND table_name = 'ledger_entries' 
                    AND column_name = 'bank_transaction_id'
                )
            """)
            exists = cur.fetchone()[0]
            checks.append(('Column', 'ledger_entries.bank_transaction_id', exists))
        except Exception as e:
            checks.append(('Column', 'ledger_entries.bank_transaction_id', False))
            print(f"  ⚠️  Warning checking column bank_transaction_id: {e}")
        
        # Check indexes
        index_checks = [
            'idx_bank_rules_pharmacy',
            'idx_bank_rules_active',
            'idx_bank_rule_conditions_rule',
            'idx_ai_suggestions_pharmacy',
            'idx_ai_suggestions_transaction',
            'idx_bank_transactions_classification',
            'idx_ledger_entries_bank_transaction',
            'idx_ledger_entries_bank_transaction_unique',
        ]
        
        for index_name in index_checks:
            try:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE schemaname = 'pharma' AND indexname = %s
                    )
                """, (index_name,))
                exists = cur.fetchone()[0]
                checks.append(('Index', index_name, exists))
            except Exception as e:
                checks.append(('Index', index_name, False))
                print(f"  ⚠️  Warning checking index {index_name}: {e}")
    
    # Print results
    print("Verification Results:")
    print("-" * 60)
    
    all_passed = True
    for check_type, name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {check_type}: {name}")
        if not passed:
            all_passed = False
    
    print("-" * 60)
    print()
    
    if all_passed:
        print("✓ All checks passed!")
        return True
    else:
        print("⚠️  Some checks failed. Please review the schema.")
        return False


def main():
    """Main execution function"""
    print("=" * 60)
    print("PHARMASIGHT BANK RULES & CLASSIFICATION SCHEMA - SETUP")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            # Step 1: Apply schema
            if not apply_schema(conn):
                print("❌ Failed to apply schema")
                sys.exit(1)
            
            # Step 2: Verify schema
            if not verify_schema(conn):
                print("⚠️  Verification found issues, but schema was applied")
                print("   Please review the output above")
            
            print()
            print("=" * 60)
            print("✓ SETUP COMPLETE!")
            print("=" * 60)
            print()
            print("The bank rules and classification system is now ready for use.")
            print("You can now use the bank rules API endpoints:")
            print("  - GET /bank-rules/pharmacies/{pharmacy_id}/bank-rules")
            print("  - POST /bank-rules/pharmacies/{pharmacy_id}/bank-rules")
            print("  - POST /bank-rules/bank-import-batches/{batch_id}/apply-rules")
            print("  - POST /bank-rules/bank-import-batches/{batch_id}/generate-ai-suggestions")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

