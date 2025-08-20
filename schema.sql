-- ========== DIMENSIONS ==========
CREATE TABLE IF NOT EXISTS pharma.pharmacies (
  pharmacy_id   integer PRIMARY KEY,
  name          text NOT NULL,
  is_active     boolean NOT NULL DEFAULT true
);

-- Department codes are preloaded but must auto-extend when new codes appear
CREATE TABLE IF NOT EXISTS pharma.departments (
  department_id  bigserial PRIMARY KEY,
  department_code text NOT NULL UNIQUE,
  department_name text,
  created_at      timestamptz NOT NULL DEFAULT now()
);

-- Products keyed by code (per brand; if same code differs by pharmacy, add pharmacy_id to the PK)
CREATE TABLE IF NOT EXISTS pharma.products (
  product_id    bigserial PRIMARY KEY,
  product_code  text NOT NULL,
  description   text,
  department_id bigint REFERENCES pharma.departments(department_id),
  UNIQUE (product_code)
);

-- ========== RECEIPTS & COVERAGE ==========
-- What files we've seen (dedupe & audit)
CREATE TYPE pharma.report_kind AS ENUM ('turnover_summary','trading_account','dispensary_scripts','gross_profit');

CREATE TABLE IF NOT EXISTS pharma.report_receipts (
  receipt_id     bigserial PRIMARY KEY,
  pharmacy_id    integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  business_date  date NOT NULL,
  report_type    pharma.report_kind NOT NULL,
  filename       text,
  sha256         text NOT NULL, -- content hash to dedupe
  byte_size      bigint,
  received_at    timestamptz NOT NULL DEFAULT now(),
  processed_at   timestamptz,
  UNIQUE (pharmacy_id, business_date, report_type, sha256)
);

-- Day coverage: which of the 4 reports we already have
CREATE TABLE IF NOT EXISTS pharma.report_coverage (
  pharmacy_id    integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  business_date  date NOT NULL,
  inv249_turnover bool NOT NULL DEFAULT false,
  stk261_trading  bool NOT NULL DEFAULT false,
  phm080_scripts  bool NOT NULL DEFAULT false,
  stk260_gp       bool NOT NULL DEFAULT false,
  last_updated   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (pharmacy_id, business_date)
);

-- ========== FACTS: DAILY SUMMARY ==========
-- Raw daily fields (one row per pharmacy per day). We overwrite *today* in the live process;
-- historical loads fill only NULLs.
CREATE TABLE IF NOT EXISTS pharma.fact_daily_sales (
  pharmacy_id     integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  business_date   date    NOT NULL,

  -- from Turnover Summary
  turnover                  numeric(18,2), -- nett excl VAT
  sales_cash                numeric(18,2),
  sales_account             numeric(18,2),
  sales_cod                 numeric(18,2),
  type_r_sales              numeric(18,2),
  transaction_count         integer,
  avg_basket                numeric(18,2),

  -- from Trading Account
  purchases                 numeric(18,2),
  cost_of_sales             numeric(18,2),
  closing_stock             numeric(18,2),

  -- from Scripts (PHM080) -- already excl VAT in our parser
  dispensary_turnover       numeric(18,2),
  scripts_qty               integer,
  avg_script_value          numeric(18,2),

  -- bookkeeping
  first_seen_at            timestamptz NOT NULL DEFAULT now(),
  last_updated_at          timestamptz NOT NULL DEFAULT now(),

  PRIMARY KEY (pharmacy_id, business_date)
);

CREATE INDEX IF NOT EXISTS fact_daily_sales_mdate_idx
  ON pharma.fact_daily_sales (business_date);

-- A convenience VIEW with derived fields (GP, GP%, frontshop, etc.)
CREATE OR REPLACE VIEW pharma.v_daily_sales AS
SELECT
  f.*,
  (turnover - cost_of_sales - COALESCE(type_r_sales,0))                          AS gp_value,
  NULLIF((turnover - COALESCE(type_r_sales,0)),0)                                AS denom_excl_type_r,
  CASE WHEN (turnover - COALESCE(type_r_sales,0)) > 0
       THEN ROUND((turnover - cost_of_sales - COALESCE(type_r_sales,0))
                  / (turnover - COALESCE(type_r_sales,0)) * 100, 2)
       ELSE NULL END                                                              AS gp_pct,
  (turnover - COALESCE(type_r_sales,0))                                          AS retail_excl_type_r,
  dispensary_turnover                                                            AS dispensary_excl_vat,
  CASE WHEN turnover IS NOT NULL AND turnover <> 0
       THEN ROUND(COALESCE(dispensary_turnover,0) / turnover * 100, 2) END       AS disp_pct,
  CASE WHEN turnover IS NOT NULL AND turnover <> 0
       THEN ROUND(100 - (COALESCE(dispensary_turnover,0) / turnover * 100), 2) END AS frontshop_pct,
  (turnover - COALESCE(type_r_sales,0) - COALESCE(dispensary_turnover,0))        AS frontshop_turnover
FROM pharma.fact_daily_sales f;

-- ========== FACTS: STOCK ACTIVITY (line-level) ==========
-- One row per product per day. We generally overwrite the entire day for live updates.
CREATE TABLE IF NOT EXISTS pharma.fact_stock_activity (
  pharmacy_id     integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  business_date   date    NOT NULL,
  product_id      bigint  NOT NULL REFERENCES pharma.products(product_id),
  department_id   bigint  REFERENCES pharma.departments(department_id),
  qty_sold        numeric(18,3),
  sales_val       numeric(18,2),
  cost_of_sales   numeric(18,2),
  gp_value        numeric(18,2),
  gp_pct          numeric(9,2),
  on_hand         numeric(18,3),
  last_updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (pharmacy_id, business_date, product_id)
);

CREATE INDEX IF NOT EXISTS fact_stock_activity_lookup
  ON pharma.fact_stock_activity (business_date);

-- ========== PRODUCT USAGE (rolling averages) ==========
CREATE TABLE IF NOT EXISTS pharma.product_usage (
  pharmacy_id     integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  product_id      bigint  NOT NULL REFERENCES pharma.products(product_id),
  avg_qty_30d     numeric(18,3),
  avg_qty_90d     numeric(18,3),
  avg_qty_180d    numeric(18,3),
  last_recalc     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (pharmacy_id, product_id)
);

-- ========== MTD / YTD AGGREGATES (for fast dashboard) ==========
-- We pre-aggregate totals so the dashboard reads quickly.
CREATE TABLE IF NOT EXISTS pharma.agg_sales_mtd (
  pharmacy_id    integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  month_start    date    NOT NULL,  -- e.g., 2025-08-01
  -- additive rollups (all excl VAT)
  turnover               numeric(18,2),
  purchases              numeric(18,2),
  cost_of_sales          numeric(18,2),
  type_r_sales           numeric(18,2),
  dispensary_turnover    numeric(18,2),
  scripts_qty            integer,
  transaction_count      integer,
  frontshop_turnover     numeric(18,2),
  gp_value               numeric(18,2),
  last_refreshed         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (pharmacy_id, month_start)
);

CREATE TABLE IF NOT EXISTS pharma.agg_sales_ytd (
  pharmacy_id    integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id),
  year_start     date    NOT NULL,  -- e.g., 2025-01-01
  turnover               numeric(18,2),
  purchases              numeric(18,2),
  cost_of_sales          numeric(18,2),
  type_r_sales           numeric(18,2),
  dispensary_turnover    numeric(18,2),
  scripts_qty            integer,
  transaction_count      integer,
  frontshop_turnover     numeric(18,2),
  gp_value               numeric(18,2),
  last_refreshed         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (pharmacy_id, year_start)
);

--seed pharmacies once:
INSERT INTO pharma.pharmacies (pharmacy_id, name) VALUES
  (1, 'REITZ APTEEK')
ON CONFLICT (pharmacy_id) DO NOTHING;

INSERT INTO pharma.pharmacies (pharmacy_id, name) VALUES
  (2, 'TLC PHARMACY WINTERTON')
ON CONFLICT (pharmacy_id) DO NOTHING;
