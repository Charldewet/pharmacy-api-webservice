from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..db import get_conn
from ..schemas import Pharmacy
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
