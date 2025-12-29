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
  (turnover - cost_of_sales)                                                      AS gp_value,
  NULLIF((turnover - COALESCE(type_r_sales,0)),0)                                AS denom_excl_type_r,
  CASE WHEN turnover > 0
       THEN ROUND((turnover - cost_of_sales) / turnover * 100, 2)
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

-- ========== USERS & ACCESS CONTROL ==========
CREATE TABLE IF NOT EXISTS pharma.users (
  user_id       bigserial PRIMARY KEY,
  username      text NOT NULL UNIQUE,
  email         text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  is_active     boolean NOT NULL DEFAULT true,
  is_admin      boolean NOT NULL DEFAULT false,
  is_accounting boolean NOT NULL DEFAULT false,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pharma.user_pharmacies (
  user_id     bigint  NOT NULL REFERENCES pharma.users(user_id) ON DELETE CASCADE,
  pharmacy_id integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  can_read    boolean NOT NULL DEFAULT true,
  can_write   boolean NOT NULL DEFAULT false,
  PRIMARY KEY (user_id, pharmacy_id)
);

-- ========== FINANCIAL MANAGEMENT - CHART OF ACCOUNTS ==========
-- Global chart of accounts shared across all pharmacies
-- Used for management financial reporting and P&L generation
CREATE TYPE pharma.account_type AS ENUM (
  'ASSET',
  'LIABILITY',
  'EQUITY',
  'INCOME',
  'COGS',
  'EXPENSE',
  'FINANCE_COST',
  'OTHER_INCOME',
  'TAX'
);

CREATE TABLE IF NOT EXISTS pharma.accounts (
  id                bigserial PRIMARY KEY,
  code              varchar(10) NOT NULL UNIQUE,
  name              text NOT NULL,
  type              pharma.account_type NOT NULL,
  category          text NOT NULL,
  parent_account_id bigint REFERENCES pharma.accounts(id) ON DELETE SET NULL,
  is_active         boolean NOT NULL DEFAULT true,
  display_order     integer NOT NULL DEFAULT 0,
  notes             text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_accounts_code ON pharma.accounts(code);
CREATE INDEX IF NOT EXISTS idx_accounts_type ON pharma.accounts(type);
CREATE INDEX IF NOT EXISTS idx_accounts_category ON pharma.accounts(category);
CREATE INDEX IF NOT EXISTS idx_accounts_parent ON pharma.accounts(parent_account_id);
CREATE INDEX IF NOT EXISTS idx_accounts_active ON pharma.accounts(is_active);
CREATE INDEX IF NOT EXISTS idx_accounts_display_order ON pharma.accounts(display_order);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_account_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_account_updated_at ON pharma.accounts;
CREATE TRIGGER trigger_update_account_updated_at
    BEFORE UPDATE ON pharma.accounts
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_account_updated_at();

-- ========== FINANCIAL MANAGEMENT - BANKING & LEDGER TABLES ==========
-- Step 2: Core Accounting & Bank Tables for PharmaSight Financial Layer

-- Bank import batch status enum
CREATE TYPE pharma.bank_import_status AS ENUM (
  'IMPORTED',
  'CLASSIFIED_PARTIAL',
  'CLASSIFIED_COMPLETE',
  'POSTED_TO_LEDGER'
);

-- Ledger entry source enum
CREATE TYPE pharma.ledger_source AS ENUM (
  'PHARMASIGHT',
  'BANK',
  'MANUAL'
);

-- Bank accounts attached to a pharmacy
CREATE TABLE IF NOT EXISTS pharma.bank_accounts (
  id             bigserial PRIMARY KEY,
  pharmacy_id    integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  name           text NOT NULL,
  bank_name      text NOT NULL,
  account_number text,
  branch_code    text,
  currency       varchar(3) NOT NULL DEFAULT 'ZAR',
  is_active      boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (pharmacy_id, name)
);

CREATE INDEX IF NOT EXISTS idx_bank_accounts_pharmacy ON pharma.bank_accounts(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_active ON pharma.bank_accounts(is_active);

-- Function to update updated_at timestamp for bank_accounts
CREATE OR REPLACE FUNCTION pharma.update_bank_account_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at for bank_accounts
DROP TRIGGER IF EXISTS trigger_update_bank_account_updated_at ON pharma.bank_accounts;
CREATE TRIGGER trigger_update_bank_account_updated_at
    BEFORE UPDATE ON pharma.bank_accounts
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_bank_account_updated_at();

-- Bank import batches - each CSV upload is grouped as an import batch
CREATE TABLE IF NOT EXISTS pharma.bank_import_batches (
  id                bigserial PRIMARY KEY,
  bank_account_id   bigint NOT NULL REFERENCES pharma.bank_accounts(id) ON DELETE CASCADE,
  pharmacy_id       integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  period_start      date,
  period_end        date,
  file_name         text NOT NULL,
  uploaded_by_user_id bigint REFERENCES pharma.users(user_id) ON DELETE SET NULL,
  uploaded_at       timestamptz NOT NULL DEFAULT now(),
  status            pharma.bank_import_status NOT NULL DEFAULT 'IMPORTED',
  notes             text
);

CREATE INDEX IF NOT EXISTS idx_bank_import_batches_bank_account ON pharma.bank_import_batches(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_bank_import_batches_pharmacy ON pharma.bank_import_batches(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_bank_import_batches_period ON pharma.bank_import_batches(pharmacy_id, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_bank_import_batches_status ON pharma.bank_import_batches(status);

-- Bank transactions - raw lines imported from CSV
CREATE TABLE IF NOT EXISTS pharma.bank_transactions (
  id                   bigserial PRIMARY KEY,
  bank_import_batch_id bigint NOT NULL REFERENCES pharma.bank_import_batches(id) ON DELETE CASCADE,
  bank_account_id      bigint NOT NULL REFERENCES pharma.bank_accounts(id) ON DELETE CASCADE,
  pharmacy_id          integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  date                 date NOT NULL,
  description          text NOT NULL,
  raw_description      text,
  reference            text,
  amount               numeric(18,2) NOT NULL,
  balance              numeric(18,2),
  raw_data             jsonb,
  external_id          text,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_batch ON pharma.bank_transactions(bank_import_batch_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_bank_account ON pharma.bank_transactions(bank_account_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_pharmacy ON pharma.bank_transactions(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_date ON pharma.bank_transactions(date);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_external_id ON pharma.bank_transactions(external_id);

-- Unique index for external_id (if bank provides unique transaction IDs)
-- This allows nulls (partial index) since not all banks provide external_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transactions_external_id_unique
  ON pharma.bank_transactions(bank_account_id, external_id)
  WHERE external_id IS NOT NULL;

-- Optional unique index to help prevent exact-duplicate imports (heuristic fallback)
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transactions_unique_import 
  ON pharma.bank_transactions(bank_account_id, date, amount, COALESCE(description, ''))
  WHERE external_id IS NULL;

-- Function to update updated_at timestamp for bank_transactions
CREATE OR REPLACE FUNCTION pharma.update_bank_transaction_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at for bank_transactions
DROP TRIGGER IF EXISTS trigger_update_bank_transaction_updated_at ON pharma.bank_transactions;
CREATE TRIGGER trigger_update_bank_transaction_updated_at
    BEFORE UPDATE ON pharma.bank_transactions
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_bank_transaction_updated_at();

-- Ledger entries - single source of truth for all accounting movements
CREATE TABLE IF NOT EXISTS pharma.ledger_entries (
  id                  bigserial PRIMARY KEY,
  pharmacy_id         integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  date                date NOT NULL,
  description         text NOT NULL,
  amount              numeric(18,2) NOT NULL CHECK (amount > 0),
  debit_account_id    bigint NOT NULL REFERENCES pharma.accounts(id),
  credit_account_id   bigint NOT NULL REFERENCES pharma.accounts(id),
  source              pharma.ledger_source NOT NULL,
  source_reference_type text,
  source_reference_id   text,
  created_by_user_id  bigint REFERENCES pharma.users(user_id) ON DELETE SET NULL,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_pharmacy ON pharma.ledger_entries(pharmacy_id);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_date ON pharma.ledger_entries(date);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_debit_account ON pharma.ledger_entries(debit_account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_credit_account ON pharma.ledger_entries(credit_account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_pharmacy_date ON pharma.ledger_entries(pharmacy_id, date);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_source ON pharma.ledger_entries(source);
CREATE INDEX IF NOT EXISTS idx_ledger_entries_source_ref ON pharma.ledger_entries(source_reference_type, source_reference_id);

-- Function to update updated_at timestamp for ledger_entries
CREATE OR REPLACE FUNCTION pharma.update_ledger_entry_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at for ledger_entries
DROP TRIGGER IF EXISTS trigger_update_ledger_entry_updated_at ON pharma.ledger_entries;
CREATE TRIGGER trigger_update_ledger_entry_updated_at
    BEFORE UPDATE ON pharma.ledger_entries
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_ledger_entry_updated_at();

-- ========== BANK IMPORT ERRORS ==========
-- Store parsing errors for bank import batches (optional but useful)
CREATE TABLE IF NOT EXISTS pharma.bank_import_errors (
  id                   bigserial PRIMARY KEY,
  bank_import_batch_id bigint REFERENCES pharma.bank_import_batches(id) ON DELETE CASCADE,
  row_number           integer NOT NULL,
  raw_data             jsonb,
  error_message        text NOT NULL,
  created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bank_import_errors_batch ON pharma.bank_import_errors(bank_import_batch_id);

-- ========== TARGETS ==========
-- Daily turnover targets set by pharmacy managers
CREATE TABLE IF NOT EXISTS pharma.pharmacy_targets (
  id                bigserial PRIMARY KEY,
  pharmacy_id       integer NOT NULL REFERENCES pharma.pharmacies(pharmacy_id) ON DELETE CASCADE,
  date              date NOT NULL,
  target_value      numeric(12, 2) NOT NULL CHECK (target_value >= 0),
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  created_by_user_id bigint REFERENCES pharma.users(user_id) ON DELETE SET NULL,
  UNIQUE(pharmacy_id, date)
);

CREATE INDEX IF NOT EXISTS idx_pharmacy_targets_pharmacy_date ON pharma.pharmacy_targets(pharmacy_id, date);
CREATE INDEX IF NOT EXISTS idx_pharmacy_targets_date ON pharma.pharmacy_targets(date);

-- ========== PUSH & NOTIFICATIONS ==========
-- Store one row per device per user
CREATE TABLE IF NOT EXISTS pharma.devices (
  id              bigserial PRIMARY KEY,
  user_id         bigint NOT NULL REFERENCES pharma.users(user_id) ON DELETE CASCADE,
  device_id       text NOT NULL,
  platform        text NOT NULL CHECK (platform IN ('ios','android')),
  push_token_enc  bytea NOT NULL,
  timezone        text NOT NULL,
  device_model    text,
  os_version      text,
  app_version     text,
  locale          text,
  last_seen_at    timestamptz NOT NULL DEFAULT now(),
  disabled_at     timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, device_id)
);
CREATE INDEX IF NOT EXISTS devices_user_idx ON pharma.devices(user_id);

-- Per-user notification preferences
CREATE TABLE IF NOT EXISTS pharma.notification_settings (
  user_id                bigint PRIMARY KEY REFERENCES pharma.users(user_id) ON DELETE CASCADE,
  daily_enabled          boolean NOT NULL DEFAULT false,
  daily_time             text,
  daily_pharmacy_ids     integer[],
  lowgp_enabled          boolean NOT NULL DEFAULT false,
  lowgp_time             text,
  lowgp_pharmacy_ids     integer[],
  lowgp_threshold        numeric(5,2),
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now()
);

-- Log sends and enforce idempotency
CREATE TABLE IF NOT EXISTS pharma.notification_log (
  id                bigserial PRIMARY KEY,
  user_id           bigint NOT NULL REFERENCES pharma.users(user_id) ON DELETE CASCADE,
  kind              text NOT NULL CHECK (kind IN ('DAILY_SUMMARY','LOW_GP_ALERT')),
  pharmacy_id       integer REFERENCES pharma.pharmacies(pharmacy_id),
  sent_at           timestamptz NOT NULL DEFAULT now(),
  idempotency_key   text NOT NULL UNIQUE,
  status            text NOT NULL CHECK (status IN ('SENT','SKIPPED','FAILED','RETRY')),
  error             text,
  ticket_id         text,
  receipt_status    text,
  receipt_error     text,
  created_at        timestamptz NOT NULL DEFAULT now()
);

-- Track broadcast notification history
CREATE TABLE IF NOT EXISTS pharma.broadcast_notifications (
  id                bigserial PRIMARY KEY,
  title             text NOT NULL,
  body              text NOT NULL,
  data              jsonb,
  target_audience   text NOT NULL CHECK (target_audience IN ('all', 'pharmacy_specific', 'access_based')),
  pharmacy_ids      integer[],
  access_type       text CHECK (access_type IN ('read', 'write')),
  sent_count        integer DEFAULT 0,
  failed_count      integer DEFAULT 0,
  created_by        text,
  created_at        timestamptz NOT NULL DEFAULT now()
);

