#!/usr/bin/env python3
"""
Clear all bank transactions and import batches for Reitz Pharmacy.
This will delete:
- All bank_transactions for pharmacy_id = 1
- All bank_import_batches for pharmacy_id = 1
- Bank accounts will be preserved

Note: This will also check for any ledger entries that reference bank transactions.

Usage:
    python clear_reitz_bank_transactions.py [--yes]
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.conn import get_conn

def main():
    parser = argparse.ArgumentParser(description='Clear bank transactions for Reitz Pharmacy')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    pharmacy_id = 1  # Reitz Pharmacy
    
    print("=" * 80)
    print(f"CLEARING BANK TRANSACTIONS FOR REITZ PHARMACY (pharmacy_id = {pharmacy_id})")
    print("=" * 80)
    print()
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify pharmacy exists
            cur.execute("""
                SELECT pharmacy_id, name 
                FROM pharma.pharmacies 
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            
            pharmacy = cur.fetchone()
            if not pharmacy:
                print(f"❌ Pharmacy with ID {pharmacy_id} not found!")
                return
            
            print(f"Pharmacy: {pharmacy['name']}")
            print()
            
            # Count what will be deleted
            cur.execute("""
                SELECT COUNT(*) as count
                FROM pharma.bank_transactions
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            transaction_count = cur.fetchone()['count']
            
            cur.execute("""
                SELECT COUNT(*) as count
                FROM pharma.bank_import_batches
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            batch_count = cur.fetchone()['count']
            
            # Check for ledger entries that reference bank transactions
            cur.execute("""
                SELECT COUNT(*) as count
                FROM pharma.ledger_entries
                WHERE pharmacy_id = %s 
                AND source = 'BANK'
            """, (pharmacy_id,))
            ledger_count = cur.fetchone()['count']
            
            print("CURRENT STATE:")
            print(f"  Bank Transactions: {transaction_count}")
            print(f"  Import Batches: {batch_count}")
            print(f"  Ledger Entries (source=BANK): {ledger_count}")
            print()
            
            if ledger_count > 0:
                print("⚠️  WARNING: There are ledger entries with source='BANK' for this pharmacy.")
                print("   These ledger entries will NOT be deleted by this script.")
                print("   You may want to review and delete them separately if needed.")
                print()
            
            # Confirm deletion
            print("This will delete:")
            print(f"  - {transaction_count} bank transactions")
            print(f"  - {batch_count} import batches")
            print()
            print("Bank accounts will be preserved.")
            print()
            
            if not args.yes:
                try:
                    response = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
                    if response != 'yes':
                        print("❌ Deletion cancelled.")
                        return
                except (EOFError, KeyboardInterrupt):
                    print("\n❌ Deletion cancelled.")
                    return
            else:
                print("Proceeding with deletion (--yes flag provided)...")
            
            print()
            print("Deleting bank transactions and batches...")
            
            # First, get batch IDs for deleting errors
            cur.execute("""
                SELECT id FROM pharma.bank_import_batches WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            batch_ids = [row['id'] for row in cur.fetchall()]
            
            # Delete import errors first (they reference batches)
            deleted_errors = 0
            if batch_ids:
                cur.execute("""
                    DELETE FROM pharma.bank_import_errors
                    WHERE bank_import_batch_id = ANY(%s)
                """, (batch_ids,))
                deleted_errors = cur.rowcount
            
            # Delete transactions first (though CASCADE should handle this)
            # But being explicit is safer
            cur.execute("""
                DELETE FROM pharma.bank_transactions
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            deleted_transactions = cur.rowcount
            
            # Delete import batches (this will also cascade delete any remaining transactions)
            cur.execute("""
                DELETE FROM pharma.bank_import_batches
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            deleted_batches = cur.rowcount
            
            conn.commit()
            
            print()
            print("=" * 80)
            print("DELETION COMPLETE")
            print("=" * 80)
            print(f"  Deleted {deleted_transactions} bank transactions")
            print(f"  Deleted {deleted_batches} import batches")
            print(f"  Deleted {deleted_errors} import errors")
            print()
            print("✅ All bank transactions and batches have been cleared for Reitz Pharmacy.")
            print("   Bank accounts have been preserved.")
            
            if ledger_count > 0:
                print()
                print(f"⚠️  Note: {ledger_count} ledger entries with source='BANK' still exist.")
                print("   These were not deleted. Review them separately if needed.")

if __name__ == "__main__":
    main()

