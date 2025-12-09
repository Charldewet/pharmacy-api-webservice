# Bank Statement Preview API - Frontend Integration Guide

## Overview

This guide explains how to correctly use the bank statement preview API to display accurate transaction totals (Total IN and Total OUT).

## API Endpoint

**POST** `/api/bank-imports/preview`

### Request Format

```javascript
const formData = new FormData();
formData.append('pharmacy_id', '1');
formData.append('bank_account_id', '1');
formData.append('file', fileInput.files[0]); // CSV file

const response = await fetch('/api/bank-imports/preview', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key-here'
  },
  body: formData
});

const data = await response.json();
```

## Response Structure

```json
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
  "sample_transactions": [
    {
      "row_number": 1,
      "date": "2025-11-29",
      "description": "SERVICE FEE ACC 301666148",
      "reference": null,
      "amount": -341.40,
      "balance": null
    },
    // ... more transactions (first 20)
  ],
  "errors": []
}
```

## Important: Use Summary Values Directly

### ✅ CORRECT - Use Summary Values

```javascript
const previewData = await response.json();

// Use the summary values directly - these are calculated by the backend
const totalIn = previewData.summary.total_in;      // R 15,394,604.51
const totalOut = previewData.summary.total_out;    // R 15,231,904.44
const transactionCount = previewData.summary.transaction_count; // 1757

// Display these values
displaySummary({
  transactionCount: previewData.summary.transaction_count,
  totalIn: previewData.summary.total_in,
  totalOut: previewData.summary.total_out,
  periodStart: previewData.summary.min_date,
  periodEnd: previewData.summary.max_date
});
```

### ❌ INCORRECT - Don't Recalculate from Sample Transactions

```javascript
// DON'T DO THIS - sample_transactions only contains first 20 rows!
const totalIn = previewData.sample_transactions
  .filter(t => t.amount > 0)
  .reduce((sum, t) => sum + t.amount, 0);

const totalOut = Math.abs(previewData.sample_transactions
  .filter(t => t.amount < 0)
  .reduce((sum, t) => sum + t.amount, 0));

// This will give WRONG values because:
// 1. sample_transactions only has 20 rows, not all 1757
// 2. The calculation logic might differ from backend
```

## Summary Field Definitions

### `summary.total_in`
- **Type**: `number` (float)
- **Description**: Sum of all **positive** transaction amounts
- **Example**: `15394604.51` (R 15,394,604.51)
- **Calculation**: Backend sums all transactions where `amount > 0`

### `summary.total_out`
- **Type**: `number` (float)
- **Description**: Absolute value of sum of all **negative** transaction amounts (always positive)
- **Example**: `15231904.44` (R 15,231,904.44)
- **Calculation**: Backend sums all transactions where `amount < 0`, then takes absolute value
- **Note**: This is a **positive number** representing money going out

### `summary.transaction_count`
- **Type**: `number` (integer)
- **Description**: Total number of valid transactions parsed from the CSV
- **Example**: `1757`

### `summary.min_date` / `summary.max_date`
- **Type**: `string` (ISO date format: `YYYY-MM-DD`)
- **Description**: Earliest and latest transaction dates
- **Example**: `"2025-03-01"` / `"2025-11-29"`

## Sample Transactions

The `sample_transactions` array contains only the **first 20 transactions** for preview purposes. 

**Important**: 
- Do NOT use `sample_transactions` to calculate totals
- Use `sample_transactions` only for displaying a preview table
- The actual amounts in `sample_transactions` may differ from the summary because:
  - Sample shows only 20 rows
  - Sample shows raw transaction amounts (positive/negative)
  - Summary shows aggregated totals

## Display Formatting Example

```javascript
function formatCurrency(amount) {
  return new Intl.NumberFormat('en-ZA', {
    style: 'currency',
    currency: 'ZAR',
    minimumFractionDigits: 2
  }).format(amount);
}

function displayPreviewSummary(previewData) {
  const summary = previewData.summary;
  
  // Display summary card
  document.getElementById('transaction-count').textContent = summary.transaction_count;
  document.getElementById('total-in').textContent = formatCurrency(summary.total_in);
  document.getElementById('total-out').textContent = formatCurrency(summary.total_out);
  document.getElementById('period').textContent = 
    `${summary.min_date} → ${summary.max_date}`;
  
  // Display sample transactions table
  const tableBody = document.getElementById('preview-table-body');
  previewData.sample_transactions.forEach(transaction => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${transaction.date}</td>
      <td>${transaction.description}</td>
      <td class="${transaction.amount >= 0 ? 'text-green' : 'text-red'}">
        ${formatCurrency(transaction.amount)}
      </td>
    `;
    tableBody.appendChild(row);
  });
}
```

## Common Mistakes to Avoid

### ❌ Mistake 1: Recalculating from Sample Transactions
```javascript
// WRONG - sample_transactions only has 20 rows
const totalIn = sample_transactions
  .filter(t => t.amount > 0)
  .reduce((sum, t) => sum + t.amount, 0);
```

### ❌ Mistake 2: Using Negative total_out
```javascript
// WRONG - total_out is already a positive number
const totalOut = -previewData.summary.total_out; // Don't negate it!
```

### ❌ Mistake 3: Summing All Sample Amounts
```javascript
// WRONG - this doesn't match backend calculation
const net = sample_transactions.reduce((sum, t) => sum + t.amount, 0);
```

### ✅ Correct Approach
```javascript
// RIGHT - use summary values directly
const totalIn = previewData.summary.total_in;   // Already calculated correctly
const totalOut = previewData.summary.total_out;  // Already positive, don't negate
const net = totalIn - totalOut;  // Calculate net from summary values
```

## Complete Example

```javascript
async function previewBankImport(pharmacyId, bankAccountId, file) {
  try {
    const formData = new FormData();
    formData.append('pharmacy_id', pharmacyId);
    formData.append('bank_account_id', bankAccountId);
    formData.append('file', file);
    
    const response = await fetch('/api/bank-imports/preview', {
      method: 'POST',
      headers: {
        'X-API-Key': getApiKey()
      },
      body: formData
    });
    
    if (!response.ok) {
      throw new Error(`Preview failed: ${response.statusText}`);
    }
    
    const data = await response.json();
    
    // ✅ Use summary values directly
    return {
      summary: {
        transactionCount: data.summary.transaction_count,
        totalIn: data.summary.total_in,        // R 15,394,604.51
        totalOut: data.summary.total_out,      // R 15,231,904.44 (positive)
        net: data.summary.total_in - data.summary.total_out, // R 162,700.07
        periodStart: data.summary.min_date,
        periodEnd: data.summary.max_date
      },
      sampleTransactions: data.sample_transactions, // For preview table only
      errors: data.errors
    };
    
  } catch (error) {
    console.error('Preview error:', error);
    throw error;
  }
}
```

## Summary

1. **Always use `summary.total_in` and `summary.total_out`** - these are pre-calculated by the backend
2. **Don't recalculate from `sample_transactions`** - it only contains 20 rows
3. **`total_out` is already positive** - don't negate it
4. **Use `sample_transactions` only for display** - not for calculations

## Questions?

If the totals don't match what you expect:
1. Check that you're using `summary.total_in` and `summary.total_out` directly
2. Verify you're not recalculating from `sample_transactions`
3. Check the backend logs for any parsing errors
4. Ensure the CSV file format matches expected structure

