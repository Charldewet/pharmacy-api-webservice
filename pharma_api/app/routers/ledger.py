"""
Ledger Entries API Router
Provides endpoints for querying ledger entries (the single source of truth for accounting).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date
from ..db import get_conn
from ..schemas import LedgerEntry, LedgerEntryCreate
from ..auth import require_api_key

router = APIRouter(prefix="/ledger-entries", tags=["ledger"])


@router.post("", response_model=LedgerEntry, dependencies=[Depends(require_api_key)])
def create_ledger_entry(entry: LedgerEntryCreate):
    """
    Create a new ledger entry.
    
    This is the single source of truth for all accounting movements.
    Amount must be positive - debit/credit is determined by account type.
    
    - **pharmacy_id**: ID of the pharmacy
    - **date**: Effective posting date
    - **description**: Description of the transaction
    - **amount**: Positive amount (always stored as positive)
    - **debit_account_id**: Account ID for debit leg
    - **credit_account_id**: Account ID for credit leg
    - **source**: Source of entry (PHARMASIGHT, BANK, MANUAL)
    - **source_reference_type**: Optional reference type (e.g., 'bank_transaction')
    - **source_reference_id**: Optional reference ID
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Validate amount is positive
        if entry.amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")
        
        # Verify pharmacy exists
        cur.execute(
            "SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s AND is_active = true",
            (entry.pharmacy_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found or inactive")
        
        # Verify accounts exist
        cur.execute("""
            SELECT id FROM pharma.accounts 
            WHERE id IN (%s, %s) AND is_active = true
        """, (entry.debit_account_id, entry.credit_account_id))
        
        accounts = cur.fetchall()
        if len(accounts) != 2:
            raise HTTPException(status_code=404, detail="One or both accounts not found or inactive")
        
        # Verify source is valid
        valid_sources = ['PHARMASIGHT', 'BANK', 'MANUAL']
        if entry.source not in valid_sources:
            raise HTTPException(
                status_code=400, 
                detail=f"Source must be one of: {', '.join(valid_sources)}"
            )
        
        # Insert ledger entry
        cur.execute("""
            INSERT INTO pharma.ledger_entries 
            (pharmacy_id, date, description, amount, debit_account_id, credit_account_id,
             source, source_reference_type, source_reference_id, created_by_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, pharmacy_id, date, description, amount, debit_account_id,
                     credit_account_id, source, source_reference_type, source_reference_id,
                     created_by_user_id, created_at, updated_at
        """, (
            entry.pharmacy_id,
            entry.date,
            entry.description,
            entry.amount,
            entry.debit_account_id,
            entry.credit_account_id,
            entry.source,
            entry.source_reference_type,
            entry.source_reference_id,
            entry.created_by_user_id
        ))
        
        result = cur.fetchone()
        conn.commit()
        return result


@router.get("/pharmacies/{pharmacy_id}", response_model=List[LedgerEntry], dependencies=[Depends(require_api_key)])
def list_ledger_entries(
    pharmacy_id: int,
    start_date: Optional[date] = Query(None, description="Start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="End date (inclusive)"),
    source: Optional[str] = Query(None, description="Filter by source (PHARMASIGHT, BANK, MANUAL)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip")
):
    """
    List ledger entries for a specific pharmacy.
    
    - **pharmacy_id**: ID of the pharmacy
    - **start_date**: Optional start date filter (inclusive)
    - **end_date**: Optional end date filter (inclusive)
    - **source**: Optional source filter (PHARMASIGHT, BANK, MANUAL)
    - **limit**: Maximum number of entries (default: 100, max: 1000)
    - **offset**: Number of entries to skip (default: 0)
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Verify pharmacy exists
        cur.execute(
            "SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s",
            (pharmacy_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found")
        
        # Build query
        conditions = ["pharmacy_id = %s"]
        params = [pharmacy_id]
        
        if start_date:
            conditions.append("date >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("date <= %s")
            params.append(end_date)
        
        if source:
            valid_sources = ['PHARMASIGHT', 'BANK', 'MANUAL']
            if source not in valid_sources:
                raise HTTPException(
                    status_code=400,
                    detail=f"Source must be one of: {', '.join(valid_sources)}"
                )
            conditions.append("source = %s")
            params.append(source)
        
        # Add limit and offset
        params.extend([limit, offset])
        
        query = f"""
            SELECT id, pharmacy_id, date, description, amount, debit_account_id,
                   credit_account_id, source, source_reference_type, source_reference_id,
                   created_by_user_id, created_at, updated_at
            FROM pharma.ledger_entries
            WHERE {' AND '.join(conditions)}
            ORDER BY date DESC, id DESC
            LIMIT %s OFFSET %s
        """
        
        cur.execute(query, params)
        return cur.fetchall()


@router.get("/{ledger_entry_id}", response_model=LedgerEntry, dependencies=[Depends(require_api_key)])
def get_ledger_entry(ledger_entry_id: int):
    """
    Get a specific ledger entry by ID.
    
    - **ledger_entry_id**: ID of the ledger entry
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, pharmacy_id, date, description, amount, debit_account_id,
                   credit_account_id, source, source_reference_type, source_reference_id,
                   created_by_user_id, created_at, updated_at
            FROM pharma.ledger_entries
            WHERE id = %s
        """, (ledger_entry_id,))
        
        entry = cur.fetchone()
        if not entry:
            raise HTTPException(status_code=404, detail="Ledger entry not found")
        
        return entry

