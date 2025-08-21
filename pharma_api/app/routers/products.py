from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from datetime import date
from ..db import get_conn
from ..auth import require_api_key
from pydantic import BaseModel

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(require_api_key)])

class ProductInfo(BaseModel):
    product_code: str
    description: str
    department_code: Optional[str] = None
    department_name: Optional[str] = None

class ProductSearchResponse(BaseModel):
    items: List[ProductInfo]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class ProductSales(BaseModel):
    product_code: str
    description: str
    department_code: Optional[str] = None
    total_qty_sold: float
    total_sales_value: float
    total_cost_of_sales: float
    total_gp_value: float
    avg_gp_percentage: float
    avg_unit_price: float
    avg_unit_cost: float
    sales_days: int
    first_sale_date: Optional[date] = None
    last_sale_date: Optional[date] = None

class ProductSalesResponse(BaseModel):
    product_code: str
    description: str
    date_range: str
    summary: ProductSales
    daily_breakdown: List[dict]

@router.get("/search", response_model=ProductSearchResponse)
def search_products(
    query: str = Query(..., description="Search term (product code or description)"),
    pharmacy_id: int = Query(1, description="Pharmacy ID (default: 1)"),
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (default: 50, max: 200)")
):
    """
    Search for products by product code or description.
    Returns paginated results with basic product information.
    """
    offset = (page - 1) * page_size
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Search query - look for matches in product code or description
            search_sql = """
                SELECT 
                    p.product_code,
                    p.description,
                    d.department_code,
                    d.department_name
                FROM pharma.products p
                LEFT JOIN pharma.departments d ON d.department_id = p.department_id
                WHERE p.product_code ILIKE %s OR p.description ILIKE %s
                ORDER BY 
                    CASE 
                        WHEN p.product_code ILIKE %s THEN 1
                        WHEN p.description ILIKE %s THEN 2
                        ELSE 3
                    END,
                    p.product_code
                LIMIT %s OFFSET %s
            """
            
            # Count total matches for pagination
            count_sql = """
                SELECT COUNT(*) as total
                FROM pharma.products p
                WHERE p.product_code ILIKE %s OR p.description ILIKE %s
            """
            
            search_pattern = f"%{query}%"
            exact_pattern = query
            
            # Get total count
            cur.execute(count_sql, (search_pattern, search_pattern))
            total_count = cur.fetchone()['total']
            
            # Get paginated results
            cur.execute(search_sql, (search_pattern, search_pattern, exact_pattern, exact_pattern, page_size, offset))
            rows = cur.fetchall()
            
            # Check if there are more pages
            has_more = (offset + page_size) < total_count
            
            return ProductSearchResponse(
                items=rows,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_more=has_more
            )

@router.get("/{product_code}", response_model=ProductInfo)
def get_product_info(
    product_code: str,
    pharmacy_id: int = Query(1, description="Pharmacy ID (default: 1)")
):
    """
    Get basic information for a specific product by product code.
    Returns product details without requiring a date range.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    p.product_code,
                    p.description,
                    d.department_code,
                    d.department_name
                FROM pharma.products p
                LEFT JOIN pharma.departments d ON d.department_id = p.department_id
                WHERE p.product_code = %s
            """, (product_code,))
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {product_code} not found"
                )
            
            return ProductInfo(
                product_code=row['product_code'],
                description=row['description'],
                department_code=row['department_code'],
                department_name=row['department_name']
            )

@router.get("/{product_code}/sales", response_model=ProductSalesResponse)
def get_product_sales(
    product_code: str,
    from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    pharmacy_id: int = Query(1, description="Pharmacy ID (default: 1)")
):
    """
    Get detailed sales performance for a specific product over a date range.
    Returns summary metrics and daily breakdown.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get product details and summary
            cur.execute("""
                SELECT 
                    pr.product_code,
                    pr.description,
                    d.department_code,
                    SUM(f.qty_sold) as total_qty_sold,
                    SUM(f.sales_val) as total_sales_value,
                    SUM(f.cost_of_sales) as total_cost_of_sales,
                    SUM(f.gp_value) as total_gp_value,
                    CASE 
                        WHEN SUM(f.sales_val) > 0 THEN 
                            (SUM(f.gp_value) / SUM(f.sales_val)) * 100
                        ELSE 0 
                    END as avg_gp_percentage,
                    CASE 
                        WHEN SUM(f.qty_sold) > 0 THEN 
                            SUM(f.sales_val) / SUM(f.qty_sold)
                        ELSE 0 
                    END as avg_unit_price,
                    CASE 
                        WHEN SUM(f.qty_sold) > 0 THEN 
                            SUM(f.cost_of_sales) / SUM(f.qty_sold)
                        ELSE 0 
                    END as avg_unit_cost,
                    COUNT(DISTINCT f.business_date) as sales_days,
                    MIN(f.business_date) as first_sale_date,
                    MAX(f.business_date) as last_sale_date
                FROM pharma.fact_stock_activity f
                JOIN pharma.products pr ON pr.product_id = f.product_id
                LEFT JOIN pharma.departments d ON d.department_id = f.department_id
                WHERE f.pharmacy_id = %s 
                AND pr.product_code = %s
                AND f.business_date BETWEEN %s AND %s
                AND f.qty_sold > 0
                GROUP BY pr.product_code, pr.description, d.department_code
            """, (pharmacy_id, product_code, from_date, to_date))
            
            summary = cur.fetchone()
            
            if not summary:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No sales data found for product {product_code} in the specified date range"
                )
            
            # Get daily breakdown
            cur.execute("""
                SELECT 
                    f.business_date,
                    f.qty_sold,
                    f.sales_val,
                    f.cost_of_sales,
                    f.gp_value,
                    CASE 
                        WHEN f.sales_val > 0 THEN 
                            (f.gp_value / f.sales_val) * 100
                        ELSE 0 
                    END as gp_percentage
                FROM pharma.fact_stock_activity f
                JOIN pharma.products pr ON pr.product_id = f.product_id
                WHERE f.pharmacy_id = %s 
                AND pr.product_code = %s
                AND f.business_date BETWEEN %s AND %s
                AND f.qty_sold > 0
                ORDER BY f.business_date
            """, (pharmacy_id, product_code, from_date, to_date))
            
            daily_breakdown = cur.fetchall()
            
            # Format the response
            product_sales = ProductSales(
                product_code=summary['product_code'],
                description=summary['description'],
                department_code=summary['department_code'],
                total_qty_sold=summary['total_qty_sold'],
                total_sales_value=summary['total_sales_value'],
                total_cost_of_sales=summary['total_cost_of_sales'],
                total_gp_value=summary['total_gp_value'],
                avg_gp_percentage=summary['avg_gp_percentage'],
                avg_unit_price=summary['avg_unit_price'],
                avg_unit_cost=summary['avg_unit_cost'],
                sales_days=summary['sales_days'],
                first_sale_date=summary['first_sale_date'],
                last_sale_date=summary['last_sale_date']
            )
            
            return ProductSalesResponse(
                product_code=product_code,
                description=summary['description'],
                date_range=f"{from_date} to {to_date}",
                summary=product_sales,
                daily_breakdown=daily_breakdown
            )

@router.get("/{product_code}/sales/summary", response_model=ProductSales)
def get_product_sales_summary(
    product_code: str,
    from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    pharmacy_id: int = Query(1, description="Pharmacy ID (default: 1)")
):
    """
    Get summary sales performance for a specific product over a date range.
    Returns only the summary metrics without daily breakdown.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    pr.product_code,
                    pr.description,
                    d.department_code,
                    SUM(f.qty_sold) as total_qty_sold,
                    SUM(f.sales_val) as total_sales_value,
                    SUM(f.cost_of_sales) as total_cost_of_sales,
                    SUM(f.gp_value) as total_gp_value,
                    CASE 
                        WHEN SUM(f.sales_val) > 0 THEN 
                            (SUM(f.gp_value) / SUM(f.sales_val)) * 100
                        ELSE 0 
                    END as avg_gp_percentage,
                    CASE 
                        WHEN SUM(f.qty_sold) > 0 THEN 
                            SUM(f.sales_val) / SUM(f.qty_sold)
                        ELSE 0 
                    END as avg_unit_price,
                    CASE 
                        WHEN SUM(f.qty_sold) > 0 THEN 
                            SUM(f.cost_of_sales) / SUM(f.qty_sold)
                        ELSE 0 
                    END as avg_unit_cost,
                    COUNT(DISTINCT f.business_date) as sales_days,
                    MIN(f.business_date) as first_sale_date,
                    MAX(f.business_date) as last_sale_date
                FROM pharma.fact_stock_activity f
                JOIN pharma.products pr ON pr.product_id = f.product_id
                LEFT JOIN pharma.departments d ON d.department_id = f.department_id
                WHERE f.pharmacy_id = %s 
                AND pr.product_code = %s
                AND f.business_date BETWEEN %s AND %s
                AND f.qty_sold > 0
                GROUP BY pr.product_code, pr.description, d.department_code
            """, (pharmacy_id, product_code, from_date, to_date))
            
            summary = cur.fetchone()
            
            if not summary:
                raise HTTPException(
                    status_code=404, 
                    detail=f"No sales data found for product {product_code} in the specified date range"
                )
            
            return ProductSales(
                product_code=summary['product_code'],
                description=summary['description'],
                department_code=summary['department_code'],
                total_qty_sold=summary['total_qty_sold'],
                total_sales_value=summary['total_sales_value'],
                total_cost_of_sales=summary['total_cost_of_sales'],
                total_gp_value=summary['total_gp_value'],
                avg_gp_percentage=summary['avg_gp_percentage'],
                avg_unit_price=summary['avg_unit_price'],
                avg_unit_cost=summary['avg_unit_cost'],
                sales_days=summary['sales_days'],
                first_sale_date=summary['first_sale_date'],
                last_sale_date=summary['last_sale_date']
            ) 