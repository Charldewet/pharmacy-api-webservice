# Frontend Example: Fetching Unmatched Transactions

Complete example of how to call and display unmatched bank transactions from the frontend.

## Basic Example

```javascript
// Simple fetch example
async function fetchUnmatchedTransactions(pharmacyId) {
  try {
    const response = await fetch(
      `/bank-rules/pharmacies/${pharmacyId}/bank-transactions/unmatched`
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const transactions = await response.json();
    return transactions;
  } catch (error) {
    console.error('Error fetching unmatched transactions:', error);
    throw error;
  }
}

// Usage
const transactions = await fetchUnmatchedTransactions(1);
console.log(`Found ${transactions.length} unmatched transactions`);
```

---

## React Example with Loading States

```jsx
import React, { useState, useEffect } from 'react';

function UnmatchedTransactions({ pharmacyId }) {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadTransactions() {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(
          `/bank-rules/pharmacies/${pharmacyId}/bank-transactions/unmatched`
        );
        
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.status}`);
        }
        
        const data = await response.json();
        setTransactions(data);
      } catch (err) {
        setError(err.message);
        console.error('Error loading unmatched transactions:', err);
      } finally {
        setLoading(false);
      }
    }

    if (pharmacyId) {
      loadTransactions();
    }
  }, [pharmacyId]);

  if (loading) {
    return <div>Loading unmatched transactions...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (transactions.length === 0) {
    return <div>No unmatched transactions found.</div>;
  }

  return (
    <div>
      <h2>Unmatched Transactions ({transactions.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Reference</th>
            <th>Amount</th>
            <th>Status</th>
            <th>AI Suggestion</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map(txn => (
            <tr key={txn.id}>
              <td>{txn.date}</td>
              <td>{txn.description}</td>
              <td>{txn.reference || '-'}</td>
              <td style={{ color: txn.amount < 0 ? 'red' : 'green' }}>
                {txn.amount.toLocaleString('en-ZA', { 
                  style: 'currency', 
                  currency: 'ZAR' 
                })}
              </td>
              <td>
                <span className={`status-${txn.classification_status}`}>
                  {txn.classification_status}
                </span>
              </td>
              <td>
                {txn.ai_suggestion ? (
                  <div>
                    <div>Account: {txn.ai_suggestion.suggested_account_id}</div>
                    <div>Confidence: {(txn.ai_suggestion.confidence * 100).toFixed(0)}%</div>
                    <div>{txn.ai_suggestion.suggested_description}</div>
                  </div>
                ) : (
                  <span>No suggestion</span>
                )}
              </td>
              <td>
                {txn.ai_suggestion && (
                  <>
                    <button 
                      onClick={() => acceptSuggestion(txn.ai_suggestion.id)}
                    >
                      Accept
                    </button>
                    <button 
                      onClick={() => rejectSuggestion(txn.ai_suggestion.id)}
                    >
                      Reject
                    </button>
                  </>
                )}
                <button onClick={() => applyRules(txn.id)}>
                  Apply Rules
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Helper functions
async function acceptSuggestion(suggestionId) {
  try {
    const response = await fetch(
      `/bank-rules/ai-suggestions/${suggestionId}/accept`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      }
    );
    
    if (!response.ok) {
      throw new Error('Failed to accept suggestion');
    }
    
    const result = await response.json();
    console.log('Suggestion accepted:', result);
    // Refresh the list
    window.location.reload();
  } catch (error) {
    console.error('Error accepting suggestion:', error);
    alert('Failed to accept suggestion');
  }
}

async function rejectSuggestion(suggestionId) {
  try {
    const response = await fetch(
      `/bank-rules/ai-suggestions/${suggestionId}/reject`,
      {
        method: 'POST'
      }
    );
    
    if (!response.ok) {
      throw new Error('Failed to reject suggestion');
    }
    
    console.log('Suggestion rejected');
    // Refresh the list
    window.location.reload();
  } catch (error) {
    console.error('Error rejecting suggestion:', error);
    alert('Failed to reject suggestion');
  }
}

async function applyRules(transactionId) {
  try {
    const response = await fetch(
      `/bank-rules/bank-transactions/${transactionId}/apply-rules`,
      {
        method: 'POST'
      }
    );
    
    if (!response.ok) {
      throw new Error('Failed to apply rules');
    }
    
    const result = await response.json();
    console.log('Rules applied:', result);
    // Refresh the list
    window.location.reload();
  } catch (error) {
    console.error('Error applying rules:', error);
    alert('Failed to apply rules');
  }
}

export default UnmatchedTransactions;
```

---

## Vue.js Example

```vue
<template>
  <div>
    <h2>Unmatched Transactions ({{ transactions.length }})</h2>
    
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">Error: {{ error }}</div>
    <div v-else-if="transactions.length === 0">
      No unmatched transactions found.
    </div>
    <div v-else>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Amount</th>
            <th>Status</th>
            <th>AI Suggestion</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="txn in transactions" :key="txn.id">
            <td>{{ txn.date }}</td>
            <td>{{ txn.description }}</td>
            <td :class="{ 'text-red': txn.amount < 0, 'text-green': txn.amount > 0 }">
              R {{ Math.abs(txn.amount).toLocaleString() }}
            </td>
            <td>
              <span :class="`status-${txn.classification_status}`">
                {{ txn.classification_status }}
              </span>
            </td>
            <td>
              <div v-if="txn.ai_suggestion">
                <div>Account: {{ txn.ai_suggestion.suggested_account_id }}</div>
                <div>Confidence: {{ (txn.ai_suggestion.confidence * 100).toFixed(0) }}%</div>
              </div>
              <span v-else>No suggestion</span>
            </td>
            <td>
              <button 
                v-if="txn.ai_suggestion"
                @click="acceptSuggestion(txn.ai_suggestion.id)"
              >
                Accept
              </button>
              <button 
                v-if="txn.ai_suggestion"
                @click="rejectSuggestion(txn.ai_suggestion.id)"
              >
                Reject
              </button>
              <button @click="applyRules(txn.id)">
                Apply Rules
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UnmatchedTransactions',
  props: {
    pharmacyId: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      transactions: [],
      loading: true,
      error: null
    };
  },
  async mounted() {
    await this.loadTransactions();
  },
  methods: {
    async loadTransactions() {
      try {
        this.loading = true;
        this.error = null;
        
        const response = await fetch(
          `/bank-rules/pharmacies/${this.pharmacyId}/bank-transactions/unmatched`
        );
        
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.status}`);
        }
        
        this.transactions = await response.json();
      } catch (err) {
        this.error = err.message;
        console.error('Error loading transactions:', err);
      } finally {
        this.loading = false;
      }
    },
    async acceptSuggestion(suggestionId) {
      try {
        const response = await fetch(
          `/bank-rules/ai-suggestions/${suggestionId}/accept`,
          { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) }
        );
        if (response.ok) {
          await this.loadTransactions();
        }
      } catch (error) {
        console.error('Error accepting suggestion:', error);
      }
    },
    async rejectSuggestion(suggestionId) {
      try {
        const response = await fetch(
          `/bank-rules/ai-suggestions/${suggestionId}/reject`,
          { method: 'POST' }
        );
        if (response.ok) {
          await this.loadTransactions();
        }
      } catch (error) {
        console.error('Error rejecting suggestion:', error);
      }
    },
    async applyRules(transactionId) {
      try {
        const response = await fetch(
          `/bank-rules/bank-transactions/${transactionId}/apply-rules`,
          { method: 'POST' }
        );
        if (response.ok) {
          await this.loadTransactions();
        }
      } catch (error) {
        console.error('Error applying rules:', error);
      }
    }
  }
};
</script>
```

---

## Vanilla JavaScript with Error Handling

```javascript
// Complete example with error handling and account name lookup
class UnmatchedTransactionsManager {
  constructor(pharmacyId, baseUrl = '') {
    this.pharmacyId = pharmacyId;
    this.baseUrl = baseUrl;
    this.transactions = [];
    this.accounts = new Map(); // Cache for account names
  }

  async fetchUnmatchedTransactions() {
    try {
      const response = await fetch(
        `${this.baseUrl}/bank-rules/pharmacies/${this.pharmacyId}/bank-transactions/unmatched`,
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
        if (response.status === 500) {
          throw new Error('Server error. Please try again later.');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const transactions = await response.json();
      this.transactions = transactions;
      
      // Load account names for AI suggestions
      await this.loadAccountNames(transactions);
      
      return transactions;
    } catch (error) {
      console.error('Error fetching unmatched transactions:', error);
      throw error;
    }
  }

  async loadAccountNames(transactions) {
    // Get unique account IDs from AI suggestions
    const accountIds = new Set();
    transactions.forEach(txn => {
      if (txn.ai_suggestion?.suggested_account_id) {
        accountIds.add(txn.ai_suggestion.suggested_account_id);
      }
    });

    // Fetch account details (you'll need an accounts endpoint)
    for (const accountId of accountIds) {
      if (!this.accounts.has(accountId)) {
        try {
          // Assuming you have an endpoint to get account by ID
          const response = await fetch(`${this.baseUrl}/accounts/${accountId}`);
          if (response.ok) {
            const account = await response.json();
            this.accounts.set(accountId, account);
          }
        } catch (error) {
          console.warn(`Could not load account ${accountId}:`, error);
        }
      }
    }
  }

  getAccountName(accountId) {
    const account = this.accounts.get(accountId);
    return account ? `${account.code} - ${account.name}` : `Account ${accountId}`;
  }

  formatAmount(amount) {
    return new Intl.NumberFormat('en-ZA', {
      style: 'currency',
      currency: 'ZAR'
    }).format(amount);
  }

  formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-ZA');
  }

  render() {
    const container = document.getElementById('unmatched-transactions');
    if (!container) {
      console.error('Container element not found');
      return;
    }

    if (this.transactions.length === 0) {
      container.innerHTML = '<p>No unmatched transactions found.</p>';
      return;
    }

    const html = `
      <h2>Unmatched Transactions (${this.transactions.length})</h2>
      <table class="transactions-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th>Reference</th>
            <th>Amount</th>
            <th>Status</th>
            <th>AI Suggestion</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${this.transactions.map(txn => `
            <tr data-transaction-id="${txn.id}">
              <td>${this.formatDate(txn.date)}</td>
              <td>${this.escapeHtml(txn.description)}</td>
              <td>${txn.reference || '-'}</td>
              <td class="${txn.amount < 0 ? 'negative' : 'positive'}">
                ${this.formatAmount(txn.amount)}
              </td>
              <td>
                <span class="status-badge status-${txn.classification_status}">
                  ${txn.classification_status}
                </span>
              </td>
              <td>
                ${txn.ai_suggestion ? `
                  <div class="ai-suggestion">
                    <div><strong>${this.getAccountName(txn.ai_suggestion.suggested_account_id)}</strong></div>
                    <div>Confidence: ${(txn.ai_suggestion.confidence * 100).toFixed(0)}%</div>
                    <div class="suggestion-desc">${this.escapeHtml(txn.ai_suggestion.suggested_description || '')}</div>
                  </div>
                ` : '<span class="no-suggestion">No suggestion</span>'}
              </td>
              <td>
                <div class="action-buttons">
                  ${txn.ai_suggestion ? `
                    <button 
                      class="btn-accept" 
                      onclick="manager.acceptSuggestion(${txn.ai_suggestion.id})"
                    >
                      Accept
                    </button>
                    <button 
                      class="btn-reject" 
                      onclick="manager.rejectSuggestion(${txn.ai_suggestion.id})"
                    >
                      Reject
                    </button>
                  ` : ''}
                  <button 
                    class="btn-apply-rules" 
                    onclick="manager.applyRules(${txn.id})"
                  >
                    Apply Rules
                  </button>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;

    container.innerHTML = html;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async acceptSuggestion(suggestionId) {
    try {
      const response = await fetch(
        `${this.baseUrl}/bank-rules/ai-suggestions/${suggestionId}/accept`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({})
        }
      );

      if (!response.ok) {
        throw new Error('Failed to accept suggestion');
      }

      const result = await response.json();
      console.log('Suggestion accepted:', result);
      alert('Suggestion accepted! Ledger entry created.');
      
      // Reload transactions
      await this.fetchUnmatchedTransactions();
      this.render();
    } catch (error) {
      console.error('Error accepting suggestion:', error);
      alert('Failed to accept suggestion. Please try again.');
    }
  }

  async rejectSuggestion(suggestionId) {
    try {
      const response = await fetch(
        `${this.baseUrl}/bank-rules/ai-suggestions/${suggestionId}/reject`,
        {
          method: 'POST'
        }
      );

      if (!response.ok) {
        throw new Error('Failed to reject suggestion');
      }

      console.log('Suggestion rejected');
      
      // Reload transactions
      await this.fetchUnmatchedTransactions();
      this.render();
    } catch (error) {
      console.error('Error rejecting suggestion:', error);
      alert('Failed to reject suggestion. Please try again.');
    }
  }

  async applyRules(transactionId) {
    try {
      const response = await fetch(
        `${this.baseUrl}/bank-rules/bank-transactions/${transactionId}/apply-rules`,
        {
          method: 'POST'
        }
      );

      if (!response.ok) {
        throw new Error('Failed to apply rules');
      }

      const result = await response.json();
      console.log('Rules applied:', result);
      
      if (result.rule_id) {
        alert(`Rule ${result.rule_id} matched and applied!`);
      } else {
        alert('No matching rule found.');
      }
      
      // Reload transactions
      await this.fetchUnmatchedTransactions();
      this.render();
    } catch (error) {
      console.error('Error applying rules:', error);
      alert('Failed to apply rules. Please try again.');
    }
  }
}

// Usage
const manager = new UnmatchedTransactionsManager(1, 'https://your-api-url.com');

// Load and display
manager.fetchUnmatchedTransactions()
  .then(() => manager.render())
  .catch(error => {
    console.error('Failed to load transactions:', error);
    document.getElementById('unmatched-transactions').innerHTML = 
      `<p class="error">Error loading transactions: ${error.message}</p>`;
  });
```

---

## Response Data Structure

Each transaction in the response has this structure:

```typescript
interface UnmatchedTransaction {
  id: number;
  bank_import_batch_id: number;
  bank_account_id: number;
  pharmacy_id: number;
  date: string; // "YYYY-MM-DD"
  description: string;
  reference: string | null;
  amount: number; // Negative for expenses, positive for income
  balance: number | null;
  classification_status: 'unclassified' | 'ai_classified';
  classified_at: string | null;
  classified_by_rule_id: number | null;
  ai_suggestion_id: number | null;
  ledger_entry_id: number | null;
  ai_suggestion?: {
    id: number;
    pharmacy_id: number;
    bank_transaction_id: number;
    suggested_account_id: number;
    suggested_description: string | null;
    suggested_type: 'receive' | 'spend' | 'transfer' | null;
    model_name: string | null;
    raw_response: object | null;
    confidence: number | null; // 0-1
    status: 'pending' | 'accepted' | 'rejected';
    created_at: string; // ISO 8601
    updated_at: string; // ISO 8601
  };
}
```

---

## Complete HTML Example

```html
<!DOCTYPE html>
<html>
<head>
  <title>Unmatched Transactions</title>
  <style>
    .transactions-table {
      width: 100%;
      border-collapse: collapse;
    }
    .transactions-table th,
    .transactions-table td {
      padding: 8px;
      border: 1px solid #ddd;
      text-align: left;
    }
    .transactions-table th {
      background-color: #f2f2f2;
    }
    .negative { color: red; }
    .positive { color: green; }
    .status-badge {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
    }
    .status-unclassified { background-color: #ffeb3b; }
    .status-ai_classified { background-color: #2196f3; color: white; }
    .ai-suggestion {
      font-size: 12px;
    }
    .action-buttons button {
      margin: 2px;
      padding: 4px 8px;
      cursor: pointer;
    }
    .btn-accept { background-color: #4caf50; color: white; }
    .btn-reject { background-color: #f44336; color: white; }
    .btn-apply-rules { background-color: #2196f3; color: white; }
  </style>
</head>
<body>
  <div id="unmatched-transactions">
    <p>Loading...</p>
  </div>

  <script>
    // Include the UnmatchedTransactionsManager class from above
    // Then use it:
    const manager = new UnmatchedTransactionsManager(1);
    manager.fetchUnmatchedTransactions()
      .then(() => manager.render())
      .catch(error => {
        document.getElementById('unmatched-transactions').innerHTML = 
          `<p style="color: red;">Error: ${error.message}</p>`;
      });
  </script>
</body>
</html>
```

---

## Key Points

1. **Endpoint**: `GET /bank-rules/pharmacies/{pharmacy_id}/bank-transactions/unmatched`
2. **Returns**: Array of transactions with `classification_status` of `'unclassified'` or `'ai_classified'`
3. **AI Suggestions**: Included in the `ai_suggestion` property if available
4. **Actions**: You can accept/reject AI suggestions or apply rules to individual transactions
5. **Error Handling**: Always check `response.ok` and handle errors gracefully
6. **Loading States**: Show loading indicators while fetching data
7. **Refresh**: Reload the list after accepting/rejecting suggestions or applying rules

