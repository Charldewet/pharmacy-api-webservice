# Admin API - Quick Reference Card

## Authentication
- **Required:** Bearer token in `Authorization` header
- **Access:** Only user_id 2 (Charl) can access
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
  can_write?: boolean
}
→ Returns: UserDetail
```

### Update User
```
PUT /admin/users/{user_id}
Body: {
  email?: string,
  password?: string,
  is_active?: boolean
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
if (currentUser.user_id !== 2) {
  // Hide admin UI or redirect
}
```

