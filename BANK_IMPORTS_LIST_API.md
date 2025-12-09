# Bank Imports List API - Frontend Integration Guide

## Overview

The endpoint for listing historical bank import batches has been enhanced to include transaction counts and bank account details needed for the frontend display.

## Endpoint

**GET** `/bank-imports/pharmacies/{pharmacy_id}/batches`

### Request

```http
GET /bank-imports/pharmacies/1/batches?limit=50&offset=0
X-API-Key: your-api-key-here
```

**Query Parameters:**
- `limit` (optional, default: 50) - Maximum number of batches to return
- `offset` (optional, default: 0) - Number of batches to skip (for pagination)

### Response

**Success (200 OK):**

```json
[
  {
    "id": 6,
    "bank_account_id": 1,
    "pharmacy_id": 1,
    "period_start": "2025-03-01",
    "period_end": "2025-11-29",
    "file_name": "transactions.csv",
    "uploaded_by_user_id": null,
    "uploaded_at": "2025-12-09T11:25:12.765456+00:00",
    "status": "IMPORTED",
    "notes": null,
    "transaction_count": 1475,
    "bank_account_name": "Main SB2 148",
    "bank_name": "Standard Bank"
  },
  {
    "id": 5,
    "bank_account_id": 1,
    "pharmacy_id": 1,
    "period_start": "2025-03-01",
    "period_end": "2025-11-29",
    "file_name": "transactions.csv",
    "uploaded_by_user_id": null,
    "uploaded_at": "2025-12-09T11:15:30.339097+00:00",
    "status": "IMPORTED",
    "notes": null,
    "transaction_count": 0,
    "bank_account_name": "Main SB2 148",
    "bank_name": "Standard Bank"
  }
]
```

**Error (404 Not Found):**

```json
{
  "detail": "Pharmacy not found"
}
```

## Response Fields

### Standard Fields (from BankImportBatch)
- `id` - Batch ID
- `bank_account_id` - ID of the bank account
- `pharmacy_id` - ID of the pharmacy
- `period_start` - Start date of the import period (nullable)
- `period_end` - End date of the import period (nullable)
- `file_name` - Original filename of the uploaded CSV
- `uploaded_by_user_id` - ID of user who uploaded (nullable)
- `uploaded_at` - Timestamp when batch was uploaded
- `status` - Import status: `IMPORTED`, `CLASSIFIED_PARTIAL`, `CLASSIFIED_COMPLETE`, `POSTED_TO_LEDGER`
- `notes` - Optional notes about the import (nullable)

### Enhanced Fields (from BankImportBatchWithDetails)
- `transaction_count` - Number of transactions in this batch
- `bank_account_name` - Display name of the bank account (e.g., "Main SB2 148")
- `bank_name` - Name of the bank (e.g., "Standard Bank")

## Frontend Integration Example

```javascript
async function fetchPastImports(pharmacyId) {
  try {
    const response = await fetch(
      `/bank-imports/pharmacies/${pharmacyId}/batches?limit=50&offset=0`,
      {
        headers: {
          'X-API-Key': getApiKey()
        }
      }
    );
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Pharmacy not found');
      }
      throw new Error(`Failed to fetch imports: ${response.statusText}`);
    }
    
    const batches = await response.json();
    
    // Display in table
    batches.forEach(batch => {
      const period = batch.period_start && batch.period_end
        ? `${formatDate(batch.period_start)} - ${formatDate(batch.period_end)}`
        : 'N/A';
      
      const bankAccount = batch.bank_account_name 
        ? `${batch.bank_account_name} (${batch.bank_name})`
        : 'Unknown';
      
      addTableRow({
        period: period,
        bankAccount: bankAccount,
        transactionCount: batch.transaction_count,
        status: batch.status,
        uploadedAt: formatDateTime(batch.uploaded_at),
        actions: createActionButtons(batch.id)
      });
    });
    
    return batches;
  } catch (error) {
    console.error('Error fetching past imports:', error);
    showError('Failed to load past imports: ' + error.message);
    throw error;
  }
}
```

## Display Formatting

### Period Display
```javascript
function formatPeriod(batch) {
  if (batch.period_start && batch.period_end) {
    return `${formatDate(batch.period_start)} - ${formatDate(batch.period_end)}`;
  }
  return 'N/A';
}
```

### Bank Account Display
```javascript
function formatBankAccount(batch) {
  if (batch.bank_account_name) {
    return `${batch.bank_account_name} (${batch.bank_account_name})`;
  }
  return 'Unknown Account';
}
```

### Status Display
```javascript
function getStatusLabel(status) {
  const statusMap = {
    'IMPORTED': 'Imported',
    'CLASSIFIED_PARTIAL': 'Partially Classified',
    'CLASSIFIED_COMPLETE': 'Fully Classified',
    'POSTED_TO_LEDGER': 'Posted to Ledger'
  };
  return statusMap[status] || status;
}
```

## Table Columns

Based on the frontend UI, the following columns should be displayed:

1. **PERIOD** - `period_start` to `period_end` (or "N/A" if not available)
2. **BANK ACCOUNT** - `bank_account_name (bank_name)` (e.g., "Main SB2 148 (Standard Bank)")
3. **TRANSACTION COUNT** - `transaction_count` (number of transactions)
4. **STATUS** - `status` (formatted label)
5. **ACTIONS** - Action buttons (view details, delete, etc.)

## Error Handling

### Empty Results
If no batches are found, the API returns an empty array `[]`. Handle this gracefully:

```javascript
const batches = await fetchPastImports(pharmacyId);
if (batches.length === 0) {
  showMessage('No past imports found');
}
```

### 404 Error
If the pharmacy doesn't exist:
```javascript
if (response.status === 404) {
  showError('Pharmacy not found');
}
```

## Pagination

Use `limit` and `offset` for pagination:

```javascript
async function fetchPastImportsPaginated(pharmacyId, page = 1, pageSize = 50) {
  const offset = (page - 1) * pageSize;
  const response = await fetch(
    `/bank-imports/pharmacies/${pharmacyId}/batches?limit=${pageSize}&offset=${offset}`,
    {
      headers: {
        'X-API-Key': getApiKey()
      }
    }
  );
  return await response.json();
}
```

## Notes

- Batches are ordered by `uploaded_at DESC` (most recent first)
- Transaction count includes all transactions in the batch, even if some were skipped as duplicates
- Bank account information is included via JOIN, so it will be `null` if the bank account was deleted (shouldn't happen in normal operation)

