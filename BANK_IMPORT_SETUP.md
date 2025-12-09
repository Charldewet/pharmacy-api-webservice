# Bank CSV Import Flow - Step 3 Complete ✅

This document describes the implementation of Step 3 of the PharmaSight Management Accounts financial system.

## Overview

The bank CSV import system allows users to upload bank statement CSV files, preview the parsed data, and import transactions into the database. The system supports multiple South African bank formats (FNB, ABSA, Standard Bank) with extensible parser architecture.

## Features

- **CSV Upload & Parsing** - Support for FNB, ABSA, and Standard Bank formats
- **Preview Before Import** - Review parsed transactions before saving
- **Error Handling** - Track parsing errors per row
- **Duplicate Prevention** - Unique index prevents exact duplicate imports
- **Flexible Parser Architecture** - Easy to add new bank formats

## Files Created

1. **`pharma_api/app/services/bank_parsers.py`** - CSV parser module with bank-specific parsers
2. **`pharma_api/app/routers/bank_imports.py`** - API router for import endpoints
3. **`schema_banking.sql`** - Updated with `bank_import_errors` table
4. **`schema.sql`** - Updated main schema file

## Database Schema

### Bank Import Errors Table

```sql
CREATE TABLE pharma.bank_import_errors (
  id                   bigserial PRIMARY KEY,
  bank_import_batch_id bigint REFERENCES pharma.bank_import_batches(id),
  row_number           integer NOT NULL,
  raw_data             jsonb,
  error_message        text NOT NULL,
  created_at           timestamptz NOT NULL DEFAULT now()
);
```

## API Endpoints

### Preview Import

Preview a CSV file without saving to database.

```http
POST /bank-imports/preview
Authorization: Bearer YOUR_API_KEY
Content-Type: multipart/form-data

pharmacy_id: 1
bank_account_id: 5
file: [CSV file]
```

**Response:**
```json
{
  "pharmacy_id": 1,
  "bank_account_id": 5,
  "summary": {
    "transaction_count": 123,
    "total_in": 456789.12,
    "total_out": -345678.90,
    "min_date": "2025-03-01",
    "max_date": "2025-03-31"
  },
  "sample_transactions": [
    {
      "row_number": 2,
      "date": "2025-03-01",
      "description": "CARD PURCHASE - VODACOM",
      "reference": "POS 12345",
      "amount": -450.00,
      "balance": 10234.56
    }
  ],
  "errors": [
    {
      "row_number": 10,
      "error": "Invalid date format",
      "raw_data": {...}
    }
  ]
}
```

### Confirm Import

Confirm and save the import to database.

```http
POST /bank-imports/confirm
Authorization: Bearer YOUR_API_KEY
Content-Type: multipart/form-data

pharmacy_id: 1
bank_account_id: 5
file_name: "statement_march_2025.csv"
file: [CSV file]
notes: "March 2025 statement"
```

**Response:**
```json
{
  "bank_import_batch_id": 42,
  "transactions_inserted": 120,
  "transactions_skipped_as_duplicates": 8,
  "errors_count": 3,
  "period_start": "2025-03-01",
  "period_end": "2025-03-31",
  "status": "IMPORTED"
}
```

**Parameters:**
- `skip_duplicates` (boolean, default: true) - Whether to skip duplicate transactions

### Get Import Batch

Get details of a specific import batch.

```http
GET /bank-imports/batches/{batch_id}
Authorization: Bearer YOUR_API_KEY
```

### List Import Batches

List import batches for a pharmacy.

```http
GET /bank-imports/pharmacies/{pharmacy_id}/batches?limit=50&offset=0
Authorization: Bearer YOUR_API_KEY
```

## Supported Bank Formats

### FNB (First National Bank)
- Date formats: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`
- Amount fields: `Amount`, `Debit`, `Credit`
- Description fields: `Description`, `Transaction Description`, `Narrative`

### ABSA
- Date formats: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`
- Amount fields: `Amount`, `Debit`, `Credit`, `Withdrawal`, `Deposit`
- Description fields: `Description`, `Transaction Description`, `Narrative`, `Memo`

### Standard Bank
- Date formats: `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`
- Amount fields: `Amount`, `Debit`, `Credit`
- Description fields: `Description`, `Transaction Description`, `Narrative`

## Parser Architecture

The parser system is designed to be extensible:

1. **Base Parser** (`BankParser`) - Abstract base class with common functionality
2. **Bank-Specific Parsers** - Inherit from base and implement bank-specific field mappings
3. **Parser Factory** - `get_parser(bank_name)` returns appropriate parser

To add a new bank format:

1. Create a new parser class inheriting from `BankParser`
2. Implement `_parse_date()`, `_get_description()`, `_parse_amount()` methods
3. Add bank name detection logic to `get_parser()`

## Import Flow

1. **Upload & Preview**
   - User uploads CSV file via `/bank-imports/preview`
   - System detects bank format from `bank_accounts.bank_name`
   - CSV is parsed row by row
   - Valid transactions and errors are separated
   - Summary statistics computed
   - Sample transactions (first 20) returned

2. **Confirm & Import**
   - User confirms import via `/bank-imports/confirm`
   - System re-parses CSV (or uses cached data)
   - Creates `bank_import_batch` record
   - Inserts valid transactions into `bank_transactions`
   - Inserts errors into `bank_import_errors`
   - Returns import summary

## Error Handling

- **Invalid Date Format** - Row marked as error, stored in `bank_import_errors`
- **Missing Required Fields** - Row marked as error
- **Invalid Amount Format** - Row marked as error
- **Unsupported Bank Format** - Returns 422 error

## Duplicate Detection

The system uses a two-tier duplicate detection strategy:

### 1. External ID (Preferred)
- If the bank CSV includes a unique transaction ID (stored in `external_id`)
- Uses unique index: `(bank_account_id, external_id)`
- Most reliable method for duplicate detection
- Parser automatically extracts from common fields: Transaction ID, Reference Number, External ID, etc.

### 2. Heuristic Fallback
- If no external_id is available
- Uses composite match: `(bank_account_id, date, amount, description)`
- Unique index ensures exact duplicates are prevented
- Less reliable but works when banks don't provide unique IDs

### Behavior
- When `skip_duplicates=true` (default):
  - Duplicates are detected before insert and skipped
  - Count of skipped duplicates returned in response
- When `skip_duplicates=false`:
  - Attempts to insert all transactions
  - Database unique constraints will prevent duplicates
  - Failed inserts are counted as skipped

## Data Normalization

All descriptions are normalized:
- Trimmed of whitespace
- Multiple spaces collapsed to single space
- Converted to uppercase for consistency

Amounts are stored as:
- **Positive** = Money in (credits)
- **Negative** = Money out (debits)

## Next Steps

Future enhancements:
- Step 4: Bank transaction classification and rules
- Step 5: Auto-classification using AI/ML
- Step 6: Bulk import operations
- Step 7: Import history and audit trail

---

**Last Updated**: December 2025

