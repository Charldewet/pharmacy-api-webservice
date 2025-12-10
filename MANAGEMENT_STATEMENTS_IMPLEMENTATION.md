# Management Financial Statements - Backend Implementation Complete ✅

This document describes the backend implementation of Step 6 - Monthly Management Financials.

## Overview

The management P&L statement system generates profit & loss reports from ledger entries, grouped by `report_category`. Only accounts with a non-NULL `report_category` are included in the statements.

## Files Created

1. **`schema_management_financials.sql`** - Migration to add `report_category` column to accounts table
2. **`pharma_api/app/routers/management_statement.py`** - API router for management statements
3. **`scripts/load_management_financials_schema.py`** - Script to apply and verify the schema migration
4. **`pharma_api/app/schemas.py`** - Updated with management statement schemas

## Database Changes

### Migration: Add report_category Column

The migration adds a `report_category` column to the `pharma.accounts` table:

```sql
ALTER TABLE pharma.accounts
  ADD COLUMN IF NOT EXISTS report_category varchar(50);

CREATE INDEX IF NOT EXISTS idx_accounts_report_category 
  ON pharma.accounts(report_category) 
  WHERE report_category IS NOT NULL;
```

**Valid report_category values:**
- `revenue` - Income accounts (typically 4000-4999)
- `cogs` - Cost of goods sold (typically 5000-5999)
- `expenses` - Operating expenses (typically 6000-6999)
- `other_income` - Other income accounts (typically 7500-7999)
- `other_expenses` - Other expense accounts

**Note:** Accounts with NULL `report_category` are excluded from management statements.

## API Endpoints

### 1. Monthly Management Statement

**Endpoint:**
```
GET /pharmacies/{pharmacy_id}/management-statement?year=YYYY&month=MM
```

**Parameters:**
- `pharmacy_id` (path): ID of the pharmacy
- `year` (query, required): Year (e.g., 2025)
- `month` (query, required): Month number (1-12)

**Example:**
```http
GET /pharmacies/1/management-statement?year=2025&month=12
```

**Response:**
```json
{
  "pharmacy_id": 1,
  "year": 2025,
  "month": 12,
  "from_date": "2025-12-01",
  "to_date": "2025-12-31",
  "summary": {
    "total_revenue": 450000.00,
    "total_cogs": 300000.00,
    "gross_profit": 150000.00,
    "gross_profit_percent": 33.3,
    "total_expenses": 105000.00,
    "operating_profit": 45000.00,
    "total_other_income": 2000.00,
    "total_other_expenses": 1000.00,
    "net_profit": 46000.00
  },
  "revenue": [
    {
      "account_id": 4000,
      "code": "4000",
      "name": "OTC Sales",
      "amount": 250000.00
    },
    {
      "account_id": 4010,
      "code": "4010",
      "name": "Dispensary Sales",
      "amount": 200000.00
    }
  ],
  "cogs": [
    {
      "account_id": 5000,
      "code": "5000",
      "name": "Cost of Sales – OTC",
      "amount": -180000.00
    },
    {
      "account_id": 5010,
      "code": "5010",
      "name": "Cost of Sales – Disp",
      "amount": -120000.00
    }
  ],
  "expenses": [
    {
      "account_id": 6000,
      "code": "6000",
      "name": "Salaries & Wages",
      "amount": -85000.00
    },
    {
      "account_id": 6200,
      "code": "6200",
      "name": "Utilities",
      "amount": -12000.00
    }
  ],
  "other_income": [
    {
      "account_id": 7100,
      "code": "7100",
      "name": "Interest Received",
      "amount": 2000.00
    }
  ],
  "other_expenses": [
    {
      "account_id": 7200,
      "code": "7200",
      "name": "Bank Charges",
      "amount": -1000.00
    }
  ]
}
```

### 2. Historical Trend (Optional)

**Endpoint:**
```
GET /pharmacies/{pharmacy_id}/management-statement/trend?from=YYYY-MM&to=YYYY-MM
```

**Parameters:**
- `pharmacy_id` (path): ID of the pharmacy
- `from` (query, required): Start month in YYYY-MM format (e.g., 2025-01)
- `to` (query, required): End month in YYYY-MM format (e.g., 2025-12)

**Example:**
```http
GET /pharmacies/1/management-statement/trend?from=2025-01&to=2025-12
```

**Response:**
```json
[
  {
    "month": "2025-01",
    "revenue": 400000.00,
    "gross_profit": 130000.00,
    "net_profit": 40000.00
  },
  {
    "month": "2025-02",
    "revenue": 420000.00,
    "gross_profit": 135000.00,
    "net_profit": 41000.00
  }
]
```

## Implementation Details

### Double-Entry to Single-Entry Conversion

The system uses `ledger_entries` (double-entry bookkeeping) but converts them to account-level transactions for P&L reporting:

- **INCOME accounts**: Credits increase income (positive), debits decrease income (negative)
  - Net balance = Credits - Debits
- **EXPENSE/COGS accounts**: Debits increase expenses (positive), credits decrease expenses (negative)
  - Net balance = Debits - Credits

### Amount Sign Convention

Per the specification:
- **Revenue and other income**: Positive amounts
- **COGS and expenses**: Negative amounts (for readability in the API response)
- The internal calculation uses positive values, but the API response negates COGS and expenses

### Calculation Logic

1. **Date Range**: Computes first and last day of the specified month
2. **Account Aggregation**: Queries all accounts with non-NULL `report_category`
3. **Balance Calculation**: For each account, calculates net balance from ledger entries:
   - Sums debit-side entries (where account is debited)
   - Sums credit-side entries (where account is credited)
   - Applies account-type-specific logic to get net balance
4. **Grouping**: Groups accounts by `report_category` (revenue, cogs, expenses, etc.)
5. **Totals**: Calculates summary totals (revenue, COGS, gross profit, expenses, operating profit, net profit)

## Setup Instructions

### 1. Apply Database Migration

Run the migration script:

```bash
python scripts/load_management_financials_schema.py
```

This will:
- Add `report_category` column to `pharma.accounts`
- Create index on `report_category`
- Verify the schema changes

### 2. Set report_category on Accounts

Update accounts with appropriate `report_category` values:

```sql
-- Example: Set revenue accounts
UPDATE pharma.accounts 
SET report_category = 'revenue' 
WHERE code BETWEEN '4000' AND '4999' 
  AND type = 'INCOME';

-- Example: Set COGS accounts
UPDATE pharma.accounts 
SET report_category = 'cogs' 
WHERE code BETWEEN '5000' AND '5999' 
  AND type = 'COGS';

-- Example: Set expense accounts
UPDATE pharma.accounts 
SET report_category = 'expenses' 
WHERE code BETWEEN '6000' AND '6999' 
  AND type = 'EXPENSE';

-- Example: Set other income accounts
UPDATE pharma.accounts 
SET report_category = 'other_income' 
WHERE code BETWEEN '7500' AND '7999' 
  AND type = 'OTHER_INCOME';

-- Example: Set other expense accounts
UPDATE pharma.accounts 
SET report_category = 'other_expenses' 
WHERE code >= '8000' 
  AND type IN ('EXPENSE', 'FINANCE_COST');
```

### 3. Verify API Endpoints

Test the endpoints:

```bash
# Monthly statement
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/pharmacies/1/management-statement?year=2025&month=12"

# Trend data
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/pharmacies/1/management-statement/trend?from=2025-01&to=2025-12"
```

## Authentication

All endpoints require Bearer token authentication via the `Authorization` header:

```http
Authorization: Bearer your-api-key-here
```

## Error Handling

- **404**: Pharmacy not found
- **400**: Invalid date format or parameters
- **401**: Missing or invalid authentication token

## Performance Considerations

- The implementation uses a single optimized query to aggregate all account balances
- Indexes on `pharmacy_id`, `date`, and `report_category` ensure fast queries
- Zero-balance accounts are filtered out to reduce response size

## Next Steps (Frontend)

The frontend team should:
1. Add month/year selector on Management Financials screen
2. Call `/pharmacies/{id}/management-statement` endpoint on filter change
3. Display key metrics strip (turnover, GP, expenses, net profit)
4. Display P&L sections with subtotals and final totals
5. Optionally add trend charts using the trend endpoint

## Related Endpoints

- **Reconciliation Summary**: `GET /pharmacies/{id}/reconciliation-summary?month=YYYY-MM`
- **Ledger Entries**: `GET /ledger-entries/pharmacies/{id}?start_date=...&end_date=...`
- **Accounts**: `GET /accounts` (to view/update report_category)
