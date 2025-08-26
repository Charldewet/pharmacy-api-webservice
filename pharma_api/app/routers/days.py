from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from ..db import get_conn
from ..schemas import DailySales
from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies/{pid}/days", tags=["daily"], dependencies=[Depends(require_api_key)])

@router.get("", response_model=List[DailySales])
def list_days(pid: int, from_: str = Query(..., alias="from"), to: str = Query(..., alias="to")):
    # Use group view for TLC GROUP (pharmacy_id=100), else normal per-pharmacy view
    sql = (
        """
        SELECT * FROM pharma.v_daily_sales_group
        WHERE pharmacy_id = %s AND business_date BETWEEN %s AND %s
        ORDER BY business_date
        """
        if pid == 100
        else
        """
        SELECT * FROM pharma.v_daily_sales
        WHERE pharmacy_id = %s AND business_date BETWEEN %s AND %s
        ORDER BY business_date
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (pid, from_, to))
        return cur.fetchall()

@router.get("/{bdate}", response_model=DailySales)
def one_day(pid: int, bdate: str):
    # Use group view for TLC GROUP (pharmacy_id=100), else normal per-pharmacy view
    sql = (
        """
        SELECT * FROM pharma.v_daily_sales_group
        WHERE pharmacy_id = %s AND business_date = %s
        """
        if pid == 100
        else
        """
        SELECT * FROM pharma.v_daily_sales
        WHERE pharmacy_id = %s AND business_date = %s
        """
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (pid, bdate))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        return row
