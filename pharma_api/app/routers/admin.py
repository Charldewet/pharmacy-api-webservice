from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import FileResponse
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from pathlib import Path
from ..db import get_conn
from ..auth import get_current_user_id, require_api_key, get_user_id_or_api_key
from ..schemas import Account, AccountCreate
import hashlib

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin user IDs
CHARL_USER_ID = 2
AMIN_USER_ID = 9
ADMIN_USER_IDS = {CHARL_USER_ID, AMIN_USER_ID}

def require_charl(user_id: int = Depends(get_current_user_id)) -> int:
    """Only allow admin users (Charl and Amin) to access admin endpoints"""
    if user_id not in ADMIN_USER_IDS:
        raise HTTPException(status_code=403, detail="Admin access restricted to authorized users only")
    return user_id

def check_pharmacy_access(user_id: int, pharmacy_id: int, require_write: bool = False) -> None:
    """Check if user has access to a pharmacy"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT can_read, can_write
            FROM pharma.user_pharmacies
            WHERE user_id = %s AND pharmacy_id = %s
        """, (user_id, pharmacy_id))
        
        access = cur.fetchone()
        if not access:
            raise HTTPException(status_code=403, detail=f"Access denied to pharmacy {pharmacy_id}")
        
        if not access['can_read']:
            raise HTTPException(status_code=403, detail=f"Read access denied to pharmacy {pharmacy_id}")
        
        if require_write and not access['can_write']:
            raise HTTPException(status_code=403, detail=f"Write access denied to pharmacy {pharmacy_id}")

# Request/Response Models
class UserListItem(BaseModel):
    user_id: int
    username: str
    email: str
    is_active: bool
    created_at: str
    pharmacy_count: int

class UserDetail(BaseModel):
    user_id: int
    username: str
    email: str
    is_active: bool
    created_at: str
    pharmacies: List[dict]

class CreateUserRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    pharmacy_ids: Optional[List[int]] = None
    can_write: bool = False

class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class GrantPharmacyAccessRequest(BaseModel):
    pharmacy_id: int
    can_read: bool = True
    can_write: bool = False

def _sha256(s: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

@router.get("/users", response_model=List[UserListItem])
def list_users(user_id: int = Depends(require_charl)):
    """List all users in the system"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT 
                u.user_id,
                u.username,
                u.email,
                u.is_active,
                u.created_at,
                COUNT(up.pharmacy_id) as pharmacy_count
            FROM pharma.users u
            LEFT JOIN pharma.user_pharmacies up ON up.user_id = u.user_id
            GROUP BY u.user_id, u.username, u.email, u.is_active, u.created_at
            ORDER BY u.user_id
        """)
        
        users = []
        for row in cur.fetchall():
            users.append(UserListItem(
                user_id=row['user_id'],
                username=row['username'],
                email=row['email'],
                is_active=row['is_active'],
                created_at=row['created_at'].isoformat() if row['created_at'] else '',
                pharmacy_count=row['pharmacy_count']
            ))
        
        return users

@router.get("/users/{user_id}", response_model=UserDetail)
def get_user(user_id_param: int, user_id: int = Depends(require_charl)):
    """Get detailed information about a specific user"""
    with get_conn() as conn, conn.cursor() as cur:
        # Get user info
        cur.execute("""
            SELECT user_id, username, email, is_active, created_at
            FROM pharma.users
            WHERE user_id = %s
        """, (user_id_param,))
        
        user_row = cur.fetchone()
        if not user_row:
            raise HTTPException(status_code=404, detail=f"User ID {user_id_param} not found")
        
        # Get pharmacy access
        cur.execute("""
            SELECT 
                p.pharmacy_id,
                p.name as pharmacy_name,
                up.can_read,
                up.can_write
            FROM pharma.user_pharmacies up
            JOIN pharma.pharmacies p ON p.pharmacy_id = up.pharmacy_id
            WHERE up.user_id = %s
            ORDER BY p.pharmacy_id
        """, (user_id_param,))
        
        pharmacies = []
        for row in cur.fetchall():
            pharmacies.append({
                "pharmacy_id": row['pharmacy_id'],
                "pharmacy_name": row['pharmacy_name'],
                "can_read": row['can_read'],
                "can_write": row['can_write']
            })
        
        return UserDetail(
            user_id=user_row['user_id'],
            username=user_row['username'],
            email=user_row['email'],
            is_active=user_row['is_active'],
            created_at=user_row['created_at'].isoformat() if user_row['created_at'] else '',
            pharmacies=pharmacies
        )

@router.post("/users", response_model=UserDetail)
def create_user(req: CreateUserRequest, user_id: int = Depends(require_charl)):
    """Create a new user"""
    password_hash = _sha256(req.password)
    
    with get_conn() as conn, conn.cursor() as cur:
        # Check if user already exists
        cur.execute("""
            SELECT user_id FROM pharma.users 
            WHERE username = %s OR email = %s
        """, (req.username, req.email))
        
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        # Create user
        cur.execute("""
            INSERT INTO pharma.users (username, email, password_hash, is_active)
            VALUES (%s, %s, %s, true)
            RETURNING user_id
        """, (req.username, req.email, password_hash))
        
        new_user_id = cur.fetchone()['user_id']
        
        # Grant pharmacy access if specified
        if req.pharmacy_ids:
            for pharmacy_id in req.pharmacy_ids:
                cur.execute("""
                    INSERT INTO pharma.user_pharmacies (user_id, pharmacy_id, can_read, can_write)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, pharmacy_id) DO UPDATE SET
                        can_read = EXCLUDED.can_read,
                        can_write = EXCLUDED.can_write
                """, (new_user_id, pharmacy_id, True, req.can_write))
        
        conn.commit()
        
        # Return created user
        return get_user(new_user_id, user_id)

@router.put("/users/{user_id_param}", response_model=UserDetail)
def update_user(user_id_param: int, req: UpdateUserRequest, user_id: int = Depends(require_charl)):
    """Update user information (email, password, status)"""
    with get_conn() as conn, conn.cursor() as cur:
        # Check if user exists
        cur.execute("SELECT user_id FROM pharma.users WHERE user_id = %s", (user_id_param,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"User ID {user_id_param} not found")
        
        # Build update query dynamically
        updates = []
        params = []
        
        if req.email is not None:
            # Check if email already exists for another user
            cur.execute("SELECT user_id FROM pharma.users WHERE email = %s AND user_id != %s", 
                       (req.email, user_id_param))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Email already in use")
            updates.append("email = %s")
            params.append(req.email)
        
        if req.password is not None:
            password_hash = _sha256(req.password)
            updates.append("password_hash = %s")
            params.append(password_hash)
        
        if req.is_active is not None:
            updates.append("is_active = %s")
            params.append(req.is_active)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        params.append(user_id_param)
        sql = f"UPDATE pharma.users SET {', '.join(updates)} WHERE user_id = %s"
        cur.execute(sql, params)
        conn.commit()
        
        # Return updated user
        return get_user(user_id_param, user_id)

@router.post("/users/{user_id_param}/pharmacies", response_model=UserDetail)
def grant_pharmacy_access(user_id_param: int, req: GrantPharmacyAccessRequest, 
                         user_id: int = Depends(require_charl)):
    """Grant or update pharmacy access for a user"""
    with get_conn() as conn, conn.cursor() as cur:
        # Check if user exists
        cur.execute("SELECT user_id FROM pharma.users WHERE user_id = %s", (user_id_param,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"User ID {user_id_param} not found")
        
        # Check if pharmacy exists
        cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", 
                   (req.pharmacy_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Pharmacy ID {req.pharmacy_id} not found")
        
        # Grant/update access
        cur.execute("""
            INSERT INTO pharma.user_pharmacies (user_id, pharmacy_id, can_read, can_write)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, pharmacy_id) DO UPDATE SET
                can_read = EXCLUDED.can_read,
                can_write = EXCLUDED.can_write
        """, (user_id_param, req.pharmacy_id, req.can_read, req.can_write))
        
        conn.commit()
        
        # Return updated user
        return get_user(user_id_param, user_id)

@router.delete("/users/{user_id_param}/pharmacies/{pharmacy_id}", response_model=UserDetail)
def revoke_pharmacy_access(user_id_param: int, pharmacy_id: int, 
                          user_id: int = Depends(require_charl)):
    """Revoke pharmacy access for a user"""
    with get_conn() as conn, conn.cursor() as cur:
        # Remove access
        cur.execute("""
            DELETE FROM pharma.user_pharmacies 
            WHERE user_id = %s AND pharmacy_id = %s
        """, (user_id_param, pharmacy_id))
        
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, 
                              detail=f"No access found for user {user_id_param} to pharmacy {pharmacy_id}")
        
        conn.commit()
        
        # Return updated user
        return get_user(user_id_param, user_id)

@router.get("/pharmacies", response_model=List[dict])
def list_pharmacies(user_id: int = Depends(require_charl)):
    """List all available pharmacies"""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT pharmacy_id, name, is_active
            FROM pharma.pharmacies
            ORDER BY pharmacy_id
        """)
        
        pharmacies = []
        for row in cur.fetchall():
            pharmacies.append({
                "pharmacy_id": row['pharmacy_id'],
                "name": row['name'],
                "is_active": row['is_active']
            })
        
        return pharmacies

# ========== TARGETS ENDPOINTS ==========

class TargetItem(BaseModel):
    date: str
    value: float

class TargetsResponse(BaseModel):
    pharmacy_id: int
    month: str
    targets: List[TargetItem]

class SaveTargetsResponse(BaseModel):
    success: bool
    message: str
    saved_count: int
    pharmacy_id: int
    month: str

@router.get("/pharmacies/{pharmacy_id}/targets", response_model=TargetsResponse)
def get_pharmacy_targets(
    pharmacy_id: int,
    month: str = Query(..., description="Month in YYYY-MM format"),
    user_id: Optional[int] = Depends(get_user_id_or_api_key)
):
    """Get all targets for a pharmacy within a specific month
    
    Accepts either:
    - API key: Use 'Authorization: Bearer <api-key>' or 'X-API-Key: <api-key>' header (no permission check)
    - JWT token: Use 'Authorization: Bearer <jwt-token>' header (checks user permissions)
    """
    # If user_id is provided (JWT token), check permissions
    # If user_id is None (API key), skip permission check
    if user_id is not None:
        check_pharmacy_access(user_id, pharmacy_id, require_write=False)
    
    # Validate month format
    try:
        year, month_num = month.split('-')
        year = int(year)
        month_num = int(month_num)
        if month_num < 1 or month_num > 12:
            raise ValueError("Month must be between 1 and 12")
        month_start = date(year, month_num, 1)
        # Calculate month end
        if month_num == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month_num + 1, 1)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format")
    
    # Check pharmacy exists
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Pharmacy ID {pharmacy_id} not found")
        
        # Get targets for the month
        cur.execute("""
            SELECT date, target_value
            FROM pharma.pharmacy_targets
            WHERE pharmacy_id = %s
              AND date >= %s
              AND date < %s
            ORDER BY date
        """, (pharmacy_id, month_start, month_end))
        
        targets = []
        for row in cur.fetchall():
            targets.append(TargetItem(
                date=row['date'].isoformat(),
                value=float(row['target_value'])
            ))
        
        return TargetsResponse(
            pharmacy_id=pharmacy_id,
            month=month,
            targets=targets
        )

@router.post("/pharmacies/{pharmacy_id}/targets", response_model=SaveTargetsResponse)
def save_pharmacy_targets(
    pharmacy_id: int,
    month: str = Query(..., description="Month in YYYY-MM format"),
    targets_data: Dict[str, float] = Body(...),
    user_id: Optional[int] = Depends(get_user_id_or_api_key)
):
    """Save or update targets for a pharmacy and month
    
    Accepts either:
    - API key: Use 'Authorization: Bearer <api-key>' or 'X-API-Key: <api-key>' header (no permission check)
    - JWT token: Use 'Authorization: Bearer <jwt-token>' header (checks user permissions)
    """
    # If user_id is provided (JWT token), check permissions
    # If user_id is None (API key), skip permission check
    if user_id is not None:
        check_pharmacy_access(user_id, pharmacy_id, require_write=True)
    
    if not targets_data or len(targets_data) == 0:
        raise HTTPException(status_code=400, detail="No targets provided")
    
    # Validate month format
    try:
        year, month_num = month.split('-')
        year = int(year)
        month_num = int(month_num)
        if month_num < 1 or month_num > 12:
            raise ValueError("Month must be between 1 and 12")
        month_start = date(year, month_num, 1)
        # Calculate month end
        if month_num == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month_num + 1, 1)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format")
    
    # Check pharmacy exists
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE pharmacy_id = %s", (pharmacy_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Pharmacy ID {pharmacy_id} not found")
        
        saved_count = 0
        now = datetime.now()
        
        for date_str, target_value in targets_data.items():
            # Validate date format
            try:
                target_date = date.fromisoformat(date_str)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Must be YYYY-MM-DD")
            
            # Validate date is within the specified month
            if target_date < month_start or target_date >= month_end:
                raise HTTPException(
                    status_code=400,
                    detail=f"Date {date_str} is outside the specified month {month}"
                )
            
            # Validate target value
            if target_value < 0:
                raise HTTPException(status_code=400, detail=f"Target value cannot be negative: {target_value}")
            
            if target_value > 10000000:  # Reasonable maximum
                raise HTTPException(status_code=400, detail=f"Target value too large: {target_value}")
            
            # Upsert target
            cur.execute("""
                INSERT INTO pharma.pharmacy_targets (
                    pharmacy_id, date, target_value, created_by_user_id, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (pharmacy_id, date) DO UPDATE SET
                    target_value = EXCLUDED.target_value,
                    updated_at = EXCLUDED.updated_at,
                    created_by_user_id = COALESCE(EXCLUDED.created_by_user_id, pharma.pharmacy_targets.created_by_user_id)
            """, (pharmacy_id, target_date, target_value, user_id, now, now))
            
            saved_count += 1
        
        conn.commit()
        
        return SaveTargetsResponse(
            success=True,
            message="Targets saved successfully",
            saved_count=saved_count,
            pharmacy_id=pharmacy_id,
            month=month
        )

@router.delete("/pharmacies/{pharmacy_id}/targets/{target_date}")
def delete_pharmacy_target(
    pharmacy_id: int,
    target_date: str,
    user_id: Optional[int] = Depends(get_user_id_or_api_key)
):
    """Delete a specific target for a pharmacy and date
    
    Accepts either:
    - API key: Use 'Authorization: Bearer <api-key>' or 'X-API-Key: <api-key>' header (no permission check)
    - JWT token: Use 'Authorization: Bearer <jwt-token>' header (checks user permissions)
    """
    # If user_id is provided (JWT token), check permissions
    # If user_id is None (API key), skip permission check
    if user_id is not None:
        check_pharmacy_access(user_id, pharmacy_id, require_write=True)
    
    # Validate date format
    try:
        date_obj = date.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {target_date}. Must be YYYY-MM-DD")
    
    with get_conn() as conn, conn.cursor() as cur:
        # Check if target exists
        cur.execute("""
            SELECT id FROM pharma.pharmacy_targets
            WHERE pharmacy_id = %s AND date = %s
        """, (pharmacy_id, date_obj))
        
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Target not found for pharmacy {pharmacy_id} on {target_date}")
        
        # Delete target
        cur.execute("""
            DELETE FROM pharma.pharmacy_targets
            WHERE pharmacy_id = %s AND date = %s
        """, (pharmacy_id, date_obj))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "Target deleted successfully"
        }

@router.post("/chart-of-accounts", response_model=Account, dependencies=[Depends(require_api_key)])
def create_chart_of_account(account: AccountCreate):
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

@router.get("/", response_class=FileResponse)
def admin_interface():
    """Serve the admin interface HTML page"""
    template_path = Path(__file__).parent.parent.parent / "templates" / "admin.html"
    return FileResponse(template_path)

