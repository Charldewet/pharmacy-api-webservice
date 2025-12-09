# Frontend Bank Statement Upload - Update Guide

## ✅ What Changed (Backend)

The backend CSV parser has been **significantly enhanced** to handle date parsing more robustly. **No frontend changes are required** - the API endpoints remain the same, but the parser now handles many more date formats automatically.

## 📋 API Endpoints (Unchanged)

The endpoints remain exactly the same:

### Preview Import
```
POST https://pharmacy-api-webservice.onrender.com/bank-imports/preview
```

### Confirm Import
```
POST https://pharmacy-api-webservice.onrender.com/bank-imports/confirm
```

## 🎯 What This Means for Frontend

### ✅ **No Code Changes Needed**

Your existing frontend code will continue to work exactly as before. The improvements are all backend-side.

### 📅 **Supported Date Formats**

The parser now automatically handles these date formats (and more):

- ✅ `DD/MM/YYYY` (e.g., "29/11/2025") - **Most common in South Africa**
- ✅ `DD-MM-YYYY` (e.g., "29-11-2025")
- ✅ `YYYY-MM-DD` (e.g., "2025-11-29") - ISO format
- ✅ `YYYY/MM/DD` (e.g., "2025/11/29")
- ✅ `DD/MM/YY` (e.g., "29/11/25")
- ✅ `DD Mon YYYY` (e.g., "29 Nov 2025")
- ✅ `DD Month YYYY` (e.g., "29 November 2025")
- ✅ `DD.MM.YYYY` (e.g., "29.11.2025")

### 🔤 **Case-Insensitive Headers**

CSV headers are now matched case-insensitively, so these all work:
- `Date`, `date`, `DATE`
- `Description`, `description`, `DESCRIPTION`
- `Amount`, `amount`, `AMOUNT`

### 📊 **CSV Format Requirements**

Your CSV files should have at minimum these columns (case-insensitive):

**Required:**
- `Date` - Transaction date (any supported format)
- `Description` - Transaction description
- `Amount` - Transaction amount (positive for credits, negative for debits)

**Optional:**
- `Reference` - Reference number
- `Balance` - Running balance
- `Debit` / `Credit` - Separate debit/credit columns (if not using single Amount column)

### 📝 **Example CSV Format**

```csv
Date,Description,Amount
29/11/2025,SERVICE FEE ACC   301666148,-341.40
29/11/2025,MONTHLY MANAGEMENT FEE ACC   301666148,-110.00
29/11/2025,CREDIT CARD EFTPOS SETTLEMENT DR EFTPOS 1OB  1  0000304515587,18796.65
```

This format will now parse correctly without errors!

## 🚀 **Frontend Implementation (No Changes Required)**

Your existing code should work perfectly. Here's a reminder of the correct implementation:

### JavaScript/React Example

```javascript
// Preview Import
async function previewBankStatement(pharmacyId, bankAccountId, csvFile) {
  const formData = new FormData();
  formData.append('pharmacy_id', pharmacyId);
  formData.append('bank_account_id', bankAccountId);
  formData.append('file', csvFile);
  
  const response = await fetch(
    'https://pharmacy-api-webservice.onrender.com/bank-imports/preview',
    {
      method: 'POST',
      headers: {
        'X-API-Key': 'your-api-key'
        // ⚠️ IMPORTANT: Don't set Content-Type header
      },
      body: formData
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Preview failed');
  }
  
  return await response.json();
}

// Confirm Import
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
  
  const response = await fetch(
    'https://pharmacy-api-webservice.onrender.com/bank-imports/confirm',
    {
      method: 'POST',
      headers: {
        'X-API-Key': 'your-api-key'
        // ⚠️ IMPORTANT: Don't set Content-Type header
      },
      body: formData
    }
  );
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Import failed');
  }
  
  return await response.json();
}
```

## 🐛 **Error Handling**

### Before (Old Behavior)
- Date parsing errors were common with `DD/MM/YYYY` format
- Case-sensitive header matching could fail
- Limited date format support

### After (New Behavior)
- ✅ Dates in `DD/MM/YYYY` format parse correctly
- ✅ Case-insensitive header matching
- ✅ Multiple date format support with automatic detection
- ✅ Better error messages if parsing still fails

### Error Response Format (Unchanged)

If there are still parsing errors, they'll be returned in the same format:

```json
{
  "errors": [
    {
      "row_number": 10,
      "error": "Missing or invalid date",
      "raw_data": {...}
    }
  ]
}
```

## 📋 **Testing Checklist**

To verify everything works:

1. ✅ Upload a CSV with `DD/MM/YYYY` dates (e.g., "29/11/2025")
2. ✅ Upload a CSV with lowercase headers (e.g., "date", "description", "amount")
3. ✅ Upload a CSV with mixed case headers (e.g., "Date", "DESCRIPTION", "Amount")
4. ✅ Check that preview shows correct dates in `YYYY-MM-DD` format
5. ✅ Verify that confirm import works without date errors

## 🎉 **Summary**

- **No frontend code changes needed** ✅
- **Better date format support** ✅
- **Case-insensitive headers** ✅
- **Same API endpoints** ✅
- **Same request/response format** ✅

The backend improvements are transparent to the frontend - your existing code will just work better with fewer errors!

---

**Last Updated**: December 2025
**Backend Version**: Enhanced date parsing (commit 9a7e582)

