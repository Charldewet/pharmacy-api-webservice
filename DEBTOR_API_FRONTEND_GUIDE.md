# Debtor Management API - Frontend Guide

Complete API reference for the debtor management system.

**Base URL**: `/pharmacies/{pharmacy_id}/debtors`

All endpoints require authentication via Bearer token in the `Authorization` header.

---

## Table of Contents

1. [Upload Debtor Report](#1-upload-debtor-report)
2. [Get Debtors List](#2-get-debtors-list)
3. [Get Statistics](#3-get-statistics)
4. [Send Email Reminders](#4-send-email-reminders)
5. [Send SMS Reminders](#5-send-sms-reminders)
6. [Download CSV](#6-download-csv)
7. [Download PDF](#7-download-pdf)
8. [Get Communication History](#8-get-communication-history)

---

## 1. Upload Debtor Report

Upload a PDF debtor report to extract and store debtor information.

**Endpoint**: `POST /pharmacies/{pharmacy_id}/debtors/upload`

**Authentication**: Required (Bearer token with write access)

**Request**:
- **Content-Type**: `multipart/form-data`
- **Body**: FormData with `file` field containing the PDF

**cURL Example**:
```bash
curl -X POST "https://api.example.com/pharmacies/1/debtors/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@debtor_report.pdf"
```

**JavaScript Example**:
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch(`/pharmacies/${pharmacyId}/debtors/upload`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const data = await response.json();
```

**Response** (200 OK):
```json
{
  "report_id": 123,
  "total_accounts": 150,
  "total_outstanding": 125000.50,
  "debtors": [
    {
      "id": 1,
      "pharmacy_id": 1,
      "report_id": 123,
      "acc_no": "123456",
      "name": "John Doe",
      "current": 100.50,
      "d30": 200.00,
      "d60": 150.00,
      "d90": 75.00,
      "d120": 50.00,
      "d150": 25.00,
      "d180": 10.00,
      "balance": 610.50,
      "email": "john@example.com",
      "phone": "0821234567",
      "is_medical_aid_control": false,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Error Responses**:
- `400`: No file provided or invalid file
- `403`: Access denied (no write permission)
- `404`: Pharmacy not found
- `500`: PDF processing error

---

## 2. Get Debtors List

Retrieve a paginated list of debtors with filtering options.

**Endpoint**: `GET /pharmacies/{pharmacy_id}/debtors`

**Authentication**: Required (Bearer token with read access)

**Query Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `min_balance` | float | No | - | Minimum balance for 60+ day arrears |
| `ageing_buckets` | string | No | - | Comma-separated list: "d60,d90,d120" |
| `has_email` | boolean | No | - | Filter by email availability |
| `has_phone` | boolean | No | - | Filter by phone availability |
| `search` | string | No | - | Search in acc_no, name, email, phone |
| `exclude_medical_aid` | boolean | No | true | Exclude medical aid accounts |
| `page` | integer | No | 1 | Page number (≥1) |
| `per_page` | integer | No | 100 | Items per page (1-1000) |

**Example Request**:
```bash
GET /pharmacies/1/debtors?min_balance=100&ageing_buckets=d60,d90&has_email=true&page=1&per_page=50
```

**JavaScript Example**:
```javascript
const params = new URLSearchParams({
  min_balance: 100,
  ageing_buckets: 'd60,d90',
  has_email: 'true',
  page: 1,
  per_page: 50
});

const response = await fetch(`/pharmacies/${pharmacyId}/debtors?${params}`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const data = await response.json();
```

**Response** (200 OK):
```json
{
  "total": 150,
  "page": 1,
  "per_page": 50,
  "pages": 3,
  "debtors": [
    {
      "id": 1,
      "pharmacy_id": 1,
      "report_id": 123,
      "acc_no": "123456",
      "name": "John Doe",
      "current": 100.50,
      "d30": 200.00,
      "d60": 150.00,
      "d90": 75.00,
      "d120": 50.00,
      "d150": 25.00,
      "d180": 10.00,
      "balance": 610.50,
      "email": "john@example.com",
      "phone": "0821234567",
      "is_medical_aid_control": false,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Error Responses**:
- `403`: Access denied
- `404`: Pharmacy not found

---

## 3. Get Statistics

Get aggregated statistics for all debtors (excluding medical aid accounts).

**Endpoint**: `GET /pharmacies/{pharmacy_id}/debtors/statistics`

**Authentication**: Required (Bearer token with read access)

**Example Request**:
```bash
GET /pharmacies/1/debtors/statistics
```

**JavaScript Example**:
```javascript
const response = await fetch(`/pharmacies/${pharmacyId}/debtors/statistics`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const stats = await response.json();
```

**Response** (200 OK):
```json
{
  "total_accounts": 150,
  "total_outstanding": 125000.50,
  "current": 50000.00,
  "d30": 30000.00,
  "d60": 25000.00,
  "d90": 15000.00,
  "d120": 5000.00,
  "d150": 0.00,
  "d180": 0.00
}
```

**Error Responses**:
- `403`: Access denied
- `404`: Pharmacy not found

---

## 4. Send Email Reminders

Send email reminders to selected debtors.

**Endpoint**: `POST /pharmacies/{pharmacy_id}/debtors/send-email`

**Authentication**: Required (Bearer token with write access)

**Request Body**:
```json
{
  "debtor_ids": [1, 2, 3],
  "ageing_buckets": ["d60", "d90", "d120", "d150", "d180"]
}
```

**Request Schema**:
- `debtor_ids` (array of integers, required): List of debtor IDs to send emails to
- `ageing_buckets` (array of strings, optional): Ageing buckets to include in calculation. Default: `["d60", "d90", "d120", "d150", "d180"]`

**JavaScript Example**:
```javascript
const response = await fetch(`/pharmacies/${pharmacyId}/debtors/send-email`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    debtor_ids: [1, 2, 3],
    ageing_buckets: ['d60', 'd90', 'd120']
  })
});

const result = await response.json();
```

**Response** (200 OK):
```json
{
  "sent": [
    {
      "debtor_id": 1,
      "email": "john@example.com",
      "status": "sent",
      "external_id": "sg_123456"
    }
  ],
  "errors": [
    {
      "debtor_id": 2,
      "error": "No email address"
    },
    {
      "debtor_id": 3,
      "error": "SendGrid API error: Invalid API key"
    }
  ]
}
```

**Error Responses**:
- `400`: SendGrid API key not configured for pharmacy
- `403`: Access denied (no write permission)
- `404`: Pharmacy not found or no debtors found
- `500`: Error sending emails

**Note**: Requires pharmacy to have `sendgrid_api_key` configured.

---

## 5. Send SMS Reminders

Send SMS reminders to selected debtors.

**Endpoint**: `POST /pharmacies/{pharmacy_id}/debtors/send-sms`

**Authentication**: Required (Bearer token with write access)

**Request Body**:
```json
{
  "debtor_ids": [1, 2, 3],
  "ageing_buckets": ["d60", "d90", "d120", "d150", "d180"]
}
```

**Request Schema**:
- `debtor_ids` (array of integers, required): List of debtor IDs to send SMS to
- `ageing_buckets` (array of strings, optional): Ageing buckets to include in calculation. Default: `["d60", "d90", "d120", "d150", "d180"]`

**JavaScript Example**:
```javascript
const response = await fetch(`/pharmacies/${pharmacyId}/debtors/send-sms`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    debtor_ids: [1, 2, 3],
    ageing_buckets: ['d60', 'd90', 'd120']
  })
});

const result = await response.json();
```

**Response** (200 OK):
```json
{
  "sent": [
    {
      "debtor_id": 1,
      "phone": "0821234567",
      "status": "sent",
      "external_id": "sms_123456"
    }
  ],
  "errors": [
    {
      "debtor_id": 2,
      "error": "No phone number"
    }
  ]
}
```

**Error Responses**:
- `400`: SMS Portal credentials not configured for pharmacy
- `403`: Access denied (no write permission)
- `404`: Pharmacy not found or no debtors found
- `500`: Error sending SMS

**Note**: Requires pharmacy to have `smsportal_client_id` and `smsportal_api_secret` configured.

---

## 6. Download CSV

Download debtors data as a CSV file.

**Endpoint**: `POST /pharmacies/{pharmacy_id}/debtors/download-csv`

**Authentication**: Required (Bearer token with read access)

**Request Body**:
```json
{
  "debtor_ids": [1, 2, 3],
  "min_balance": 100
}
```

**Request Schema**:
- `debtor_ids` (array of integers, optional): Filter by specific debtor IDs
- `min_balance` (float, optional): Minimum balance for 60+ day arrears

**JavaScript Example**:
```javascript
const response = await fetch(`/pharmacies/${pharmacyId}/debtors/download-csv`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    debtor_ids: [1, 2, 3],
    min_balance: 100
  })
});

const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `debtors_${pharmacyId}.csv`;
a.click();
```

**Response** (200 OK):
- **Content-Type**: `text/csv`
- **Headers**: `Content-Disposition: attachment; filename=debtors_{pharmacy_id}.csv`
- **Body**: CSV file with columns: Account No, Name, Current, 30 Days, 60 Days, 90 Days, 120 Days, 150 Days, 180 Days, Balance, Email, Phone

**CSV Format**:
```csv
Account No,Name,Current,30 Days,60 Days,90 Days,120 Days,150 Days,180 Days,Balance,Email,Phone
123456,John Doe,100.50,200.00,150.00,75.00,50.00,25.00,10.00,610.50,john@example.com,0821234567
```

**Error Responses**:
- `403`: Access denied
- `404`: Pharmacy not found

---

## 7. Download PDF

Download debtors data as a PDF report.

**Endpoint**: `POST /pharmacies/{pharmacy_id}/debtors/download-pdf`

**Authentication**: Required (Bearer token with read access)

**Request Body**:
```json
{
  "debtor_ids": [1, 2, 3],
  "ageing_buckets": ["d60", "d90"]
}
```

**Request Schema**:
- `debtor_ids` (array of integers, optional): Filter by specific debtor IDs
- `ageing_buckets` (array of strings, optional): Filter by ageing buckets

**JavaScript Example**:
```javascript
const response = await fetch(`/pharmacies/${pharmacyId}/debtors/download-pdf`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    debtor_ids: [1, 2, 3],
    ageing_buckets: ['d60', 'd90']
  })
});

const blob = await response.blob();
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = `debtors_${pharmacyId}.pdf`;
a.click();
```

**Response** (200 OK):
- **Content-Type**: `application/pdf`
- **Headers**: `Content-Disposition: attachment; filename=debtors_{pharmacy_id}.pdf`
- **Body**: PDF file with debtor report

**Error Responses**:
- `403`: Access denied
- `404`: Pharmacy not found
- `500`: PDF generation error

---

## 8. Get Communication History

Get all communication logs (emails and SMS) for a specific debtor.

**Endpoint**: `GET /pharmacies/{pharmacy_id}/debtors/{debtor_id}/communications`

**Authentication**: Required (Bearer token with read access)

**Example Request**:
```bash
GET /pharmacies/1/debtors/123/communications
```

**JavaScript Example**:
```javascript
const response = await fetch(`/pharmacies/${pharmacyId}/debtors/${debtorId}/communications`, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const logs = await response.json();
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "pharmacy_id": 1,
    "debtor_id": 123,
    "communication_type": "email",
    "recipient": "john@example.com",
    "subject": "Reminder: Account Overdue at Pharmacy Name",
    "message": "<html>...</html>",
    "status": "sent",
    "external_id": "sg_123456",
    "error_message": null,
    "sent_at": "2025-01-15T10:30:00Z",
    "created_at": "2025-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "pharmacy_id": 1,
    "debtor_id": 123,
    "communication_type": "sms",
    "recipient": "0821234567",
    "subject": null,
    "message": "Dear John Doe, Your account...",
    "status": "sent",
    "external_id": "sms_789012",
    "error_message": null,
    "sent_at": "2025-01-15T11:00:00Z",
    "created_at": "2025-01-15T11:00:00Z"
  }
]
```

**Error Responses**:
- `403`: Access denied
- `404`: Pharmacy or debtor not found

---

## Data Models

### Debtor Object
```typescript
interface Debtor {
  id: number;
  pharmacy_id: number;
  report_id: number | null;
  acc_no: string;
  name: string;
  current: number;
  d30: number;
  d60: number;
  d90: number;
  d120: number;
  d150: number;
  d180: number;
  balance: number;
  email: string | null;
  phone: string | null;
  is_medical_aid_control: boolean;
  created_at: string; // ISO 8601 datetime
  updated_at: string; // ISO 8601 datetime
}
```

### Debtor Statistics
```typescript
interface DebtorStatistics {
  total_accounts: number;
  total_outstanding: number;
  current: number;
  d30: number;
  d60: number;
  d90: number;
  d120: number;
  d150: number;
  d180: number;
}
```

### Communication Result
```typescript
interface CommunicationResult {
  debtor_id: number;
  email?: string;
  phone?: string;
  status: string;
  external_id?: string;
}
```

### Communication Error
```typescript
interface CommunicationError {
  debtor_id: number;
  error: string;
}
```

### Communication Log
```typescript
interface CommunicationLog {
  id: number;
  pharmacy_id: number;
  debtor_id: number;
  communication_type: 'email' | 'sms';
  recipient: string;
  subject: string | null;
  message: string;
  status: 'pending' | 'sent' | 'failed';
  external_id: string | null;
  error_message: string | null;
  sent_at: string | null; // ISO 8601 datetime
  created_at: string; // ISO 8601 datetime
}
```

---

## Error Handling

All endpoints may return standard HTTP error codes:

- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Missing or invalid authentication token
- **403 Forbidden**: User doesn't have required permissions
- **404 Not Found**: Resource (pharmacy, debtor, etc.) not found
- **500 Internal Server Error**: Server error

Error response format:
```json
{
  "detail": "Error message description"
}
```

---

## Notes

1. **Medical Aid Accounts**: Medical aid control accounts are automatically excluded from statistics and totals by default. Set `exclude_medical_aid=false` to include them.

2. **Ageing Buckets**: 
   - `current`: Current balance (not overdue)
   - `d30`: 30 days overdue
   - `d60`: 60 days overdue
   - `d90`: 90 days overdue
   - `d120`: 120 days overdue
   - `d150`: 150 days overdue
   - `d180`: 180+ days overdue
   - `balance`: Total outstanding balance

3. **Pagination**: The debtors list endpoint supports pagination. Use `page` and `per_page` parameters. Response includes `total`, `pages`, and `page` for building pagination UI.

4. **File Uploads**: PDF uploads use `multipart/form-data`. Ensure proper Content-Type header is set.

5. **Authentication**: All endpoints require a Bearer token in the Authorization header: `Authorization: Bearer YOUR_TOKEN`

6. **Permissions**: 
   - Read access required for: list, statistics, download, communications
   - Write access required for: upload, send-email, send-sms

---

## Example Frontend Integration

### React Hook Example
```typescript
import { useState, useEffect } from 'react';

function useDebtors(pharmacyId: number, filters: DebtorFilters) {
  const [debtors, setDebtors] = useState<Debtor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDebtors = async () => {
      try {
        setLoading(true);
        const params = new URLSearchParams({
          page: filters.page?.toString() || '1',
          per_page: filters.perPage?.toString() || '100',
          ...(filters.minBalance && { min_balance: filters.minBalance.toString() }),
          ...(filters.ageingBuckets && { ageing_buckets: filters.ageingBuckets.join(',') }),
          ...(filters.hasEmail && { has_email: 'true' }),
          ...(filters.hasPhone && { has_phone: 'true' }),
          ...(filters.search && { search: filters.search }),
        });

        const response = await fetch(
          `/pharmacies/${pharmacyId}/debtors?${params}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch debtors');
        }

        const data = await response.json();
        setDebtors(data.debtors);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDebtors();
  }, [pharmacyId, filters]);

  return { debtors, loading, error };
}
```

---

## Support

For questions or issues, contact the backend team or refer to the main API documentation.

