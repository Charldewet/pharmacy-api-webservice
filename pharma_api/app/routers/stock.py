from fastapi import APIRouter, Depends, Query
from typing import Optional
from ..db import get_conn
from ..schemas import StockPage
from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies/{pid}/stock-activity", tags=["stock"], dependencies=[Depends(require_api_key)])

@router.get("", response_model=StockPage)
def stock_activity(pid: int, date: str, limit: int = Query(50, ge=1, le=200), cursor: Optional[str] = None):
    where_cur = ""
    params = []
    if cursor:
        sv, prod_id = cursor.split(":")
        where_cur = "AND (f.sales_val, f.product_id) < (%s::numeric, %s::bigint)"
        params += [sv, prod_id]
    params += [limit]
    if pid == 100:
        sql = f"""
        SELECT f.department_code, f.product_code, f.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.v_stock_activity_group f
        WHERE f.business_date = %s
        {where_cur}
        ORDER BY f.sales_val DESC NULLS LAST, f.product_id
        LIMIT %s
        """
        params = [date] + params
    else:
        sql = f"""
        SELECT d.department_code, pr.product_code, pr.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.fact_stock_activity f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        LEFT JOIN pharma.departments d ON d.department_id = f.department_id
        WHERE f.pharmacy_id = %s AND f.business_date = %s
        {where_cur}
        ORDER BY f.sales_val DESC NULLS LAST, f.product_id
        LIMIT %s
        """
        params = [pid, date] + params
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
    next_cur = None
    if rows:
        last = rows[-1]
        next_cur = f"{last['sales_val']}:{last['product_id']}"
    return {"items": rows, "nextCursor": next_cur}

@router.get("/by-quantity", response_model=StockPage)
def stock_activity_by_quantity(pid: int, date: str, limit: int = Query(50, ge=1, le=200)):
    if pid == 100:
        sql = """
        SELECT f.department_code, f.product_code, f.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.v_stock_activity_group f
        WHERE f.business_date = %s
        ORDER BY f.qty_sold DESC NULLS LAST, f.product_id
        LIMIT %s
        """
        params = (date, limit)
    else:
        sql = """
        SELECT d.department_code, pr.product_code, pr.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.fact_stock_activity f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        LEFT JOIN pharma.departments d ON d.department_id = f.department_id
        WHERE f.pharmacy_id = %s AND f.business_date = %s
        ORDER BY f.qty_sold DESC NULLS LAST, f.product_id
        LIMIT %s
        """
        params = (pid, date, limit)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return {"items": rows, "nextCursor": None}

@router.get("/worst-gp", response_model=StockPage)
def stock_activity_worst_gp(pid: int, date: str, limit: int = Query(50, ge=1, le=200)):
    if pid == 100:
        sql = """
        SELECT f.department_code, f.product_code, f.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.v_stock_activity_group f
        WHERE f.business_date = %s AND f.gp_pct IS NOT NULL
        ORDER BY f.gp_pct ASC NULLS LAST, f.product_id
        LIMIT %s
        """
        params = (date, limit)
    else:
        sql = """
        SELECT d.department_code, pr.product_code, pr.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.fact_stock_activity f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        LEFT JOIN pharma.departments d ON d.department_id = f.department_id
        WHERE f.pharmacy_id = %s AND f.business_date = %s AND f.gp_pct IS NOT NULL
        ORDER BY f.gp_pct ASC NULLS LAST, f.product_id
        LIMIT %s
        """
        params = (pid, date, limit)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return {"items": rows, "nextCursor": None}

@router.get("/negative-soh", response_model=StockPage)
def stock_activity_negative_soh(pid: int, date: str, limit: int = Query(50, ge=1, le=200)):
    """Return items where on_hand < 0 for the given day, ordered by most negative."""
    if pid == 100:
        sql = """
        SELECT f.department_code, f.product_code, f.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.v_stock_activity_group f
        WHERE f.business_date = %s AND f.on_hand < 0
        ORDER BY f.on_hand ASC, f.product_id
        LIMIT %s
        """
        params = (date, limit)
    else:
        sql = """
        SELECT d.department_code, pr.product_code, pr.description,
               f.qty_sold, f.sales_val, f.cost_of_sales, f.gp_value, f.gp_pct, f.on_hand,
               f.product_id
        FROM pharma.fact_stock_activity f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        LEFT JOIN pharma.departments d ON d.department_id = f.department_id
        WHERE f.pharmacy_id = %s AND f.business_date = %s AND f.on_hand < 0
        ORDER BY f.on_hand ASC, f.product_id
        LIMIT %s
        """
        params = (pid, date, limit)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return {"items": rows, "nextCursor": None}
