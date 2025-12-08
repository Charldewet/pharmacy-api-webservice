from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from datetime import date
from ..db import get_conn
from ..schemas import DailySales, FrontshopDispensaryGP, GPBreakdown
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

@router.get("/{bdate}/gp-breakdown", response_model=FrontshopDispensaryGP)
def get_gp_breakdown(pid: int, bdate: str):
    """
    Get frontshop vs dispensary GP breakdown using line-level GP report data.
    
    Dispensary is calculated from all PDST departments (PDST%).
    Frontshop is calculated from all other departments.
    
    Returns detailed GP breakdown including:
    - Product counts
    - Sales values
    - Cost of sales
    - Gross profit
    - GP percentages
    """
    with get_conn() as conn, conn.cursor() as cur:
        # Validate date format
        try:
            business_date = date.fromisoformat(bdate)
        except ValueError:
            raise HTTPException(status_code=400, detail="Date must be in YYYY-MM-DD format")
        
        # Get GP data for all PDST departments (dispensary)
        cur.execute("""
            SELECT 
                COUNT(*) as product_count,
                COALESCE(SUM(sales_val), 0) as total_sales,
                COALESCE(SUM(cost_of_sales), 0) as total_cost,
                COALESCE(SUM(gp_value), 0) as total_gp
            FROM pharma.fact_stock_activity f
            JOIN pharma.departments d ON f.department_id = d.department_id
            WHERE f.pharmacy_id = %s 
            AND f.business_date = %s
            AND d.department_code LIKE 'PDST' || '%%'
        """, (pid, business_date))
        
        pdst_data = cur.fetchone()
        
        if not pdst_data or not pdst_data['product_count']:
            raise HTTPException(
                status_code=404, 
                detail=f"No GP report data found for pharmacy {pid} on {bdate}. The GP report may not have been imported yet."
            )
        
        # Get total GP data for all products
        cur.execute("""
            SELECT 
                COUNT(*) as product_count,
                COALESCE(SUM(sales_val), 0) as total_sales,
                COALESCE(SUM(cost_of_sales), 0) as total_cost,
                COALESCE(SUM(gp_value), 0) as total_gp
            FROM pharma.fact_stock_activity
            WHERE pharmacy_id = %s 
            AND business_date = %s
        """, (pid, business_date))
        
        total_gp_data = cur.fetchone()
        
        # Get frontshop GP (everything except PDST%)
        cur.execute("""
            SELECT 
                COUNT(*) as product_count,
                COALESCE(SUM(sales_val), 0) as total_sales,
                COALESCE(SUM(cost_of_sales), 0) as total_cost,
                COALESCE(SUM(gp_value), 0) as total_gp
            FROM pharma.fact_stock_activity f
            LEFT JOIN pharma.departments d ON f.department_id = d.department_id
            WHERE f.pharmacy_id = %s 
            AND f.business_date = %s
            AND (d.department_code IS NULL OR d.department_code NOT LIKE 'PDST' || '%%')
        """, (pid, business_date))
        
        frontshop_gp_data = cur.fetchone()
        
        # Get daily sales summary for comparison
        cur.execute("""
            SELECT gp_value as daily_gp
            FROM pharma.v_daily_sales
            WHERE pharmacy_id = %s AND business_date = %s
        """, (pid, business_date))
        
        daily = cur.fetchone()
        
        # Calculate values
        pdst_sales = float(pdst_data['total_sales'] or 0)
        pdst_cost = float(pdst_data['total_cost'] or 0)
        pdst_gp = float(pdst_data['total_gp'] or 0)
        pdst_gp_pct = (pdst_gp / pdst_sales * 100) if pdst_sales > 0 else 0.0
        
        frontshop_sales = float(frontshop_gp_data['total_sales'] or 0)
        frontshop_cost = float(frontshop_gp_data['total_cost'] or 0)
        frontshop_gp = float(frontshop_gp_data['total_gp'] or 0)
        frontshop_gp_pct = (frontshop_gp / frontshop_sales * 100) if frontshop_sales > 0 else 0.0
        
        total_sales = float(total_gp_data['total_sales'] or 0)
        total_cost = float(total_gp_data['total_cost'] or 0)
        total_gp = float(total_gp_data['total_gp'] or 0)
        total_gp_pct = (total_gp / total_sales * 100) if total_sales > 0 else 0.0
        
        # Calculate percentages of total GP
        dispensary_gp_pct_of_total = (pdst_gp / total_gp * 100) if total_gp > 0 else 0.0
        frontshop_gp_pct_of_total = (frontshop_gp / total_gp * 100) if total_gp > 0 else 0.0
        
        daily_gp = float(daily['daily_gp']) if daily and daily.get('daily_gp') else None
        difference = abs(daily_gp - total_gp) if daily_gp is not None else None
        
        return FrontshopDispensaryGP(
            business_date=business_date,
            pharmacy_id=pid,
            dispensary=GPBreakdown(
                product_count=pdst_data['product_count'],
                sales_value=pdst_sales,
                cost_of_sales=pdst_cost,
                gross_profit=pdst_gp,
                gp_percentage=round(pdst_gp_pct, 2),
                gp_percentage_of_total=round(dispensary_gp_pct_of_total, 2)
            ),
            frontshop=GPBreakdown(
                product_count=frontshop_gp_data['product_count'],
                sales_value=frontshop_sales,
                cost_of_sales=frontshop_cost,
                gross_profit=frontshop_gp,
                gp_percentage=round(frontshop_gp_pct, 2),
                gp_percentage_of_total=round(frontshop_gp_pct_of_total, 2)
            ),
            total=GPBreakdown(
                product_count=total_gp_data['product_count'],
                sales_value=total_sales,
                cost_of_sales=total_cost,
                gross_profit=total_gp,
                gp_percentage=round(total_gp_pct, 2)
            ),
            daily_summary_gp=daily_gp,
            difference=difference
        )
