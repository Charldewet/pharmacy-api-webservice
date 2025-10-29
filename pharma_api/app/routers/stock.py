from fastapi import APIRouter, Depends, Query
from typing import Optional
from ..db import get_conn
from ..schemas import StockPage, BestSellerPage, LowGPPage
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

@router.get("/by-quantity/range", response_model=BestSellerPage)
def best_sellers_by_quantity(
    pid: int,
    from_date: str = Query(..., alias="from", description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., alias="to", description="End date YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=200)
):
    """
    Returns the top-selling products by quantity sold within the specified date range,
    aggregated across all days in that range.
    """
    if pid == 100:
        sql = """
        SELECT 
            pr.description as product_name,
            pr.product_code as nappi_code,
            SUM(f.qty_sold) as quantity_sold,
            SUM(f.sales_val) as total_sales,
            CASE 
                WHEN SUM(f.sales_val) > 0 
                THEN ROUND((SUM(f.gp_value) / SUM(f.sales_val) * 100)::numeric, 2)
                ELSE NULL 
            END as gp_percent
        FROM pharma.v_stock_activity_group f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        WHERE f.business_date BETWEEN %s AND %s
        GROUP BY pr.product_code, pr.description
        HAVING SUM(f.qty_sold) > 0
        ORDER BY quantity_sold DESC NULLS LAST
        LIMIT %s
        """
        params = (from_date, to_date, limit)
    else:
        sql = """
        SELECT 
            pr.description as product_name,
            pr.product_code as nappi_code,
            SUM(f.qty_sold) as quantity_sold,
            SUM(f.sales_val) as total_sales,
            CASE 
                WHEN SUM(f.sales_val) > 0 
                THEN ROUND((SUM(f.gp_value) / SUM(f.sales_val) * 100)::numeric, 2)
                ELSE NULL 
            END as gp_percent
        FROM pharma.fact_stock_activity f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        WHERE f.pharmacy_id = %s 
          AND f.business_date BETWEEN %s AND %s
        GROUP BY pr.product_code, pr.description
        HAVING SUM(f.qty_sold) > 0
        ORDER BY quantity_sold DESC NULLS LAST
        LIMIT %s
        """
        params = (pid, from_date, to_date, limit)
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    
    return {"items": rows}

@router.get("/low-gp/range", response_model=LowGPPage)
def low_gp_products(
    pid: int,
    from_date: str = Query(..., alias="from", description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., alias="to", description="End date YYYY-MM-DD"),
    threshold: float = Query(..., description="Maximum GP% to include (e.g., 20 for GP% ≤ 20%)"),
    limit: int = Query(100, ge=1, le=500),
    exclude_pdst: bool = Query(False, description="Exclude PDST/KSAA products")
):
    """
    Returns products with GP% at or below the specified threshold within the date range,
    aggregated across all days. Excludes products with zero or negative turnover.
    """
    # Build PDST/KSAA exclusion filter (use pattern matching for PDST## and KSAA## codes)
    # Database has codes like PDST01, PDST02, PDST08, KSAA01, etc. (not just "PDST" or "KSAA")
    if exclude_pdst:
        pdst_filter_group = "AND f.department_code NOT LIKE 'PDST%' AND f.department_code NOT LIKE 'KSAA%'"
        pdst_filter_individual = "AND d.department_code NOT LIKE 'PDST%' AND d.department_code NOT LIKE 'KSAA%'"
    else:
        pdst_filter_group = ""
        pdst_filter_individual = ""
    
    if pid == 100:
        # For group view, department_code comes directly from view
        sql = f"""
        SELECT 
            pr.description as product_name,
            pr.product_code as nappi_code,
            SUM(f.qty_sold) as quantity_sold,
            SUM(f.sales_val) as total_sales,
            SUM(f.cost_of_sales) as total_cost,
            SUM(f.gp_value) as gp_value,
            CASE 
                WHEN SUM(f.sales_val) > 0 
                THEN ROUND((SUM(f.gp_value) / SUM(f.sales_val) * 100)::numeric, 2)
                ELSE NULL 
            END as gp_percent
        FROM pharma.v_stock_activity_group f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        WHERE f.business_date BETWEEN %s AND %s
          {pdst_filter_group}
        GROUP BY pr.product_code, pr.description
        HAVING SUM(f.sales_val) > 0 
          AND (SUM(f.gp_value) / NULLIF(SUM(f.sales_val), 0) * 100) <= %s
        ORDER BY gp_percent ASC NULLS LAST
        LIMIT %s
        """
        params = (from_date, to_date, threshold, limit)
    else:
        sql = f"""
        SELECT 
            pr.description as product_name,
            pr.product_code as nappi_code,
            SUM(f.qty_sold) as quantity_sold,
            SUM(f.sales_val) as total_sales,
            SUM(f.cost_of_sales) as total_cost,
            SUM(f.gp_value) as gp_value,
            CASE 
                WHEN SUM(f.sales_val) > 0 
                THEN ROUND((SUM(f.gp_value) / SUM(f.sales_val) * 100)::numeric, 2)
                ELSE NULL 
            END as gp_percent
        FROM pharma.fact_stock_activity f
        JOIN pharma.products pr ON pr.product_id = f.product_id
        LEFT JOIN pharma.departments d ON d.department_id = f.department_id
        WHERE f.pharmacy_id = %s 
          AND f.business_date BETWEEN %s AND %s
          {pdst_filter_individual}
        GROUP BY pr.product_code, pr.description
        HAVING SUM(f.sales_val) > 0 
          AND (SUM(f.gp_value) / NULLIF(SUM(f.sales_val), 0) * 100) <= %s
        ORDER BY gp_percent ASC NULLS LAST
        LIMIT %s
        """
        params = (pid, from_date, to_date, threshold, limit)
    
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    
    return {"items": rows}
