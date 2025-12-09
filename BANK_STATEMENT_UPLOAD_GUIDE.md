# Bank Statement Upload API Guide

## Overview

The bank statement upload process has two steps:
1. **Preview** - Upload CSV and see what will be imported (without saving)
2. **Confirm** - Save the import to database

---

## Step 1: Preview Import

**Endpoint**: `POST /bank-imports/preview`

**Purpose**: Upload CSV file and get a preview of parsed transactions without saving to database.

### Request

**URL**: `https://pharmacy-api-webservice.onrender.com/bank-imports/preview`

**Method**: `POST`

**Content-Type**: `multipart/form-data`

**Headers**:
```
X-API-Key: your-api-key
```
or
```
Authorization: Bearer your-api-key
```

**Form Data**:
- `pharmacy_id` (integer, required) - ID of the pharmacy
- `bank_account_id` (integer, required) - ID of the bank account
- `file` (file, required) - CSV file to upload

### Response

**Success (200 OK)**:
```json
{
  "pharmacy_id": 1,
  "bank_account_id": 5,
  "summary": {
    "transaction_count": 123,
    "total_in": 456789.12,
    "total_out": -345678.90,
    "min_date": "2025-03-01",
    "max_date": "2025-03-31"
  },
  "sample_transactions": [
    {
      "row_number": 2,
      "date": "2025-03-01",
      "description": "CARD PURCHASE - VODACOM",
      "reference": "POS 12345",
      "amount": -450.00,
      "balance": 10234.56
    }
  ],
  "errors": [
    {
      "row_number": 10,
      "error": "Invalid date format",
      "raw_data": {...}
    }
  ]
}
```

---

## Step 2: Confirm Import

**Endpoint**: `POST /bank-imports/confirm`

**Purpose**: Save the parsed transactions to database.

### Request

**URL**: `https://pharmacy-api-webservice.onrender.com/bank-imports/confirm`

**Method**: `POST`

**Content-Type**: `multipart/form-data`

**Headers**:
```
X-API-Key: your-api-key
```

**Form Data**:
- `pharmacy_id` (integer, required) - ID of the pharmacy
- `bank_account_id` (integer, required) - ID of the bank account
- `file_name` (string, required) - Original filename (e.g., "statement_march_2025.csv")
- `file` (file, required) - CSV file to import
- `notes` (string, optional) - Optional notes about this import
- `skip_duplicates` (boolean, optional, default: true) - Whether to skip duplicate transactions

### Response

**Success (200 OK)**:
```json
{
  "bank_import_batch_id": 42,
  "transactions_inserted": 120,
  "transactions_skipped_as_duplicates": 8,
  "errors_count": 3,
  "period_start": "2025-03-01",
  "period_end": "2025-03-31",
  "status": "IMPORTED"
}
```

---

## Frontend Implementation Examples

### JavaScript/React - Using Fetch API

#### Preview Import

```javascript
async function previewBankStatement(pharmacyId, bankAccountId, csvFile) {
  const formData = new FormData();
  formData.append('pharmacy_id', pharmacyId);
  formData.append('bank_account_id', bankAccountId);
  formData.append('file', csvFile); // File object from input[type="file"]
  
  try {
    const response = await fetch(
      'https://pharmacy-api-webservice.onrender.com/bank-imports/preview',
      {
        method: 'POST',
        headers: {
          'X-API-Key': 'your-api-key'
          // Don't set Content-Type header - browser will set it with boundary
        },
        body: formData
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error previewing bank statement:', error);
    throw error;
  }
}

// Usage in React component
function BankStatementUpload() {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  
  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    setLoading(true);
    try {
      const previewData = await previewBankStatement(1, 5, file);
      setPreview(previewData);
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <input 
        type="file" 
        accept=".csv" 
        onChange={handleFileSelect}
        disabled={loading}
      />
      {preview && (
        <div>
          <h3>Preview</h3>
          <p>Transactions: {preview.summary.transaction_count}</p>
          <p>Total In: R {preview.summary.total_in.toFixed(2)}</p>
          <p>Total Out: R {Math.abs(preview.summary.total_out).toFixed(2)}</p>
          {preview.errors.length > 0 && (
            <p>Errors: {preview.errors.length}</p>
          )}
        </div>
      )}
    </div>
  );
}
```

#### Confirm Import

```javascript
async function confirmBankStatementImport(
  pharmacyId, 
  bankAccountId, 
  fileName, 
  csvFile, 
  notes = null
) {
  const formData = new FormData();
  formData.append('pharmacy_id', pharmacyId);
  formData.append('bank_account_id', bankAccountId);
  formData.append('file_name', fileName);
  formData.append('file', csvFile);
  formData.append('skip_duplicates', 'true'); // or 'false'
  
  if (notes) {
    formData.append('notes', notes);
  }
  
  try {
    const response = await fetch(
      'https://pharmacy-api-webservice.onrender.com/bank-imports/confirm',
      {
        method: 'POST',
        headers: {
          'X-API-Key': 'your-api-key'
        },
        body: formData
      }
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error confirming bank statement import:', error);
    throw error;
  }
}

// Usage
async function handleConfirmImport() {
  const fileInput = document.getElementById('csv-file');
  const file = fileInput.files[0];
  
  if (!file) {
    alert('Please select a file');
    return;
  }
  
  try {
    const result = await confirmBankStatementImport(
      1,           // pharmacy_id
      5,           // bank_account_id
      file.name,   // file_name
      file,        // csvFile
      'March 2025 statement' // notes (optional)
    );
    
    alert(`Import successful!
      Transactions imported: ${result.transactions_inserted}
      Duplicates skipped: ${result.transactions_skipped_as_duplicates}
      Errors: ${result.errors_count}`);
  } catch (error) {
    alert(`Import failed: ${error.message}`);
  }
}
```

### Complete React Component Example

```javascript
import React, { useState } from 'react';

function BankStatementUploader({ pharmacyId, bankAccountId, apiKey }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [importResult, setImportResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState('select'); // 'select', 'preview', 'success'
  
  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setPreview(null);
    setImportResult(null);
    setStep('select');
  };
  
  const handlePreview = async () => {
    if (!file) return;
    
    setLoading(true);
    const formData = new FormData();
    formData.append('pharmacy_id', pharmacyId);
    formData.append('bank_account_id', bankAccountId);
    formData.append('file', file);
    
    try {
      const response = await fetch(
        'https://pharmacy-api-webservice.onrender.com/bank-imports/preview',
        {
          method: 'POST',
          headers: {
            'X-API-Key': apiKey
          },
          body: formData
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Preview failed');
      }
      
      const data = await response.json();
      setPreview(data);
      setStep('preview');
    } catch (error) {
      alert(`Preview error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleConfirm = async () => {
    if (!file) return;
    
    setLoading(true);
    const formData = new FormData();
    formData.append('pharmacy_id', pharmacyId);
    formData.append('bank_account_id', bankAccountId);
    formData.append('file_name', file.name);
    formData.append('file', file);
    formData.append('skip_duplicates', 'true');
    
    try {
      const response = await fetch(
        'https://pharmacy-api-webservice.onrender.com/bank-imports/confirm',
        {
          method: 'POST',
          headers: {
            'X-API-Key': apiKey
          },
          body: formData
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Import failed');
      }
      
      const data = await response.json();
      setImportResult(data);
      setStep('success');
    } catch (error) {
      alert(`Import error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <h2>Upload Bank Statement</h2>
      
      {step === 'select' && (
        <div>
          <input 
            type="file" 
            accept=".csv" 
            onChange={handleFileChange}
            disabled={loading}
          />
          {file && (
            <div>
              <p>Selected: {file.name}</p>
              <button onClick={handlePreview} disabled={loading}>
                {loading ? 'Loading...' : 'Preview'}
              </button>
            </div>
          )}
        </div>
      )}
      
      {step === 'preview' && preview && (
        <div>
          <h3>Preview</h3>
          <div>
            <p><strong>Transactions:</strong> {preview.summary.transaction_count}</p>
            <p><strong>Total In:</strong> R {preview.summary.total_in.toFixed(2)}</p>
            <p><strong>Total Out:</strong> R {Math.abs(preview.summary.total_out).toFixed(2)}</p>
            <p><strong>Period:</strong> {preview.summary.min_date} to {preview.summary.max_date}</p>
            {preview.errors.length > 0 && (
              <div style={{color: 'red'}}>
                <p><strong>Errors:</strong> {preview.errors.length}</p>
                <ul>
                  {preview.errors.slice(0, 5).map((err, idx) => (
                    <li key={idx}>Row {err.row_number}: {err.error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          
          <div style={{marginTop: '20px'}}>
            <button onClick={() => setStep('select')}>Back</button>
            <button onClick={handleConfirm} disabled={loading}>
              {loading ? 'Importing...' : 'Confirm Import'}
            </button>
          </div>
        </div>
      )}
      
      {step === 'success' && importResult && (
        <div style={{color: 'green'}}>
          <h3>Import Successful!</h3>
          <p>Batch ID: {importResult.bank_import_batch_id}</p>
          <p>Transactions imported: {importResult.transactions_inserted}</p>
          <p>Duplicates skipped: {importResult.transactions_skipped_as_duplicates}</p>
          <p>Errors: {importResult.errors_count}</p>
          <button onClick={() => {
            setFile(null);
            setPreview(null);
            setImportResult(null);
            setStep('select');
          }}>Upload Another</button>
        </div>
      )}
    </div>
  );
}

export default BankStatementUploader;
```

### Using Axios (Alternative)

```javascript
import axios from 'axios';

async function previewBankStatement(pharmacyId, bankAccountId, csvFile) {
  const formData = new FormData();
  formData.append('pharmacy_id', pharmacyId);
  formData.append('bank_account_id', bankAccountId);
  formData.append('file', csvFile);
  
  const response = await axios.post(
    'https://pharmacy-api-webservice.onrender.com/bank-imports/preview',
    formData,
    {
      headers: {
        'X-API-Key': 'your-api-key',
        'Content-Type': 'multipart/form-data'
      }
    }
  );
  
  return response.data;
}

async function confirmBankStatementImport(
  pharmacyId, 
  bankAccountId, 
  fileName, 
  csvFile, 
  notes = null
) {
  const formData = new FormData();
  formData.append('pharmacy_id', pharmacyId);
  formData.append('bank_account_id', bankAccountId);
  formData.append('file_name', fileName);
  formData.append('file', csvFile);
  formData.append('skip_duplicates', 'true');
  
  if (notes) {
    formData.append('notes', notes);
  }
  
  const response = await axios.post(
    'https://pharmacy-api-webservice.onrender.com/bank-imports/confirm',
    formData,
    {
      headers: {
        'X-API-Key': 'your-api-key',
        'Content-Type': 'multipart/form-data'
      }
    }
  );
  
  return response.data;
}
```

---

## Common Issues & Solutions

### Issue 1: "Content-Type header is set incorrectly"

**Problem**: Manually setting `Content-Type: multipart/form-data` without boundary.

**Solution**: Let the browser set it automatically. Don't include `Content-Type` header when using `FormData` with fetch.

```javascript
// ❌ Wrong
headers: {
  'Content-Type': 'multipart/form-data'
}

// ✅ Correct - Let browser set it
headers: {
  'X-API-Key': 'your-api-key'
  // Don't set Content-Type
}
```

### Issue 2: "File is empty" error

**Problem**: File not being appended correctly to FormData.

**Solution**: Make sure you're using the File object directly, not a string path.

```javascript
// ✅ Correct
formData.append('file', fileInput.files[0]);

// ❌ Wrong
formData.append('file', fileInput.value);
```

### Issue 3: CORS errors

**Problem**: CORS not configured properly.

**Solution**: Ensure your API has CORS configured. The API should already handle this, but verify the `CORS_ALLOW_ORIGINS` setting.

### Issue 4: "Bank format not supported"

**Problem**: Bank name in `bank_accounts` table doesn't match supported formats.

**Solution**: Ensure `bank_name` in your bank account is one of:
- "FNB" or "First National Bank"
- "ABSA"
- "Standard Bank" or "STD BANK"

---

## cURL Examples

### Preview
```bash
curl -X POST "https://pharmacy-api-webservice.onrender.com/bank-imports/preview" \
  -H "X-API-Key: your-api-key" \
  -F "pharmacy_id=1" \
  -F "bank_account_id=5" \
  -F "file=@/path/to/statement.csv"
```

### Confirm
```bash
curl -X POST "https://pharmacy-api-webservice.onrender.com/bank-imports/confirm" \
  -H "X-API-Key: your-api-key" \
  -F "pharmacy_id=1" \
  -F "bank_account_id=5" \
  -F "file_name=statement_march_2025.csv" \
  -F "file=@/path/to/statement.csv" \
  -F "skip_duplicates=true" \
  -F "notes=March 2025 statement"
```

---

## CSV Format Requirements

The CSV file should contain at minimum:
- **Date** column (various formats supported)
- **Description** column
- **Amount** column (or separate Debit/Credit columns)

Supported banks:
- FNB (First National Bank)
- ABSA
- Standard Bank

The parser automatically detects the bank format based on the `bank_name` field in your `bank_accounts` table.

---

**Last Updated**: December 2025

