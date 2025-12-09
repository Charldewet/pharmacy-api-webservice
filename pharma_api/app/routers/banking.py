"""
Bank Accounts API Router
Provides endpoints for managing bank accounts per pharmacy.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date
from ..db import get_conn
from ..schemas import BankAccount, BankAccountCreate, BankAccountUpdate
from ..auth import require_api_key

router = APIRouter(prefix="/bank-accounts", tags=["banking"])


@router.post("", response_model=BankAccount, dependencies=[Depends(require_api_key)])
def create_bank_account(account: BankAccountCreate):
    """
    Create a new bank account for a pharmacy.
    
    - **pharmacy_id**: ID of the pharmacy
    - **name**: Display name (e.g., "FNB Current")
    - **bank_name**: Bank name (e.g., "FNB", "ABSA")
    - **account_number**: Account number (optional, can be masked)
    - **branch_code**: Branch code (optional)
    - **currency**: Currency code (default: "ZAR")
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Verify pharmacy exists
        cur.execute(
            "SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s AND is_active = true",
            (account.pharmacy_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found or inactive")
        
        # Insert bank account
        cur.execute("""
            INSERT INTO pharma.bank_accounts 
            (pharmacy_id, name, bank_name, account_number, branch_code, currency, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, pharmacy_id, name, bank_name, account_number, branch_code, 
                     currency, is_active, created_at, updated_at
        """, (
            account.pharmacy_id,
            account.name,
            account.bank_name,
            account.account_number,
            account.branch_code,
            account.currency,
            account.is_active
        ))
        
        result = cur.fetchone()
        conn.commit()
        return result


@router.get("/pharmacies/{pharmacy_id}", response_model=List[BankAccount], dependencies=[Depends(require_api_key)])
def list_bank_accounts(
    pharmacy_id: int,
    include_inactive: bool = Query(False, description="Include inactive bank accounts")
):
    """
    List all bank accounts for a specific pharmacy.
    
    - **pharmacy_id**: ID of the pharmacy
    - **include_inactive**: Whether to include inactive accounts (default: false)
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Verify pharmacy exists
        cur.execute(
            "SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s",
            (pharmacy_id,)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pharmacy not found")
        
        # Query bank accounts
        if include_inactive:
            cur.execute("""
                SELECT id, pharmacy_id, name, bank_name, account_number, branch_code,
                       currency, is_active, created_at, updated_at
                FROM pharma.bank_accounts
                WHERE pharmacy_id = %s
                ORDER BY created_at DESC
            """, (pharmacy_id,))
        else:
            cur.execute("""
                SELECT id, pharmacy_id, name, bank_name, account_number, branch_code,
                       currency, is_active, created_at, updated_at
                FROM pharma.bank_accounts
                WHERE pharmacy_id = %s AND is_active = true
                ORDER BY created_at DESC
            """, (pharmacy_id,))
        
        return cur.fetchall()


@router.get("/{bank_account_id}", response_model=BankAccount, dependencies=[Depends(require_api_key)])
def get_bank_account(bank_account_id: int):
    """
    Get a specific bank account by ID.
    
    - **bank_account_id**: ID of the bank account
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, pharmacy_id, name, bank_name, account_number, branch_code,
                   currency, is_active, created_at, updated_at
            FROM pharma.bank_accounts
            WHERE id = %s
        """, (bank_account_id,))
        
        account = cur.fetchone()
        if not account:
            raise HTTPException(status_code=404, detail="Bank account not found")
        
        return account


@router.put("/{bank_account_id}", response_model=BankAccount, dependencies=[Depends(require_api_key)])
def update_bank_account(bank_account_id: int, update: BankAccountUpdate):
    """
    Update a bank account.
    
    Only provided fields will be updated.
    
    - **bank_account_id**: ID of the bank account to update
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Check if account exists
        cur.execute("SELECT id FROM pharma.bank_accounts WHERE id = %s", (bank_account_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Bank account not found")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if update.name is not None:
            updates.append("name = %s")
            params.append(update.name)
        
        if update.bank_name is not None:
            updates.append("bank_name = %s")
            params.append(update.bank_name)
        
        if update.account_number is not None:
            updates.append("account_number = %s")
            params.append(update.account_number)
        
        if update.branch_code is not None:
            updates.append("branch_code = %s")
            params.append(update.branch_code)
        
        if update.is_active is not None:
            updates.append("is_active = %s")
            params.append(update.is_active)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Add updated_at
        updates.append("updated_at = NOW()")
        params.append(bank_account_id)
        
        query = f"""
            UPDATE pharma.bank_accounts
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, pharmacy_id, name, bank_name, account_number, branch_code,
                     currency, is_active, created_at, updated_at
        """
        
        cur.execute(query, params)
        result = cur.fetchone()
        conn.commit()
        
        return result


@router.delete("/{bank_account_id}", dependencies=[Depends(require_api_key)])
def delete_bank_account(bank_account_id: int):
    """
    Soft delete a bank account by setting is_active to false.
    
    - **bank_account_id**: ID of the bank account to deactivate
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Check if account exists
        cur.execute("SELECT id FROM pharma.bank_accounts WHERE id = %s", (bank_account_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Bank account not found")
        
        # Soft delete
        cur.execute("""
            UPDATE pharma.bank_accounts
            SET is_active = false, updated_at = NOW()
            WHERE id = %s
        """, (bank_account_id,))
        
        conn.commit()
        return {"message": "Bank account deactivated successfully"}

