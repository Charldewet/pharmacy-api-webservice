-- ========== SEED CHART OF ACCOUNTS ==========
-- Initial chart of accounts based on Tugela Pharmacy 2025 AFS + Reitz Apteek MIS
-- This is a global chart shared across all pharmacies

-- Clear existing accounts (if re-seeding)
-- TRUNCATE TABLE pharma.accounts CASCADE;

-- ========== ASSETS (1000-1999) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('1000', 'Cash on Hand', 'ASSET', 'CURRENT_ASSET', 1000, 'Till cash, petty cash'),
('1010', 'Bank – Primary', 'ASSET', 'CURRENT_ASSET', 1010, 'Main pharmacy bank account (per bank account we''ll track at bank_accounts level)'),
('1020', 'Bank – Other', 'ASSET', 'CURRENT_ASSET', 1020, 'Secondary accounts if needed'),
('1100', 'Debtors / Trade Receivables', 'ASSET', 'CURRENT_ASSET', 1100, 'Account Sales, medical aids etc.'),
('1200', 'Inventory', 'ASSET', 'CURRENT_ASSET', 1200, 'Stock on hand'),
('1300', 'VAT Control', 'ASSET', 'CURRENT_ASSET', 1300, 'VAT asset/liability net position'),
('1400', 'Takings Clearing', 'ASSET', 'CLEARING', 1400, 'Used for card settlements / cash deposits vs POS sales'),
('1500', 'Loans Receivable', 'ASSET', 'NONCURRENT_ASSET', 1500, 'Short-term loans in AFS'),
('1600', 'Property, Plant & Equipment', 'ASSET', 'NONCURRENT_ASSET', 1600, 'Furniture, solar system, etc.'),
('1700', 'Goodwill & Intangibles', 'ASSET', 'NONCURRENT_ASSET', 1700, 'Pharmacy goodwill etc.')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== LIABILITIES & EQUITY (2000-3999) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('2000', 'Trade Creditors', 'LIABILITY', 'CURRENT_LIABILITY', 2000, 'Supplier balances'),
('2100', 'Accrued Expenses', 'LIABILITY', 'CURRENT_LIABILITY', 2100, 'Provisions, WCA, etc.'),
('2200', 'Borrowings – Bank Loans', 'LIABILITY', 'NONCURRENT_LIAB', 2200, 'Term loans, finance leases'),
('2210', 'Borrowings – Intercompany', 'LIABILITY', 'NONCURRENT_LIAB', 2210, 'Loans from other pharmacies / trusts'),
('2300', 'PAYE & SDL Control', 'LIABILITY', 'CURRENT_LIABILITY', 2300, 'Payroll liabilities'),
('2310', 'UIF Control', 'LIABILITY', 'CURRENT_LIABILITY', 2310, 'UIF'),
('2400', 'VAT Payable', 'LIABILITY', 'CURRENT_LIABILITY', 2400, 'If VAT is in liability position'),
('3000', 'Share Capital', 'EQUITY', 'EQUITY', 3000, '100 ordinary shares'),
('3100', 'Retained Earnings', 'EQUITY', 'EQUITY', 3100, 'Accumulated profit/loss')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== INCOME (4000-4999) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('4000', 'Sales – Dispensary', 'INCOME', 'SALES', 4000, 'MIS "Dispensary"; POS dispensary turnover'),
('4010', 'Sales – Front Shop', 'INCOME', 'SALES', 4010, 'Front shop, OTC, cosmetics etc.'),
('4020', 'Sales – Other / Clinic', 'INCOME', 'SALES', 4020, 'Clinic income, services'),
('4100', 'Sales – Account', 'INCOME', 'SALES', 4100, 'MIS "Account Sales" if you want explicit tracking'),
('4110', 'Sales – Cash / COD', 'INCOME', 'SALES', 4110, 'MIS "Cash Sales" + "COD Sales" (optional separate)'),
('4200', 'Other Income – Loyalty', 'OTHER_INCOME', 'OTHER_OP', 4200, 'AFS "Loyalty Rewards Program"'),
('4210', 'Other Income – Rebates', 'OTHER_INCOME', 'OTHER_OP', 4210, 'MIS "**REBATE" by supplier'),
('4220', 'Other Income – Other', 'OTHER_INCOME', 'OTHER_OP', 4220, 'MIS "Other Income", government grants etc.'),
('4300', 'Interest Received', 'OTHER_INCOME', 'FIN_INCOME', 4300, 'MIS "Interest"; bank interest')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== COST OF SALES (5000-5999) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('5000', 'Cost of Sales – Merchandise', 'COGS', 'COGS', 5000, 'Main COGS from POS / stock system'),
('5010', 'Stock Adjustments / Write-offs', 'COGS', 'COGS', 5010, 'Shrinkage, expiry, manual adjustments'),
('5100', 'Direct Delivery / Freight In', 'COGS', 'DIRECT_COST', 5100, 'MIS "Delivery Charge", inbound freight linked to stock'),
('5200', 'Merchant Fees (Card) – Direct', 'COGS', 'DIRECT_COST', 5200, 'Could sit in COGS or expenses; decide during implementation (often treated as expense)')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== OPERATING EXPENSES - PROFESSIONAL & ADMIN (6000-6099) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('6000', 'Accounting Fees', 'EXPENSE', 'ADMIN_PROF', 6000, 'AFS "Accounting fees", MIS "ACCOUNTING FEES"'),
('6010', 'Admin & Selling Expenses', 'EXPENSE', 'ADMIN_OTHER', 6010, 'AFS "Admin and selling expenses"'),
('6020', 'Bank Charges', 'EXPENSE', 'ADMIN_BANK', 6020, 'AFS "Bank charges"; MIS "BANK CHARGES"'),
('6030', 'Consulting Fees', 'EXPENSE', 'ADMIN_PROF', 6030, 'AFS & MIS "Consulting fees"'),
('6040', 'Printing & Stationery', 'EXPENSE', 'ADMIN_OFFICE', 6040, 'AFS & MIS "Printing and stationery / Stationery"'),
('6050', 'Postage & Courier', 'EXPENSE', 'ADMIN_OFFICE', 6050, 'AFS "Postage"; MIS "POSTAGE & COURIER"'),
('6060', 'Subscriptions & Licences', 'EXPENSE', 'ADMIN_SUBS', 6060, 'AFS "Subscriptions"; MIS "SUBSCRIPTIONS", PSSA, SAPC, SAMRO, etc.'),
('6070', 'Computer / Software / POS', 'EXPENSE', 'IT', 6070, 'AFS "Computer expenses"; MIS "COMPUTER SOFTWARE", "POINT OF SALE"'),
('6080', 'Telephone & Internet', 'EXPENSE', 'IT', 6080, 'AFS "Telephone and fax"; MIS "TELECOMMUNICATIONS", Vodacom, VOX')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== OPERATING EXPENSES - PREMISES & OCCUPANCY (6100-6199) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('6100', 'Rent – Premises', 'EXPENSE', 'OCCUPANCY', 6100, 'AFS "Lease rental on operating lease", MIS "RENTAL PREMISES"'),
('6110', 'Electricity & Water', 'EXPENSE', 'OCCUPANCY', 6110, 'AFS "Electricity and water"; MIS "WATER & ELECTRICITY"'),
('6120', 'Municipal Rates / Services', 'EXPENSE', 'OCCUPANCY', 6120, 'For cash-paid municipal accounts you mentioned'),
('6130', 'Security', 'EXPENSE', 'OCCUPANCY', 6130, 'AFS "Security"; MIS "SECURITY"'),
('6140', 'Cleaning', 'EXPENSE', 'OCCUPANCY', 6140, 'AFS "Cleaning"; MIS "CLEANING MATERIALS"')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== OPERATING EXPENSES - STAFF COSTS (6200-6299) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('6200', 'Salaries & Wages', 'EXPENSE', 'STAFF_COSTS', 6200, 'AFS "Salaries"; MIS "SALARIES" (core)'),
('6210', 'Casual / Temp Wages', 'EXPENSE', 'STAFF_COSTS', 6210, 'MIS "Casual Wages", "Temps", etc.'),
('6220', 'Bonuses & Leave Pay', 'EXPENSE', 'STAFF_COSTS', 6220, 'MIS "Bonus", "Leave Pay"'),
('6230', 'Clinic Staff', 'EXPENSE', 'STAFF_COSTS', 6230, 'MIS "Clinic" salary lines'),
('6240', 'Management Salaries', 'EXPENSE', 'STAFF_COSTS', 6240, 'MIS "Management"'),
('6250', 'Staff Training', 'EXPENSE', 'STAFF_COSTS', 6250, 'AFS "Training"; MIS "STAFF TRAINING"'),
('6260', 'Staff Welfare', 'EXPENSE', 'STAFF_COSTS', 6260, 'AFS & MIS "Staff welfare"'),
('6270', 'Staff Clothing / Uniforms', 'EXPENSE', 'STAFF_COSTS', 6270, 'AFS "Staff clothing"; MIS "UNIFORMS"'),
('6280', 'COID / Workmen''s Comp', 'EXPENSE', 'STAFF_COSTS', 6280, 'AFS "COID: Workmanship Compensation"; MIS "WCA"'),
('6290', 'PAYE / SDL / UIF Expense', 'EXPENSE', 'STAFF_COSTS', 6290, 'Employer cost (company SDL, UIF); liability side goes to control accounts')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== OPERATING EXPENSES - MARKETING & COMMUNITY (6300-6399) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('6300', 'Advertising & Marketing', 'EXPENSE', 'MARKETING', 6300, 'AFS "Advertising"; MIS "ADVERTISING", promotions'),
('6310', 'Sponsorships & Donations', 'EXPENSE', 'MARKETING', 6310, 'AFS "Sponserships"; MIS "#DONATIONS#"'),
('6320', 'Flowers & Gifts', 'EXPENSE', 'MARKETING', 6320, 'AFS "Flowers"')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== OPERATING EXPENSES - OPERATIONS & OTHER (6400-6599) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('6400', 'Cash in Transit', 'EXPENSE', 'OPERATIONS', 6400, 'AFS "Cash in Transit"'),
('6410', 'Packaging / Wrapping', 'EXPENSE', 'OPERATIONS', 6410, 'AFS "Packaging"; MIS "WRAPPING & PACKING"'),
('6420', 'Consumables', 'EXPENSE', 'OPERATIONS', 6420, 'AFS & MIS "Consumables" (clinic & pharmacy)'),
('6430', 'Rental – Equipment', 'EXPENSE', 'OPERATIONS', 6430, 'AFS "Hire - Equipment"; MIS "RENTAL EQUIPMENT"'),
('6440', 'Repairs & Maintenance', 'EXPENSE', 'OPERATIONS', 6440, 'AFS & MIS "Repairs and maintenance" (all subtypes)'),
('6450', 'Motor Vehicle Expense', 'EXPENSE', 'OPERATIONS', 6450, 'AFS "Motor vehicle expense"; MIS vehicle costs'),
('6460', 'Fuel & Oil', 'EXPENSE', 'OPERATIONS', 6460, 'AFS "Petrol and oil"; MIS "FUEL"'),
('6470', 'Insurance – Short Term', 'EXPENSE', 'OPERATIONS', 6470, 'AFS "Insurance"; MIS "INSURANCE – SHORT TERM"'),
('6480', 'Insurance – Life', 'EXPENSE', 'OPERATIONS', 6480, 'MIS "INSURANCE – LIFE"'),
('6490', 'Medical Waste & Health & Safety', 'EXPENSE', 'OPERATIONS', 6490, 'MIS "MEDICAL WASTE", "HEALTH & SAFETY"'),
('6500', 'Small Assets < R7,000', 'EXPENSE', 'OPERATIONS', 6500, 'AFS "Assets <R7000"'),
('6510', 'Loose Tools', 'EXPENSE', 'OPERATIONS', 6510, 'MIS "LOOSE TOOLS"'),
('6520', 'Entertainment', 'EXPENSE', 'OPERATIONS', 6520, 'AFS & MIS "Entertainment"'),
('6530', 'Fines & Penalties', 'EXPENSE', 'OPERATIONS', 6530, 'AFS "Fines and penalties"'),
('6540', 'Merchant Fees – Bank', 'EXPENSE', 'OPERATIONS', 6540, 'MIS "MERCHANT FEE" (if not treated as COGS)')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== OPERATING EXPENSES - DEPRECIATION & AMORTISATION (6600-6699) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('6600', 'Depreciation – PPE', 'EXPENSE', 'DEPRECIATION', 6600, 'AFS "Depreciation – tangible assets", MIS total depreciation'),
('6610', 'Amortisation – Intangibles', 'EXPENSE', 'DEPRECIATION', 6610, 'Goodwill amortisation if applied')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== FINANCE COSTS (7000-7999) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('7000', 'Interest Paid – Loans', 'FINANCE_COST', 'FINANCE_COSTS', 7000, 'AFS "Interest Paid – Other"; MIS "INTEREST"'),
('7010', 'Bank Overdraft Interest', 'FINANCE_COST', 'FINANCE_COSTS', 7010, 'If split out later')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

-- ========== TAX (8000-8999) ==========
INSERT INTO pharma.accounts (code, name, type, category, display_order, notes) VALUES
('8000', 'Income Tax Expense', 'TAX', 'TAX', 8000, 'AFS income tax computation / provisional tax')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  category = EXCLUDED.category,
  display_order = EXCLUDED.display_order,
  notes = EXCLUDED.notes,
  updated_at = NOW();

