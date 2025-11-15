from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from ..db import get_conn
from ..auth import get_current_user_id
import hashlib

router = APIRouter(prefix="/admin", tags=["admin"])

# Charl's user_id is 2
CHARL_USER_ID = 2

def require_charl(user_id: int = Depends(get_current_user_id)) -> int:
    """Only allow Charl to access admin endpoints"""
    if user_id != CHARL_USER_ID:
        raise HTTPException(status_code=403, detail="Admin access restricted to Charl only")
    return user_id

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

