# User Roles Implementation Guide

## Overview

The user role system has been enhanced to support multiple roles per user. Users can now have:
- **Read/Write access** (per pharmacy) - existing functionality
- **Admin role** - administrative access to user management and system configuration
- **Accounting role** - access to accounting-related endpoints (banking, ledger, chart of accounts, etc.)

A user can have **one, a combination, or all roles**.

## Database Changes

### Schema Updates

Two new columns have been added to the `pharma.users` table:

```sql
ALTER TABLE pharma.users 
  ADD COLUMN is_admin boolean NOT NULL DEFAULT false,
  ADD COLUMN is_accounting boolean NOT NULL DEFAULT false;
```

### Migration

Run the migration script to add the columns and set existing admin users:

```bash
python scripts/migrate_user_roles.py
```

This script will:
1. Add `is_admin` and `is_accounting` columns if they don't exist
2. Set `is_admin=true` for existing admin users (user_id 2 and 9)
3. Verify the migration

## API Changes

### Authentication Functions

New authentication functions have been added in `pharma_api/app/auth.py`:

1. **`require_accounting_or_api_key`** - Requires accounting role or API key
2. **`require_admin_or_accounting_or_api_key`** - Requires admin OR accounting role or API key
3. **`_check_user_role(user_id, role)`** - Internal helper to check user roles

The existing `require_admin_or_api_key` function now checks the database `is_admin` column instead of hardcoded user IDs.

### User Management Endpoints

#### Create User

**POST** `/admin/users`

Now accepts `is_admin` and `is_accounting` fields:

```json
{
  "username": "accountant1",
  "email": "accountant@example.com",
  "password": "secure_password",
  "pharmacy_ids": [1, 2],
  "can_write": true,
  "is_admin": false,
  "is_accounting": true
}
```

#### Update User

**PUT** `/admin/users/{user_id}`

Now accepts `is_admin` and `is_accounting` fields:

```json
{
  "email": "newemail@example.com",
  "is_admin": true,
  "is_accounting": true
}
```

#### Get User Details

**GET** `/admin/users/{user_id}`

Response now includes role information:

```json
{
  "user_id": 10,
  "username": "accountant1",
  "email": "accountant@example.com",
  "is_active": true,
  "is_admin": false,
  "is_accounting": true,
  "created_at": "2025-01-15T10:00:00Z",
  "pharmacies": [...]
}
```

#### List Users

**GET** `/admin/users`

Response now includes role information for each user.

### Login Response

**POST** `/auth/login`

The login response now includes role information:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 43200,
  "user": {
    "user_id": 10,
    "username": "accountant1",
    "email": "accountant@example.com",
    "is_admin": false,
    "is_accounting": true
  }
}
```

## Using Roles in Endpoints

### Protecting Admin Endpoints

```python
from ..auth import require_admin_or_api_key

@router.get("/admin/users")
def list_users(user_id: Optional[int] = Depends(require_admin_or_api_key)):
    # Only admin users or API keys can access
    ...
```

### Protecting Accounting Endpoints

```python
from ..auth import require_accounting_or_api_key

@router.get("/ledger-entries")
def list_ledger_entries(user_id: Optional[int] = Depends(require_accounting_or_api_key)):
    # Only accounting users or API keys can access
    ...
```

### Protecting Endpoints for Admin OR Accounting

```python
from ..auth import require_admin_or_accounting_or_api_key

@router.get("/financial-reports")
def get_financial_reports(user_id: Optional[int] = Depends(require_admin_or_accounting_or_api_key)):
    # Admin or accounting users or API keys can access
    ...
```

## Role Combinations

Users can have any combination of roles:

| is_admin | is_accounting | Capabilities |
|----------|---------------|--------------|
| false | false | Standard user with pharmacy read/write access only |
| true | false | Admin access (user management, system config) |
| false | true | Accounting access (banking, ledger, accounts) |
| true | true | Full access (admin + accounting) |

## Frontend Integration

### Check User Roles After Login

```javascript
// After login
const response = await fetch('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ username, password })
});

const data = await response.json();
const user = data.user;

// Check roles
const isAdmin = user.is_admin;
const isAccounting = user.is_accounting;

// Show/hide UI based on roles
if (isAdmin) {
  // Show admin panel
}

if (isAccounting) {
  // Show accounting features
}
```

### Conditional UI Rendering

```javascript
function UserDashboard({ user }) {
  return (
    <div>
      {user.is_admin && <AdminPanel />}
      {user.is_accounting && <AccountingPanel />}
      <PharmacyAccessPanel />
    </div>
  );
}
```

## Examples

### Example 1: Create an Accounting User

```bash
curl -X POST https://your-api.com/admin/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "accountant",
    "email": "accountant@pharmacy.com",
    "password": "secure123",
    "is_accounting": true,
    "pharmacy_ids": [1, 2],
    "can_write": true
  }'
```

### Example 2: Grant Accounting Role to Existing User

```bash
curl -X PUT https://your-api.com/admin/users/5 \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "is_accounting": true
  }'
```

### Example 3: Create User with Multiple Roles

```bash
curl -X POST https://your-api.com/admin/users \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superuser",
    "email": "super@pharmacy.com",
    "password": "secure123",
    "is_admin": true,
    "is_accounting": true,
    "pharmacy_ids": [1, 2, 3],
    "can_write": true
  }'
```

## Backward Compatibility

- Existing admin users (user_id 2 and 9) are automatically set to `is_admin=true` by the migration script
- The `ADMIN_USER_IDS` constant in `admin.py` is kept for backward compatibility but is no longer used for authorization checks
- All existing endpoints continue to work as before
- API keys continue to work as before (treated as admin/accounting access)

## Security Notes

1. **Role Management**: Only admin users can grant/revoke roles
2. **API Keys**: API keys are treated as having both admin and accounting access
3. **Database Checks**: All role checks are performed against the database, not hardcoded values
4. **Pharmacy Access**: Role-based access is separate from pharmacy-specific read/write permissions

## Next Steps

To use accounting roles for specific endpoints:

1. Identify which endpoints should require accounting access (e.g., `/ledger-entries`, `/accounts`, `/bank-accounts`)
2. Update those endpoints to use `require_accounting_or_api_key` or `require_admin_or_accounting_or_api_key`
3. Update frontend to check `is_accounting` flag and show/hide accounting features accordingly

## Migration Checklist

- [x] Add `is_admin` and `is_accounting` columns to schema
- [x] Create migration script
- [x] Update auth functions to check database roles
- [x] Update admin endpoints to support role management
- [x] Update login endpoint to return role information
- [x] Update user schemas to include roles
- [ ] Run migration script on production database
- [ ] Update frontend to use role information
- [ ] Update accounting endpoints to use accounting role checks (optional)

