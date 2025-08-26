from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from ..db import get_conn
from ..schemas import ProductUsage, ProductUsagePage
from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies/{pid}/usage", tags=["usage"], dependencies=[Depends(require_api_key)])

@router.get("/top-180d", response_model=ProductUsagePage)
def top_usage_180d(pid: int, limit: int = Query(10, ge=1, le=200)):
    if pid == 100:
        # Group-level: compute on-the-fly across all pharmacies
        sql = """
        WITH sums AS (
          SELECT 
            p.product_code,
            p.description,
            COALESCE(SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '29 days'  THEN f.qty_sold END),0)/30.0  AS avg_qty_30d,
            COALESCE(SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '89 days'  THEN f.qty_sold END),0)/90.0  AS avg_qty_90d,
            COALESCE(SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '179 days' THEN f.qty_sold END),0)/180.0 AS avg_qty_180d
          FROM pharma.fact_stock_activity f
          JOIN pharma.products p ON p.product_id = f.product_id
          WHERE f.business_date >= CURRENT_DATE - INTERVAL '179 days'
            AND f.qty_sold > 0
          GROUP BY p.product_code, p.description
        )
        SELECT product_code, description,
               ROUND(avg_qty_30d::numeric, 3) AS avg_qty_30d,
               ROUND(avg_qty_90d::numeric, 3) AS avg_qty_90d,
               ROUND(avg_qty_180d::numeric,3) AS avg_qty_180d,
               now()::timestamptz AS last_recalc
        FROM sums
        ORDER BY avg_qty_180d DESC
        LIMIT %s
        """
        params = (limit,)
    else:
        sql = """
        SELECT p.product_code, p.description, u.avg_qty_30d, u.avg_qty_90d, u.avg_qty_180d, u.last_recalc
        FROM pharma.product_usage u
        JOIN pharma.products p ON p.product_id = u.product_id
        WHERE u.pharmacy_id = %s AND u.avg_qty_180d IS NOT NULL
        ORDER BY u.avg_qty_180d DESC
        LIMIT %s
        """
        params = (pid, limit)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return {"items": rows}

@router.get("/product/{product_code}", response_model=ProductUsage)
def product_usage(pid: int, product_code: str):
    if pid == 100:
        # Group-level for a specific product: compute on-the-fly across all pharmacies
        sql = """
        WITH sums AS (
          SELECT 
            COALESCE(SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '29 days'  THEN f.qty_sold END),0)/30.0  AS avg_qty_30d,
            COALESCE(SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '89 days'  THEN f.qty_sold END),0)/90.0  AS avg_qty_90d,
            COALESCE(SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '179 days' THEN f.qty_sold END),0)/180.0 AS avg_qty_180d
          FROM pharma.fact_stock_activity f
          JOIN pharma.products p ON p.product_id = f.product_id
          WHERE p.product_code = %s
            AND f.business_date >= CURRENT_DATE - INTERVAL '179 days'
            AND f.qty_sold > 0
        )
        SELECT p.product_code, p.description,
               ROUND(s.avg_qty_30d::numeric, 3) AS avg_qty_30d,
               ROUND(s.avg_qty_90d::numeric, 3) AS avg_qty_90d,
               ROUND(s.avg_qty_180d::numeric,3) AS avg_qty_180d,
               now()::timestamptz AS last_recalc
        FROM pharma.products p, sums s
        WHERE p.product_code = %s
        """
        params = (product_code, product_code)
    else:
        sql = """
        SELECT p.product_code, p.description, u.avg_qty_30d, u.avg_qty_90d, u.avg_qty_180d, u.last_recalc
        FROM pharma.product_usage u
        JOIN pharma.products p ON p.product_id = u.product_id
        WHERE u.pharmacy_id = %s AND p.product_code = %s
        """
        params = (pid, product_code)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Usage not found for product")
        return row 