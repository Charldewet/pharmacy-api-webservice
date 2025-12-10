-- ========== MANAGEMENT FINANCIAL STATEMENTS ==========
-- Step 6: Add report_category to accounts for P&L reporting

-- Add report_category column to accounts table
ALTER TABLE pharma.accounts
  ADD COLUMN IF NOT EXISTS report_category varchar(50);

-- Create index for report_category lookups
CREATE INDEX IF NOT EXISTS idx_accounts_report_category 
  ON pharma.accounts(report_category) 
  WHERE report_category IS NOT NULL;

-- Add comment explaining report_category
COMMENT ON COLUMN pharma.accounts.report_category IS 
  'Category for P&L reporting: revenue, cogs, expenses, other_income, other_expenses. NULL accounts are excluded from management statements.';
