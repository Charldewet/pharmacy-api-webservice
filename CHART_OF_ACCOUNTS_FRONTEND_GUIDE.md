# Chart of Accounts Frontend Integration Guide

## Issue: Missing Authorization Header

When calling the `/admin/chart-of-accounts` endpoint, you must include the Authorization header with a Bearer token.

## Endpoint Details

**POST** `/admin/chart-of-accounts`

**Authentication Required:** Bearer token (JWT) in Authorization header

**Authorization:** Only admin users (user_id: 2 or 9) can access this endpoint

## Correct Implementation

### JavaScript/TypeScript Example

```javascript
async function createAccount(accountData) {
  // Get the JWT token from your auth system
  const token = localStorage.getItem('admin_token') || getAuthToken(); // Use your token retrieval method
  
  if (!token) {
    throw new Error('No authentication token available. Please log in.');
  }
  
  const response = await fetch('/admin/chart-of-accounts', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,  // REQUIRED: Must include Authorization header
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      code: accountData.code,
      name: accountData.name,
      type: accountData.type,
      category: accountData.category,
      parent_account_id: accountData.parent_account_id || null,
      is_active: accountData.is_active !== undefined ? accountData.is_active : true,
      display_order: accountData.display_order || 0,
      notes: accountData.notes || null
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create account');
  }
  
  return await response.json();
}

// Usage example
try {
  const newAccount = await createAccount({
    code: '2101',
    name: 'Account Name',
    type: 'EXPENSE',
    category: 'OPERATING_EXPENSE'
  });
  console.log('Account created:', newAccount);
} catch (error) {
  console.error('Error creating account:', error.message);
}
```

### React Example

```jsx
import { useState } from 'react';

function CreateAccountForm() {
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    type: 'EXPENSE',
    category: '',
    parent_account_id: null,
    is_active: true,
    display_order: 0,
    notes: ''
  });
  
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      // Get token from your auth context/store
      const token = localStorage.getItem('admin_token');
      
      if (!token) {
        throw new Error('Please log in to create accounts');
      }
      
      const response = await fetch('/admin/chart-of-accounts', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,  // REQUIRED
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create account');
      }
      
      const newAccount = await response.json();
      console.log('Account created:', newAccount);
      // Reset form or redirect
      setFormData({
        code: '',
        name: '',
        type: 'EXPENSE',
        category: '',
        parent_account_id: null,
        is_active: true,
        display_order: 0,
        notes: ''
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {error && <div className="error">{error}</div>}
      
      <input
        type="text"
        placeholder="Account Code (max 10 chars)"
        value={formData.code}
        onChange={(e) => setFormData({...formData, code: e.target.value})}
        maxLength={10}
        required
      />
      
      <input
        type="text"
        placeholder="Account Name"
        value={formData.name}
        onChange={(e) => setFormData({...formData, name: e.target.value})}
        required
      />
      
      <select
        value={formData.type}
        onChange={(e) => setFormData({...formData, type: e.target.value})}
        required
      >
        <option value="ASSET">Asset</option>
        <option value="LIABILITY">Liability</option>
        <option value="EQUITY">Equity</option>
        <option value="INCOME">Income</option>
        <option value="COGS">Cost of Goods Sold</option>
        <option value="EXPENSE">Expense</option>
        <option value="FINANCE_COST">Finance Cost</option>
        <option value="OTHER_INCOME">Other Income</option>
        <option value="TAX">Tax</option>
      </select>
      
      <input
        type="text"
        placeholder="Category"
        value={formData.category}
        onChange={(e) => setFormData({...formData, category: e.target.value})}
        required
      />
      
      <button type="submit" disabled={loading}>
        {loading ? 'Creating...' : 'Create Account'}
      </button>
    </form>
  );
}
```

### Vue Example

```javascript
export default {
  data() {
    return {
      formData: {
        code: '',
        name: '',
        type: 'EXPENSE',
        category: '',
        parent_account_id: null,
        is_active: true,
        display_order: 0,
        notes: ''
      },
      error: '',
      loading: false
    };
  },
  methods: {
    async createAccount() {
      this.error = '';
      this.loading = true;
      
      try {
        // Get token from your auth store/composable
        const token = this.$store.state.auth.token || localStorage.getItem('admin_token');
        
        if (!token) {
          throw new Error('Please log in to create accounts');
        }
        
        const response = await fetch('/admin/chart-of-accounts', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,  // REQUIRED
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.formData)
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to create account');
        }
        
        const newAccount = await response.json();
        console.log('Account created:', newAccount);
        // Reset form or emit event
        this.$emit('account-created', newAccount);
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    }
  }
};
```

## Common Errors

### Error: "Missing Authorization header"

**Cause:** The Authorization header is not included in the request.

**Solution:** Always include the Authorization header:
```javascript
headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

### Error: "Invalid token"

**Cause:** The token is expired or invalid.

**Solution:** Refresh the token or re-authenticate the user.

### Error: "Admin access restricted to authorized users only"

**Cause:** The user is not an admin (user_id must be 2 or 9).

**Solution:** Ensure the logged-in user is an admin user.

## Helper Function

Create a reusable function for making authenticated requests:

```javascript
// apiHelper.js
export async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem('admin_token') || getAuthToken();
  
  if (!token) {
    throw new Error('No authentication token available');
  }
  
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  const response = await fetch(url, {
    ...options,
    headers
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }
  
  return await response.json();
}

// Usage
try {
  const account = await authenticatedFetch('/admin/chart-of-accounts', {
    method: 'POST',
    body: JSON.stringify({
      code: '2101',
      name: 'Account Name',
      type: 'EXPENSE',
      category: 'OPERATING_EXPENSE'
    })
  });
  console.log('Account created:', account);
} catch (error) {
  console.error('Error:', error.message);
}
```

## Request Body Format

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

## Response Format

```json
{
  "id": 123,
  "code": "2101",
  "name": "Account Name",
  "type": "EXPENSE",
  "category": "OPERATING_EXPENSE",
  "parent_account_id": null,
  "is_active": true,
  "display_order": 0,
  "notes": null,
  "created_at": "2025-01-15T10:30:00.000000+00:00",
  "updated_at": "2025-01-15T10:30:00.000000+00:00"
}
```

## Summary

1. **Always include the Authorization header** with Bearer token
2. **Ensure the user is logged in** and has a valid token
3. **Verify the user is an admin** (user_id: 2 or 9)
4. **Handle errors appropriately** (401, 403, 400, etc.)
5. **Use proper Content-Type header** (application/json)
