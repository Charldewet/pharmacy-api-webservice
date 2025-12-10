#!/usr/bin/env python3
"""
Test the management statement functionality.
This script tests the database queries and logic directly.

Usage:
    python scripts/test_management_statement_api.py [pharmacy_id] [year] [month]
    
Example:
    python scripts/test_management_statement_api.py 1 2025 12
"""

import sys
import json
from pathlib import Path
from datetime import datetime, date
from calendar import monthrange
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def _get_month_date_range(year: int, month: int) -> tuple[date, date]:
    """Get the first and last day of a given month"""
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    return first_day, last_day


def _get_account_balances(conn, pharmacy_id: int, from_date: date, to_date: date) -> dict[int, float]:
    """Calculate net balances for all accounts with report_category"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 
                a.id AS account_id,
                a.type AS account_type,
                COALESCE(SUM(
                    CASE 
                        WHEN le.debit_account_id = a.id THEN le.amount
                        WHEN le.credit_account_id = a.id THEN -le.amount
                        ELSE 0
                    END
                ), 0) AS net_balance
            FROM pharma.accounts a
            LEFT JOIN pharma.ledger_entries le ON (
                (le.debit_account_id = a.id OR le.credit_account_id = a.id)
                AND le.pharmacy_id = %s
                AND le.date >= %s
                AND le.date <= %s
            )
            WHERE a.report_category IS NOT NULL
              AND a.is_active = true
            GROUP BY a.id, a.type
        """, (pharmacy_id, from_date, to_date))
        
        results = cur.fetchall()
        
        balances = {}
        for row in results:
            account_id = row['account_id']
            account_type = row['account_type']
            net_balance = float(row['net_balance']) if row['net_balance'] else 0.0
            
            if account_type in ('INCOME', 'OTHER_INCOME'):
                balances[account_id] = -net_balance
            elif account_type in ('EXPENSE', 'COGS', 'FINANCE_COST'):
                balances[account_id] = net_balance
            else:
                balances[account_id] = 0.0
        
        return balances


def test_monthly_statement(pharmacy_id: int, year: int, month: int):
    """Test the monthly management statement logic"""
    print("=" * 60)
    print(f"TESTING MONTHLY STATEMENT")
    print(f"Pharmacy ID: {pharmacy_id}, Year: {year}, Month: {month}")
    print("=" * 60)
    print()
    
    try:
        from_date, to_date = _get_month_date_range(year, month)
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Verify pharmacy exists
                cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
                if not cur.fetchone():
                    print(f"❌ Pharmacy {pharmacy_id} not found")
                    return False
                
                # Get accounts with report_category
                cur.execute("""
                    SELECT DISTINCT
                        a.id AS account_id,
                        a.code AS account_code,
                        a.name AS account_name,
                        a.report_category,
                        a.type AS account_type
                    FROM pharma.accounts a
                    WHERE a.report_category IS NOT NULL
                      AND a.is_active = true
                    ORDER BY a.report_category, a.code
                """)
                
                accounts = cur.fetchall()
                
                # Get balances
                balances = _get_account_balances(conn, pharmacy_id, from_date, to_date)
                
                # Group by category
                revenue = []
                cogs = []
                expenses = []
                other_income = []
                other_expenses = []
                
                for account in accounts:
                    account_id = account['account_id']
                    balance = balances.get(account_id, 0.0)
                    
                    if abs(balance) < 0.01:
                        continue
                    
                    category = account['report_category']
                    
                    if category in ('cogs', 'expenses', 'other_expenses'):
                        display_amount = -balance
                    else:
                        display_amount = balance
                    
                    item = {
                        'account_id': account_id,
                        'code': account['account_code'],
                        'name': account['account_name'],
                        'amount': display_amount
                    }
                    
                    if category == 'revenue':
                        revenue.append(item)
                    elif category == 'cogs':
                        cogs.append(item)
                    elif category == 'expenses':
                        expenses.append(item)
                    elif category == 'other_income':
                        other_income.append(item)
                    elif category == 'other_expenses':
                        other_expenses.append(item)
                
                # Calculate totals
                total_revenue = sum(item['amount'] for item in revenue)
                total_cogs = sum(item['amount'] for item in cogs)
                gross_profit = total_revenue - total_cogs
                gross_profit_percent = (gross_profit / total_revenue * 100) if total_revenue != 0 else 0.0
                total_expenses = sum(item['amount'] for item in expenses)
                operating_profit = gross_profit - total_expenses
                total_other_income = sum(item['amount'] for item in other_income)
                total_other_expenses = sum(item['amount'] for item in other_expenses)
                net_profit = operating_profit + total_other_income - total_other_expenses
        
        print("✅ Success!")
        print()
        print(f"Period: {from_date} to {to_date}")
        print()
        print("SUMMARY:")
        print(f"  Total Revenue:        R {total_revenue:,.2f}")
        print(f"  Total COGS:           R {total_cogs:,.2f}")
        print(f"  Gross Profit:         R {gross_profit:,.2f}")
        print(f"  Gross Profit %:       {gross_profit_percent:.1f}%")
        print(f"  Total Expenses:       R {total_expenses:,.2f}")
        print(f"  Operating Profit:     R {operating_profit:,.2f}")
        print(f"  Other Income:         R {total_other_income:,.2f}")
        print(f"  Other Expenses:       R {total_other_expenses:,.2f}")
        print(f"  Net Profit:           R {net_profit:,.2f}")
        print()
        
        print(f"REVENUE ({len(revenue)} accounts):")
        for item in revenue[:5]:
            print(f"  {item['code']:6} {item['name']:40} R {item['amount']:>12,.2f}")
        if len(revenue) > 5:
            print(f"  ... and {len(revenue) - 5} more")
        print()
        
        print(f"COGS ({len(cogs)} accounts):")
        for item in cogs[:5]:
            print(f"  {item['code']:6} {item['name']:40} R {item['amount']:>12,.2f}")
        if len(cogs) > 5:
            print(f"  ... and {len(cogs) - 5} more")
        print()
        
        print(f"EXPENSES ({len(expenses)} accounts):")
        for item in expenses[:5]:
            print(f"  {item['code']:6} {item['name']:40} R {item['amount']:>12,.2f}")
        if len(expenses) > 5:
            print(f"  ... and {len(expenses) - 5} more")
        print()
        
        if other_income:
            print(f"OTHER INCOME ({len(other_income)} accounts):")
            for item in other_income:
                print(f"  {item['code']:6} {item['name']:40} R {item['amount']:>12,.2f}")
            print()
        
        if other_expenses:
            print(f"OTHER EXPENSES ({len(other_expenses)} accounts):")
            for item in other_expenses:
                print(f"  {item['code']:6} {item['name']:40} R {item['amount']:>12,.2f}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trend(pharmacy_id: int, from_month: str, to_month: str):
    """Test the trend logic"""
    print("=" * 60)
    print(f"TESTING TREND DATA")
    print(f"Pharmacy ID: {pharmacy_id}, From: {from_month}, To: {to_month}")
    print("=" * 60)
    print()
    
    try:
        from_date = datetime.strptime(from_month, "%Y-%m").date()
        to_date = datetime.strptime(to_month, "%Y-%m").date()
        
        trend_points = []
        current = from_date.replace(day=1)
        end = to_date.replace(day=1)
        
        with get_conn() as conn:
            while current <= end:
                year = current.year
                month = current.month
                month_start, month_end = _get_month_date_range(year, month)
                
                balances = _get_account_balances(conn, pharmacy_id, month_start, month_end)
                
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT
                            a.id AS account_id,
                            a.report_category
                        FROM pharma.accounts a
                        WHERE a.report_category IS NOT NULL
                          AND a.is_active = true
                    """)
                    
                    accounts = cur.fetchall()
                    
                    total_revenue = 0.0
                    total_cogs = 0.0
                    total_expenses = 0.0
                    total_other_income = 0.0
                    total_other_expenses = 0.0
                    
                    for account in accounts:
                        account_id = account['account_id']
                        balance = balances.get(account_id, 0.0)
                        
                        # Apply same sign convention as monthly statement
                        # COGS and expenses should be negative for display/calculation
                        category = account['report_category']
                        if category == 'revenue':
                            total_revenue += balance
                        elif category == 'cogs':
                            total_cogs += -balance  # Negate for consistency with monthly statement
                        elif category == 'expenses':
                            total_expenses += -balance  # Negate for consistency with monthly statement
                        elif category == 'other_income':
                            total_other_income += balance
                        elif category == 'other_expenses':
                            total_other_expenses += -balance  # Negate for consistency with monthly statement
                    
                    gross_profit = total_revenue - total_cogs
                    operating_profit = gross_profit - total_expenses
                    net_profit = operating_profit + total_other_income - total_other_expenses
                    
                    trend_points.append({
                        'month': f"{year}-{month:02d}",
                        'revenue': total_revenue,
                        'gross_profit': gross_profit,
                        'net_profit': net_profit
                    })
                    
                    if month == 12:
                        current = current.replace(year=year + 1, month=1)
                    else:
                        current = current.replace(month=month + 1)
        
        print(f"✅ Success! Retrieved {len(trend_points)} months of data")
        print()
        
        if trend_points:
            print("TREND DATA:")
            print(f"{'Month':<10} {'Revenue':>15} {'Gross Profit':>15} {'Net Profit':>15}")
            print("-" * 60)
            for point in trend_points:
                print(f"{point['month']:<10} R {point['revenue']:>12,.2f} R {point['gross_profit']:>12,.2f} R {point['net_profit']:>12,.2f}")
        else:
            print("⚠ No data returned")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_pharmacy_exists(pharmacy_id: int) -> bool:
    """Check if pharmacy exists"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
            return cur.fetchone() is not None


def main():
    """Main function"""
    # Get parameters from command line or use defaults
    if len(sys.argv) >= 4:
        pharmacy_id = int(sys.argv[1])
        year = int(sys.argv[2])
        month = int(sys.argv[3])
    else:
        # Use defaults
        pharmacy_id = 1
        year = 2025
        month = 12
    
    print("=" * 60)
    print("MANAGEMENT STATEMENT API TEST")
    print("=" * 60)
    print()
    
    # Check if pharmacy exists
    if not check_pharmacy_exists(pharmacy_id):
        print(f"❌ Pharmacy {pharmacy_id} not found")
        return 1
    
    # Test monthly statement
    success1 = test_monthly_statement(pharmacy_id, year, month)
    
    # Test trend (last 3 months)
    from_month = f"{year}-{max(1, month-2):02d}"
    to_month = f"{year}-{month:02d}"
    success2 = test_trend(pharmacy_id, from_month, to_month)
    
    if success1 and success2:
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    else:
        print("=" * 60)
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
