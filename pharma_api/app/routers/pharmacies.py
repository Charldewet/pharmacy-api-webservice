from fastapi import APIRouter, Depends
from typing import List
from ..db import get_conn
from ..schemas import Pharmacy
from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies", tags=["pharmacies"], dependencies=[Depends(require_api_key)])

@router.get("", response_model=List[Pharmacy])
def list_pharmacies():
    from ..db import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT pharmacy_id, name FROM pharma.pharmacies WHERE is_active ORDER BY pharmacy_id;")
        return cur.fetchall()
