# Frontend Guide: Bank Reconciliation Summary

Complete guide for calling and displaying the bank reconciliation summary endpoint from the frontend.

## Quick Reference

**Endpoint:**
```
GET /pharmacies/{pharmacy_id}/reconciliation-summary?month=YYYY-MM
```

**Example:**
```javascript
GET /pharmacies/1/reconciliation-summary?month=2025-01
```

**Response Structure:**
```json
{
  "total_lines": 134,
  "reconciled_lines": 126,    // ⚠️ Use this field name exactly!
  "unmatched_lines": 8,
  "bank_total": 154000.50,
  "ledger_total": 153999.00,
  "difference": 1.50
}
```

**⚠️ IMPORTANT:** The field is called `reconciled_lines` (not `reconciled`, `matched`, or `reconciled_count`)

---

## API Endpoint

```
GET /pharmacies/{pharmacy_id}/reconciliation-summary?month=YYYY-MM
```

## Basic Example

```javascript
// Simple fetch example
async function fetchReconciliationSummary(pharmacyId, month) {
  try {
    const response = await fetch(
      `/pharmacies/${pharmacyId}/reconciliation-summary?month=${month}`,
      {
        headers: {
          'Content-Type': 'application/json',
          // Add auth header if needed
          // 'Authorization': `Bearer ${apiKey}`
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const summary = await response.json();
    return summary;
  } catch (error) {
    console.error('Error fetching reconciliation summary:', error);
    throw error;
  }
}

// Usage
const summary = await fetchReconciliationSummary(1, '2025-01');
console.log(`Reconciled: ${summary.reconciled_lines} of ${summary.total_lines}`);
```

---

## React Example with Loading States

```jsx
import React, { useState, useEffect } from 'react';

function ReconciliationSummary({ pharmacyId, month }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadSummary() {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(
          `/pharmacies/${pharmacyId}/reconciliation-summary?month=${month}`
        );
        
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.status}`);
        }
        
        const data = await response.json();
        setSummary(data);
      } catch (err) {
        setError(err.message);
        console.error('Error loading reconciliation summary:', err);
      } finally {
        setLoading(false);
      }
    }

    if (pharmacyId && month) {
      loadSummary();
    }
  }, [pharmacyId, month]);

  if (loading) {
    return <div>Loading reconciliation summary...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!summary) {
    return <div>No data available</div>;
  }

  const reconciliationPercentage = summary.total_lines > 0 
    ? ((summary.reconciled_lines / summary.total_lines) * 100).toFixed(1)
    : 0;

  const isBalanced = Math.abs(summary.difference) < 0.01;

  return (
    <div className="reconciliation-summary">
      <h2>Reconciliation Summary - {month}</h2>
      
      {/* Progress Overview */}
      <div className="reconciliation-stats">
        <div className="stat-card">
          <div className="stat-label">Total Lines</div>
          <div className="stat-value">{summary.total_lines}</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-label">Reconciled</div>
          <div className="stat-value success">{summary.reconciled_lines}</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-label">Unmatched</div>
          <div className="stat-value warning">{summary.unmatched_lines}</div>
        </div>
        
        <div className="stat-card">
          <div className="stat-label">Progress</div>
          <div className="stat-value">{reconciliationPercentage}%</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div 
          className="progress-bar" 
          style={{ width: `${reconciliationPercentage}%` }}
        />
      </div>

      {/* Financial Totals */}
      <div className="financial-totals">
        <div className="total-row">
          <span className="label">Bank Total:</span>
          <span className="value">
            {summary.bank_total.toLocaleString('en-ZA', { 
              style: 'currency', 
              currency: 'ZAR' 
            })}
          </span>
        </div>
        
        <div className="total-row">
          <span className="label">Ledger Total:</span>
          <span className="value">
            {summary.ledger_total.toLocaleString('en-ZA', { 
              style: 'currency', 
              currency: 'ZAR' 
            })}
          </span>
        </div>
        
        <div className={`total-row difference ${isBalanced ? 'balanced' : 'unbalanced'}`}>
          <span className="label">Difference:</span>
          <span className="value">
            {summary.difference.toLocaleString('en-ZA', { 
              style: 'currency', 
              currency: 'ZAR' 
            })}
          </span>
          {isBalanced && <span className="badge">✓ Balanced</span>}
          {!isBalanced && <span className="badge warning">⚠ Unbalanced</span>}
        </div>
      </div>

      {/* Status Messages */}
      {summary.unmatched_lines > 0 && (
        <div className="alert warning">
          ⚠ {summary.unmatched_lines} transaction(s) still need to be classified.
        </div>
      )}

      {summary.total_lines > 0 && summary.reconciled_lines === 0 && (
        <div className="alert info">
          ℹ No transactions have been reconciled yet. Start by applying rules or manually classifying transactions.
        </div>
      )}

      {isBalanced && summary.unmatched_lines === 0 && (
        <div className="alert success">
          ✓ All transactions are reconciled and totals match perfectly!
        </div>
      )}
    </div>
  );
}

export default ReconciliationSummary;
```

---

## Vue.js Example

```vue
<template>
  <div class="reconciliation-summary">
    <h2>Reconciliation Summary - {{ month }}</h2>
    
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">Error: {{ error }}</div>
    <div v-else-if="summary">
      <!-- Stats Cards -->
      <div class="reconciliation-stats">
        <div class="stat-card">
          <div class="stat-label">Total Lines</div>
          <div class="stat-value">{{ summary.total_lines }}</div>
        </div>
        
        <div class="stat-card">
          <div class="stat-label">Reconciled</div>
          <div class="stat-value success">{{ summary.reconciled_lines }}</div>
        </div>
        
        <div class="stat-card">
          <div class="stat-label">Unmatched</div>
          <div class="stat-value warning">{{ summary.unmatched_lines }}</div>
        </div>
        
        <div class="stat-card">
          <div class="stat-label">Progress</div>
          <div class="stat-value">{{ reconciliationPercentage }}%</div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-bar-container">
        <div 
          class="progress-bar" 
          :style="{ width: reconciliationPercentage + '%' }"
        />
      </div>

      <!-- Financial Totals -->
      <div class="financial-totals">
        <div class="total-row">
          <span class="label">Bank Total:</span>
          <span class="value">{{ formatCurrency(summary.bank_total) }}</span>
        </div>
        
        <div class="total-row">
          <span class="label">Ledger Total:</span>
          <span class="value">{{ formatCurrency(summary.ledger_total) }}</span>
        </div>
        
        <div class="total-row" :class="{ 'balanced': isBalanced, 'unbalanced': !isBalanced }">
          <span class="label">Difference:</span>
          <span class="value">{{ formatCurrency(summary.difference) }}</span>
          <span v-if="isBalanced" class="badge">✓ Balanced</span>
          <span v-else class="badge warning">⚠ Unbalanced</span>
        </div>
      </div>

      <!-- Status Messages -->
      <div v-if="summary.unmatched_lines > 0" class="alert warning">
        ⚠ {{ summary.unmatched_lines }} transaction(s) still need to be classified.
      </div>

      <div v-if="summary.total_lines > 0 && summary.reconciled_lines === 0" class="alert info">
        ℹ No transactions have been reconciled yet.
      </div>

      <div v-if="isBalanced && summary.unmatched_lines === 0" class="alert success">
        ✓ All transactions are reconciled and totals match perfectly!
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReconciliationSummary',
  props: {
    pharmacyId: {
      type: Number,
      required: true
    },
    month: {
      type: String,
      required: true,
      validator: (value) => /^\d{4}-\d{2}$/.test(value) // YYYY-MM format
    }
  },
  data() {
    return {
      summary: null,
      loading: true,
      error: null
    };
  },
  computed: {
    reconciliationPercentage() {
      if (!this.summary || this.summary.total_lines === 0) return 0;
      return ((this.summary.reconciled_lines / this.summary.total_lines) * 100).toFixed(1);
    },
    isBalanced() {
      if (!this.summary) return false;
      return Math.abs(this.summary.difference) < 0.01;
    }
  },
  async mounted() {
    await this.loadSummary();
  },
  watch: {
    pharmacyId() {
      this.loadSummary();
    },
    month() {
      this.loadSummary();
    }
  },
  methods: {
    async loadSummary() {
      try {
        this.loading = true;
        this.error = null;
        
        const response = await fetch(
          `/pharmacies/${this.pharmacyId}/reconciliation-summary?month=${this.month}`
        );
        
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.status}`);
        }
        
        this.summary = await response.json();
      } catch (err) {
        this.error = err.message;
        console.error('Error loading reconciliation summary:', err);
      } finally {
        this.loading = false;
      }
    },
    formatCurrency(amount) {
      return new Intl.NumberFormat('en-ZA', {
        style: 'currency',
        currency: 'ZAR'
      }).format(amount);
    }
  }
};
</script>
```

---

## Vanilla JavaScript with Error Handling

```javascript
// Complete example with error handling and auto-refresh
class ReconciliationSummaryManager {
  constructor(pharmacyId, baseUrl = '') {
    this.pharmacyId = pharmacyId;
    this.baseUrl = baseUrl;
    this.summary = null;
    this.month = null; // Will be set to current month by default
  }

  async fetchSummary(month = null) {
    // Default to current month if not provided
    if (!month) {
      const now = new Date();
      month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    }
    
    this.month = month;
    
    try {
      const response = await fetch(
        `${this.baseUrl}/pharmacies/${this.pharmacyId}/reconciliation-summary?month=${month}`,
        {
          headers: {
            'Content-Type': 'application/json',
            // Add auth header if needed
            // 'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Pharmacy not found');
        }
        if (response.status === 400) {
          const error = await response.json();
          throw new Error(error.detail || 'Invalid request');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      this.summary = await response.json();
      return this.summary;
    } catch (error) {
      console.error('Error fetching reconciliation summary:', error);
      throw error;
    }
  }

  formatCurrency(amount) {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: 'ZAR'
    }).format(amount);
  }

  getReconciliationPercentage() {
    if (!this.summary || this.summary.total_lines === 0) return 0;
    return ((this.summary.reconciled_lines / this.summary.total_lines) * 100).toFixed(1);
  }

  isBalanced() {
    if (!this.summary) return false;
    return Math.abs(this.summary.difference) < 0.01;
  }

  render() {
    const container = document.getElementById('reconciliation-summary');
    if (!container) {
      console.error('Container element not found');
      return;
    }

    if (!this.summary) {
      container.innerHTML = '<p>No data available</p>';
      return;
    }

    const percentage = this.getReconciliationPercentage();
    const balanced = this.isBalanced();

    const html = `
      <div class="reconciliation-summary">
        <h2>Reconciliation Summary - ${this.month}</h2>
        
        <!-- Stats Cards -->
        <div class="reconciliation-stats">
          <div class="stat-card">
            <div class="stat-label">Total Lines</div>
            <div class="stat-value">${this.summary.total_lines}</div>
          </div>
          
          <div class="stat-card">
            <div class="stat-label">Reconciled</div>
            <div class="stat-value success">${this.summary.reconciled_lines}</div>
          </div>
          
          <div class="stat-card">
            <div class="stat-label">Unmatched</div>
            <div class="stat-value warning">${this.summary.unmatched_lines}</div>
          </div>
          
          <div class="stat-card">
            <div class="stat-label">Progress</div>
            <div class="stat-value">${percentage}%</div>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="progress-bar-container">
          <div 
            class="progress-bar" 
            style="width: ${percentage}%"
          ></div>
        </div>

        <!-- Financial Totals -->
        <div class="financial-totals">
          <div class="total-row">
            <span class="label">Bank Total:</span>
            <span class="value">${this.formatCurrency(this.summary.bank_total)}</span>
          </div>
          
          <div class="total-row">
            <span class="label">Ledger Total:</span>
            <span class="value">${this.formatCurrency(this.summary.ledger_total)}</span>
          </div>
          
          <div class="total-row ${balanced ? 'balanced' : 'unbalanced'}">
            <span class="label">Difference:</span>
            <span class="value">${this.formatCurrency(this.summary.difference)}</span>
            ${balanced ? '<span class="badge">✓ Balanced</span>' : '<span class="badge warning">⚠ Unbalanced</span>'}
          </div>
        </div>

        <!-- Status Messages -->
        ${this.summary.unmatched_lines > 0 ? `
          <div class="alert warning">
            ⚠ ${this.summary.unmatched_lines} transaction(s) still need to be classified.
          </div>
        ` : ''}

        ${this.summary.total_lines > 0 && this.summary.reconciled_lines === 0 ? `
          <div class="alert info">
            ℹ No transactions have been reconciled yet. Start by applying rules or manually classifying transactions.
          </div>
        ` : ''}

        ${balanced && this.summary.unmatched_lines === 0 ? `
          <div class="alert success">
            ✓ All transactions are reconciled and totals match perfectly!
          </div>
        ` : ''}
      </div>
    `;

    container.innerHTML = html;
  }

  // Auto-refresh every 30 seconds
  startAutoRefresh(intervalMs = 30000) {
    this.autoRefreshInterval = setInterval(async () => {
      try {
        await this.fetchSummary(this.month);
        this.render();
      } catch (error) {
        console.error('Error auto-refreshing:', error);
      }
    }, intervalMs);
  }

  stopAutoRefresh() {
    if (this.autoRefreshInterval) {
      clearInterval(this.autoRefreshInterval);
    }
  }
}

// Usage
const manager = new ReconciliationSummaryManager(1, 'https://your-api-url.com');

// Load and display
manager.fetchSummary('2025-01')
  .then(() => manager.render())
  .catch(error => {
    console.error('Failed to load summary:', error);
    document.getElementById('reconciliation-summary').innerHTML = 
      `<p class="error">Error loading summary: ${error.message}</p>`;
  });

// Optional: Auto-refresh every 30 seconds
manager.startAutoRefresh(30000);
```

---

## Response Data Structure

The API returns this structure:

```typescript
interface ReconciliationSummary {
  total_lines: number;        // Total number of bank statement lines for the month
  reconciled_lines: number;    // Number of lines that have been reconciled (have ledger_entry_id)
  unmatched_lines: number;    // Number of lines that haven't been reconciled
  bank_total: number;         // Sum of amounts from bank transactions (signed)
  ledger_total: number;       // Sum of amounts from ledger entries linked to bank transactions
  difference: number;         // Difference between bank_total and ledger_total
}
```

### Example Response

```json
{
  "total_lines": 134,
  "reconciled_lines": 126,
  "unmatched_lines": 8,
  "bank_total": 154000.50,
  "ledger_total": 153999.00,
  "difference": 1.50
}
```

---

## Complete HTML Example with Styling

```html
<!DOCTYPE html>
<html>
<head>
  <title>Bank Reconciliation Summary</title>
  <style>
    .reconciliation-summary {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .reconciliation-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      margin: 20px 0;
    }

    .stat-card {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 20px;
      text-align: center;
      border: 1px solid #e0e0e0;
    }

    .stat-label {
      font-size: 14px;
      color: #666;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .stat-value {
      font-size: 32px;
      font-weight: bold;
      color: #333;
    }

    .stat-value.success {
      color: #4caf50;
    }

    .stat-value.warning {
      color: #ff9800;
    }

    .progress-bar-container {
      width: 100%;
      height: 24px;
      background-color: #e0e0e0;
      border-radius: 12px;
      overflow: hidden;
      margin: 20px 0;
    }

    .progress-bar {
      height: 100%;
      background: linear-gradient(90deg, #4caf50, #8bc34a);
      transition: width 0.3s ease;
    }

    .financial-totals {
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 20px;
      margin: 20px 0;
    }

    .total-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #f0f0f0;
    }

    .total-row:last-child {
      border-bottom: none;
      font-weight: bold;
      font-size: 18px;
    }

    .total-row.balanced {
      color: #4caf50;
    }

    .total-row.unbalanced {
      color: #f44336;
    }

    .label {
      font-size: 16px;
    }

    .value {
      font-size: 18px;
      font-weight: 600;
    }

    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      margin-left: 12px;
      background: #4caf50;
      color: white;
    }

    .badge.warning {
      background: #ff9800;
      color: white;
    }

    .alert {
      padding: 16px;
      border-radius: 8px;
      margin: 20px 0;
      border-left: 4px solid;
    }

    .alert.success {
      background: #e8f5e9;
      border-color: #4caf50;
      color: #2e7d32;
    }

    .alert.warning {
      background: #fff3e0;
      border-color: #ff9800;
      color: #e65100;
    }

    .alert.info {
      background: #e3f2fd;
      border-color: #2196f3;
      color: #1565c0;
    }

    .error {
      color: #f44336;
      padding: 20px;
      background: #ffebee;
      border-radius: 8px;
    }
  </style>
</head>
<body>
  <div id="reconciliation-summary">
    <p>Loading...</p>
  </div>

  <script>
    // Include the ReconciliationSummaryManager class from above
    // Then use it:
    const manager = new ReconciliationSummaryManager(1);
    
    // Get current month
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    
    manager.fetchSummary(currentMonth)
      .then(() => manager.render())
      .catch(error => {
        document.getElementById('reconciliation-summary').innerHTML = 
          `<p class="error">Error: ${error.message}</p>`;
      });
  </script>
</body>
</html>
```

---

## Common Issues and Solutions

### Issue 1: Showing 0 for reconciled_lines

**Possible Causes:**
1. **No transactions have been classified yet** - Check if transactions have `ledger_entry_id` set
2. **Wrong month parameter** - Make sure you're using `YYYY-MM` format (e.g., `2025-01`)
3. **No transactions in that month** - Check if `total_lines` is also 0
4. **API endpoint not being called correctly** - Check browser console for errors
5. **Wrong field name in frontend** - Make sure you're accessing `reconciled_lines` (not `reconciled` or `matched`)

**Debug Steps:**
```javascript
// Add comprehensive logging
async function debugReconciliation(pharmacyId, month) {
  console.log('=== Reconciliation Debug ===');
  console.log('Pharmacy ID:', pharmacyId);
  console.log('Month:', month);
  
  const url = `/pharmacies/${pharmacyId}/reconciliation-summary?month=${month}`;
  console.log('Full URL:', url);
  
  try {
    const response = await fetch(url);
    console.log('Response status:', response.status);
    console.log('Response OK:', response.ok);
    
    const summary = await response.json();
    console.log('Full response:', summary);
    console.log('Response keys:', Object.keys(summary));
    console.log('Total lines:', summary.total_lines);
    console.log('Reconciled lines:', summary.reconciled_lines);
    console.log('Unmatched lines:', summary.unmatched_lines);
    console.log('Bank total:', summary.bank_total);
    console.log('Ledger total:', summary.ledger_total);
    console.log('Difference:', summary.difference);
    
    // Check if the field exists
    if (summary.reconciled_lines === undefined) {
      console.error('❌ reconciled_lines field is missing!');
      console.log('Available fields:', Object.keys(summary));
    } else if (summary.reconciled_lines === 0) {
      console.warn('⚠️  reconciled_lines is 0');
      if (summary.total_lines > 0) {
        console.warn('⚠️  There are transactions but none are reconciled');
        console.warn('⚠️  This means no transactions have ledger_entry_id set');
      } else {
        console.warn('⚠️  No transactions found for this month');
      }
    } else {
      console.log('✅ Found', summary.reconciled_lines, 'reconciled transactions');
    }
    
    return summary;
  } catch (error) {
    console.error('❌ Error:', error);
    throw error;
  }
}

// Usage
debugReconciliation(1, '2025-01');
```

**Common Frontend Mistakes:**

```javascript
// ❌ WRONG - Using wrong field name
const reconciled = summary.reconciled;  // undefined!
const matched = summary.matched;  // undefined!

// ✅ CORRECT - Use the exact field name from API
const reconciled = summary.reconciled_lines;
const unmatched = summary.unmatched_lines;
const difference = summary.difference;

// ❌ WRONG - Not checking if response is OK
const response = await fetch(url);
const summary = await response.json();  // Might be an error object!

// ✅ CORRECT - Always check response.ok
const response = await fetch(url);
if (!response.ok) {
  const error = await response.json();
  console.error('API Error:', error);
  throw new Error(error.detail || 'Failed to fetch');
}
const summary = await response.json();
```

### Issue 2: Month format error

**Error:** `Invalid month format. Use YYYY-MM (e.g., 2025-01)`

**Solution:** Always format the month as `YYYY-MM`:
```javascript
// ✅ CORRECT
const month = '2025-01';

// ❌ WRONG
const month = '2025-1';      // Missing leading zero
const month = '01/2025';     // Wrong format
const month = 'January 2025'; // Wrong format

// Helper function to format current month
function getCurrentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}
```

### Issue 3: CORS or Authentication Errors

**Solution:** Make sure you're including the correct headers:
```javascript
const response = await fetch(url, {
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${yourApiKey}` // If required
  }
});
```

---

## Key Points

1. **Endpoint**: `GET /pharmacies/{pharmacy_id}/reconciliation-summary?month=YYYY-MM`
2. **Month Format**: Must be `YYYY-MM` (e.g., `2025-01` for January 2025)
3. **Response Fields**: 
   - `reconciled_lines`: Count of transactions with `ledger_entry_id` set
   - `unmatched_lines`: Count of transactions without `ledger_entry_id`
   - `difference`: Should be 0.00 when perfectly balanced
4. **Reconciliation Status**: A transaction is reconciled if it has a `ledger_entry_id` (from manual classification or rule classification)
5. **Error Handling**: Always check `response.ok` and handle errors gracefully
6. **Loading States**: Show loading indicators while fetching data
7. **Auto-refresh**: Consider refreshing the summary periodically if users are actively classifying transactions

---

## Integration with Unmatched Transactions

You can combine this with the unmatched transactions endpoint to show both summary and details:

```javascript
async function loadReconciliationView(pharmacyId, month) {
  // Load summary
  const summary = await fetchReconciliationSummary(pharmacyId, month);
  
  // Load unmatched transactions if there are any
  if (summary.unmatched_lines > 0) {
    const unmatched = await fetchUnmatchedTransactions(pharmacyId);
    // Display both summary and unmatched list
  }
  
  return { summary, unmatched };
}
```
