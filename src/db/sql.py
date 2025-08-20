# --- DAILY SALES UPSERTS ---
UPSERT_DAILY_SALES_LIVE = """
INSERT INTO pharma.fact_daily_sales AS f (
  pharmacy_id, business_date,
  turnover, sales_cash, sales_account, sales_cod, type_r_sales,
  transaction_count, avg_basket,
  purchases, cost_of_sales, closing_stock,
  dispensary_turnover, scripts_qty, avg_script_value
) VALUES (
  %(pharmacy_id)s, %(business_date)s,
  %(turnover)s, %(sales_cash)s, %(sales_account)s, %(sales_cod)s, %(type_r_sales)s,
  %(transaction_count)s, %(avg_basket)s,
  %(purchases)s, %(cost_of_sales)s, %(closing_stock)s,
  %(dispensary_turnover)s, %(scripts_qty)s, %(avg_script_value)s
)
ON CONFLICT (pharmacy_id, business_date) DO UPDATE
SET turnover            = COALESCE(EXCLUDED.turnover,            f.turnover),
    sales_cash          = COALESCE(EXCLUDED.sales_cash,          f.sales_cash),
    sales_account       = COALESCE(EXCLUDED.sales_account,       f.sales_account),
    sales_cod           = COALESCE(EXCLUDED.sales_cod,           f.sales_cod),
    type_r_sales        = COALESCE(EXCLUDED.type_r_sales,        f.type_r_sales),
    transaction_count   = COALESCE(EXCLUDED.transaction_count,   f.transaction_count),
    avg_basket          = COALESCE(EXCLUDED.avg_basket,          f.avg_basket),
    purchases           = COALESCE(EXCLUDED.purchases,           f.purchases),
    cost_of_sales       = COALESCE(EXCLUDED.cost_of_sales,       f.cost_of_sales),
    closing_stock       = COALESCE(EXCLUDED.closing_stock,       f.closing_stock),
    dispensary_turnover = COALESCE(EXCLUDED.dispensary_turnover, f.dispensary_turnover),
    scripts_qty         = COALESCE(EXCLUDED.scripts_qty,         f.scripts_qty),
    avg_script_value    = COALESCE(EXCLUDED.avg_script_value,    f.avg_script_value),
    last_updated_at     = now();
"""

# Historical mode: only fill NULL columns (ignore provided values if target not NULL)
UPSERT_DAILY_SALES_HISTORICAL = """
INSERT INTO pharma.fact_daily_sales AS f (
  pharmacy_id, business_date,
  turnover, sales_cash, sales_account, sales_cod, type_r_sales,
  transaction_count, avg_basket,
  purchases, cost_of_sales, closing_stock,
  dispensary_turnover, scripts_qty, avg_script_value
) VALUES (
  %(pharmacy_id)s, %(business_date)s,
  %(turnover)s, %(sales_cash)s, %(sales_account)s, %(sales_cod)s, %(type_r_sales)s,
  %(transaction_count)s, %(avg_basket)s,
  %(purchases)s, %(cost_of_sales)s, %(closing_stock)s,
  %(dispensary_turnover)s, %(scripts_qty)s, %(avg_script_value)s
)
ON CONFLICT (pharmacy_id, business_date) DO UPDATE
SET turnover            = COALESCE(f.turnover,            EXCLUDED.turnover),
    sales_cash          = COALESCE(f.sales_cash,          EXCLUDED.sales_cash),
    sales_account       = COALESCE(f.sales_account,       EXCLUDED.sales_account),
    sales_cod           = COALESCE(f.sales_cod,           EXCLUDED.sales_cod),
    type_r_sales        = COALESCE(f.type_r_sales,        EXCLUDED.type_r_sales),
    transaction_count   = COALESCE(f.transaction_count,   EXCLUDED.transaction_count),
    avg_basket          = COALESCE(f.avg_basket,          EXCLUDED.avg_basket),
    purchases           = COALESCE(f.purchases,           EXCLUDED.purchases),
    cost_of_sales       = COALESCE(f.cost_of_sales,       EXCLUDED.cost_of_sales),
    closing_stock       = COALESCE(f.closing_stock,       EXCLUDED.closing_stock),
    dispensary_turnover = COALESCE(f.dispensary_turnover, EXCLUDED.dispensary_turnover),
    scripts_qty         = COALESCE(f.scripts_qty,         EXCLUDED.scripts_qty),
    avg_script_value    = COALESCE(f.avg_script_value,    EXCLUDED.avg_script_value),
    last_updated_at     = now();
"""

# --- RECEIPTS & COVERAGE ---
INSERT_RECEIPT = """
INSERT INTO pharma.report_receipts
(pharmacy_id, business_date, report_type, filename, sha256, byte_size, processed_at)
VALUES (%(pharmacy_id)s, %(business_date)s, %(report_type)s, %(filename)s, %(sha256)s, %(byte_size)s, now())
ON CONFLICT (pharmacy_id, business_date, report_type, sha256) DO NOTHING;
"""

UPSERT_COVERAGE = """
INSERT INTO pharma.report_coverage
(pharmacy_id, business_date, inv249_turnover, stk261_trading, phm080_scripts, stk260_gp, last_updated)
VALUES (
  %(pharmacy_id)s, %(business_date)s,
  (%(report_type)s='turnover_summary'),
  (%(report_type)s='trading_account'),
  (%(report_type)s='dispensary_scripts'),
  (%(report_type)s='gross_profit'),
  now()
)
ON CONFLICT (pharmacy_id, business_date) DO UPDATE
SET inv249_turnover = pharma.report_coverage.inv249_turnover OR EXCLUDED.inv249_turnover,
    stk261_trading  = pharma.report_coverage.stk261_trading  OR EXCLUDED.stk261_trading,
    phm080_scripts  = pharma.report_coverage.phm080_scripts  OR EXCLUDED.phm080_scripts,
    stk260_gp       = pharma.report_coverage.stk260_gp       OR EXCLUDED.stk260_gp,
    last_updated    = now();
"""

# --- DIM LOOKUPS ---
ENSURE_DEPT = """
WITH ins AS (
  INSERT INTO pharma.departments (department_code)
  VALUES (%(department_code)s)
  ON CONFLICT (department_code) DO NOTHING
  RETURNING department_id
)
SELECT COALESCE(
  (SELECT department_id FROM ins),
  (SELECT department_id FROM pharma.departments WHERE department_code = %(department_code)s)
) AS department_id;
"""

UPSERT_DEPARTMENT = """
INSERT INTO pharma.departments (department_code, department_name)
VALUES (%(department_code)s, %(department_name)s)
ON CONFLICT (department_code) DO UPDATE
SET department_name = COALESCE(EXCLUDED.department_name, pharma.departments.department_name)
RETURNING department_id;
"""

ENSURE_PRODUCT = """
WITH ins AS (
  INSERT INTO pharma.products (product_code, description, department_id)
  VALUES (%(product_code)s, %(description)s, %(department_id)s)
  ON CONFLICT (product_code) DO UPDATE
    SET description = EXCLUDED.description,
        department_id = COALESCE(EXCLUDED.department_id, pharma.products.department_id)
  RETURNING product_id
)
SELECT COALESCE(
  (SELECT product_id FROM ins),
  (SELECT product_id FROM pharma.products WHERE product_code = %(product_code)s)
) AS product_id;
"""

# --- STOCK ACTIVITY UPSERT ---
UPSERT_STOCK_ACTIVITY = """
INSERT INTO pharma.fact_stock_activity AS s (
  pharmacy_id, business_date, product_id, department_id,
  qty_sold, sales_val, cost_of_sales, gp_value, gp_pct, on_hand
) VALUES (
  %(pharmacy_id)s, %(business_date)s, %(product_id)s, %(department_id)s,
  %(qty_sold)s, %(sales_val)s, %(cost_of_sales)s, %(gp_value)s, %(gp_pct)s, %(on_hand)s
)
ON CONFLICT (pharmacy_id, business_date, product_id) DO UPDATE
SET department_id   = COALESCE(EXCLUDED.department_id, s.department_id),
    qty_sold        = EXCLUDED.qty_sold,
    sales_val       = EXCLUDED.sales_val,
    cost_of_sales   = EXCLUDED.cost_of_sales,
    gp_value        = EXCLUDED.gp_value,
    gp_pct          = EXCLUDED.gp_pct,
    on_hand         = EXCLUDED.on_hand,
    last_updated_at = now();
"""

# --- USAGE REFRESH (touched product) ---
REFRESH_PRODUCT_USAGE = """
WITH q AS (
  SELECT
    COALESCE(SUM(CASE WHEN business_date >= %(asof)s::date - INTERVAL '29 days'  THEN qty_sold END),0)/30.0 AS avg30,
    COALESCE(SUM(CASE WHEN business_date >= %(asof)s::date - INTERVAL '89 days'  THEN qty_sold END),0)/90.0 AS avg90,
    COALESCE(SUM(CASE WHEN business_date >= %(asof)s::date - INTERVAL '179 days' THEN qty_sold END),0)/180.0 AS avg180
  FROM pharma.fact_stock_activity
  WHERE pharmacy_id = %(pharmacy_id)s
    AND product_id  = %(product_id)s
    AND business_date <= %(asof)s::date
    AND business_date >= %(asof)s::date - INTERVAL '179 days'
)
INSERT INTO pharma.product_usage AS u (pharmacy_id, product_id, avg_qty_30d, avg_qty_90d, avg_qty_180d, last_recalc)
SELECT %(pharmacy_id)s, %(product_id)s, ROUND(q.avg30::numeric,3), ROUND(q.avg90::numeric,3), ROUND(q.avg180::numeric,3), now()
FROM q
ON CONFLICT (pharmacy_id, product_id) DO UPDATE
SET avg_qty_30d = EXCLUDED.avg_qty_30d,
    avg_qty_90d = EXCLUDED.avg_qty_90d,
    avg_qty_180d = EXCLUDED.avg_qty_180d,
    last_recalc  = now();
"""

# --- MTD/YTD REFRESH ---
REFRESH_MTD = """
WITH src AS (
  SELECT *
  FROM pharma.v_daily_sales
  WHERE pharmacy_id = %(pharmacy_id)s
    AND business_date >= %(month_start)s
    AND business_date <  %(month_start)s + INTERVAL '1 month'
)
INSERT INTO pharma.agg_sales_mtd AS m (
  pharmacy_id, month_start,
  turnover, purchases, cost_of_sales, type_r_sales, dispensary_turnover,
  scripts_qty, transaction_count, frontshop_turnover, gp_value, last_refreshed
)
SELECT
  %(pharmacy_id)s, %(month_start)s::date,
  ROUND(SUM(src.turnover)::numeric,2),
  ROUND(SUM(src.purchases)::numeric,2),
  ROUND(SUM(src.cost_of_sales)::numeric,2),
  ROUND(SUM(src.type_r_sales)::numeric,2),
  ROUND(SUM(src.dispensary_excl_vat)::numeric,2),
  SUM(src.scripts_qty),
  SUM(src.transaction_count),
  ROUND(SUM(src.frontshop_turnover)::numeric,2),
  ROUND(SUM(src.gp_value)::numeric,2),
  now()
FROM src
ON CONFLICT (pharmacy_id, month_start) DO UPDATE
SET turnover            = EXCLUDED.turnover,
    purchases           = EXCLUDED.purchases,
    cost_of_sales       = EXCLUDED.cost_of_sales,
    type_r_sales        = EXCLUDED.type_r_sales,
    dispensary_turnover = EXCLUDED.dispensary_turnover,
    scripts_qty         = EXCLUDED.scripts_qty,
    transaction_count   = EXCLUDED.transaction_count,
    frontshop_turnover  = EXCLUDED.frontshop_turnover,
    gp_value            = EXCLUDED.gp_value,
    last_refreshed      = now();
"""

REFRESH_YTD = """
WITH src AS (
  SELECT *
  FROM pharma.v_daily_sales
  WHERE pharmacy_id = %(pharmacy_id)s
    AND business_date >= %(year_start)s
    AND business_date <  %(year_start)s + INTERVAL '1 year'
)
INSERT INTO pharma.agg_sales_ytd AS y (
  pharmacy_id, year_start,
  turnover, purchases, cost_of_sales, type_r_sales, dispensary_turnover,
  scripts_qty, transaction_count, frontshop_turnover, gp_value, last_refreshed
)
SELECT
  %(pharmacy_id)s, %(year_start)s::date,
  ROUND(SUM(src.turnover)::numeric,2),
  ROUND(SUM(src.purchases)::numeric,2),
  ROUND(SUM(src.cost_of_sales)::numeric,2),
  ROUND(SUM(src.type_r_sales)::numeric,2),
  ROUND(SUM(src.dispensary_excl_vat)::numeric,2),
  SUM(src.scripts_qty),
  SUM(src.transaction_count),
  ROUND(SUM(src.frontshop_turnover)::numeric,2),
  ROUND(SUM(src.gp_value)::numeric,2),
  now()
FROM src
ON CONFLICT (pharmacy_id, year_start) DO UPDATE
SET turnover            = EXCLUDED.turnover,
    purchases           = EXCLUDED.purchases,
    cost_of_sales       = EXCLUDED.cost_of_sales,
    type_r_sales        = EXCLUDED.type_r_sales,
    dispensary_turnover = EXCLUDED.dispensary_turnover,
    scripts_qty         = EXCLUDED.scripts_qty,
    transaction_count   = EXCLUDED.transaction_count,
    frontshop_turnover  = EXCLUDED.frontshop_turnover,
    gp_value            = EXCLUDED.gp_value,
    last_refreshed      = now();
""" 