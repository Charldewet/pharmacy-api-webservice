# User Pharmacy Access - Frontend Guide

Complete guide for viewing and managing user-pharmacy access permissions on the frontend.

## API Endpoints

### 1. Get All Users with Pharmacy Access (Recommended)

**Endpoint:** `GET /admin/users/access`

**Authentication:** API key or JWT (admin only)

**Description:** Returns all users with their complete pharmacy access details (read/write permissions) in a single call.

**Example Request:**
```javascript
const response = await fetch(
  'https://pharmacy-api-webservice.onrender.com/admin/users/access',
  {
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    }
  }
);

const users = await response.json();
```

**Response:**
```json
[
  {
    "user_id": 1,
    "username": "john",
    "email": "john@example.com",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "pharmacies": [
      {
        "pharmacy_id": 1,
        "pharmacy_name": "REITZ APTEEK",
        "can_read": true,
        "can_write": true
      },
      {
        "pharmacy_id": 2,
        "pharmacy_name": "Another Pharmacy",
        "can_read": true,
        "can_write": false
      }
    ]
  },
  {
    "user_id": 2,
    "username": "Charl",
    "email": "charl@example.com",
    "is_active": true,
    "created_at": "2025-01-10T08:00:00Z",
    "pharmacies": []
  }
]
```

---

### 2. Get Single User Details (Alternative)

**Endpoint:** `GET /admin/users/{user_id}`

**Authentication:** API key or JWT (admin only)

**Description:** Get detailed information about a specific user including their pharmacy access.

**Example:**
```javascript
const response = await fetch(
  'https://pharmacy-api-webservice.onrender.com/admin/users/1',
  {
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    }
  }
);

const user = await response.json();
```

**Response:**
```json
{
  "user_id": 1,
  "username": "john",
  "email": "john@example.com",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00Z",
  "pharmacies": [
    {
      "pharmacy_id": 1,
      "pharmacy_name": "REITZ APTEEK",
      "can_read": true,
      "can_write": true
    }
  ]
}
```

---

### 3. List All Users (Summary)

**Endpoint:** `GET /admin/users`

**Authentication:** API key or JWT (admin only)

**Description:** Get a summary list of all users with pharmacy count (but not detailed access).

**Example:**
```javascript
const response = await fetch(
  'https://pharmacy-api-webservice.onrender.com/admin/users',
  {
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    }
  }
);

const users = await response.json();
```

**Response:**
```json
[
  {
    "user_id": 1,
    "username": "john",
    "email": "john@example.com",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "pharmacy_count": 2
  }
]
```

---

## Frontend Implementation Examples

### React Component - Display User Pharmacy Access Table

```jsx
import React, { useState, useEffect } from 'react';

function UserPharmacyAccessTable() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadUsers();
  }, []);

  async function loadUsers() {
    try {
      setLoading(true);
      const response = await fetch(
        'https://pharmacy-api-webservice.onrender.com/admin/users/access',
        {
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to load users');
      }

      const data = await response.json();
      setUsers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="user-pharmacy-access-table">
      <h2>User Pharmacy Access</h2>
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Email</th>
            <th>Status</th>
            <th>Pharmacies</th>
            <th>Permissions</th>
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.user_id}>
              <td>{user.username}</td>
              <td>{user.email}</td>
              <td>
                <span className={user.is_active ? 'active' : 'inactive'}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td>
                {user.pharmacies.length === 0 ? (
                  <span className="no-access">No access</span>
                ) : (
                  <ul>
                    {user.pharmacies.map(pharm => (
                      <li key={pharm.pharmacy_id}>
                        {pharm.pharmacy_name}
                      </li>
                    ))}
                  </ul>
                )}
              </td>
              <td>
                {user.pharmacies.length === 0 ? (
                  <span>-</span>
                ) : (
                  <ul>
                    {user.pharmacies.map(pharm => (
                      <li key={pharm.pharmacy_id}>
                        <span className={pharm.can_read ? 'read' : 'no-read'}>
                          {pharm.can_read ? '✓ Read' : '✗ Read'}
                        </span>
                        {' / '}
                        <span className={pharm.can_write ? 'write' : 'no-write'}>
                          {pharm.can_write ? '✓ Write' : '✗ Write'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default UserPharmacyAccessTable;
```

---

### React Component - Matrix View (Users vs Pharmacies)

```jsx
import React, { useState, useEffect } from 'react';

function UserPharmacyAccessMatrix() {
  const [users, setUsers] = useState([]);
  const [pharmacies, setPharmacies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      // Load users with access
      const usersResponse = await fetch(
        'https://pharmacy-api-webservice.onrender.com/admin/users/access',
        {
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );
      const usersData = await usersResponse.json();
      setUsers(usersData);

      // Load all pharmacies
      const pharmaciesResponse = await fetch(
        'https://pharmacy-api-webservice.onrender.com/admin/pharmacies',
        {
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
          }
        }
      );
      const pharmaciesData = await pharmaciesResponse.json();
      setPharmacies(pharmaciesData);
    } catch (err) {
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  }

  function getUserAccess(userId, pharmacyId) {
    const user = users.find(u => u.user_id === userId);
    if (!user) return null;
    
    const access = user.pharmacies.find(p => p.pharmacy_id === pharmacyId);
    if (!access) return null;
    
    return {
      can_read: access.can_read,
      can_write: access.can_write
    };
  }

  if (loading) return <div>Loading...</div>;

  return (
    <div className="access-matrix">
      <h2>User Pharmacy Access Matrix</h2>
      <table>
        <thead>
          <tr>
            <th>User</th>
            {pharmacies.map(pharm => (
              <th key={pharm.pharmacy_id}>{pharm.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {users.map(user => (
            <tr key={user.user_id}>
              <td>
                <div>{user.username}</div>
                <div className="email">{user.email}</div>
              </td>
              {pharmacies.map(pharm => {
                const access = getUserAccess(user.user_id, pharm.pharmacy_id);
                return (
                  <td key={pharm.pharmacy_id}>
                    {access ? (
                      <div className="access-badges">
                        {access.can_read && <span className="badge read">R</span>}
                        {access.can_write && <span className="badge write">W</span>}
                        {!access.can_read && <span className="badge none">-</span>}
                      </div>
                    ) : (
                      <span className="no-access">-</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default UserPharmacyAccessMatrix;
```

---

### Vue.js Component Example

```vue
<template>
  <div class="user-pharmacy-access">
    <h2>User Pharmacy Access</h2>
    
    <div v-if="loading">Loading...</div>
    <div v-else-if="error">Error: {{ error }}</div>
    <div v-else>
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Email</th>
            <th>Pharmacies</th>
            <th>Permissions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.user_id">
            <td>{{ user.username }}</td>
            <td>{{ user.email }}</td>
            <td>
              <ul v-if="user.pharmacies.length > 0">
                <li v-for="pharm in user.pharmacies" :key="pharm.pharmacy_id">
                  {{ pharm.pharmacy_name }}
                </li>
              </ul>
              <span v-else>No access</span>
            </td>
            <td>
              <ul v-if="user.pharmacies.length > 0">
                <li v-for="pharm in user.pharmacies" :key="pharm.pharmacy_id">
                  <span :class="{ 'has-access': pharm.can_read }">
                    {{ pharm.can_read ? '✓ Read' : '✗ Read' }}
                  </span>
                  /
                  <span :class="{ 'has-access': pharm.can_write }">
                    {{ pharm.can_write ? '✓ Write' : '✗ Write' }}
                  </span>
                </li>
              </ul>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UserPharmacyAccess',
  data() {
    return {
      users: [],
      loading: true,
      error: null
    };
  },
  async mounted() {
    await this.loadUsers();
  },
  methods: {
    async loadUsers() {
      try {
        this.loading = true;
        const response = await fetch(
          'https://pharmacy-api-webservice.onrender.com/admin/users/access',
          {
            headers: {
              'Authorization': `Bearer ${this.$store.state.apiKey}`,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to load users');
        }

        this.users = await response.json();
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>
```

---

### Vanilla JavaScript Example

```javascript
async function loadUserPharmacyAccess() {
  try {
    const response = await fetch(
      'https://pharmacy-api-webservice.onrender.com/admin/users/access',
      {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        }
      }
    );

    if (!response.ok) {
      throw new Error('Failed to load users');
    }

    const users = await response.json();
    
    // Display in table
    const tableBody = document.getElementById('access-table-body');
    tableBody.innerHTML = '';

    users.forEach(user => {
      const row = document.createElement('tr');
      
      // User info
      row.innerHTML = `
        <td>${user.username}</td>
        <td>${user.email}</td>
        <td>${user.is_active ? 'Active' : 'Inactive'}</td>
        <td>
          ${user.pharmacies.length === 0 
            ? '<span>No access</span>' 
            : user.pharmacies.map(p => p.pharmacy_name).join(', ')}
        </td>
        <td>
          ${user.pharmacies.length === 0 
            ? '-' 
            : user.pharmacies.map(p => 
                `${p.can_read ? '✓' : '✗'} Read / ${p.can_write ? '✓' : '✗'} Write`
              ).join('<br>')}
        </td>
      `;
      
      tableBody.appendChild(row);
    });
  } catch (error) {
    console.error('Error loading user pharmacy access:', error);
  }
}

// Call on page load
loadUserPharmacyAccess();
```

---

## CSS Styling Example

```css
.user-pharmacy-access-table {
  padding: 20px;
}

.user-pharmacy-access-table table {
  width: 100%;
  border-collapse: collapse;
}

.user-pharmacy-access-table th,
.user-pharmacy-access-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.user-pharmacy-access-table th {
  background-color: #f5f5f5;
  font-weight: bold;
}

.user-pharmacy-access-table .active {
  color: green;
  font-weight: bold;
}

.user-pharmacy-access-table .inactive {
  color: red;
}

.user-pharmacy-access-table .read,
.user-pharmacy-access-table .write {
  color: green;
}

.user-pharmacy-access-table .no-read,
.user-pharmacy-access-table .no-write {
  color: red;
}

.user-pharmacy-access-table .no-access {
  color: #999;
  font-style: italic;
}

.access-matrix table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.access-matrix th,
.access-matrix td {
  padding: 8px;
  border: 1px solid #ddd;
  text-align: center;
}

.access-matrix .badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: bold;
  margin: 2px;
}

.access-matrix .badge.read {
  background-color: #4caf50;
  color: white;
}

.access-matrix .badge.write {
  background-color: #2196f3;
  color: white;
}

.access-matrix .badge.none {
  background-color: #f44336;
  color: white;
}
```

---

## Summary

**Best Endpoint for Admin View:**
- **`GET /admin/users/access`** - Returns all users with complete pharmacy access details in one call

**Authentication:**
- Use API key: `Authorization: Bearer <your-api-key>`
- Or JWT token (must be admin user)

**Response Format:**
- Array of users
- Each user includes:
  - Basic info (user_id, username, email, is_active, created_at)
  - `pharmacies` array with:
    - `pharmacy_id`
    - `pharmacy_name`
    - `can_read` (boolean)
    - `can_write` (boolean)

**Use Cases:**
1. **Admin Dashboard** - Show all users and their access
2. **Access Matrix** - Display users vs pharmacies grid
3. **User Management** - View/edit user permissions
4. **Audit Trail** - See who has access to what

