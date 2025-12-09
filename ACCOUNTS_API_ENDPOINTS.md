# Chart of Accounts API Endpoints

## Base URL
All endpoints are prefixed with `/accounts`

## Authentication
All endpoints require API key authentication:
```
Authorization: Bearer YOUR_API_KEY
```
or
```
X-API-Key: YOUR_API_KEY
```

---

## Endpoints

### 1. List Accounts
**GET** `/accounts`

Get all accounts in the chart of accounts with optional filtering.

**Query Parameters:**
- `type` (optional): Filter by account type (ASSET, LIABILITY, EQUITY, INCOME, COGS, EXPENSE, FINANCE_COST, OTHER_INCOME, TAX)
- `category` (optional): Filter by category (e.g., CURRENT_ASSET, SALES, STAFF_COSTS)
- `is_active` (optional): Filter by active status (true/false)
- `include_inactive` (optional, default: false): Include inactive accounts

**Example:**
```bash
GET /accounts?type=INCOME&include_inactive=false
```

**Response:**
```json
[
  {
    "id": 1,
    "code": "4000",
    "name": "Sales – Dispensary",
    "type": "INCOME",
    "category": "SALES",
    "parent_account_id": null,
    "is_active": true,
    "display_order": 4000,
    "notes": "MIS \"Dispensary\"; POS dispensary turnover",
    "created_at": "2025-12-15T10:00:00Z",
    "updated_at": "2025-12-15T10:00:00Z"
  }
]
```

---

### 2. Get Account by ID
**GET** `/accounts/{account_id}`

Get a specific account by its ID.

**Example:**
```bash
GET /accounts/1
```

**Response:**
```json
{
  "id": 1,
  "code": "4000",
  "name": "Sales – Dispensary",
  "type": "INCOME",
  "category": "SALES",
  "parent_account_id": null,
  "is_active": true,
  "display_order": 4000,
  "notes": "MIS \"Dispensary\"; POS dispensary turnover",
  "created_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
```

---

### 3. Get Account by Code
**GET** `/accounts/code/{account_code}`

Get a specific account by its code (e.g., "4000", "6200").

**Example:**
```bash
GET /accounts/code/4000
```

**Response:**
```json
{
  "id": 1,
  "code": "4000",
  "name": "Sales – Dispensary",
  "type": "INCOME",
  "category": "SALES",
  "parent_account_id": null,
  "is_active": true,
  "display_order": 4000,
  "notes": "MIS \"Dispensary\"; POS dispensary turnover",
  "created_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
```

---

### 4. List Account Types
**GET** `/accounts/types/list`

Get list of all available account types.

**Example:**
```bash
GET /accounts/types/list
```

**Response:**
```json
{
  "types": [
    "ASSET",
    "LIABILITY",
    "EQUITY",
    "INCOME",
    "COGS",
    "EXPENSE",
    "FINANCE_COST",
    "OTHER_INCOME",
    "TAX"
  ]
}
```

---

### 5. List Account Categories
**GET** `/accounts/categories/list`

Get list of all available account categories.

**Example:**
```bash
GET /accounts/categories/list
```

**Response:**
```json
{
  "categories": [
    "ADMIN_BANK",
    "ADMIN_OFFICE",
    "ADMIN_PROF",
    "CURRENT_ASSET",
    "CURRENT_LIABILITY",
    "EQUITY",
    "MARKETING",
    "OCCUPANCY",
    "OPERATIONS",
    "SALES",
    "STAFF_COSTS"
  ]
}
```

---

### 6. Get Accounts Summary Statistics
**GET** `/accounts/summary/stats`

Get summary statistics about accounts (counts by type and category).

**Example:**
```bash
GET /accounts/summary/stats
```

**Response:**
```json
{
  "total": 79,
  "active": 79,
  "inactive": 0,
  "by_type": {
    "ASSET": 10,
    "LIABILITY": 7,
    "EQUITY": 2,
    "INCOME": 5,
    "COGS": 4,
    "EXPENSE": 44,
    "FINANCE_COST": 2,
    "OTHER_INCOME": 4,
    "TAX": 1
  },
  "by_category": {
    "ADMIN_BANK": 1,
    "ADMIN_OFFICE": 2,
    "CURRENT_ASSET": 6,
    "SALES": 5,
    "STAFF_COSTS": 10
  }
}
```

---

## Common Use Cases

### Filter by Type
```bash
GET /accounts?type=INCOME
```

### Filter by Category
```bash
GET /accounts?category=SALES
```

### Get All Active Accounts
```bash
GET /accounts?include_inactive=false
```

### Get All Accounts (Including Inactive)
```bash
GET /accounts?include_inactive=true
```

### Combine Filters
```bash
GET /accounts?type=EXPENSE&category=STAFF_COSTS&is_active=true
```

---

## Frontend Integration Example

```javascript
// Get all accounts
const response = await fetch('/accounts', {
  headers: {
    'X-API-Key': API_KEY
  }
});
const accounts = await response.json();

// Filter by type
const incomeAccounts = await fetch('/accounts?type=INCOME', {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());

// Get account by code
const account = await fetch('/accounts/code/4000', {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());

// Get summary stats
const stats = await fetch('/accounts/summary/stats', {
  headers: { 'X-API-Key': API_KEY }
}).then(r => r.json());
```

---

**Last Updated**: December 2025

