# Admin API - Quick Reference Card

## Authentication
- **Required:** Bearer token in `Authorization` header
- **Access:** Only users with `is_admin: true` can access
- **Base URL:** `/admin`

## Endpoints

### List Users
```
GET /admin/users
→ Returns: Array of UserListItem
```

### Get User Details
```
GET /admin/users/{user_id}
→ Returns: UserDetail with pharmacy access list
```

### Create User
```
POST /admin/users
Body: {
  username: string,
  email: string,
  password: string,
  pharmacy_ids?: number[],
  can_write?: boolean,
  is_admin?: boolean,        // NEW: Grant admin role
  is_accounting?: boolean    // NEW: Grant accounting role
}
→ Returns: UserDetail
```

### Update User
```
PUT /admin/users/{user_id}
Body: {
  email?: string,
  password?: string,
  is_active?: boolean,
  is_admin?: boolean,        // NEW: Update admin role
  is_accounting?: boolean    // NEW: Update accounting role
}
→ Returns: UserDetail
```

### Grant Pharmacy Access
```
POST /admin/users/{user_id}/pharmacies
Body: {
  pharmacy_id: number,
  can_read: boolean,
  can_write: boolean
}
→ Returns: UserDetail
```

### Revoke Pharmacy Access
```
DELETE /admin/users/{user_id}/pharmacies/{pharmacy_id}
→ Returns: UserDetail
```

### List Pharmacies
```
GET /admin/pharmacies
→ Returns: Array of {pharmacy_id, name, is_active}
```

## Error Codes
- **401:** Unauthorized (missing/invalid token)
- **403:** Forbidden (not Charl)
- **404:** Not Found (user/pharmacy doesn't exist)
- **400:** Bad Request (validation error)

## Frontend Check
```javascript
// Before showing admin UI, check:
const currentUser = getCurrentUser();
if (!currentUser.is_admin) {
  // Hide admin UI or redirect
}

// Check roles from login response:
const user = loginResponse.user;
const isAdmin = user.is_admin;        // true/false
const isAccounting = user.is_accounting; // true/false
```



