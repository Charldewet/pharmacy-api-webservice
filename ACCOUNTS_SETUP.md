# Chart of Accounts Setup - Step 1 Complete ✅

This document describes the implementation of Step 1 of the PharmaSight Management Accounts financial system.

## Overview

A global chart of accounts has been created that is shared across all pharmacies. This chart is based on:
- Tugela Pharmacy 2025 AFS + detailed income statement
- Reitz Apteek Management Income Statement (MIS)

The accounts table uses `pharmacy_id` from the existing `pharmacies` table as the entity key. Future tables (ledger_entries, bank_transactions, etc.) will reference `pharmacy_id` to associate transactions with specific pharmacies.

## Files Created

1. **`schema_accounts.sql`** - Standalone migration file for the accounts table
2. **`seed_accounts.sql`** - Seed data with all chart of accounts entries
3. **`scripts/load_accounts.py`** - Python script to create, load, and verify accounts
4. **`schema.sql`** - Updated main schema file (includes accounts table)

## Database Schema

### Accounts Table

```sql
CREATE TABLE pharma.accounts (
  id                bigserial PRIMARY KEY,
  code              varchar(10) NOT NULL UNIQUE,
  name              text NOT NULL,
  type              pharma.account_type NOT NULL,
  category          text NOT NULL,
  parent_account_id bigint REFERENCES pharma.accounts(id),
  is_active         boolean NOT NULL DEFAULT true,
  display_order     integer NOT NULL DEFAULT 0,
  notes             text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
```

### Account Types (Enum)

- `ASSET`
- `LIABILITY`
- `EQUITY`
- `INCOME`
- `COGS`
- `EXPENSE`
- `FINANCE_COST`
- `OTHER_INCOME`
- `TAX`

### Code Ranges

- **1000-1999**: Assets
- **2000-2999**: Liabilities
- **3000-3999**: Equity
- **4000-4999**: Income (Sales & Rebates)
- **5000-5999**: Cost of Sales / Direct Costs
- **6000-6999**: Operating Expenses
- **7000-7499**: Finance Costs
- **7500-7999**: Other Income
- **8000-8999**: Tax
- **9000-9999**: Reserved / future

## Setup Instructions

### Option 1: Using the Python Script (Recommended)

```bash
python scripts/load_accounts.py
```

This script will:
1. Create the accounts table and enum type if they don't exist
2. Load all seed accounts data
3. Verify data integrity (unique codes, valid types, required accounts)

### Option 2: Using SQL Files Directly

```bash
# Create the table
psql $DATABASE_URL -f schema_accounts.sql

# Load seed data
psql $DATABASE_URL -f seed_accounts.sql
```

## Verification

After loading, verify the accounts:

```sql
-- Check total count
SELECT COUNT(*) FROM pharma.accounts;

-- Check by type
SELECT type, COUNT(*) 
FROM pharma.accounts 
GROUP BY type 
ORDER BY type;

-- List all active accounts
SELECT code, name, type, category 
FROM pharma.accounts 
WHERE is_active = true 
ORDER BY display_order;
```

## Required Core Accounts

The following accounts are verified to exist:
- `4000` - Sales – Dispensary (INCOME)
- `4010` - Sales – Front Shop (INCOME)
- `5000` - Cost of Sales – Merchandise (COGS)
- `6200` - Salaries & Wages (EXPENSE)
- `6100` - Rent – Premises (EXPENSE)
- `7000` - Interest Paid – Loans (FINANCE_COST)

## Account Categories

Accounts are organized into logical categories for P&L reporting:

- **CURRENT_ASSET** / **NONCURRENT_ASSET** - Balance sheet assets
- **CURRENT_LIABILITY** / **NONCURRENT_LIAB** - Balance sheet liabilities
- **EQUITY** - Equity accounts
- **SALES** - Revenue accounts
- **COGS** / **DIRECT_COST** - Cost of goods sold
- **ADMIN_PROF** / **ADMIN_OTHER** / **ADMIN_BANK** / **ADMIN_OFFICE** / **ADMIN_SUBS** - Administrative expenses
- **IT** - IT-related expenses
- **OCCUPANCY** - Premises and occupancy costs
- **STAFF_COSTS** - Staff-related expenses
- **MARKETING** - Marketing and community expenses
- **OPERATIONS** - Operational expenses
- **DEPRECIATION** - Depreciation and amortization
- **FINANCE_COSTS** - Finance costs
- **OTHER_OP** / **FIN_INCOME** - Other income
- **TAX** - Tax accounts

## Next Steps

Future steps will include:
- Step 2: Bank accounts table
- Step 3: Ledger entries table
- Step 4: Bank transactions table
- Step 5: P&L report generation

## Notes

- Accounts are **global** - not duplicated per pharmacy
- Pharmacy-specific data will be tracked in `ledger_entries` and `bank_transactions` tables (to be created)
- The `parent_account_id` field allows for future sub-account hierarchies
- Accounts can be soft-disabled using `is_active = false` without deleting them
- `display_order` controls the order in which accounts appear in reports

## Mapping Reference

For internal reference, mappings from financial statements to account codes:
- **Tugela AFS line → account code** (to be documented)
- **Reitz MIS line → account code** (to be documented)

This mapping can be maintained in Notion/Confluence or as a CSV file for reference during implementation.

---

**Last Updated**: December 2025

