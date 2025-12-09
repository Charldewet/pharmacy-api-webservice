# Pharmacy Targets API - Frontend Integration Guide

## 📋 Overview

The Pharmacy Targets API allows pharmacy managers to set and manage **daily turnover targets** for each pharmacy. Targets are stored in the database and persist across server restarts. These targets are used to:

1. Display in the Targets table on the frontend
2. Calculate purchase budgets (75% of turnover target)
3. Show in daily summary (actual vs. target turnover)
4. Track performance metrics

---

## 🔐 Authentication & Authorization

**All endpoints require:**
- **Authentication:** Bearer token in `Authorization` header (same as your existing auth)
- **Authorization:** User must have **read access** to view targets, **write access** to create/update/delete targets
- **Base URL:** `/admin/pharmacies/{pharmacy_id}/targets`

**Important:** Users can only access targets for pharmacies they have access to. The API automatically checks pharmacy permissions.

---

## 📡 API Endpoints

### 1. Get Targets for a Month

**Endpoint:** `GET /admin/pharmacies/{pharmacy_id}/targets`

**Query Parameters:**
- `month` (required): Month in `YYYY-MM` format (e.g., `2025-11`)

**Example Request:**
```javascript
const pharmacyId = 1;
const month = "2025-11"; // November 2025

const response = await fetch(
  `${API_BASE_URL}/admin/pharmacies/${pharmacyId}/targets?month=${month}`,
  {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }
);

const data = await response.json();
```

**Response (200 OK):**
```json
{
  "pharmacy_id": 1,
  "month": "2025-11",
  "targets": [
    {
      "date": "2025-11-01",
      "value": 8500.00
    },
    {
      "date": "2025-11-02",
      "value": 9200.00
    },
    {
      "date": "2025-11-15",
      "value": 10000.00
    }
  ]
}
```

**Response Format:**
- `pharmacy_id`: The pharmacy ID
- `month`: The requested month (YYYY-MM format)
- `targets`: Array of target objects, each containing:
  - `date`: Date in YYYY-MM-DD format
  - `value`: Target turnover amount (decimal number)

**Empty Response (no targets set):**
```json
{
  "pharmacy_id": 1,
  "month": "2025-11",
  "targets": []
}
```

**Error Responses:**
- `400 Bad Request`: Invalid month format (must be YYYY-MM)
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: User doesn't have read access to this pharmacy
- `404 Not Found`: Pharmacy doesn't exist

---

### 2. Save/Update Targets for a Month

**Endpoint:** `POST /admin/pharmacies/{pharmacy_id}/targets`

**Query Parameters:**
- `month` (required): Month in `YYYY-MM` format (e.g., `2025-11`)

**Request Body:**
```json
{
  "2025-11-01": 8500.00,
  "2025-11-02": 9200.00,
  "2025-11-15": 10000.00,
  "2025-11-20": 11000.00
}
```

**Request Format:**
- **Keys:** Date strings in `YYYY-MM-DD` format
- **Values:** Decimal numbers representing target turnover amount (in Rands)
- Only dates within the specified month will be processed
- Dates outside the month will return a 400 error

**Example Request:**
```javascript
const pharmacyId = 1;
const month = "2025-11";

// Targets object: date string -> target value
const targets = {
  "2025-11-01": 8500.00,
  "2025-11-02": 9200.00,
  "2025-11-15": 10000.00,
  "2025-11-20": 11000.00
};

const response = await fetch(
  `${API_BASE_URL}/admin/pharmacies/${pharmacyId}/targets?month=${month}`,
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(targets)
  }
);

const result = await response.json();
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Targets saved successfully",
  "saved_count": 4,
  "pharmacy_id": 1,
  "month": "2025-11"
}
```

**Response Format:**
- `success`: Boolean indicating success
- `message`: Human-readable success message
- `saved_count`: Number of targets saved/updated
- `pharmacy_id`: The pharmacy ID
- `month`: The month these targets belong to

**Important Notes:**
- **UPSERT Logic:** If a target exists for a date, it will be **updated**. If not, it will be **created**.
- **Partial Updates:** You can send only the dates that have changed. Other dates remain unchanged.
- **Validation:** The API validates:
  - Date format (must be YYYY-MM-DD)
  - Date is within the specified month
  - Target value is >= 0
  - Target value is <= 10,000,000 (reasonable maximum)

**Error Responses:**
- `400 Bad Request`: 
  - Empty request body: `{"detail": "No targets provided"}`
  - Invalid date format: `{"detail": "Invalid date format: 2025-11-XX. Must be YYYY-MM-DD"}`
  - Date outside month: `{"detail": "Date 2025-12-01 is outside the specified month 2025-11"}`
  - Negative value: `{"detail": "Target value cannot be negative: -1000"}`
  - Invalid month format: `{"detail": "Month must be in YYYY-MM format"}`
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: User doesn't have write access to this pharmacy
- `404 Not Found`: Pharmacy doesn't exist

---

### 3. Delete a Target

**Endpoint:** `DELETE /admin/pharmacies/{pharmacy_id}/targets/{date}`

**Path Parameters:**
- `pharmacy_id`: Pharmacy ID
- `date`: Date in `YYYY-MM-DD` format

**Example Request:**
```javascript
const pharmacyId = 1;
const date = "2025-11-15";

const response = await fetch(
  `${API_BASE_URL}/admin/pharmacies/${pharmacyId}/targets/${date}`,
  {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  }
);

const result = await response.json();
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Target deleted successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid date format
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: User doesn't have write access to this pharmacy
- `404 Not Found`: Target doesn't exist for that date

---

## 💻 Frontend Implementation Examples

### Complete Service Class

```javascript
// targetsService.js
const API_BASE_URL = 'https://pharmacy-api-webservice.onrender.com';

class TargetsService {
  constructor(getAuthToken) {
    this.getAuthToken = getAuthToken;
  }
  
  getHeaders() {
    return {
      'Authorization': `Bearer ${this.getAuthToken()}`,
      'Content-Type': 'application/json'
    };
  }
  
  /**
   * Get all targets for a pharmacy in a specific month
   * @param {number} pharmacyId - Pharmacy ID
   * @param {string} month - Month in YYYY-MM format
   * @returns {Promise<{pharmacy_id: number, month: string, targets: Array}>}
   */
  async getTargets(pharmacyId, month) {
    const response = await fetch(
      `${API_BASE_URL}/admin/pharmacies/${pharmacyId}/targets?month=${month}`,
      {
        headers: this.getHeaders()
      }
    );
    
    if (response.status === 401) {
      throw new Error('Unauthorized. Please log in again.');
    }
    
    if (response.status === 403) {
      throw new Error('Access denied. You do not have permission to view targets for this pharmacy.');
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch targets');
    }
    
    return await response.json();
  }
  
  /**
   * Save or update targets for a pharmacy and month
   * @param {number} pharmacyId - Pharmacy ID
   * @param {string} month - Month in YYYY-MM format
   * @param {Object} targets - Object with date strings as keys and target values as numbers
   * @returns {Promise<{success: boolean, saved_count: number}>}
   */
  async saveTargets(pharmacyId, month, targets) {
    if (!targets || Object.keys(targets).length === 0) {
      throw new Error('No targets provided');
    }
    
    const response = await fetch(
      `${API_BASE_URL}/admin/pharmacies/${pharmacyId}/targets?month=${month}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(targets)
      }
    );
    
    if (response.status === 401) {
      throw new Error('Unauthorized. Please log in again.');
    }
    
    if (response.status === 403) {
      throw new Error('Access denied. You do not have write permission for this pharmacy.');
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to save targets');
    }
    
    return await response.json();
  }
  
  /**
   * Delete a target for a specific date
   * @param {number} pharmacyId - Pharmacy ID
   * @param {string} date - Date in YYYY-MM-DD format
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async deleteTarget(pharmacyId, date) {
    const response = await fetch(
      `${API_BASE_URL}/admin/pharmacies/${pharmacyId}/targets/${date}`,
      {
        method: 'DELETE',
        headers: this.getHeaders()
      }
    );
    
    if (response.status === 401) {
      throw new Error('Unauthorized. Please log in again.');
    }
    
    if (response.status === 403) {
      throw new Error('Access denied. You do not have write permission for this pharmacy.');
    }
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete target');
    }
    
    return await response.json();
  }
}

export default TargetsService;
```

---

## 🎨 React Component Examples

### Loading Targets

```jsx
import { useState, useEffect } from 'react';
import TargetsService from './services/targetsService';

function TargetsTable({ pharmacyId, month }) {
  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const targetsService = new TargetsService(() => getAuthToken()); // Your auth token getter
  
  useEffect(() => {
    loadTargets();
  }, [pharmacyId, month]);
  
  async function loadTargets() {
    try {
      setLoading(true);
      setError(null);
      const data = await targetsService.getTargets(pharmacyId, month);
      setTargets(data.targets);
    } catch (err) {
      setError(err.message);
      console.error('Error loading targets:', err);
    } finally {
      setLoading(false);
    }
  }
  
  if (loading) return <div>Loading targets...</div>;
  if (error) return <div className="error">Error: {error}</div>;
  
  // Convert targets array to a map for easy lookup
  const targetsMap = {};
  targets.forEach(target => {
    targetsMap[target.date] = target.value;
  });
  
  // Generate all days in the month
  const daysInMonth = getDaysInMonth(month);
  
  return (
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Target (R)</th>
          <th>Purchase Budget (75%)</th>
        </tr>
      </thead>
      <tbody>
        {daysInMonth.map(day => (
          <tr key={day}>
            <td>{formatDate(day)}</td>
            <td>
              <input
                type="number"
                value={targetsMap[day] || ''}
                onChange={(e) => handleTargetChange(day, e.target.value)}
                placeholder="0.00"
              />
            </td>
            <td>R{((targetsMap[day] || 0) * 0.75).toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### Saving Targets

```jsx
function TargetsTable({ pharmacyId, month }) {
  const [targets, setTargets] = useState({}); // { "2025-11-01": 8500.00, ... }
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  
  const targetsService = new TargetsService(() => getAuthToken());
  
  // Handle individual target change
  function handleTargetChange(date, value) {
    const numValue = value === '' ? null : parseFloat(value);
    setTargets(prev => {
      const updated = { ...prev };
      if (numValue === null || numValue === 0) {
        delete updated[date];
      } else {
        updated[date] = numValue;
      }
      return updated;
    });
  }
  
  // Save all targets
  async function saveTargets() {
    if (Object.keys(targets).length === 0) {
      setSaveStatus({ type: 'error', message: 'No targets to save' });
      return;
    }
    
    try {
      setSaving(true);
      setSaveStatus(null);
      
      const result = await targetsService.saveTargets(pharmacyId, month, targets);
      
      setSaveStatus({
        type: 'success',
        message: `Successfully saved ${result.saved_count} target(s)`
      });
      
      // Optionally reload targets to get updated data
      await loadTargets();
      
    } catch (err) {
      setSaveStatus({
        type: 'error',
        message: err.message
      });
      console.error('Error saving targets:', err);
    } finally {
      setSaving(false);
    }
  }
  
  return (
    <div>
      {/* Targets table */}
      <table>...</table>
      
      {/* Save button */}
      <button 
        onClick={saveTargets} 
        disabled={saving || Object.keys(targets).length === 0}
      >
        {saving ? 'Saving...' : 'Save Targets'}
      </button>
      
      {/* Status message */}
      {saveStatus && (
        <div className={saveStatus.type === 'success' ? 'success' : 'error'}>
          {saveStatus.message}
        </div>
      )}
    </div>
  );
}
```

### Optimistic Updates (Save on Change)

```jsx
function TargetsTable({ pharmacyId, month }) {
  const [targets, setTargets] = useState({});
  const [pendingSaves, setPendingSaves] = useState(new Set());
  
  const targetsService = new TargetsService(() => getAuthToken());
  
  // Auto-save when user changes a target (with debounce)
  const debouncedSave = useMemo(
    () => debounce(async (date, value) => {
      try {
        setPendingSaves(prev => new Set(prev).add(date));
        
        await targetsService.saveTargets(pharmacyId, month, {
          [date]: value
        });
        
        setPendingSaves(prev => {
          const next = new Set(prev);
          next.delete(date);
          return next;
        });
      } catch (err) {
        console.error('Error saving target:', err);
        // Show error notification
      }
    }, 1000), // Wait 1 second after user stops typing
    [pharmacyId, month]
  );
  
  function handleTargetChange(date, value) {
    const numValue = parseFloat(value) || 0;
    setTargets(prev => ({ ...prev, [date]: numValue }));
    
    // Trigger debounced save
    debouncedSave(date, numValue);
  }
  
  return (
    <table>
      <tbody>
        {daysInMonth.map(day => (
          <tr key={day}>
            <td>{formatDate(day)}</td>
            <td>
              <input
                type="number"
                value={targets[day] || ''}
                onChange={(e) => handleTargetChange(day, e.target.value)}
              />
              {pendingSaves.has(day) && <span>Saving...</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

## 📊 Common Use Cases

### Use Case 1: Display Targets in Calendar View

```javascript
// Load targets for a month
const data = await targetsService.getTargets(1, "2025-11");

// Convert to map for easy lookup
const targetsMap = {};
data.targets.forEach(target => {
  targetsMap[target.date] = target.value;
});

// Display in calendar
calendarDays.forEach(day => {
  const target = targetsMap[day.date];
  if (target) {
    day.target = target;
    day.purchaseBudget = target * 0.75; // 75% of target
  }
});
```

### Use Case 2: Bulk Set Targets for Multiple Days

```javascript
// User selects multiple days and sets a target value
const selectedDays = ["2025-11-01", "2025-11-02", "2025-11-03"];
const targetValue = 10000.00;

// Build targets object
const targets = {};
selectedDays.forEach(date => {
  targets[date] = targetValue;
});

// Save all at once
await targetsService.saveTargets(1, "2025-11", targets);
```

### Use Case 3: Copy Targets from Previous Month

```javascript
// Get targets from previous month
const previousMonth = "2025-10";
const data = await targetsService.getTargets(1, previousMonth);

// Convert to new month's dates
const currentMonth = "2025-11";
const newTargets = {};

data.targets.forEach(target => {
  // Convert date to new month (keep day number)
  const date = new Date(target.date);
  const newDate = new Date(currentMonth + "-01");
  newDate.setDate(date.getDate());
  
  // Only include valid dates (e.g., don't include Nov 31)
  if (newDate.getMonth() === parseInt(currentMonth.split('-')[1]) - 1) {
    newTargets[newDate.toISOString().split('T')[0]] = target.value;
  }
});

// Save new targets
await targetsService.saveTargets(1, currentMonth, newTargets);
```

### Use Case 4: Clear All Targets for a Month

```javascript
// Get all targets for the month
const data = await targetsService.getTargets(1, "2025-11");

// Delete each target
for (const target of data.targets) {
  await targetsService.deleteTarget(1, target.date);
}
```

---

## 🔍 Error Handling Best Practices

```javascript
async function handleTargetsOperation(operation) {
  try {
    return await operation();
  } catch (error) {
    // Handle specific error types
    if (error.message.includes('Unauthorized')) {
      // Token expired - redirect to login
      redirectToLogin();
      return;
    }
    
    if (error.message.includes('Access denied')) {
      // User doesn't have permission
      showError('You do not have permission to perform this action.');
      return;
    }
    
    if (error.message.includes('Invalid date format')) {
      // Date format error
      showError('Invalid date format. Please use YYYY-MM-DD format.');
      return;
    }
    
    if (error.message.includes('outside the specified month')) {
      // Date outside month
      showError('Date is outside the selected month.');
      return;
    }
    
    // Generic error
    showError(error.message || 'An error occurred. Please try again.');
    console.error('Targets operation error:', error);
  }
}

// Usage
await handleTargetsOperation(async () => {
  return await targetsService.saveTargets(pharmacyId, month, targets);
});
```

---

## ✅ Validation Checklist

Before sending targets to the API, validate:

- [ ] Month format is `YYYY-MM` (e.g., "2025-11")
- [ ] Date strings are in `YYYY-MM-DD` format
- [ ] Dates are within the specified month
- [ ] Target values are numbers (not strings)
- [ ] Target values are >= 0
- [ ] Target values are reasonable (e.g., <= 10,000,000)
- [ ] User has write access to the pharmacy (for POST/DELETE)
- [ ] User has read access to the pharmacy (for GET)

---

## 📝 Summary

**Key Points:**
1. **Authentication:** Use Bearer token in Authorization header
2. **Authorization:** API checks pharmacy access automatically
3. **Month Format:** Always use `YYYY-MM` format (e.g., "2025-11")
4. **Date Format:** Always use `YYYY-MM-DD` format (e.g., "2025-11-15")
5. **UPSERT Logic:** POST updates existing targets and creates new ones
6. **Partial Updates:** You can send only changed dates
7. **Error Handling:** Check for 401, 403, 400, 404 errors

**API Endpoints:**
- `GET /admin/pharmacies/{pharmacy_id}/targets?month=YYYY-MM` - Get targets
- `POST /admin/pharmacies/{pharmacy_id}/targets?month=YYYY-MM` - Save/update targets
- `DELETE /admin/pharmacies/{pharmacy_id}/targets/{date}` - Delete a target

The targets API is now ready to use! 🎉



