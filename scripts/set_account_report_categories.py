#!/usr/bin/env python3
"""
Set report_category values on accounts based on their code ranges and types.
This enables accounts to appear in management financial statements.

Usage:
    python scripts/set_account_report_categories.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def set_report_categories(conn):
    """Set report_category values based on account codes and types"""
    print("Setting report_category values on accounts...")
    print()
    
    with conn.cursor() as cur:
        # Revenue accounts (4000-4999) - INCOME type
        print("Setting revenue accounts (4000-4999, type=INCOME)...")
        cur.execute("""
            UPDATE pharma.accounts
            SET report_category = 'revenue'
            WHERE code >= '4000' AND code < '5000'
              AND type = 'INCOME'
              AND is_active = true
        """)
        revenue_count = cur.rowcount
        print(f"  ✓ Updated {revenue_count} revenue accounts")
        
        # COGS accounts (5000-5999) - COGS type
        print("Setting COGS accounts (5000-5999, type=COGS)...")
        cur.execute("""
            UPDATE pharma.accounts
            SET report_category = 'cogs'
            WHERE code >= '5000' AND code < '6000'
              AND type = 'COGS'
              AND is_active = true
        """)
        cogs_count = cur.rowcount
        print(f"  ✓ Updated {cogs_count} COGS accounts")
        
        # Operating expenses (6000-6999) - EXPENSE type
        print("Setting expense accounts (6000-6999, type=EXPENSE)...")
        cur.execute("""
            UPDATE pharma.accounts
            SET report_category = 'expenses'
            WHERE code >= '6000' AND code < '7000'
              AND type = 'EXPENSE'
              AND is_active = true
        """)
        expense_count = cur.rowcount
        print(f"  ✓ Updated {expense_count} expense accounts")
        
        # Finance costs (7000-7499) - FINANCE_COST type
        print("Setting finance cost accounts (7000-7499, type=FINANCE_COST)...")
        cur.execute("""
            UPDATE pharma.accounts
            SET report_category = 'other_expenses'
            WHERE code >= '7000' AND code < '7500'
              AND type = 'FINANCE_COST'
              AND is_active = true
        """)
        finance_count = cur.rowcount
        print(f"  ✓ Updated {finance_count} finance cost accounts")
        
        # Other income (7500-7999) - OTHER_INCOME type
        print("Setting other income accounts (7500-7999, type=OTHER_INCOME)...")
        cur.execute("""
            UPDATE pharma.accounts
            SET report_category = 'other_income'
            WHERE code >= '7500' AND code < '8000'
              AND type = 'OTHER_INCOME'
              AND is_active = true
        """)
        other_income_count = cur.rowcount
        print(f"  ✓ Updated {other_income_count} other income accounts")
        
        # Other expenses (8000-8999) - EXPENSE type (if any)
        print("Setting other expense accounts (8000-8999, type=EXPENSE)...")
        cur.execute("""
            UPDATE pharma.accounts
            SET report_category = 'other_expenses'
            WHERE code >= '8000' AND code < '9000'
              AND type IN ('EXPENSE', 'FINANCE_COST')
              AND is_active = true
        """)
        other_expense_count = cur.rowcount
        print(f"  ✓ Updated {other_expense_count} other expense accounts")
        
        conn.commit()
        
        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Revenue accounts:        {revenue_count}")
        print(f"COGS accounts:          {cogs_count}")
        print(f"Expense accounts:       {expense_count}")
        print(f"Finance cost accounts:  {finance_count}")
        print(f"Other income accounts:  {other_income_count}")
        print(f"Other expense accounts: {other_expense_count}")
        print(f"Total updated:          {revenue_count + cogs_count + expense_count + finance_count + other_income_count + other_expense_count}")
        print()
        
        return True


def verify_report_categories(conn):
    """Verify report_category assignments"""
    print("Verifying report_category assignments...")
    print()
    
    with conn.cursor() as cur:
        # Count by report_category
        cur.execute("""
            SELECT 
                report_category,
                COUNT(*) as count
            FROM pharma.accounts
            WHERE report_category IS NOT NULL
              AND is_active = true
            GROUP BY report_category
            ORDER BY report_category
        """)
        
        categories = cur.fetchall()
        
        if not categories:
            print("⚠ No accounts have report_category set")
            return False
        
        print("Accounts by report_category:")
        for cat in categories:
            print(f"  {cat['report_category']:20} {cat['count']:4} accounts")
        
        print()
        
        # Show sample accounts from each category
        for category in ['revenue', 'cogs', 'expenses', 'other_income', 'other_expenses']:
            cur.execute("""
                SELECT code, name, type
                FROM pharma.accounts
                WHERE report_category = %s
                  AND is_active = true
                ORDER BY code
                LIMIT 5
            """, (category,))
            
            accounts = cur.fetchall()
            if accounts:
                print(f"Sample {category} accounts:")
                for acc in accounts:
                    print(f"  {acc['code']:6} {acc['name']:40} [{acc['type']}]")
                print()
        
        return True


def main():
    """Main function"""
    print("=" * 60)
    print("SET ACCOUNT REPORT CATEGORIES")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            if not set_report_categories(conn):
                print("❌ Failed to set report categories")
                return 1
            
            if not verify_report_categories(conn):
                print("⚠ Verification showed issues")
                return 1
            
            print("✅ Report categories set successfully!")
            print()
            print("Accounts are now ready for management statement generation.")
            return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
