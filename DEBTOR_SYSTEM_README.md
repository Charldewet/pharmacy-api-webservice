# Debtor Reminder System

This document describes the debtor management system integrated into the pharmacy API.

## Overview

The debtor reminder system allows pharmacies to:
- Upload PDF debtor reports
- Track individual debtor accounts with ageing buckets (30, 60, 90, 120, 150, 180 days)
- Send email and SMS reminders to debtors
- Generate CSV and PDF reports
- Track communication history

## Setup

### 1. Database Migration

Run the SQL migration to create the necessary tables:

```bash
psql -d your_database -f schema_debtors.sql
```

This will create:
- Extended `pharmacies` table with banking and API key fields
- `debtor_reports` table for tracking uploaded PDFs
- `debtors` table for individual debtor accounts
- `communication_logs` table for email/SMS history

### 2. Environment Variables

Set the encryption key for API keys (SendGrid, SMS Portal):

```bash
# Generate a key:
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'

# Add to .env:
TOKEN_ENCRYPTION_KEY=your_generated_key_here
```

### 3. Install Dependencies

```bash
pip install -r pharma_api/requirements.txt
```

New dependencies include:
- `pandas` - Data processing
- `pdfminer.six` - PDF text extraction
- `sendgrid` - Email sending
- `fpdf` - PDF generation
- `requests` - SMS API calls

### 4. Configure Pharmacy Settings

Update pharmacy records with banking and API credentials:

```sql
UPDATE pharma.pharmacies SET
    email = 'pharmacy@example.com',
    phone = '0821234567',
    banking_account = '1234567890',
    bank_name = 'ABSA',
    sendgrid_api_key = '<encrypted_key>',  -- Use encrypt_api_key() function
    smsportal_client_id = '<encrypted_id>',
    smsportal_api_secret = '<encrypted_secret>'
WHERE pharmacy_id = 1;
```

## API Endpoints

All endpoints are under `/pharmacies/{pharmacy_id}/debtors` and require authentication.

### Upload Debtor Report

**POST** `/pharmacies/{pharmacy_id}/debtors/upload`

Upload a PDF debtor report. The system will:
- Extract debtor information from the PDF
- Identify medical aid control accounts (excluded from totals)
- Update existing debtors or create new ones

**Request:**
- `file`: PDF file (multipart/form-data)

**Response:**
```json
{
  "report_id": 123,
  "total_accounts": 150,
  "total_outstanding": 125000.50,
  "debtors": [...]
}
```

### Get Debtors List

**GET** `/pharmacies/{pharmacy_id}/debtors`

Get paginated list of debtors with filtering options.

**Query Parameters:**
- `min_balance` (float): Minimum balance for 60+ day arrears
- `ageing_buckets` (string): Comma-separated list (e.g., "d60,d90,d120")
- `has_email` (boolean): Filter by email availability
- `has_phone` (boolean): Filter by phone availability
- `search` (string): Search term
- `exclude_medical_aid` (boolean): Default true
- `page` (int): Page number (default 1)
- `per_page` (int): Items per page (default 100)

### Get Statistics

**GET** `/pharmacies/{pharmacy_id}/debtors/statistics`

Get aggregated statistics for all debtors.

**Response:**
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

### Send Email Reminders

**POST** `/pharmacies/{pharmacy_id}/debtors/send-email`

Send email reminders to selected debtors.

**Request:**
```json
{
  "debtor_ids": [1, 2, 3],
  "ageing_buckets": ["d60", "d90", "d120"]
}
```

**Response:**
```json
{
  "sent": [
    {
      "debtor_id": 1,
      "email": "john@example.com",
      "status": "sent",
      "external_id": "sg_123"
    }
  ],
  "errors": [
    {
      "debtor_id": 2,
      "error": "No email address"
    }
  ]
}
```

### Send SMS Reminders

**POST** `/pharmacies/{pharmacy_id}/debtors/send-sms`

Similar to email endpoint, sends SMS reminders.

### Download CSV

**POST** `/pharmacies/{pharmacy_id}/debtors/download-csv`

Download debtors as CSV file.

**Request:**
```json
{
  "debtor_ids": [1, 2, 3],  // Optional
  "min_balance": 100  // Optional
}
```

### Download PDF

**POST** `/pharmacies/{pharmacy_id}/debtors/download-pdf`

Download debtors as PDF report.

**Request:**
```json
{
  "debtor_ids": [1, 2, 3],  // Optional
  "ageing_buckets": ["d60", "d90"]  // Optional
}
```

### Get Communication History

**GET** `/pharmacies/{pharmacy_id}/debtors/{debtor_id}/communications`

Get all communication logs for a specific debtor.

## PDF Parsing

The system uses `pdfminer` to extract text from PDF reports. The parser looks for:
- Account numbers (4-8 digits)
- Customer names
- Ageing bucket amounts (current, d30, d60, d90, d120, d150, d180)
- Email addresses
- Phone numbers

The parser automatically identifies medical aid control accounts by matching patterns like:
- "MEDAID CONTROL ACC"
- "MEDICAL AID CONTROL"
- "MED AID CONTROL"

## Security

- All API keys are encrypted at rest using Fernet encryption
- Row-level security: Users can only access debtors for pharmacies they have access to
- Authentication required for all endpoints
- Write access required for upload, send-email, and send-sms endpoints

## Notes

- Medical aid control accounts are automatically excluded from statistics and totals
- Debtors are uniquely identified by `pharmacy_id` + `acc_no`
- Uploading a new report updates existing debtors with the same account number
- Communication logs track all email/SMS attempts (successful and failed)

## Troubleshooting

### PDF Parsing Issues

If PDFs aren't parsing correctly:
1. Check that the PDF contains extractable text (not scanned images)
2. Verify the PDF format matches expected debtor report structure
3. Check logs for parsing errors

### Email/SMS Not Sending

1. Verify pharmacy has API credentials configured
2. Check that `TOKEN_ENCRYPTION_KEY` is set correctly
3. Verify API keys are valid and have proper permissions
4. Check `communication_logs` table for error messages

### Encryption Errors

If you see encryption errors:
1. Ensure `TOKEN_ENCRYPTION_KEY` is set in environment
2. The key must be a valid Fernet key (32 bytes, base64 encoded)
3. Generate a new key if needed: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`



