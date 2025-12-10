"""
Chart of Accounts API Router
Provides endpoints for managing and querying the chart of accounts.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..db import get_conn
from ..schemas import Account, AccountCreate, AccountUpdate
from ..auth import require_api_key

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=List[Account], dependencies=[Depends(require_api_key)])
def list_accounts(
    type: Optional[str] = Query(None, description="Filter by account type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    include_inactive: bool = Query(False, description="Include inactive accounts")
):
    """
    List all accounts in the chart of accounts.
    
    Supports filtering by:
    - **type**: Account type (ASSET, LIABILITY, EQUITY, INCOME, COGS, EXPENSE, FINANCE_COST, OTHER_INCOME, TAX)
    - **category**: Account category (e.g., CURRENT_ASSET, SALES, STAFF_COSTS)
    - **is_active**: Filter by active status
    - **include_inactive**: Include inactive accounts (default: false)
    
    Results are ordered by display_order, then by code.
    """
    with get_conn() as conn, conn.cursor() as cur:
        conditions = []
        params = []
        
        # Build WHERE clause
        if not include_inactive:
            if is_active is None:
                conditions.append("is_active = true")
            elif is_active:
                conditions.append("is_active = true")
            else:
                conditions.append("is_active = false")
        elif is_active is not None:
            conditions.append("is_active = %s")
            params.append(is_active)
        
        if type:
            valid_types = [
                'ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'COGS',
                'EXPENSE', 'FINANCE_COST', 'OTHER_INCOME', 'TAX'
            ]
            if type.upper() not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid account type. Must be one of: {', '.join(valid_types)}"
                )
            conditions.append("type::text = %s")
            params.append(type.upper())
        
        if category:
            conditions.append("category = %s")
            params.append(category)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
            SELECT id, code, name, type::text as type, category, parent_account_id,
                   is_active, display_order, notes, created_at, updated_at
            FROM pharma.accounts
            WHERE {where_clause}
            ORDER BY display_order, code
        """
        
        cur.execute(query, params)
        return cur.fetchall()


@router.post("", response_model=Account, dependencies=[Depends(require_api_key)])
def create_account(account: AccountCreate):
    """
    Create a new account in the chart of accounts.
    
    - **code**: Unique account code (max 10 characters, must be unique)
    - **name**: Display name of the account
    - **type**: Account type (ASSET, LIABILITY, EQUITY, INCOME, COGS, EXPENSE, FINANCE_COST, OTHER_INCOME, TAX)
    - **category**: Account category for grouping
    - **parent_account_id**: Optional ID of parent account if this is a sub-account
    - **is_active**: Whether the account is active (default: true)
    - **display_order**: Order for display/sorting (default: 0)
    - **notes**: Optional notes about the account
    """
    # Validate account type
    valid_types = [
        'ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'COGS',
        'EXPENSE', 'FINANCE_COST', 'OTHER_INCOME', 'TAX'
    ]
    if account.type.upper() not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid account type '{account.type}'. Must be one of: {', '.join(valid_types)}"
        )
    
    # Validate code length
    if len(account.code) > 10:
        raise HTTPException(
            status_code=400,
            detail="Account code must be 10 characters or less"
        )
    
    with get_conn() as conn, conn.cursor() as cur:
        # Check if code already exists
        cur.execute("""
            SELECT id FROM pharma.accounts WHERE code = %s
        """, (account.code,))
        if cur.fetchone():
            raise HTTPException(
                status_code=409,
                detail=f"Account with code '{account.code}' already exists"
            )
        
        # Validate parent_account_id if provided
        if account.parent_account_id is not None:
            cur.execute("""
                SELECT id FROM pharma.accounts WHERE id = %s
            """, (account.parent_account_id,))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail=f"Parent account with ID {account.parent_account_id} not found"
                )
        
        # Insert new account
        cur.execute("""
            INSERT INTO pharma.accounts 
            (code, name, type, category, parent_account_id, is_active, display_order, notes)
            VALUES (%s, %s, %s::pharma.account_type, %s, %s, %s, %s, %s)
            RETURNING id, code, name, type::text as type, category, parent_account_id,
                     is_active, display_order, notes, created_at, updated_at
        """, (
            account.code,
            account.name,
            account.type.upper(),
            account.category,  # Empty string is fine since category is NOT NULL but can be empty
            account.parent_account_id,
            account.is_active,
            account.display_order,
            account.notes
        ))
        
        result = cur.fetchone()
        conn.commit()
        return result


@router.get("/{account_id}", response_model=Account, dependencies=[Depends(require_api_key)])
def get_account(account_id: int):
    """
    Get a specific account by ID.
    
    - **account_id**: ID of the account
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, code, name, type::text as type, category, parent_account_id,
                   is_active, display_order, notes, created_at, updated_at
            FROM pharma.accounts
            WHERE id = %s
        """, (account_id,))
        
        account = cur.fetchone()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return account


@router.get("/code/{account_code}", response_model=Account, dependencies=[Depends(require_api_key)])
def get_account_by_code(account_code: str):
    """
    Get a specific account by code.
    
    - **account_code**: Code of the account (e.g., "4000", "6200")
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT id, code, name, type::text as type, category, parent_account_id,
                   is_active, display_order, notes, created_at, updated_at
            FROM pharma.accounts
            WHERE code = %s
        """, (account_code,))
        
        account = cur.fetchone()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return account


@router.get("/types/list", dependencies=[Depends(require_api_key)])
def list_account_types():
    """
    Get list of all available account types.
    """
    return {
        "types": [
            "ASSET",
            "LIABILITY",
            "EQUITY",
            "INCOME",
            "COGS",
            "EXPENSE",
            "FINANCE_COST",
            "OTHER_INCOME",
            "TAX"
        ]
    }


@router.get("/categories/list", dependencies=[Depends(require_api_key)])
def list_account_categories():
    """
    Get list of all available account categories.
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT category
            FROM pharma.accounts
            WHERE category IS NOT NULL
            ORDER BY category
        """)
        
        categories = [row['category'] for row in cur.fetchall()]
        return {"categories": categories}


@router.get("/summary/stats", dependencies=[Depends(require_api_key)])
def get_accounts_summary():
    """
    Get summary statistics about accounts.
    
    Returns counts by type and category.
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Count by type
        cur.execute("""
            SELECT type::text as type, COUNT(*) as count
            FROM pharma.accounts
            GROUP BY type
            ORDER BY type
        """)
        by_type = {row['type']: row['count'] for row in cur.fetchall()}
        
        # Count by category
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM pharma.accounts
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY category
        """)
        by_category = {row['category']: row['count'] for row in cur.fetchall()}
        
        # Total counts
        cur.execute("SELECT COUNT(*) as total FROM pharma.accounts")
        total = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as active FROM pharma.accounts WHERE is_active = true")
        active = cur.fetchone()['active']
        
        return {
            "total": total,
            "active": active,
            "inactive": total - active,
            "by_type": by_type,
            "by_category": by_category
        }

