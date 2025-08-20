#!/usr/bin/env python
"""
Manual refresh script for product usage averages.
Recalculates 30d, 90d, and 180d daily averages for all products.
"""

import os
import sys
from datetime import date
from psycopg import connect
from psycopg.rows import dict_row
from pathlib import Path

# Ensure project root for src.* imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=False)

DSN = os.environ.get("DATABASE_URL")

# SQL for refreshing product usage
REFRESH_ALL_PRODUCT_USAGE = """
WITH product_sales AS (
  SELECT 
    f.pharmacy_id,
    f.product_id,
    COUNT(DISTINCT f.business_date) as days_with_sales,
    SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '29 days' THEN f.qty_sold END) as qty_30d,
    SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '89 days' THEN f.qty_sold END) as qty_90d,
    SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '179 days' THEN f.qty_sold END) as qty_180d
  FROM pharma.fact_stock_activity f
  WHERE f.business_date >= CURRENT_DATE - INTERVAL '179 days'
    AND f.qty_sold > 0
  GROUP BY f.pharmacy_id, f.product_id
),
usage_calc AS (
  SELECT 
    ps.pharmacy_id,
    ps.product_id,
    CASE 
      WHEN ps.days_with_sales >= 1 THEN ROUND((ps.qty_30d / 30.0)::numeric, 3)
      ELSE 0 
    END as avg_qty_30d,
    CASE 
      WHEN ps.days_with_sales >= 1 THEN ROUND((ps.qty_90d / 90.0)::numeric, 3)
      ELSE 0 
    END as avg_qty_90d,
    CASE 
      WHEN ps.days_with_sales >= 1 THEN ROUND((ps.qty_180d / 180.0)::numeric, 3)
      ELSE 0 
    END as avg_qty_180d
  FROM product_sales ps
)
INSERT INTO pharma.product_usage AS u (
  pharmacy_id, product_id, avg_qty_30d, avg_qty_90d, avg_qty_180d, last_recalc
)
SELECT 
  uc.pharmacy_id, uc.product_id, 
  uc.avg_qty_30d, uc.avg_qty_90d, uc.avg_qty_180d, 
  now()
FROM usage_calc uc
ON CONFLICT (pharmacy_id, product_id) DO UPDATE
SET 
  avg_qty_30d = EXCLUDED.avg_qty_30d,
  avg_qty_90d = EXCLUDED.avg_qty_90d,
  avg_qty_180d = EXCLUDED.avg_qty_180d,
  last_recalc = now();
"""

def refresh_all_product_usage():
    """Refresh product usage averages for all products."""
    if not DSN:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    print("🔄 Refreshing product usage averages...")
    
    try:
        with connect(DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                # Set longer timeout for this operation
                cur.execute("SET LOCAL statement_timeout = 300000;")  # 5 minutes
                
                print("📊 Calculating 30d, 90d, and 180d averages...")
                cur.execute(REFRESH_ALL_PRODUCT_USAGE)
                
                # Get count of updated records
                cur.execute("SELECT COUNT(*) as total_products FROM pharma.product_usage")
                result = cur.fetchone()
                total_products = result['total_products'] if result else 0
                
                conn.commit()
                print(f"✅ Successfully refreshed {total_products} product usage records")
                
    except Exception as e:
        print(f"❌ Error refreshing product usage: {e}")
        sys.exit(1)

def refresh_specific_product(pharmacy_id: int, product_code: str):
    """Refresh usage for a specific product."""
    if not DSN:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    print(f"🔄 Refreshing usage for product {product_code} (pharmacy {pharmacy_id})...")
    
    sql = """
    WITH product_sales AS (
      SELECT 
        COUNT(DISTINCT f.business_date) as days_with_sales,
        SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '29 days' THEN f.qty_sold END) as qty_30d,
        SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '89 days' THEN f.qty_sold END) as qty_90d,
        SUM(CASE WHEN f.business_date >= CURRENT_DATE - INTERVAL '179 days' THEN f.qty_sold END) as qty_180d
      FROM pharma.fact_stock_activity f
      JOIN pharma.products p ON p.product_id = f.product_id
      WHERE f.pharmacy_id = %s 
        AND p.product_code = %s
        AND f.business_date >= CURRENT_DATE - INTERVAL '179 days'
        AND f.qty_sold > 0
    ),
    usage_calc AS (
      SELECT 
        CASE 
          WHEN ps.days_with_sales >= 1 THEN ROUND((ps.qty_30d / 30.0)::numeric, 3)
          ELSE 0 
        END as avg_qty_30d,
        CASE 
          WHEN ps.days_with_sales >= 1 THEN ROUND((ps.qty_90d / 90.0)::numeric, 3)
          ELSE 0 
        END as avg_qty_90d,
        CASE 
          WHEN ps.days_with_sales >= 1 THEN ROUND((ps.qty_180d / 180.0)::numeric, 3)
          ELSE 0 
        END as avg_qty_180d
      FROM product_sales ps
    )
    INSERT INTO pharma.product_usage AS u (
      pharmacy_id, product_id, avg_qty_30d, avg_qty_90d, avg_qty_180d, last_recalc
    )
    SELECT 
      %s, p.product_id, 
      uc.avg_qty_30d, uc.avg_qty_90d, uc.avg_qty_180d, 
      now()
    FROM usage_calc uc
    CROSS JOIN pharma.products p
    WHERE p.product_code = %s
    ON CONFLICT (pharmacy_id, product_id) DO UPDATE
    SET 
      avg_qty_30d = EXCLUDED.avg_qty_30d,
      avg_qty_90d = EXCLUDED.avg_qty_90d,
      avg_qty_180d = EXCLUDED.avg_qty_180d,
      last_recalc = now();
    """
    
    try:
        with connect(DSN, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (pharmacy_id, product_code, pharmacy_id, product_code))
                
                # Get the updated values
                cur.execute("""
                    SELECT avg_qty_30d, avg_qty_90d, avg_qty_180d, last_recalc 
                    FROM pharma.product_usage pu
                    JOIN pharma.products p ON p.product_id = pu.product_id
                    WHERE pu.pharmacy_id = %s AND p.product_code = %s
                """, (pharmacy_id, product_code))
                
                result = cur.fetchone()
                if result:
                    print(f"✅ Updated usage averages:")
                    print(f"   30d: {result['avg_qty_30d']}")
                    print(f"   90d: {result['avg_qty_90d']}")
                    print(f"   180d: {result['avg_qty_180d']}")
                    print(f"   Last recalc: {result['last_recalc']}")
                else:
                    print("⚠️  No usage data found for this product")
                
                conn.commit()
                
    except Exception as e:
        print(f"❌ Error refreshing product usage: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Refresh product usage averages")
    parser.add_argument("--all", action="store_true", help="Refresh all products")
    parser.add_argument("--product", help="Specific product code to refresh")
    parser.add_argument("--pharmacy", type=int, default=1, help="Pharmacy ID (default: 1)")
    
    args = parser.parse_args()
    
    if args.all:
        refresh_all_product_usage()
    elif args.product:
        refresh_specific_product(args.pharmacy, args.product)
    else:
        print("Usage:")
        print("  python refresh_product_usage.py --all                    # Refresh all products")
        print("  python refresh_product_usage.py --product LP9103984      # Refresh specific product")
        print("  python refresh_product_usage.py --product LP9103984 --pharmacy 2  # For different pharmacy") 