# 📢 Broadcast Notifications - Usage Guide

## Overview

This guide shows you how to send broadcast notifications to your pharmacy app users using the TLC PharmaSight API.

## 🔑 Prerequisites

- **API Endpoint**: `https://pharmacy-api-webservice.onrender.com`
- **API Key**: `super-secret-long-random-string`
- **Authentication**: Use `Authorization: Bearer {API_KEY}` header

## 📋 Quick Reference

### 1. Send to All Users
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TLC PharmaSight",
    "body": "Your message here",
    "targetAudience": "all"
  }'
```

### 2. Send to Specific Pharmacy Users
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast/pharmacy/1 \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "REITZ APTEEK - Announcement",
    "body": "Your pharmacy-specific message here"
  }'
```

### 3. Send to Users with Read Access
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast/access/read \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Reports Available",
    "body": "New reports are ready for review"
  }'
```

### 4. Send to Users with Write Access (Admins)
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast/access/write \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Admin Alert",
    "body": "Admin action required"
  }'
```

## 🎯 Common Use Cases

### Marketing Announcement
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "🎉 Special Promotion",
    "body": "20% off all vitamins this week! Check the app for details.",
    "targetAudience": "all",
    "data": {
      "type": "PROMOTION",
      "category": "marketing"
    }
  }'
```

### System Maintenance Notice
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "⚠️ Maintenance Notice",
    "body": "System maintenance scheduled tonight 2-4 AM. App may be temporarily unavailable.",
    "targetAudience": "all",
    "data": {
      "type": "MAINTENANCE",
      "category": "system"
    }
  }'
```

### Pharmacy-Specific Alert
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast/pharmacy/1 \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "REITZ APTEEK - Stock Alert",
    "body": "New inventory has arrived. Please check the latest reports.",
    "data": {
      "type": "STOCK_ALERT",
      "category": "operations"
    }
  }'
```

### Daily Reminder
```bash
curl -X POST https://pharmacy-api-webservice.onrender.com/push/broadcast \
  -H "Authorization: Bearer super-secret-long-random-string" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "TLC PharmaSight",
    "body": "Keep your eye on the app for daily updates",
    "targetAudience": "all",
    "data": {
      "type": "REMINDER",
      "category": "general"
    }
  }'
```

## 📊 Pharmacy IDs Reference

| Pharmacy ID | Name |
|-------------|------|
| `1` | REITZ APTEEK |
| `2` | TLC PHARMACY WINTERTON |

## 📋 Message Guidelines

### ✅ Best Practices
- **Title**: Keep under 50 characters (shows fully on mobile)
- **Body**: Keep under 200 characters for best display
- **Timing**: Send during business hours for better engagement
- **Frequency**: Don't spam - max 2-3 broadcasts per day

### 📝 Title Suggestions
- `"TLC PharmaSight"` - General announcements
- `"REITZ APTEEK - [Topic]"` - Pharmacy-specific
- `"📊 Reports Update"` - Data/reporting
- `"⚠️ Important Notice"` - Urgent messages
- `"🎉 Promotion Alert"` - Marketing

### 📱 Message Categories
- **PROMOTION** - Marketing and sales
- **MAINTENANCE** - System updates
- **STOCK_ALERT** - Inventory notices
- **REPORTS** - Data and analytics
- **REMINDER** - General reminders
- **URGENT** - Critical alerts

## 🔍 Checking Results

### View Recent Broadcasts
```bash
psql "postgresql://pharmacy_user:PzL1HpYNaYOrmcfImjeZm8LitHTd4d7F@dpg-d28vb1muk2gs73frrns0-a.oregon-postgres.render.com/pharmacy_reports" -c "SELECT id, title, target_audience, sent_count, failed_count, created_at FROM pharma.broadcast_notifications ORDER BY created_at DESC LIMIT 10;"
```

### Response Format
Every broadcast returns:
```json
{
  "success": true,
  "sent": 5,
  "failed": 0,
  "totalDevices": 5,
  "message": null
}
```

## 🚨 Troubleshooting

### Common Issues

#### 1. "Invalid or missing API key"
- Check your API key is correct: `super-secret-long-random-string`
- Ensure you're using `Authorization: Bearer` header

#### 2. "Broadcast failed"
- Check your JSON format is valid
- Ensure required fields (`title`, `body`) are included

#### 3. "No devices found for target audience"
- Normal for write access if no admin users exist
- Check if users have registered devices for the app

### Testing Connection
```bash
# Test API is running
curl https://pharmacy-api-webservice.onrender.com/health

# Should return: {"status":"healthy"}
```

## 📈 Analytics

Track your broadcast performance by checking:
- **sent_count**: How many notifications were delivered
- **failed_count**: How many failed to send
- **target_audience**: Who you targeted
- **created_at**: When you sent it

## 🔐 Security Notes

- ✅ API key authentication required
- ✅ Only authorized personnel should have access
- ✅ All broadcasts are logged in the database
- ✅ Use HTTPS for all requests

## 📞 Support

If you need help with broadcast notifications:
1. Check this README first
2. Test with a simple broadcast to all users
3. Check the database logs for any errors
4. Verify your API key is working with `/health` endpoint

---

**🎯 Ready to send your first broadcast? Use the "Send to All Users" example above!** 