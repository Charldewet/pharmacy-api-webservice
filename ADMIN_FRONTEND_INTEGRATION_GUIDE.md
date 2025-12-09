# Admin User Management - Frontend Integration Guide

## Overview

This guide provides detailed instructions for integrating the User Management Admin interface into your existing web application. The admin interface allows managing users, passwords, and pharmacy access. **Only the user "Charl" (user_id: 2) can access these endpoints.**

## Prerequisites

- Existing authentication system (JWT tokens)
- Current user information available in your app
- API base URL: `https://pharmacy-api-webservice.onrender.com` (or your API URL)

---

## Step 1: Check if Current User is Charl

Before showing the admin interface, verify that the current logged-in user is Charl.

### Method 1: Check User ID

```javascript
// After login, check if user_id === 2
const currentUser = getCurrentUser(); // Your existing method to get current user
const isCharl = currentUser.user_id === 2;

if (!isCharl) {
  // Redirect or show access denied
  console.error('Access denied. Only Charl can access admin panel.');
  return;
}
```

### Method 2: Check Username

```javascript
const currentUser = getCurrentUser();
const isCharl = currentUser.username === 'Charl';

if (!isCharl) {
  // Redirect or show access denied
  return;
}
```

**Recommendation:** Use user_id check (Method 1) as it's more reliable.

---

## Step 2: API Endpoints

All admin endpoints require:
- **Authentication:** Bearer token in Authorization header
- **Authorization:** Only user_id 2 (Charl) can access
- **Base URL:** `/admin`

### Endpoint Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List all users |
| GET | `/admin/users/{user_id}` | Get user details |
| POST | `/admin/users` | Create new user |
| PUT | `/admin/users/{user_id}` | Update user |
| POST | `/admin/users/{user_id}/pharmacies` | Grant pharmacy access |
| DELETE | `/admin/users/{user_id}/pharmacies/{pharmacy_id}` | Revoke pharmacy access |
| GET | `/admin/pharmacies` | List all pharmacies |

---

## Step 3: API Request/Response Formats

### 1. List All Users

**Request:**
```javascript
GET /admin/users
Headers: {
  Authorization: `Bearer ${token}`
}
```

**Response:**
```json
[
  {
    "user_id": 1,
    "username": "user",
    "email": "user@example.com",
    "is_active": true,
    "created_at": "2025-08-26T07:21:16.306755+00:00",
    "pharmacy_count": 5
  },
  {
    "user_id": 2,
    "username": "Charl",
    "email": "charl@example.com",
    "is_active": true,
    "created_at": "2025-08-28T09:33:49.351014+00:00",
    "pharmacy_count": 6
  }
]
```

**JavaScript Example:**
```javascript
async function fetchUsers() {
  const token = getAuthToken(); // Your existing method
  const response = await fetch(`${API_BASE_URL}/admin/users`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (response.status === 401 || response.status === 403) {
    throw new Error('Access denied. Only Charl can access admin panel.');
  }
  
  if (!response.ok) {
    throw new Error('Failed to fetch users');
  }
  
  return await response.json();
}
```

---

### 2. Get User Details

**Request:**
```javascript
GET /admin/users/{user_id}
Headers: {
  Authorization: `Bearer ${token}`
}
```

**Response:**
```json
{
  "user_id": 2,
  "username": "Charl",
  "email": "charl@example.com",
  "is_active": true,
  "created_at": "2025-08-28T09:33:49.351014+00:00",
  "pharmacies": [
    {
      "pharmacy_id": 1,
      "pharmacy_name": "TLC REITZ",
      "can_read": true,
      "can_write": false
    },
    {
      "pharmacy_id": 101,
      "pharmacy_name": "TLC UMDONI",
      "can_read": true,
      "can_write": true
    }
  ]
}
```

**JavaScript Example:**
```javascript
async function fetchUserDetails(userId) {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch user details');
  }
  
  return await response.json();
}
```

---

### 3. Create New User

**Request:**
```javascript
POST /admin/users
Headers: {
  Authorization: `Bearer ${token}`,
  Content-Type: `application/json`
}
Body: {
  "username": "NewUser",
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "pharmacy_ids": [1, 2, 100],  // Optional: array of pharmacy IDs
  "can_write": false  // Optional: default false
}
```

**Response:**
```json
{
  "user_id": 8,
  "username": "NewUser",
  "email": "newuser@example.com",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00.000000+00:00",
  "pharmacies": [
    {
      "pharmacy_id": 1,
      "pharmacy_name": "TLC REITZ",
      "can_read": true,
      "can_write": false
    }
  ]
}
```

**JavaScript Example:**
```javascript
async function createUser(userData) {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}/admin/users`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      username: userData.username,
      email: userData.email,
      password: userData.password,
      pharmacy_ids: userData.pharmacyIds || null,
      can_write: userData.canWrite || false
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create user');
  }
  
  return await response.json();
}

// Usage
try {
  const newUser = await createUser({
    username: 'NewUser',
    email: 'newuser@example.com',
    password: 'SecurePassword123!',
    pharmacyIds: [1, 2, 100],
    canWrite: false
  });
  console.log('User created:', newUser);
} catch (error) {
  console.error('Error creating user:', error.message);
}
```

---

### 4. Update User

**Request:**
```javascript
PUT /admin/users/{user_id}
Headers: {
  Authorization: `Bearer ${token}`,
  Content-Type: `application/json`
}
Body: {
  "email": "updated@example.com",  // Optional
  "password": "NewPassword123!",     // Optional (leave blank to keep current)
  "is_active": true                   // Optional
}
```

**Response:**
```json
{
  "user_id": 2,
  "username": "Charl",
  "email": "updated@example.com",
  "is_active": true,
  "created_at": "2025-08-28T09:33:49.351014+00:00",
  "pharmacies": [...]
}
```

**JavaScript Example:**
```javascript
async function updateUser(userId, updates) {
  const token = getAuthToken();
  const body = {};
  
  if (updates.email) body.email = updates.email;
  if (updates.password) body.password = updates.password;
  if (updates.isActive !== undefined) body.is_active = updates.isActive;
  
  const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update user');
  }
  
  return await response.json();
}

// Usage
try {
  const updated = await updateUser(2, {
    email: 'newemail@example.com',
    password: 'NewPassword123!',
    isActive: true
  });
  console.log('User updated:', updated);
} catch (error) {
  console.error('Error updating user:', error.message);
}
```

---

### 5. Grant Pharmacy Access

**Request:**
```javascript
POST /admin/users/{user_id}/pharmacies
Headers: {
  Authorization: `Bearer ${token}`,
  Content-Type: `application/json`
}
Body: {
  "pharmacy_id": 101,
  "can_read": true,
  "can_write": false
}
```

**Response:**
```json
{
  "user_id": 2,
  "username": "Charl",
  "email": "charl@example.com",
  "is_active": true,
  "created_at": "2025-08-28T09:33:49.351014+00:00",
  "pharmacies": [
    // ... existing pharmacies ...
    {
      "pharmacy_id": 101,
      "pharmacy_name": "TLC UMDONI",
      "can_read": true,
      "can_write": false
    }
  ]
}
```

**JavaScript Example:**
```javascript
async function grantPharmacyAccess(userId, pharmacyId, canRead = true, canWrite = false) {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/pharmacies`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      pharmacy_id: pharmacyId,
      can_read: canRead,
      can_write: canWrite
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to grant pharmacy access');
  }
  
  return await response.json();
}

// Usage
try {
  const updated = await grantPharmacyAccess(2, 101, true, false);
  console.log('Pharmacy access granted:', updated);
} catch (error) {
  console.error('Error granting access:', error.message);
}
```

---

### 6. Revoke Pharmacy Access

**Request:**
```javascript
DELETE /admin/users/{user_id}/pharmacies/{pharmacy_id}
Headers: {
  Authorization: `Bearer ${token}`
}
```

**Response:**
```json
{
  "user_id": 2,
  "username": "Charl",
  "email": "charl@example.com",
  "is_active": true,
  "created_at": "2025-08-28T09:33:49.351014+00:00",
  "pharmacies": [
    // Pharmacy access removed from list
  ]
}
```

**JavaScript Example:**
```javascript
async function revokePharmacyAccess(userId, pharmacyId) {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/pharmacies/${pharmacyId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to revoke pharmacy access');
  }
  
  return await response.json();
}

// Usage
try {
  const updated = await revokePharmacyAccess(2, 101);
  console.log('Pharmacy access revoked:', updated);
} catch (error) {
  console.error('Error revoking access:', error.message);
}
```

---

### 7. List All Pharmacies

**Request:**
```javascript
GET /admin/pharmacies
Headers: {
  Authorization: `Bearer ${token}`
}
```

**Response:**
```json
[
  {
    "pharmacy_id": 1,
    "name": "TLC REITZ",
    "is_active": true
  },
  {
    "pharmacy_id": 2,
    "name": "TLC WINTERTON",
    "is_active": true
  },
  {
    "pharmacy_id": 100,
    "name": "TLC GROUP",
    "is_active": true
  },
  {
    "pharmacy_id": 101,
    "name": "TLC UMDONI",
    "is_active": true
  }
]
```

**JavaScript Example:**
```javascript
async function fetchPharmacies() {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}/admin/pharmacies`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch pharmacies');
  }
  
  return await response.json();
}
```

---

## Step 4: Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "detail": "Missing Authorization header"
}
```

**403 Forbidden:**
```json
{
  "detail": "Admin access restricted to Charl only"
}
```

**404 Not Found:**
```json
{
  "detail": "User ID 999 not found"
}
```

**400 Bad Request:**
```json
{
  "detail": "Username or email already exists"
}
```

### Error Handling Example

```javascript
async function handleApiCall(apiCall) {
  try {
    const response = await apiCall();
    
    if (response.status === 401) {
      // Token expired or invalid
      logout(); // Your logout function
      redirectToLogin();
      return;
    }
    
    if (response.status === 403) {
      // Not Charl
      showError('Access denied. Only Charl can access admin panel.');
      return;
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    showError(error.message || 'An error occurred');
    throw error;
  }
}
```

---

## Step 5: UI Components Recommendations

### 1. User List Table

```jsx
// React example
function UserList() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchUsers()
      .then(setUsers)
      .catch(handleError)
      .finally(() => setLoading(false));
  }, []);
  
  if (loading) return <LoadingSpinner />;
  
  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Username</th>
          <th>Email</th>
          <th>Status</th>
          <th>Pharmacies</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {users.map(user => (
          <tr key={user.user_id}>
            <td>{user.user_id}</td>
            <td>{user.username}</td>
            <td>{user.email}</td>
            <td>
              <Badge active={user.is_active}>
                {user.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </td>
            <td>{user.pharmacy_count}</td>
            <td>
              <button onClick={() => viewUser(user.user_id)}>View</button>
              <button onClick={() => editUser(user.user_id)}>Edit</button>
              <button onClick={() => grantAccess(user.user_id)}>Grant Access</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### 2. Create User Form

```jsx
function CreateUserForm({ onSuccess }) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    pharmacyIds: [],
    canWrite: false
  });
  
  const [pharmacies, setPharmacies] = useState([]);
  
  useEffect(() => {
    fetchPharmacies().then(setPharmacies);
  }, []);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const newUser = await createUser(formData);
      onSuccess(newUser);
      resetForm();
    } catch (error) {
      showError(error.message);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Username"
        value={formData.username}
        onChange={(e) => setFormData({...formData, username: e.target.value})}
        required
      />
      <input
        type="email"
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({...formData, email: e.target.value})}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={formData.password}
        onChange={(e) => setFormData({...formData, password: e.target.value})}
        required
      />
      <div>
        <label>Grant Pharmacy Access:</label>
        {pharmacies.filter(p => p.is_active).map(pharmacy => (
          <label key={pharmacy.pharmacy_id}>
            <input
              type="checkbox"
              checked={formData.pharmacyIds.includes(pharmacy.pharmacy_id)}
              onChange={(e) => {
                if (e.target.checked) {
                  setFormData({
                    ...formData,
                    pharmacyIds: [...formData.pharmacyIds, pharmacy.pharmacy_id]
                  });
                } else {
                  setFormData({
                    ...formData,
                    pharmacyIds: formData.pharmacyIds.filter(id => id !== pharmacy.pharmacy_id)
                  });
                }
              }}
            />
            {pharmacy.name}
          </label>
        ))}
      </div>
      <label>
        <input
          type="checkbox"
          checked={formData.canWrite}
          onChange={(e) => setFormData({...formData, canWrite: e.target.checked})}
        />
        Grant Write Access
      </label>
      <button type="submit">Create User</button>
    </form>
  );
}
```

### 3. User Details Modal

```jsx
function UserDetailsModal({ userId, onClose }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchUserDetails(userId)
      .then(setUser)
      .catch(handleError)
      .finally(() => setLoading(false));
  }, [userId]);
  
  if (loading) return <LoadingSpinner />;
  if (!user) return <div>User not found</div>;
  
  return (
    <Modal onClose={onClose}>
      <h2>{user.username}</h2>
      <p>Email: {user.email}</p>
      <p>Status: {user.is_active ? 'Active' : 'Inactive'}</p>
      
      <h3>Pharmacy Access:</h3>
      {user.pharmacies.length === 0 ? (
        <p>No pharmacy access granted.</p>
      ) : (
        <ul>
          {user.pharmacies.map(pharmacy => (
            <li key={pharmacy.pharmacy_id}>
              {pharmacy.pharmacy_name}
              <span>({pharmacy.can_read ? 'READ' : ''} {pharmacy.can_write ? 'WRITE' : ''})</span>
              <button onClick={() => revokeAccess(user.user_id, pharmacy.pharmacy_id)}>
                Revoke
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
```

---

## Step 6: Route Protection

### React Router Example

```jsx
import { Navigate } from 'react-router-dom';

function AdminRoute({ children }) {
  const currentUser = useAuth(); // Your auth hook
  
  if (!currentUser) {
    return <Navigate to="/login" />;
  }
  
  if (currentUser.user_id !== 2) {
    return <Navigate to="/" />; // Redirect to home
  }
  
  return children;
}

// Usage
<Route
  path="/admin"
  element={
    <AdminRoute>
      <AdminPanel />
    </AdminRoute>
  }
/>
```

### Vue Router Example

```javascript
router.beforeEach((to, from, next) => {
  if (to.path === '/admin') {
    const currentUser = getCurrentUser();
    
    if (!currentUser) {
      next('/login');
      return;
    }
    
    if (currentUser.user_id !== 2) {
      next('/'); // Redirect to home
      return;
    }
  }
  
  next();
});
```

---

## Step 7: Complete Example Service

```javascript
// adminService.js
const API_BASE_URL = 'https://pharmacy-api-webservice.onrender.com';

class AdminService {
  constructor(getAuthToken) {
    this.getAuthToken = getAuthToken;
  }
  
  getHeaders() {
    return {
      'Authorization': `Bearer ${this.getAuthToken()}`,
      'Content-Type': 'application/json'
    };
  }
  
  async listUsers() {
    const response = await fetch(`${API_BASE_URL}/admin/users`, {
      headers: this.getHeaders()
    });
    this.checkResponse(response);
    return await response.json();
  }
  
  async getUserDetails(userId) {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
      headers: this.getHeaders()
    });
    this.checkResponse(response);
    return await response.json();
  }
  
  async createUser(userData) {
    const response = await fetch(`${API_BASE_URL}/admin/users`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        username: userData.username,
        email: userData.email,
        password: userData.password,
        pharmacy_ids: userData.pharmacyIds || null,
        can_write: userData.canWrite || false
      })
    });
    this.checkResponse(response);
    return await response.json();
  }
  
  async updateUser(userId, updates) {
    const body = {};
    if (updates.email) body.email = updates.email;
    if (updates.password) body.password = updates.password;
    if (updates.isActive !== undefined) body.is_active = updates.isActive;
    
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(body)
    });
    this.checkResponse(response);
    return await response.json();
  }
  
  async grantPharmacyAccess(userId, pharmacyId, canRead = true, canWrite = false) {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/pharmacies`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        pharmacy_id: pharmacyId,
        can_read: canRead,
        can_write: canWrite
      })
    });
    this.checkResponse(response);
    return await response.json();
  }
  
  async revokePharmacyAccess(userId, pharmacyId) {
    const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/pharmacies/${pharmacyId}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    });
    this.checkResponse(response);
    return await response.json();
  }
  
  async listPharmacies() {
    const response = await fetch(`${API_BASE_URL}/admin/pharmacies`, {
      headers: this.getHeaders()
    });
    this.checkResponse(response);
    return await response.json();
  }
  
  checkResponse(response) {
    if (response.status === 401) {
      throw new Error('Unauthorized. Please log in again.');
    }
    if (response.status === 403) {
      throw new Error('Access denied. Only Charl can access admin panel.');
    }
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
  }
}

export default AdminService;
```

---

## Step 8: Testing Checklist

- [ ] Verify only Charl (user_id: 2) can access admin routes
- [ ] Test listing all users
- [ ] Test viewing user details
- [ ] Test creating a new user
- [ ] Test updating user email
- [ ] Test updating user password
- [ ] Test updating user active status
- [ ] Test granting pharmacy access (read-only)
- [ ] Test granting pharmacy access (read+write)
- [ ] Test revoking pharmacy access
- [ ] Test error handling (401, 403, 404, 400)
- [ ] Test with expired token
- [ ] Test with non-Charl user (should be denied)

---

## Summary

1. **Check if user is Charl** before showing admin interface
2. **Use existing authentication** - no new login needed
3. **All endpoints require Bearer token** in Authorization header
4. **Only user_id 2 (Charl)** can access admin endpoints
5. **Handle errors appropriately** (401, 403, 404, 400)
6. **Use the provided API endpoints** for all user management operations

The backend is ready and all endpoints are functional. Your frontend team can integrate these APIs into your existing web application using your preferred framework (React, Vue, Angular, etc.).



