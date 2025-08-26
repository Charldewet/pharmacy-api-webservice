from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..db import get_conn
from ..auth import require_api_key
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_api_key)])

class UserPharmacyAccess(BaseModel):
    pharmacy_id: int
    pharmacy_name: str
    can_read: bool
    can_write: bool

class UserPharmacyAccessResponse(BaseModel):
    user_id: int
    username: str
    pharmacies: List[UserPharmacyAccess]

class GrantAccessRequest(BaseModel):
    pharmacy_id: int
    can_read: bool = True
    can_write: bool = False

@router.get("/{username}/pharmacies", response_model=UserPharmacyAccessResponse)
def get_user_pharmacies(username: str):
    """Get all pharmacies a user has access to"""
    with get_conn() as conn, conn.cursor() as cur:
        # Get user info
        cur.execute("""
            SELECT user_id, username 
            FROM pharma.users 
            WHERE username = %s AND is_active = true
        """, (username,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, f"User '{username}' not found")
        
        # Get pharmacy access
        cur.execute("""
            SELECT 
                up.pharmacy_id,
                p.name as pharmacy_name,
                up.can_read,
                up.can_write
            FROM pharma.user_pharmacies up
            JOIN pharma.pharmacies p ON p.pharmacy_id = up.pharmacy_id
            WHERE up.user_id = %s
            ORDER BY up.pharmacy_id
        """, (user['user_id'],))
        
        pharmacies = []
        for row in cur.fetchall():
            pharmacies.append(UserPharmacyAccess(
                pharmacy_id=row['pharmacy_id'],
                pharmacy_name=row['pharmacy_name'],
                can_read=row['can_read'],
                can_write=row['can_write']
            ))
        
        return UserPharmacyAccessResponse(
            user_id=user['user_id'],
            username=user['username'],
            pharmacies=pharmacies
        )

@router.post("/{username}/pharmacies", response_model=UserPharmacyAccessResponse)
def grant_pharmacy_access(username: str, access: GrantAccessRequest):
    """Grant or update pharmacy access for a user"""
    with get_conn() as conn, conn.cursor() as cur:
        # Get user
        cur.execute("""
            SELECT user_id, username 
            FROM pharma.users 
            WHERE username = %s AND is_active = true
        """, (username,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, f"User '{username}' not found")
        
        # Check if pharmacy exists
        cur.execute("""
            SELECT pharmacy_id, name 
            FROM pharma.pharmacies 
            WHERE pharmacy_id = %s
        """, (access.pharmacy_id,))
        pharmacy = cur.fetchone()
        if not pharmacy:
            raise HTTPException(404, f"Pharmacy ID {access.pharmacy_id} not found")
        
        # Grant/update access
        cur.execute("""
            INSERT INTO pharma.user_pharmacies (user_id, pharmacy_id, can_read, can_write)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, pharmacy_id) DO UPDATE SET
                can_read = EXCLUDED.can_read,
                can_write = EXCLUDED.can_write
        """, (user['user_id'], access.pharmacy_id, access.can_read, access.can_write))
        
        conn.commit()
        
        # Return updated access list
        return get_user_pharmacies(username)

@router.delete("/{username}/pharmacies/{pharmacy_id}")
def revoke_pharmacy_access(username: str, pharmacy_id: int):
    """Revoke pharmacy access for a user"""
    with get_conn() as conn, conn.cursor() as cur:
        # Get user
        cur.execute("""
            SELECT user_id 
            FROM pharma.users 
            WHERE username = %s AND is_active = true
        """, (username,))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, f"User '{username}' not found")
        
        # Remove access
        cur.execute("""
            DELETE FROM pharma.user_pharmacies 
            WHERE user_id = %s AND pharmacy_id = %s
        """, (user['user_id'], pharmacy_id))
        
        if cur.rowcount == 0:
            raise HTTPException(404, f"No access found for user '{username}' to pharmacy {pharmacy_id}")
        
        conn.commit()
        return {"message": f"Access revoked for user '{username}' to pharmacy {pharmacy_id}"}

@router.get("/{username}/pharmacies/{pharmacy_id}/check")
def check_pharmacy_access(username: str, pharmacy_id: int, action: str = Query("read", description="Action to check: 'read' or 'write'")):
    """Check if user has access to a specific pharmacy"""
    with get_conn() as conn, conn.cursor() as cur:
        # Get user access
        cur.execute("""
            SELECT up.can_read, up.can_write
            FROM pharma.user_pharmacies up
            JOIN pharma.users u ON u.user_id = up.user_id
            WHERE u.username = %s AND u.is_active = true AND up.pharmacy_id = %s
        """, (username, pharmacy_id))
        
        access = cur.fetchone()
        if not access:
            return {"has_access": False, "message": "No access found"}
        
        if action.lower() == "read":
            has_access = access['can_read']
        elif action.lower() == "write":
            has_access = access['can_read'] and access['can_write']
        else:
            raise HTTPException(400, "Action must be 'read' or 'write'")
        
        return {
            "has_access": has_access,
            "can_read": access['can_read'],
            "can_write": access['can_write'],
            "action": action.lower()
        } 