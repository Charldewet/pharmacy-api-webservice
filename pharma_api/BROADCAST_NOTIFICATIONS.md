# Broadcast Notifications API

## Overview

The broadcast notification system allows sending push notifications to multiple users based on different targeting criteria. It integrates with the existing push notification infrastructure and works with both Expo and Apple APNs.

## Database Schema

A new table `pharma.broadcast_notifications` tracks all broadcast notifications:

```sql
CREATE TABLE pharma.broadcast_notifications (
  id                bigserial PRIMARY KEY,
  title             text NOT NULL,
  body              text NOT NULL,
  data              jsonb,
  target_audience   text NOT NULL CHECK (target_audience IN ('all', 'pharmacy_specific', 'access_based')),
  pharmacy_ids      integer[],
  access_type       text CHECK (access_type IN ('read', 'write')),
  sent_count        integer DEFAULT 0,
  failed_count      integer DEFAULT 0,
  created_by        text,
  created_at        timestamptz NOT NULL DEFAULT now()
);
```

## API Endpoints

All broadcast endpoints require API key authentication using the `Authorization` header with `Bearer TOKEN` or `X-API-Key` header.

### 1. Broadcast to All Users

**POST** `/push/broadcast`

Send a notification to all registered devices.

```json
{
  "title": "TLC PharmaSight - New Promotion!",
  "body": "Check out our new features and promotions",
  "data": {
    "type": "PROMOTION",
    "category": "marketing"
  },
  "targetAudience": "all"
}
```

### 2. Broadcast to Specific Pharmacy

**POST** `/push/broadcast/pharmacy/{pharmacy_id}`

Send a notification to users with access to a specific pharmacy.

```json
{
  "title": "REITZ APTEEK - Maintenance Notice",
  "body": "System maintenance tonight 2-4 AM",
  "data": {
    "type": "MAINTENANCE",
    "category": "system"
  }
}
```

### 3. Broadcast to Users with Read Access

**POST** `/push/broadcast/access/read`

Send a notification to users with read access to specified pharmacies.

```json
{
  "title": "New Reports Available",
  "body": "Monthly reports are ready for review",
  "data": {
    "type": "REPORTS",
    "category": "updates"
  },
  "pharmacyIds": [1, 2]
}
```

### 4. Broadcast to Users with Write Access

**POST** `/push/broadcast/access/write`

Send a notification to users with write access to specified pharmacies.

```json
{
  "title": "Admin Alert",
  "body": "Please review and approve pending changes",
  "data": {
    "type": "ADMIN_ACTION",
    "category": "urgent"
  },
  "pharmacyIds": [1, 2]
}
```

## Response Format

All endpoints return the same response format:

```json
{
  "success": true,
  "sent": 15,
  "failed": 2,
  "totalDevices": 17,
  "message": "Optional status message"
}
```

## Usage Examples

### Send to All Users

```bash
curl -X POST https://your-api.com/push/broadcast \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TLC PharmaSight - New Promotion!",
    "body": "Check out our new features and promotions",
    "data": {
      "type": "PROMOTION",
      "category": "marketing"
    },
    "targetAudience": "all"
  }'
```

### Send to Specific Pharmacy (REITZ APTEEK - pharmacy_id = 1)

```bash
curl -X POST https://your-api.com/push/broadcast/pharmacy/1 \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "REITZ APTEEK - Maintenance Notice",
    "body": "System maintenance tonight 2-4 AM",
    "data": {
      "type": "MAINTENANCE",
      "category": "system"
    }
  }'
```

### Send to Admin Users (Write Access)

```bash
curl -X POST https://your-api.com/push/broadcast/access/write \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Admin Alert",
    "body": "Monthly reports are ready for review",
    "data": {
      "type": "ADMIN_ACTION",
      "category": "reports"
    }
  }'
```

## Key Features

✅ **Uses existing device registration infrastructure**  
✅ **Uses existing push notification sending functions**  
✅ **Supports both Expo and Apple APNs automatically**  
✅ **Tracks broadcast history and statistics**  
✅ **Flexible targeting based on pharmacy access**  
✅ **API key authentication for security**  
✅ **Mobile app automatically handles broadcast notifications**  

## Targeting Logic

- **all**: Sends to all active registered devices
- **pharmacy_specific**: Sends to users with any access to specified pharmacies
- **access_based**: Sends to users with specific access type (read/write) to specified pharmacies

## Integration Notes

- Broadcasts are sent in batches of 100 notifications for optimal performance
- Failed notification attempts are tracked and logged
- Uses the same encryption/decryption for push tokens as existing notifications
- Compatible with existing mobile app notification handling
- Notification data includes `"type": "BROADCAST"` for mobile app filtering 