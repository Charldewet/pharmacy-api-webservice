from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from ..db import get_conn
from ..schemas import ProductUsage, ProductUsagePage
from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies/{pid}/usage", tags=["usage"], dependencies=[Depends(require_api_key)])

@router.get("/top-180d", response_model=ProductUsagePage)
def top_usage_180d(pid: int, limit: int = Query(10, ge=1, le=200)):
    sql = """
    SELECT p.product_code, p.description, u.avg_qty_30d, u.avg_qty_90d, u.avg_qty_180d, u.last_recalc
    FROM pharma.product_usage u
    JOIN pharma.products p ON p.product_id = u.product_id
    WHERE u.pharmacy_id = %s AND u.avg_qty_180d IS NOT NULL
    ORDER BY u.avg_qty_180d DESC
    LIMIT %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (pid, limit))
        rows = cur.fetchall()
        return {"items": rows}

@router.get("/product/{product_code}", response_model=ProductUsage)
def product_usage(pid: int, product_code: str):
    sql = """
    SELECT p.product_code, p.description, u.avg_qty_30d, u.avg_qty_90d, u.avg_qty_180d, u.last_recalc
    FROM pharma.product_usage u
    JOIN pharma.products p ON p.product_id = u.product_id
    WHERE u.pharmacy_id = %s AND p.product_code = %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (pid, product_code))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Usage not found for product")
        return row 