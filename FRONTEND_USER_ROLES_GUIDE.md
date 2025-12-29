# Frontend User Roles Management Guide

This guide explains how to manage user roles (admin and accounting) from your frontend application.

## Overview

Users can have three types of access:
1. **Pharmacy Access** - Read/write access to specific pharmacies (existing)
2. **Admin Role** - Access to user management and system configuration
3. **Accounting Role** - Access to accounting endpoints (banking, ledger, accounts)

A user can have **one, a combination, or all** of these access types.

## Authentication

All admin endpoints require:
- **Authorization Header**: `Authorization: Bearer <jwt_token>`
- **Admin Access**: Only users with `is_admin: true` can access these endpoints

### Check if Current User is Admin

After login, check the user object:

```javascript
// After login
const loginResponse = await fetch('/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});

const data = await loginResponse.json();
const user = data.user;

// Check roles
const isAdmin = user.is_admin;        // true/false
const isAccounting = user.is_accounting; // true/false

// Store in your app state
localStorage.setItem('user', JSON.stringify(user));
localStorage.setItem('token', data.access_token);
```

### Protect Admin Routes

```javascript
function isAdminUser() {
  const userStr = localStorage.getItem('user');
  if (!userStr) return false;
  const user = JSON.parse(userStr);
  return user.is_admin === true;
}

// In your route guard
if (!isAdminUser()) {
  // Redirect to login or show access denied
  window.location.href = '/login';
}
```

## API Endpoints

Base URL: `https://pharmacy-api-webservice.onrender.com` (or your API URL)

### 1. List All Users with Roles

**GET** `/admin/users`

Returns a list of all users including their roles.

```javascript
async function listUsers() {
  const token = localStorage.getItem('token');
  
  const response = await fetch('https://pharmacy-api-webservice.onrender.com/admin/users', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Access denied. Admin access required.');
    }
    throw new Error('Failed to fetch users');
  }
  
  const users = await response.json();
  return users;
}

// Usage
const users = await listUsers();
users.forEach(user => {
  console.log(`${user.username}:`, {
    admin: user.is_admin,
    accounting: user.is_accounting,
    active: user.is_active
  });
});
```

**Response Format:**
```json
[
  {
    "user_id": 2,
    "username": "Charl",
    "email": "charl@example.com",
    "is_active": true,
    "is_admin": true,
    "is_accounting": true,
    "created_at": "2025-01-15T10:00:00Z",
    "pharmacy_count": 5
  },
  {
    "user_id": 3,
    "username": "Jaco",
    "email": "jaco@tlcpharmacy.com",
    "is_active": true,
    "is_admin": false,
    "is_accounting": false,
    "created_at": "2025-01-15T10:00:00Z",
    "pharmacy_count": 5
  }
]
```

### 2. Get User Details

**GET** `/admin/users/{user_id}`

Get detailed information about a specific user including roles and pharmacy access.

```javascript
async function getUserDetails(userId) {
  const token = localStorage.getItem('token');
  
  const response = await fetch(
    `https://pharmacy-api-webservice.onrender.com/admin/users/${userId}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to fetch user details');
  }
  
  return await response.json();
}

// Usage
const user = await getUserDetails(2);
console.log('User roles:', {
  admin: user.is_admin,
  accounting: user.is_accounting
});
```

**Response Format:**
```json
{
  "user_id": 2,
  "username": "Charl",
  "email": "charl@example.com",
  "is_active": true,
  "is_admin": true,
  "is_accounting": true,
  "created_at": "2025-01-15T10:00:00Z",
  "pharmacies": [
    {
      "pharmacy_id": 1,
      "pharmacy_name": "TLC PHARMACY",
      "can_read": true,
      "can_write": true
    }
  ]
}
```

### 3. Create User with Roles

**POST** `/admin/users`

Create a new user and assign roles.

```javascript
async function createUser(userData) {
  const token = localStorage.getItem('token');
  
  const response = await fetch('https://pharmacy-api-webservice.onrender.com/admin/users', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      username: userData.username,
      email: userData.email,
      password: userData.password,
      pharmacy_ids: userData.pharmacy_ids || [],
      can_write: userData.can_write || false,
      is_admin: userData.is_admin || false,
      is_accounting: userData.is_accounting || false
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create user');
  }
  
  return await response.json();
}

// Usage Examples:

// Create a standard user (no special roles)
await createUser({
  username: 'newuser',
  email: 'newuser@example.com',
  password: 'secure_password123',
  pharmacy_ids: [1, 2],
  can_write: true,
  is_admin: false,
  is_accounting: false
});

// Create an accounting user
await createUser({
  username: 'accountant',
  email: 'accountant@example.com',
  password: 'secure_password123',
  pharmacy_ids: [1, 2, 3],
  can_write: true,
  is_admin: false,
  is_accounting: true  // Grant accounting role
});

// Create an admin user
await createUser({
  username: 'admin',
  email: 'admin@example.com',
  password: 'secure_password123',
  pharmacy_ids: [1, 2, 3],
  can_write: true,
  is_admin: true,      // Grant admin role
  is_accounting: false
});

// Create a user with both roles
await createUser({
  username: 'superuser',
  email: 'superuser@example.com',
  password: 'secure_password123',
  pharmacy_ids: [1, 2, 3],
  can_write: true,
  is_admin: true,       // Admin role
  is_accounting: true   // Accounting role
});
```

### 4. Update User Roles

**PUT** `/admin/users/{user_id}`

Update a user's roles (and other properties).

```javascript
async function updateUserRoles(userId, roleUpdates) {
  const token = localStorage.getItem('token');
  
  const response = await fetch(
    `https://pharmacy-api-webservice.onrender.com/admin/users/${userId}`,
    {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        is_admin: roleUpdates.is_admin,        // Optional: true/false
        is_accounting: roleUpdates.is_accounting, // Optional: true/false
        is_active: roleUpdates.is_active,       // Optional: true/false
        email: roleUpdates.email,              // Optional: new email
        password: roleUpdates.password         // Optional: new password
      })
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update user');
  }
  
  return await response.json();
}

// Usage Examples:

// Grant accounting role to a user
await updateUserRoles(3, {
  is_accounting: true
});

// Grant admin role
await updateUserRoles(3, {
  is_admin: true
});

// Grant both roles
await updateUserRoles(3, {
  is_admin: true,
  is_accounting: true
});

// Revoke accounting role (keep admin)
await updateUserRoles(3, {
  is_accounting: false
});

// Revoke admin role (keep accounting)
await updateUserRoles(3, {
  is_admin: false
});

// Revoke both roles
await updateUserRoles(3, {
  is_admin: false,
  is_accounting: false
});

// Update multiple properties at once
await updateUserRoles(3, {
  is_admin: true,
  is_accounting: true,
  is_active: true,
  email: 'newemail@example.com'
});
```

## Complete React Example

Here's a complete React component for managing user roles:

```jsx
import React, { useState, useEffect } from 'react';

function UserRolesManager() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState(null);
  
  const API_BASE = 'https://pharmacy-api-webservice.onrender.com';
  
  useEffect(() => {
    loadUsers();
  }, []);
  
  async function loadUsers() {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/admin/users`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to load users');
      }
      
      const data = await response.json();
      setUsers(data);
    } catch (error) {
      console.error('Error loading users:', error);
      alert('Failed to load users');
    } finally {
      setLoading(false);
    }
  }
  
  async function updateRoles(userId, isAdmin, isAccounting) {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE}/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          is_admin: isAdmin,
          is_accounting: isAccounting
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to update roles');
      }
      
      // Reload users to show updated roles
      await loadUsers();
      alert('Roles updated successfully');
    } catch (error) {
      console.error('Error updating roles:', error);
      alert('Failed to update roles');
    }
  }
  
  if (loading) {
    return <div>Loading...</div>;
  }
  
  return (
    <div className="user-roles-manager">
      <h2>User Roles Management</h2>
      
      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Active</th>
            <th>Admin</th>
            <th>Accounting</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.user_id}>
              <td>{user.username}</td>
              <td>{user.email}</td>
              <td>{user.is_active ? '✓' : '✗'}</td>
              <td>
                <input
                  type="checkbox"
                  checked={user.is_admin}
                  onChange={(e) => updateRoles(
                    user.user_id,
                    e.target.checked,
                    user.is_accounting
                  )}
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  checked={user.is_accounting}
                  onChange={(e) => updateRoles(
                    user.user_id,
                    user.is_admin,
                    e.target.checked
                  )}
                />
              </td>
              <td>
                <button onClick={() => setSelectedUser(user)}>
                  View Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      
      {selectedUser && (
        <div className="user-details">
          <h3>User Details: {selectedUser.username}</h3>
          <p>Email: {selectedUser.email}</p>
          <p>Admin: {selectedUser.is_admin ? 'Yes' : 'No'}</p>
          <p>Accounting: {selectedUser.is_accounting ? 'Yes' : 'No'}</p>
          <p>Pharmacies: {selectedUser.pharmacy_count}</p>
        </div>
      )}
    </div>
  );
}

export default UserRolesManager;
```

## Vue.js Example

```vue
<template>
  <div class="user-roles-manager">
    <h2>User Roles Management</h2>
    
    <table>
      <thead>
        <tr>
          <th>Username</th>
          <th>Email</th>
          <th>Admin</th>
          <th>Accounting</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.user_id">
          <td>{{ user.username }}</td>
          <td>{{ user.email }}</td>
          <td>
            <input
              type="checkbox"
              :checked="user.is_admin"
              @change="updateRoles(user.user_id, $event.target.checked, user.is_accounting, 'admin')"
            />
          </td>
          <td>
            <input
              type="checkbox"
              :checked="user.is_accounting"
              @change="updateRoles(user.user_id, user.is_admin, $event.target.checked, 'accounting')"
            />
          </td>
          <td>
            <button @click="viewUserDetails(user.user_id)">View</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  data() {
    return {
      users: [],
      loading: false,
      API_BASE: 'https://pharmacy-api-webservice.onrender.com'
    };
  },
  
  mounted() {
    this.loadUsers();
  },
  
  methods: {
    async loadUsers() {
      this.loading = true;
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${this.API_BASE}/admin/users`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to load users');
        }
        
        this.users = await response.json();
      } catch (error) {
        console.error('Error loading users:', error);
        alert('Failed to load users');
      } finally {
        this.loading = false;
      }
    },
    
    async updateRoles(userId, isAdmin, isAccounting, roleType) {
      try {
        const token = localStorage.getItem('token');
        const response = await fetch(`${this.API_BASE}/admin/users/${userId}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            is_admin: isAdmin,
            is_accounting: isAccounting
          })
        });
        
        if (!response.ok) {
          throw new Error('Failed to update roles');
        }
        
        // Reload users
        await this.loadUsers();
        alert(`${roleType} role updated successfully`);
      } catch (error) {
        console.error('Error updating roles:', error);
        alert('Failed to update roles');
      }
    },
    
    async viewUserDetails(userId) {
      // Implement user details view
      const token = localStorage.getItem('token');
      const response = await fetch(`${this.API_BASE}/admin/users/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      const user = await response.json();
      console.log('User details:', user);
      // Show in modal or navigate to details page
    }
  }
};
</script>
```

## Error Handling

```javascript
async function updateUserRoles(userId, roleUpdates) {
  try {
    const token = localStorage.getItem('token');
    const response = await fetch(`/admin/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(roleUpdates)
    });
    
    if (!response.ok) {
      const error = await response.json();
      
      switch (response.status) {
        case 401:
          // Token expired or invalid
          localStorage.removeItem('token');
          window.location.href = '/login';
          break;
        case 403:
          // Not an admin user
          alert('Access denied. Admin access required.');
          break;
        case 404:
          alert(`User ID ${userId} not found`);
          break;
        case 400:
          alert(`Validation error: ${error.detail}`);
          break;
        default:
          alert('Failed to update user roles');
      }
      throw new Error(error.detail || 'Update failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error updating user roles:', error);
    throw error;
  }
}
```

## Summary

### Key Endpoints for Role Management:

1. **GET `/admin/users`** - List all users with their roles
2. **GET `/admin/users/{user_id}`** - Get user details including roles
3. **POST `/admin/users`** - Create user with roles (`is_admin`, `is_accounting`)
4. **PUT `/admin/users/{user_id}`** - Update user roles (`is_admin`, `is_accounting`)

### Important Notes:

- Only admin users (`is_admin: true`) can manage roles
- Roles are independent - a user can have admin, accounting, both, or neither
- Pharmacy access is separate from roles
- Always check `is_admin` before showing admin UI
- Store user roles from login response for quick access checks

### Role Combinations:

| Admin | Accounting | Capabilities |
|-------|------------|--------------|
| ✓ | ✓ | Full access (admin + accounting) |
| ✓ | ✗ | Admin access only |
| ✗ | ✓ | Accounting access only |
| ✗ | ✗ | Standard user (pharmacy access only) |

