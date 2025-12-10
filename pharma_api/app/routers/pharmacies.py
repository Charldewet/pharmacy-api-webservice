from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from ..db import get_conn
from ..schemas import Pharmacy, ReconciliationSummary
# from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies", tags=["pharmacies"]) # , dependencies=[Depends(require_api_key)]

@router.get("", response_model=List[Pharmacy])
def list_pharmacies():
    from ..db import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT pharmacy_id, name FROM pharma.pharmacies WHERE is_active ORDER BY pharmacy_id;")
        return cur.fetchall()

@router.patch("/{pharmacy_id}/deactivate")
def deactivate_pharmacy(pharmacy_id: int):
    """Deactivate a pharmacy by setting is_active to false"""
    from ..db import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        # Check if pharmacy exists
        cur.execute("SELECT name FROM pharma.pharmacies WHERE pharmacy_id = %s;", (pharmacy_id,))
        pharmacy = cur.fetchone()
        
        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")
        
        # Deactivate the pharmacy
        cur.execute("UPDATE pharma.pharmacies SET is_active = false WHERE pharmacy_id = %s;", (pharmacy_id,))
        conn.commit()
        
        return {"message": f"Pharmacy '{pharmacy[0]}' (ID: {pharmacy_id}) has been deactivated"}

@router.get("/{pharmacy_id}/reconciliation-debug")
def get_reconciliation_debug(pharmacy_id: int, month: str = Query(..., description="Month in YYYY-MM format")):
    """
    Debug endpoint to check what data exists for reconciliation.
    Returns detailed information about transactions and date ranges.
    """
    try:
        month_date = datetime.strptime(month, "%Y-%m").date()
        month_start = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM (e.g., 2025-01)")
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check pharmacy exists
            cur.execute("SELECT pharmacy_id, name FROM pharma.pharmacies WHERE pharmacy_id = %s;", (pharmacy_id,))
            pharmacy = cur.fetchone()
            if not pharmacy:
                raise HTTPException(status_code=404, detail="Pharmacy not found")
            
            # Get all transactions for this pharmacy (no date filter)
            cur.execute("""
                SELECT 
                    COUNT(*) as total_all_time,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date,
                    COUNT(ledger_entry_id) FILTER (WHERE ledger_entry_id IS NOT NULL) as reconciled_all_time
                FROM pharma.bank_transactions
                WHERE pharmacy_id = %s
            """, (pharmacy_id,))
            all_time_stats = cur.fetchone()
            
            # Get transactions for the requested month
            cur.execute("""
                SELECT 
                    COUNT(*) as count_in_range,
                    MIN(date) as min_date_in_range,
                    MAX(date) as max_date_in_range
                FROM pharma.bank_transactions
                WHERE pharmacy_id = %s
                  AND date >= %s
                  AND date < %s
            """, (pharmacy_id, month_start, month_end))
            month_stats = cur.fetchone()
            
            # Get sample transactions
            cur.execute("""
                SELECT id, date, description, amount, ledger_entry_id, classification_status
                FROM pharma.bank_transactions
                WHERE pharmacy_id = %s
                ORDER BY date DESC
                LIMIT 5
            """, (pharmacy_id,))
            sample_transactions = cur.fetchall()
            
            return {
                "pharmacy": dict(pharmacy),
                "requested_month": month,
                "date_range": {
                    "start": str(month_start),
                    "end": str(month_end)
                },
                "all_time_stats": dict(all_time_stats) if all_time_stats else {},
                "month_stats": dict(month_stats) if month_stats else {},
                "sample_transactions": [dict(t) for t in sample_transactions]
            }

@router.get("/{pharmacy_id}/reconciliation-summary", response_model=ReconciliationSummary)
def get_reconciliation_summary(pharmacy_id: int, month: str = Query(..., description="Month in YYYY-MM format")):
    """
    Get reconciliation summary for a pharmacy for a specific month.
    
    A bank statement line is reconciled if it has a ledger_transaction linked
    (via manual classification OR rule classification).
    
    Returns:
    - total_lines: Total number of bank statement lines for the month
    - reconciled_lines: Number of lines that have been reconciled (have ledger_entry_id)
    - unmatched_lines: Number of lines that haven't been reconciled
    - bank_total: Sum of amounts from bank transactions
    - ledger_total: Sum of amounts from ledger entries linked to bank transactions
    - difference: Difference between bank_total and ledger_total
    """
    try:
        # Parse month parameter (YYYY-MM)
        month_date = datetime.strptime(month, "%Y-%m").date()
        month_start = month_date.replace(day=1)
        
        # Calculate month end
        if month_date.month == 12:
            month_end = month_date.replace(year=month_date.year + 1, month=1, day=1)
        else:
            month_end = month_date.replace(month=month_date.month + 1, day=1)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM (e.g., 2025-01)")
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check if pharmacy exists
            cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s;", (pharmacy_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Pharmacy not found")
            
            # Get bank transaction statistics for the month
            cur.execute("""
                SELECT 
                    COUNT(*) as total_lines,
                    COUNT(ledger_entry_id) FILTER (WHERE ledger_entry_id IS NOT NULL) as reconciled_lines,
                    COUNT(*) FILTER (WHERE ledger_entry_id IS NULL) as unmatched_lines,
                    COALESCE(SUM(amount), 0) as bank_total
                FROM pharma.bank_transactions
                WHERE pharmacy_id = %s
                  AND date >= %s
                  AND date < %s
            """, (pharmacy_id, month_start, month_end))
            
            bank_stats = cur.fetchone()
            
            # With dict_row factory, results are already dict-like
            total_lines = bank_stats['total_lines'] if bank_stats else 0
            reconciled_lines = bank_stats['reconciled_lines'] if bank_stats else 0
            unmatched_lines = bank_stats['unmatched_lines'] if bank_stats else 0
            bank_total = float(bank_stats['bank_total']) if bank_stats and bank_stats['bank_total'] else 0.0
            
            if total_lines == 0:
                return ReconciliationSummary(
                    total_lines=0,
                    reconciled_lines=0,
                    unmatched_lines=0,
                    bank_total=0.0,
                    ledger_total=0.0,
                    difference=0.0
                )
            
            # Get ledger total for reconciled transactions in this month
            # Ledger entries store amounts as positive values, but we need to apply the sign
            # based on the original bank transaction to match the bank_total
            # Positive bank transaction (money in) → increases bank balance
            # Negative bank transaction (money out) → decreases bank balance
            cur.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN bt.amount > 0 THEN le.amount
                        ELSE -le.amount
                    END
                ), 0) as ledger_total
                FROM pharma.ledger_entries le
                INNER JOIN pharma.bank_transactions bt ON le.bank_transaction_id = bt.id
                WHERE bt.pharmacy_id = %s
                  AND bt.date >= %s
                  AND bt.date < %s
                  AND le.bank_transaction_id IS NOT NULL
            """, (pharmacy_id, month_start, month_end))
            
            ledger_result = cur.fetchone()
            ledger_total = float(ledger_result['ledger_total']) if ledger_result and ledger_result.get('ledger_total') else 0.0
            
            # Calculate difference
            difference = bank_total - ledger_total
            
            return ReconciliationSummary(
                total_lines=total_lines,
                reconciled_lines=reconciled_lines,
                unmatched_lines=unmatched_lines,
                bank_total=bank_total,
                ledger_total=ledger_total,
                difference=difference
            )
