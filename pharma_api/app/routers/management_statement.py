"""
Management Financial Statements API Router
Provides endpoints for generating monthly P&L statements from ledger entries.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from datetime import date, datetime
from calendar import monthrange
import logging

from ..db import get_conn
from ..schemas import ManagementStatement, ManagementStatementSummary, AccountLineItem, ManagementTrendPoint
from ..auth import require_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pharmacies", tags=["management-statement"])


def _get_month_date_range(year: int, month: int) -> tuple[date, date]:
    """Get the first and last day of a given month"""
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    return first_day, last_day


def _get_account_balances(conn, pharmacy_id: int, from_date: date, to_date: date) -> dict[int, float]:
    """
    Calculate net balances for all accounts with report_category in a single query.
    
    Returns a dictionary mapping account_id to net balance.
    For P&L accounts:
    - INCOME/OTHER_INCOME: positive balance = income
    - EXPENSE/COGS/FINANCE_COST: positive balance = expense
    """
    with conn.cursor() as cur:
        # Aggregate all accounts in one query
        # This creates "transactions" from double-entry ledger_entries
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
        
        # Convert to dictionary, applying account-type-specific logic
        balances = {}
        for row in results:
            account_id = row['account_id']
            account_type = row['account_type']
            net_balance = float(row['net_balance']) if row['net_balance'] else 0.0
            
            # The query calculates: debits - credits
            # For INCOME accounts: we want credits - debits = -(debits - credits) = -net_balance
            # For EXPENSE accounts: we want debits - credits = net_balance
            if account_type in ('INCOME', 'OTHER_INCOME'):
                balances[account_id] = -net_balance  # Flip: credits increase income
            elif account_type in ('EXPENSE', 'COGS', 'FINANCE_COST'):
                balances[account_id] = net_balance  # Correct: debits increase expenses
            else:
                balances[account_id] = 0.0
        
        return balances


@router.get("/{pharmacy_id}/management-statement", response_model=ManagementStatement, dependencies=[Depends(require_api_key)])
def get_management_statement(
    pharmacy_id: int,
    year: int = Query(..., description="Year (e.g., 2025)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)")
):
    """
    Get monthly management P&L statement for a pharmacy.
    
    Generates a profit & loss statement from ledger entries, grouped by report_category.
    Only accounts with a non-NULL report_category are included.
    
    - **pharmacy_id**: ID of the pharmacy
    - **year**: Year (e.g., 2025)
    - **month**: Month number (1-12)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify pharmacy exists
            cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Pharmacy not found")
            
            # Get date range for the month
            from_date, to_date = _get_month_date_range(year, month)
            
            # Get all accounts with report_category for this pharmacy's ledger entries
            # We need to aggregate ledger entries by account and calculate net amounts
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
            
            # Get balances for all accounts in one query
            balances = _get_account_balances(conn, pharmacy_id, from_date, to_date)
            
            # Group accounts by report_category
            revenue = []
            cogs = []
            expenses = []
            other_income = []
            other_expenses = []
            
            for account in accounts:
                account_id = account['account_id']
                balance = balances.get(account_id, 0.0)
                
                # Skip accounts with zero balance
                if abs(balance) < 0.01:
                    continue
                
                category = account['report_category']
                
                # For COGS and expenses, negate the amount for readability (per spec)
                # The balance calculation returns positive for expenses (debits increase expenses)
                # but the API should return negative amounts for expenses/COGS
                if category in ('cogs', 'expenses', 'other_expenses'):
                    display_amount = -balance
                else:
                    display_amount = balance
                
                line_item = AccountLineItem(
                    account_id=account_id,
                    code=account['account_code'],
                    name=account['account_name'],
                    amount=display_amount
                )
                
                if category == 'revenue':
                    revenue.append(line_item)
                elif category == 'cogs':
                    cogs.append(line_item)
                elif category == 'expenses':
                    expenses.append(line_item)
                elif category == 'other_income':
                    other_income.append(line_item)
                elif category == 'other_expenses':
                    other_expenses.append(line_item)
            
            # Calculate summary totals
            total_revenue = sum(item.amount for item in revenue)
            total_cogs = sum(item.amount for item in cogs)
            gross_profit = total_revenue - total_cogs
            gross_profit_percent = (gross_profit / total_revenue * 100) if total_revenue != 0 else 0.0
            total_expenses = sum(item.amount for item in expenses)
            operating_profit = gross_profit - total_expenses
            total_other_income = sum(item.amount for item in other_income)
            total_other_expenses = sum(item.amount for item in other_expenses)
            net_profit = operating_profit + total_other_income - total_other_expenses
            
            summary = ManagementStatementSummary(
                total_revenue=total_revenue,
                total_cogs=total_cogs,
                gross_profit=gross_profit,
                gross_profit_percent=round(gross_profit_percent, 1),
                total_expenses=total_expenses,
                operating_profit=operating_profit,
                total_other_income=total_other_income,
                total_other_expenses=total_other_expenses,
                net_profit=net_profit
            )
            
            return ManagementStatement(
                pharmacy_id=pharmacy_id,
                year=year,
                month=month,
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
                summary=summary,
                revenue=revenue,
                cogs=cogs,
                expenses=expenses,
                other_income=other_income,
                other_expenses=other_expenses
            )


@router.get("/{pharmacy_id}/management-statement/trend", response_model=List[ManagementTrendPoint], dependencies=[Depends(require_api_key)])
def get_management_statement_trend(
    pharmacy_id: int,
    from_month: str = Query(..., description="Start month in YYYY-MM format (e.g., 2025-01)"),
    to_month: str = Query(..., description="End month in YYYY-MM format (e.g., 2025-12)")
):
    """
    Get historical trend data for management statements.
    
    Returns monthly summaries (revenue, gross profit, net profit) for a date range.
    Useful for charts and trend analysis.
    
    - **pharmacy_id**: ID of the pharmacy
    - **from_month**: Start month in YYYY-MM format
    - **to_month**: End month in YYYY-MM format
    """
    try:
        from_date = datetime.strptime(from_month, "%Y-%m").date()
        to_date = datetime.strptime(to_month, "%Y-%m").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM (e.g., 2025-01)")
    
    # Validate date range
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_month must be before or equal to to_month")
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Verify pharmacy exists
            cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Pharmacy not found")
            
            # Generate list of months in range
            trend_points = []
            current = from_date.replace(day=1)
            end = to_date.replace(day=1)
            
            while current <= end:
                year = current.year
                month = current.month
                month_start, month_end = _get_month_date_range(year, month)
                
                # Get accounts with report_category
                cur.execute("""
                    SELECT DISTINCT
                        a.id AS account_id,
                        a.report_category,
                        a.type AS account_type
                    FROM pharma.accounts a
                    WHERE a.report_category IS NOT NULL
                      AND a.is_active = true
                """)
                
                accounts = cur.fetchall()
                
                # Get balances for all accounts in one query
                balances = _get_account_balances(conn, pharmacy_id, month_start, month_end)
                
                # Calculate totals for this month
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
                
                trend_points.append(ManagementTrendPoint(
                    month=f"{year}-{month:02d}",
                    revenue=total_revenue,
                    gross_profit=gross_profit,
                    net_profit=net_profit
                ))
                
                # Move to next month
                if month == 12:
                    current = current.replace(year=year + 1, month=1)
                else:
                    current = current.replace(month=month + 1)
            
            return trend_points
