-- ========== FINANCIAL MANAGEMENT - BANKING & LEDGER TABLES ==========
-- Step 2: Core Accounting & Bank Tables for PharmaSight Financial Layer

-- Bank import batch status enum
DO $$ BEGIN
    CREATE TYPE pharma.bank_import_status AS ENUM (
      'IMPORTED',
      'CLASSIFIED_PARTIAL',
      'CLASSIFIED_COMPLETE',
      'POSTED_TO_LEDGER'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Ledger entry source enum
DO $$ BEGIN
    CREATE TYPE pharma.ledger_source AS ENUM (
      'PHARMASIGHT',
      'BANK',
      'MANUAL'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ========== BANK ACCOUNTS ==========
-- Bank accounts attached to a pharmacy. One pharmacy can have multiple bank accounts.
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

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_bank_account_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_bank_account_updated_at ON pharma.bank_accounts;
CREATE TRIGGER trigger_update_bank_account_updated_at
    BEFORE UPDATE ON pharma.bank_accounts
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_bank_account_updated_at();

-- ========== BANK IMPORT BATCHES ==========
-- Each CSV upload (per bank account) is grouped as an import batch.
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

-- ========== BANK TRANSACTIONS ==========
-- Raw lines imported from CSV, one row per bank statement line.
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
-- Note: Using a partial unique index that allows nulls for safety
CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_transactions_unique_import 
  ON pharma.bank_transactions(bank_account_id, date, amount, COALESCE(description, ''))
  WHERE external_id IS NULL;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_bank_transaction_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS trigger_update_bank_transaction_updated_at ON pharma.bank_transactions;
CREATE TRIGGER trigger_update_bank_transaction_updated_at
    BEFORE UPDATE ON pharma.bank_transactions
    FOR EACH ROW
    EXECUTE FUNCTION pharma.update_bank_transaction_updated_at();

-- ========== LEDGER ENTRIES ==========
-- Single source of truth for all accounting movements.
-- PharmaSight journals, bank classifications, manual adjustments all create rows here.
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

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION pharma.update_ledger_entry_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
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

