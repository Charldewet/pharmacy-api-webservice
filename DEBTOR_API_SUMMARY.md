# Debtor Management API - Complete Endpoint Summary

## Base URL
All endpoints are under: `/pharmacies/{pharmacy_id}/debtors`

**Authentication**: All endpoints require Bearer token authentication via `Authorization` header.

---

## Available Endpoints

### 1. **Upload Debtor Report**
- **Method**: `POST`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/upload`
- **Description**: Upload a PDF debtor report. **IMPORTANT**: This completely replaces all existing debtors for the pharmacy with the new data.
- **Request**: `multipart/form-data` with `file` field (PDF)
- **Response**: `UploadDebtorReportResponse` with report_id, total_accounts, total_outstanding, and list of debtors
- **Access**: Requires write permission

### 2. **Get Debtor Reports History**
- **Method**: `GET`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/reports`
- **Description**: Get list of all uploaded debtor reports for a pharmacy
- **Response**: `List[DebtorReport]` - Array of report records with upload dates, status, totals
- **Access**: Requires read permission

### 3. **Get Debtors List**
- **Method**: `GET`
- **Path**: `/pharmacies/{pharmacy_id}/debtors`
- **Description**: Get paginated list of debtors with filtering options
- **Query Parameters**:
  - `min_balance` (float, optional): Filter by minimum balance in arrears (d60+d90+d120+d150+d180)
  - `ageing_buckets` (string, optional): Comma-separated list: "d30,d60,d90" to filter by buckets with balances
  - `has_email` (boolean, optional): Filter debtors with email addresses
  - `has_phone` (boolean, optional): Filter debtors with phone numbers
  - `search` (string, optional): Search in acc_no, name, email, phone
  - `exclude_medical_aid` (boolean, default: true): Exclude medical aid control accounts
  - `page` (int, default: 1): Page number
  - `per_page` (int, default: 100, max: 1000): Items per page
- **Response**: `DebtorPage` with pagination info and list of debtors
- **Access**: Requires read permission

### 4. **Get Statistics**
- **Method**: `GET`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/statistics`
- **Description**: Get aggregate statistics for all debtors
- **Response**: `DebtorStatistics` with:
  - `total_accounts`: Total number of debtor accounts
  - `total_outstanding`: Total outstanding balance
  - `current`, `d30`, `d60`, `d90`, `d120`, `d150`, `d180`: Sums for each ageing bucket
- **Access**: Requires read permission

### 5. **Send Email Reminders**
- **Method**: `POST`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/send-email`
- **Description**: Send email reminders to selected debtors via SendGrid
- **Request Body**: `SendEmailRequest`
  - `debtor_ids`: Array of debtor IDs to send to
  - `ageing_buckets`: Optional array of buckets to include in calculation (default: ["d60", "d90", "d120", "d150", "d180"])
- **Response**: `SendCommunicationResponse` with sent/errors arrays
- **Access**: Requires write permission
- **Requirements**: Pharmacy must have SendGrid API key configured

### 6. **Send SMS Reminders**
- **Method**: `POST`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/send-sms`
- **Description**: Send SMS reminders to selected debtors via SMS Portal
- **Request Body**: `SendSMSRequest`
  - `debtor_ids`: Array of debtor IDs to send to
  - `ageing_buckets`: Optional array of buckets to include in calculation
- **Response**: `SendCommunicationResponse` with sent/errors arrays
- **Access**: Requires write permission
- **Requirements**: Pharmacy must have SMS Portal credentials configured

### 7. **Download CSV**
- **Method**: `POST`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/download-csv`
- **Description**: Generate and download a CSV file of debtors
- **Request Body**: `DownloadCSVRequest` (optional)
  - `debtor_ids`: Optional array of specific debtor IDs
  - `min_balance`: Optional minimum balance filter
- **Response**: CSV file download
- **Access**: Requires read permission

### 8. **Download PDF**
- **Method**: `POST`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/download-pdf`
- **Description**: Generate and download a PDF report of debtors
- **Request Body**: `DownloadPDFRequest` (optional)
  - `debtor_ids`: Optional array of specific debtor IDs
  - `ageing_buckets`: Optional array of buckets to include
  - `col_names`: Optional custom column names mapping
- **Response**: PDF file download
- **Access**: Requires read permission

### 9. **Get Communication History**
- **Method**: `GET`
- **Path**: `/pharmacies/{pharmacy_id}/debtors/{debtor_id}/communications`
- **Description**: Get communication history (emails/SMS) for a specific debtor
- **Response**: `List[CommunicationLog]` - Array of communication records
- **Access**: Requires read permission

---

## Data Models

### Debtor
```typescript
{
  id: number;
  pharmacy_id: number;
  report_id?: number;
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
  email?: string;
  phone?: string;
  is_medical_aid_control: boolean;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}
```

### DebtorReport
```typescript
{
  id: number;
  pharmacy_id: number;
  filename: string;
  file_path?: string;
  uploaded_at: string; // ISO datetime
  uploaded_by?: number;
  total_accounts: number;
  total_outstanding: number;
  status: "processing" | "completed" | "failed";
  error_message?: string;
}
```

### DebtorStatistics
```typescript
{
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

---

## Important Notes

1. **Complete Replacement**: When uploading a new debtor report (via API or email import), ALL existing debtors for that pharmacy are deleted and replaced with the new data.

2. **Medical Aid Accounts**: Medical aid control accounts are automatically detected and flagged, but excluded from statistics and most queries by default.

3. **Authentication**: All endpoints require a valid Bearer token. The user must have read/write access to the pharmacy.

4. **Email Import**: Debtor reports are automatically imported from email attachments via the `live_import_5h.py` script, which uses the same replacement logic.

5. **Communication Logging**: All emails and SMS sent through the API are logged in `pharma.communication_logs` table.

---

## Example Frontend Usage

```typescript
// Get all debtors for pharmacy 2
const response = await fetch('/pharmacies/2/debtors?page=1&per_page=100', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const data: DebtorPage = await response.json();

// Get statistics
const stats = await fetch('/pharmacies/2/debtors/statistics', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const statistics: DebtorStatistics = await stats.json();

// Get report history
const reports = await fetch('/pharmacies/2/debtors/reports', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const reportList: DebtorReport[] = await reports.json();

// Send email to selected debtors
const emailResponse = await fetch('/pharmacies/2/debtors/send-email', {
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
```



