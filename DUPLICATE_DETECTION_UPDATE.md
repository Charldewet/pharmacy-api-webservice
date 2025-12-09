# Duplicate Detection Update - Less Strict Matching

## Overview

The duplicate detection logic has been updated to be **less strict** and provide better visibility into suspected duplicates. This addresses the issue where only 1400 out of 1700 transactions were being imported.

## Changes Made

### 1. Less Strict Duplicate Detection

**Before**: Transactions were skipped if they matched on `(date, amount, description)` - this was too strict and could skip legitimate transactions.

**Now**: 
- **High Confidence Skip**: Only skip if `external_id` matches (deterministic hash) - this catches true duplicates
- **Medium Confidence Skip**: Skip if exact match `(date, amount, description)` AND it's from a previous import batch
- **Low Confidence Flag**: Flag as suspected duplicate if `(date, amount)` matches but description differs - **don't skip**, let user decide

### 2. Suspected Duplicates Returned in Response

Both the `/preview` and `/confirm` endpoints now return a `suspected_duplicates` array that includes:

```json
{
  "suspected_duplicates": [
    {
      "row_number": 42,
      "date": "2025-11-29",
      "description": "SERVICE FEE ACC 301666148",
      "amount": -341.40,
      "reference": null,
      "match_reason": "Exact match: Same date, amount, and description (from previous import)",
      "existing_transaction_id": 12345,
      "existing_date": "2025-11-29",
      "existing_description": "SERVICE FEE ACC 301666148"
    },
    {
      "row_number": 100,
      "date": "2025-11-30",
      "description": "PAYMENT FROM CUSTOMER",
      "amount": 5000.00,
      "reference": "REF123",
      "match_reason": "Similar match: Same date (2025-11-30) and amount (5000.0), but description differs",
      "existing_transaction_id": 12346,
      "existing_date": "2025-11-30",
      "existing_description": "PAYMENT FROM CLIENT"
    }
  ]
}
```

### 3. Preview Endpoint Shows Suspected Duplicates

The `/api/bank-imports/preview` endpoint now checks the first 100 transactions for suspected duplicates and includes them in the response. This allows users to review potential duplicates **before** confirming the import.

## API Response Changes

### ImportConfirmResponse

```typescript
{
  "bank_import_batch_id": 123,
  "transactions_inserted": 1400,
  "transactions_skipped_as_duplicates": 300,
  "suspected_duplicates": [
    // Array of SuspectedDuplicate objects
  ],
  "errors_count": 0,
  "period_start": "2025-03-01",
  "period_end": "2025-11-29",
  "status": "IMPORTED"
}
```

### ImportPreviewResponse

```typescript
{
  "pharmacy_id": 1,
  "bank_account_id": 1,
  "summary": {
    "transaction_count": 1757,
    "total_in": 15394604.51,
    "total_out": 15231904.44,
    "min_date": "2025-03-01",
    "max_date": "2025-11-29"
  },
  "sample_transactions": [...],
  "suspected_duplicates": [
    // Array of SuspectedDuplicate objects (first 100 rows checked)
  ],
  "errors": []
}
```

## Match Reasons

The `match_reason` field explains why a transaction is flagged:

1. **"High confidence: Same external_id (deterministic hash)"** - Skipped (true duplicate)
2. **"Exact match: Same date, amount, and description (from previous import)"** - Skipped (likely duplicate)
3. **"Similar match: Same date (YYYY-MM-DD) and amount (X.XX), but description differs"** - **Not skipped**, flagged for review

## Frontend Integration

### Display Suspected Duplicates

```javascript
// After preview or confirm
const response = await fetch('/api/bank-imports/preview', {...});
const data = await response.json();

if (data.suspected_duplicates && data.suspected_duplicates.length > 0) {
  // Show a modal or section with suspected duplicates
  displaySuspectedDuplicates(data.suspected_duplicates);
}

function displaySuspectedDuplicates(duplicates) {
  duplicates.forEach(dup => {
    console.log(`Row ${dup.row_number}: ${dup.match_reason}`);
    console.log(`  New: ${dup.date} | ${dup.description} | ${dup.amount}`);
    console.log(`  Existing: ${dup.existing_date} | ${dup.existing_description}`);
  });
}
```

### User Decision Flow

1. **Preview** shows suspected duplicates
2. User reviews the list
3. User can:
   - Proceed with import (similar matches will still be imported)
   - Cancel and fix the CSV
   - Note which transactions are duplicates for manual review later

## Why Only 1400 of 1700 Were Imported?

The previous logic was too strict:
- It skipped transactions if `(date, amount, description)` matched exactly
- This could skip legitimate transactions if:
  - The same transaction appeared in overlapping statement periods
  - Description normalization caused false matches
  - Multiple transactions with same date/amount/description were legitimate

**New behavior**:
- Only skips high-confidence duplicates (external_id match)
- Flags medium-confidence matches but still imports them if from same batch
- Flags low-confidence matches but **doesn't skip** them

## Expected Results

After this update:
- **More transactions imported**: Similar matches are no longer automatically skipped
- **Better visibility**: Users can see which transactions are suspected duplicates
- **User control**: Users can review and decide what to do with suspected duplicates

## Testing

To verify the changes:
1. Upload a bank statement CSV
2. Check the preview response for `suspected_duplicates`
3. Confirm the import
4. Check the confirm response for `suspected_duplicates`
5. Verify that more transactions are imported (closer to 1700 instead of 1400)

