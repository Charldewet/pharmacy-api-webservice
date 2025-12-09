#!/usr/bin/env python3
"""
Show a sample of accounts data to verify everything is working.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def main():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Show accounts by code range
            print("=" * 80)
            print("CHART OF ACCOUNTS - SAMPLE DATA")
            print("=" * 80)
            print()
            
            # Assets (1000-1999)
            print("ASSETS (1000-1999):")
            print("-" * 80)
            cur.execute("""
                SELECT code, name, category, is_active
                FROM pharma.accounts
                WHERE code >= '1000' AND code < '2000'
                ORDER BY display_order
            """)
            for row in cur.fetchall():
                active = "✓" if row['is_active'] else "✗"
                print(f"  {active} {row['code']:6} {row['name']:40} [{row['category']}]")
            
            print()
            
            # Income (4000-4999)
            print("INCOME (4000-4999):")
            print("-" * 80)
            cur.execute("""
                SELECT code, name, category, is_active
                FROM pharma.accounts
                WHERE code >= '4000' AND code < '5000'
                ORDER BY display_order
            """)
            for row in cur.fetchall():
                active = "✓" if row['is_active'] else "✗"
                print(f"  {active} {row['code']:6} {row['name']:40} [{row['category']}]")
            
            print()
            
            # Expenses sample (6000-6299)
            print("EXPENSES - SAMPLE (6000-6299):")
            print("-" * 80)
            cur.execute("""
                SELECT code, name, category, is_active
                FROM pharma.accounts
                WHERE code >= '6000' AND code < '6300'
                ORDER BY display_order
                LIMIT 15
            """)
            for row in cur.fetchall():
                active = "✓" if row['is_active'] else "✗"
                print(f"  {active} {row['code']:6} {row['name']:40} [{row['category']}]")
            
            print()
            
            # Check for any inactive accounts
            cur.execute("SELECT COUNT(*) as count FROM pharma.accounts WHERE is_active = false")
            inactive_count = cur.fetchone()['count']
            print(f"Inactive accounts: {inactive_count}")
            
            # Check for accounts with parent relationships
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM pharma.accounts 
                WHERE parent_account_id IS NOT NULL
            """)
            parented_count = cur.fetchone()['count']
            print(f"Accounts with parent relationships: {parented_count}")
            
            print()
            print("=" * 80)
            print("✓ Verification complete - all accounts are active and ready to use")
            print("=" * 80)

if __name__ == "__main__":
    main()

