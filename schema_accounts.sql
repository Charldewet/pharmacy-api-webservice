-- ========== FINANCIAL MANAGEMENT - CHART OF ACCOUNTS ==========
-- Step 1: Core Accounting Setup for PharmaSight Management Accounts
-- Global chart of accounts shared across all pharmacies

-- Account type enum
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

-- Accounts table - global chart of accounts
CREATE TABLE IF NOT EXISTS pharma.accounts (
  id                bigserial PRIMARY KEY,
  code              varchar(10) NOT NULL UNIQUE,
  name              text NOT NULL,
  type              pharma.account_type NOT NULL,
  category          text NOT NULL,
  parent_account_id bigint REFERENCES pharma.accounts(id) ON DELETE SET NULL,
  is_active         boolean NOT NULL DEFAULT true,
  display_order      integer NOT NULL DEFAULT 0,
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

