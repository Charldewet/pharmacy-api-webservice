# Bank Rules API - Frontend Integration Guide

Complete guide for frontend integration with the Bank Rules API endpoints.

## Base URL

All endpoints are prefixed with `/bank-rules`

Example: `GET /bank-rules/pharmacies/1/bank-rules`

---

## 📋 Displaying Bank Rules

### 1. List All Rules for a Pharmacy

**Endpoint:** `GET /bank-rules/pharmacies/{pharmacy_id}/bank-rules`

**Description:** Get all bank rules for a specific pharmacy, ordered by priority.

**Path Parameters:**
- `pharmacy_id` (integer, required) - The pharmacy ID

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "pharmacy_id": 1,
    "name": "Card settlements (EFTPOS CR) → Takings Clearing",
    "type": "receive",
    "priority": 1,
    "allocate": [
      {
        "account_id": 7,
        "percent": 100,
        "vat_code": "NO_VAT"
      }
    ],
    "contact_name": "Card Settlement",
    "is_active": true,
    "created_by_user_id": null,
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-01-15T10:00:00Z",
    "conditions": [
      {
        "id": 1,
        "bank_rule_id": 1,
        "group_type": "ALL",
        "field": "description",
        "operator": "contains",
        "value": "EFTPOS SETTLEMENT CR",
        "created_at": "2025-01-15T10:00:00Z",
        "updated_at": "2025-01-15T10:00:00Z"
      }
    ]
  },
  {
    "id": 2,
    "pharmacy_id": 1,
    "name": "Card settlement reversals (EFTPOS DR) → Takings Clearing",
    "type": "receive",
    "priority": 2,
    "allocate": [
      {
        "account_id": 7,
        "percent": 100,
        "vat_code": "NO_VAT"
      }
    ],
    "contact_name": "Card Settlement Reversal",
    "is_active": true,
    "conditions": [...]
  }
]
```

**Example Request:**
```javascript
// Fetch all rules for pharmacy ID 1
const response = await fetch('/bank-rules/pharmacies/1/bank-rules');
const rules = await response.json();

// Rules are sorted by priority (lowest number = highest priority)
rules.forEach(rule => {
  console.log(`${rule.priority}. ${rule.name} (${rule.type})`);
  console.log(`   Active: ${rule.is_active}`);
  console.log(`   Conditions: ${rule.conditions.length}`);
  console.log(`   Allocations: ${rule.allocate.length}`);
});
```

---

### 2. Get a Single Rule

**Endpoint:** `GET /bank-rules/bank-rules/{rule_id}`

**Description:** Get detailed information about a specific bank rule.

**Path Parameters:**
- `rule_id` (integer, required) - The bank rule ID

**Response:** `200 OK`

```json
{
  "id": 1,
  "pharmacy_id": 1,
  "name": "Card settlements (EFTPOS CR) → Takings Clearing",
  "type": "receive",
  "priority": 1,
  "allocate": [
    {
      "account_id": 7,
      "percent": 100,
      "vat_code": "NO_VAT"
    }
  ],
  "contact_name": "Card Settlement",
  "is_active": true,
  "created_by_user_id": null,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z",
  "conditions": [
    {
      "id": 1,
      "bank_rule_id": 1,
      "group_type": "ALL",
      "field": "description",
      "operator": "contains",
      "value": "EFTPOS SETTLEMENT CR",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T10:00:00Z"
    }
  ]
}
```

**Error Responses:**
- `404 Not Found` - Rule not found

**Example Request:**
```javascript
const response = await fetch('/bank-rules/bank-rules/1');
const rule = await response.json();
```

---

## ✏️ Managing Bank Rules

### 3. Create a New Rule

**Endpoint:** `POST /bank-rules/pharmacies/{pharmacy_id}/bank-rules`

**Description:** Create a new bank rule for a pharmacy.

**Path Parameters:**
- `pharmacy_id` (integer, required) - The pharmacy ID

**Request Body:**
```json
{
  "name": "Supplier Payments → Cost of Sales",
  "type": "spend",
  "priority": 20,
  "allocate": [
    {
      "account_id": 29,
      "percent": 100,
      "vat_code": "NO_VAT"
    }
  ],
  "contact_name": "Supplier",
  "conditions": [
    {
      "group_type": "ALL",
      "field": "description",
      "operator": "contains",
      "value": "SUPPLIER PAYMENT"
    }
  ]
}
```

**Field Descriptions:**
- `name` (string, required) - Rule name/description
- `type` (string, required) - One of: `"receive"`, `"spend"`, `"transfer"`
- `priority` (integer, optional) - Lower number = higher priority (default: 100)
- `allocate` (array, required) - Array of allocations:
  - `account_id` (integer, required) - Chart of accounts ID
  - `percent` (float, required) - Percentage (0-100)
  - `vat_code` (string, optional) - VAT code (default: "NO_VAT")
- `contact_name` (string, optional) - Contact/payee name
- `conditions` (array, required) - Array of conditions:
  - `group_type` (string, required) - `"ALL"` (AND) or `"ANY"` (OR)
  - `field` (string, required) - One of: `"description"`, `"reference"`, `"amount"`, `"amount_in"`, `"amount_out"`, `"date"`
  - `operator` (string, required) - One of: `"contains"`, `"not_contains"`, `"equals"`, `"starts_with"`, `"ends_with"`, `"greater_than"`, `"less_than"`, `"regex"`
  - `value` (string, required) - Value to match against

**Response:** `200 OK` - Returns the created rule (same format as GET single rule)

**Error Responses:**
- `404 Not Found` - Pharmacy not found
- `422 Unprocessable Entity` - Validation error

**Example Request:**
```javascript
const newRule = {
  name: "Supplier Payments → Cost of Sales",
  type: "spend",
  priority: 20,
  allocate: [
    {
      account_id: 29,
      percent: 100,
      vat_code: "NO_VAT"
    }
  ],
  contact_name: "Supplier",
  conditions: [
    {
      group_type: "ALL",
      field: "description",
      operator: "contains",
      value: "SUPPLIER PAYMENT"
    }
  ]
};

const response = await fetch('/bank-rules/pharmacies/1/bank-rules', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(newRule)
});

const createdRule = await response.json();
```

---

### 4. Update a Rule

**Endpoint:** `PUT /bank-rules/bank-rules/{rule_id}`

**Description:** Update an existing bank rule. All fields are optional - only provided fields will be updated.

**Path Parameters:**
- `rule_id` (integer, required) - The bank rule ID

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Rule Name",
  "type": "receive",
  "priority": 5,
  "allocate": [
    {
      "account_id": 7,
      "percent": 100,
      "vat_code": "NO_VAT"
    }
  ],
  "contact_name": "Updated Contact",
  "is_active": true,
  "conditions": [
    {
      "group_type": "ALL",
      "field": "description",
      "operator": "contains",
      "value": "UPDATED VALUE"
    }
  ]
}
```

**Response:** `200 OK` - Returns the updated rule

**Error Responses:**
- `404 Not Found` - Rule not found
- `422 Unprocessable Entity` - Validation error

**Example Request:**
```javascript
const updates = {
  name: "Updated Rule Name",
  is_active: false
};

const response = await fetch('/bank-rules/bank-rules/1', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(updates)
});

const updatedRule = await response.json();
```

---

### 5. Delete a Rule (Soft Delete)

**Endpoint:** `DELETE /bank-rules/bank-rules/{rule_id}`

**Description:** Soft delete a bank rule (sets `is_active = false`). The rule is not permanently deleted.

**Path Parameters:**
- `rule_id` (integer, required) - The bank rule ID

**Response:** `200 OK`

```json
{
  "message": "Bank rule deleted"
}
```

**Error Responses:**
- `404 Not Found` - Rule not found

**Example Request:**
```javascript
const response = await fetch('/bank-rules/bank-rules/1', {
  method: 'DELETE'
});

const result = await response.json();
// { message: "Bank rule deleted" }
```

---

## 🎯 Applying Rules to Transactions

### 6. Apply Rules to a Batch

**Endpoint:** `POST /bank-rules/bank-import-batches/{batch_id}/apply-rules`

**Description:** Apply all active rules to all transactions in a bank import batch.

**Path Parameters:**
- `batch_id` (integer, required) - The bank import batch ID

**Response:** `200 OK`

```json
{
  "statement_id": 1,
  "total_lines": 250,
  "classified_by_rule": 180,
  "already_classified": 30,
  "unclassified": 40
}
```

**Example Request:**
```javascript
const response = await fetch('/bank-rules/bank-import-batches/1/apply-rules', {
  method: 'POST'
});

const result = await response.json();
console.log(`Classified ${result.classified_by_rule} transactions`);
console.log(`${result.unclassified} remain unclassified`);
```

---

### 7. Apply Rules to a Single Transaction

**Endpoint:** `POST /bank-rules/bank-transactions/{transaction_id}/apply-rules`

**Description:** Apply rules to a single bank transaction.

**Path Parameters:**
- `transaction_id` (integer, required) - The bank transaction ID

**Response:** `200 OK`

```json
{
  "message": "Rule applied",
  "rule_id": 1
}
```

Or if no rule matched:

```json
{
  "message": "No matching rule found"
}
```

**Example Request:**
```javascript
const response = await fetch('/bank-rules/bank-transactions/123/apply-rules', {
  method: 'POST'
});

const result = await response.json();
if (result.rule_id) {
  console.log(`Rule ${result.rule_id} matched`);
} else {
  console.log('No matching rule found');
}
```

---

## 🤖 AI Suggestions

### 8. Generate AI Suggestions for a Batch

**Endpoint:** `POST /bank-rules/bank-import-batches/{batch_id}/generate-ai-suggestions`

**Description:** Generate AI classification suggestions for all unclassified transactions in a batch.

**Path Parameters:**
- `batch_id` (integer, required) - The bank import batch ID

**Response:** `200 OK`

```json
{
  "statement_id": 1,
  "unclassified_before": 40,
  "suggestions_created": 35
}
```

**Note:** Requires `OPENAI_API_KEY` environment variable to be set on the backend.

**Example Request:**
```javascript
const response = await fetch('/bank-rules/bank-import-batches/1/generate-ai-suggestions', {
  method: 'POST'
});

const result = await response.json();
console.log(`Created ${result.suggestions_created} AI suggestions`);
```

---

### 9. List Unmatched Transactions

**Endpoint:** `GET /bank-rules/pharmacies/{pharmacy_id}/bank-transactions/unmatched`

**Description:** Get all unmatched/unclassified transactions for a pharmacy, including AI suggestions if available.

**Path Parameters:**
- `pharmacy_id` (integer, required) - The pharmacy ID

**Response:** `200 OK`

```json
[
  {
    "id": 123,
    "bank_import_batch_id": 1,
    "bank_account_id": 1,
    "pharmacy_id": 1,
    "date": "2025-01-15",
    "description": "PAYMENT TO SUPPLIER XYZ",
    "reference": "REF123",
    "amount": -5000.00,
    "balance": 10000.00,
    "classification_status": "ai_classified",
    "classified_at": null,
    "classified_by_rule_id": null,
    "ai_suggestion_id": 45,
    "ledger_entry_id": null,
    "ai_suggestion": {
      "id": 45,
      "pharmacy_id": 1,
      "bank_transaction_id": 123,
      "suggested_account_id": 29,
      "suggested_description": "Supplier Payment",
      "suggested_type": "spend",
      "confidence": 0.85,
      "status": "pending",
      "created_at": "2025-01-15T10:00:00Z"
    }
  }
]
```

**Example Request:**
```javascript
const response = await fetch('/bank-rules/pharmacies/1/bank-transactions/unmatched');
const unmatched = await response.json();

unmatched.forEach(txn => {
  console.log(`${txn.date}: ${txn.description} - ${txn.amount}`);
  if (txn.ai_suggestion) {
    console.log(`  AI suggests: Account ${txn.ai_suggestion.suggested_account_id} (confidence: ${txn.ai_suggestion.confidence})`);
  }
});
```

---

### 10. Accept an AI Suggestion

**Endpoint:** `POST /bank-rules/ai-suggestions/{suggestion_id}/accept`

**Description:** Accept an AI suggestion and create a ledger entry. Optionally override the suggested account.

**Path Parameters:**
- `suggestion_id` (integer, required) - The AI suggestion ID

**Request Body:** (optional)
```json
{
  "account_id": 456
}
```

If `account_id` is provided, it overrides the suggested account. Otherwise, the suggested account is used.

**Response:** `200 OK`

```json
{
  "message": "AI suggestion accepted",
  "ledger_entry_id": 789
}
```

**Example Request:**
```javascript
// Accept with suggested account
const response1 = await fetch('/bank-rules/ai-suggestions/45/accept', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({})
});

// Accept with account override
const response2 = await fetch('/bank-rules/ai-suggestions/45/accept', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    account_id: 456
  })
});

const result = await response.json();
console.log(`Ledger entry created: ${result.ledger_entry_id}`);
```

---

### 11. Reject an AI Suggestion

**Endpoint:** `POST /bank-rules/ai-suggestions/{suggestion_id}/reject`

**Description:** Reject an AI suggestion. The transaction remains unclassified.

**Path Parameters:**
- `suggestion_id` (integer, required) - The AI suggestion ID

**Response:** `200 OK`

```json
{
  "message": "AI suggestion rejected"
}
```

**Example Request:**
```javascript
const response = await fetch('/bank-rules/ai-suggestions/45/reject', {
  method: 'POST'
});

const result = await response.json();
```

---

## 📊 Response Models

### BankRule

```typescript
interface BankRule {
  id: number;
  pharmacy_id: number;
  name: string;
  type: 'receive' | 'spend' | 'transfer';
  priority: number;
  allocate: Array<{
    account_id: number;
    percent: number;
    vat_code: string;
  }>;
  contact_name: string | null;
  is_active: boolean;
  created_by_user_id: number | null;
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
  conditions: Array<{
    id: number;
    bank_rule_id: number;
    group_type: 'ALL' | 'ANY';
    field: 'description' | 'reference' | 'amount' | 'amount_in' | 'amount_out' | 'date';
    operator: 'contains' | 'not_contains' | 'equals' | 'starts_with' | 'ends_with' | 'greater_than' | 'less_than' | 'regex';
    value: string;
    created_at: string;
    updated_at: string;
  }>;
}
```

### BankTransactionWithClassification

```typescript
interface BankTransactionWithClassification {
  id: number;
  bank_import_batch_id: number;
  bank_account_id: number;
  pharmacy_id: number;
  date: string; // YYYY-MM-DD
  description: string;
  reference: string | null;
  amount: number;
  balance: number | null;
  classification_status: 'unclassified' | 'rule_classified' | 'ai_classified' | 'user_override';
  classified_at: string | null;
  classified_by_rule_id: number | null;
  ai_suggestion_id: number | null;
  ledger_entry_id: number | null;
  ai_suggestion?: AISuggestion;
}
```

---

## 🎨 Frontend Display Examples

### Display Rules List

```javascript
// Fetch and display rules
async function displayRules(pharmacyId) {
  const response = await fetch(`/bank-rules/pharmacies/${pharmacyId}/bank-rules`);
  const rules = await response.json();
  
  // Group by type
  const receiveRules = rules.filter(r => r.type === 'receive' && r.is_active);
  const spendRules = rules.filter(r => r.type === 'spend' && r.is_active);
  const transferRules = rules.filter(r => r.type === 'transfer' && r.is_active);
  
  // Display in UI
  renderRulesSection('Incoming', receiveRules);
  renderRulesSection('Outgoing', spendRules);
  renderRulesSection('Transfers', transferRules);
}

function renderRulesSection(title, rules) {
  console.log(`${title} Rules (${rules.length}):`);
  rules.forEach(rule => {
    console.log(`  [${rule.priority}] ${rule.name}`);
    console.log(`    Conditions: ${rule.conditions.map(c => `${c.field} ${c.operator} "${c.value}"`).join(', ')}`);
    console.log(`    Allocations: ${rule.allocate.map(a => `${a.percent}% to account ${a.account_id}`).join(', ')}`);
  });
}
```

### Display Unmatched Transactions

```javascript
// Fetch and display unmatched transactions
async function displayUnmatched(pharmacyId) {
  const response = await fetch(`/bank-rules/pharmacies/${pharmacyId}/bank-transactions/unmatched`);
  const transactions = await response.json();
  
  transactions.forEach(txn => {
    const status = txn.classification_status;
    const hasSuggestion = !!txn.ai_suggestion;
    
    console.log(`${txn.date}: ${txn.description}`);
    console.log(`  Amount: ${txn.amount}`);
    console.log(`  Status: ${status}`);
    
    if (hasSuggestion) {
      const suggestion = txn.ai_suggestion;
      console.log(`  AI Suggestion: Account ${suggestion.suggested_account_id}`);
      console.log(`    Confidence: ${(suggestion.confidence * 100).toFixed(0)}%`);
      console.log(`    Description: ${suggestion.suggested_description}`);
    }
  });
}
```

---

## 🔐 Authentication

All endpoints may require authentication depending on your backend configuration. Include authentication headers if needed:

```javascript
const headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Bearer YOUR_TOKEN' // If using JWT/auth
};

const response = await fetch('/bank-rules/pharmacies/1/bank-rules', {
  headers: headers
});
```

---

## 📝 Notes

1. **Priority Ordering**: Rules are evaluated in priority order (lower number = higher priority). The first matching rule is applied.

2. **Rule Types**:
   - `receive` - Money coming in (positive amounts)
   - `spend` - Money going out (negative amounts)
   - `transfer` - Transfers between accounts

3. **Condition Groups**:
   - `ALL` - All conditions must match (AND logic)
   - `ANY` - At least one condition must match (OR logic)

4. **Idempotency**: Applying rules multiple times is safe - already classified transactions are skipped.

5. **AI Suggestions**: Require OpenAI API key on backend. Suggestions are stored but don't create ledger entries until accepted.

---

## 🚀 Quick Start Example

```javascript
// 1. Get all rules for pharmacy
const rules = await fetch('/bank-rules/pharmacies/1/bank-rules').then(r => r.json());

// 2. Apply rules to a batch
const applyResult = await fetch('/bank-rules/bank-import-batches/1/apply-rules', {
  method: 'POST'
}).then(r => r.json());

console.log(`Classified ${applyResult.classified_by_rule} transactions`);

// 3. Generate AI suggestions for remaining
const aiResult = await fetch('/bank-rules/bank-import-batches/1/generate-ai-suggestions', {
  method: 'POST'
}).then(r => r.json());

console.log(`Created ${aiResult.suggestions_created} AI suggestions`);

// 4. Get unmatched transactions with suggestions
const unmatched = await fetch('/bank-rules/pharmacies/1/bank-transactions/unmatched')
  .then(r => r.json());

// 5. Accept an AI suggestion
await fetch('/bank-rules/ai-suggestions/45/accept', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({})
});
```

