# Account Create API Format

## Endpoint
**POST** `/accounts`

> **Note:** This endpoint may need to be implemented. The schema is defined but the endpoint may not exist yet.

## Authentication
Requires API key authentication:
```
Authorization: Bearer YOUR_API_KEY
```
or
```
X-API-Key: YOUR_API_KEY
```

## Request Body Format

The backend expects a JSON object with the following structure:

```json
{
  "code": "string (required, max 10 chars, must be unique)",
  "name": "string (required)",
  "type": "string (required, one of: ASSET, LIABILITY, EQUITY, INCOME, COGS, EXPENSE, FINANCE_COST, OTHER_INCOME, TAX)",
  "category": "string (required)",
  "parent_account_id": "integer (optional, null if no parent)",
  "is_active": "boolean (optional, default: true)",
  "display_order": "integer (optional, default: 0)",
  "notes": "string (optional, null if no notes)"
}
```

## Field Details

### Required Fields

- **`code`** (string, max 10 characters)
  - Unique account code (e.g., "4000", "6200", "1001")
  - Must be unique across all accounts
  - Examples: "4000", "6200", "1001"

- **`name`** (string)
  - Display name of the account
  - Examples: "Sales – Dispensary", "Staff Salaries", "Bank Account"

- **`type`** (string, enum)
  - Account type, must be one of:
    - `ASSET`
    - `LIABILITY`
    - `EQUITY`
    - `INCOME`
    - `COGS`
    - `EXPENSE`
    - `FINANCE_COST`
    - `OTHER_INCOME`
    - `TAX`

- **`category`** (string)
  - Account category for grouping
  - Examples: "CURRENT_ASSET", "SALES", "STAFF_COSTS", "OPERATING_EXPENSE"

### Optional Fields

- **`parent_account_id`** (integer, nullable)
  - ID of parent account if this is a sub-account
  - Set to `null` if this is a top-level account
  - Default: `null`

- **`is_active`** (boolean)
  - Whether the account is active
  - Default: `true`

- **`display_order`** (integer)
  - Order for display/sorting purposes
  - Default: `0`

- **`notes`** (string, nullable)
  - Additional notes about the account
  - Default: `null`

## Example Request

```json
{
  "code": "4100",
  "name": "Sales – Front Shop",
  "type": "INCOME",
  "category": "SALES",
  "parent_account_id": null,
  "is_active": true,
  "display_order": 4100,
  "notes": "POS front shop turnover"
}
```

## Example Request (Sub-Account)

```json
{
  "code": "4101",
  "name": "Sales – Front Shop – Cosmetics",
  "type": "INCOME",
  "category": "SALES",
  "parent_account_id": 5,
  "is_active": true,
  "display_order": 4101,
  "notes": "Cosmetics sub-category"
}
```

## Example Request (Minimal)

```json
{
  "code": "9999",
  "name": "Test Account",
  "type": "EXPENSE",
  "category": "TEST"
}
```

## Account Code Ranges (Guidelines)

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

## Response Format

On success, the API should return the created account with additional fields:

```json
{
  "id": 123,
  "code": "4100",
  "name": "Sales – Front Shop",
  "type": "INCOME",
  "category": "SALES",
  "parent_account_id": null,
  "is_active": true,
  "display_order": 4100,
  "notes": "POS front shop turnover",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid account type. Must be one of: ASSET, LIABILITY, EQUITY, INCOME, COGS, EXPENSE, FINANCE_COST, OTHER_INCOME, TAX"
}
```

### 409 Conflict (if code already exists)
```json
{
  "detail": "Account with code '4000' already exists"
}
```

## TypeScript Interface (for Frontend)

```typescript
interface AccountCreate {
  code: string;                    // Required, max 10 chars, unique
  name: string;                    // Required
  type: AccountType;               // Required, enum
  category: string;                // Required
  parent_account_id?: number | null; // Optional
  is_active?: boolean;             // Optional, default: true
  display_order?: number;          // Optional, default: 0
  notes?: string | null;           // Optional
}

type AccountType = 
  | 'ASSET'
  | 'LIABILITY'
  | 'EQUITY'
  | 'INCOME'
  | 'COGS'
  | 'EXPENSE'
  | 'FINANCE_COST'
  | 'OTHER_INCOME'
  | 'TAX';
```
