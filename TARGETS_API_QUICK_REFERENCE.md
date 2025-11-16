# Targets API - Quick Reference

## Endpoints

### Get Targets
```
GET /admin/pharmacies/{pharmacy_id}/targets?month=YYYY-MM
→ Returns: {pharmacy_id, month, targets: [{date, value}]}
```

### Save/Update Targets
```
POST /admin/pharmacies/{pharmacy_id}/targets?month=YYYY-MM
Body: { "YYYY-MM-DD": value, ... }
→ Returns: {success, saved_count, pharmacy_id, month}
```

### Delete Target
```
DELETE /admin/pharmacies/{pharmacy_id}/targets/{YYYY-MM-DD}
→ Returns: {success, message}
```

## Quick Example

```javascript
// Get targets
const data = await fetch(
  `/admin/pharmacies/1/targets?month=2025-11`,
  { headers: { 'Authorization': `Bearer ${token}` } }
).then(r => r.json());

// Save targets
await fetch(
  `/admin/pharmacies/1/targets?month=2025-11`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      "2025-11-01": 8500.00,
      "2025-11-15": 10000.00
    })
  }
);
```

## Key Points

- ✅ Uses existing authentication (Bearer token)
- ✅ Checks pharmacy access automatically
- ✅ UPSERT: Updates existing, creates new
- ✅ Partial updates supported
- ✅ Month format: `YYYY-MM` (e.g., "2025-11")
- ✅ Date format: `YYYY-MM-DD` (e.g., "2025-11-15")

## Error Codes

- `400`: Bad request (invalid format, date outside month, negative value)
- `401`: Unauthorized (missing/invalid token)
- `403`: Forbidden (no pharmacy access)
- `404`: Not found (pharmacy/target doesn't exist)

