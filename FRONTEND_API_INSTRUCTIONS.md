# Frontend API Usage Instructions - Worst GP Products

## 📋 Overview

This document provides step-by-step instructions for calling the **Worst GP Products API** endpoint from your frontend application. The endpoint returns products with low gross profit percentages within a specified date range.

---

## 🚀 API Endpoint Details

### **Endpoint URL**
```
GET https://pharmacy-api-webservice.onrender.com/pharmacies/{pharmacyId}/stock-activity/low-gp/range
```

### **Base URL**
```
https://pharmacy-api-webservice.onrender.com
```

---

## 📝 Required Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from` | string | ✅ Yes | Start date in format `YYYY-MM-DD` (e.g., "2025-10-01") |
| `to` | string | ✅ Yes | End date in format `YYYY-MM-DD` (e.g., "2025-10-29") |
| `threshold` | number | ✅ Yes | Maximum GP% to include (e.g., 20 for products with GP% ≤ 20%) |
| `limit` | number | ❌ No | Maximum number of products to return (default: 100, max: 500) |
| `exclude_pdst` | boolean | ❌ No | Set to `true` to exclude PDST/KSAA departments (default: false) |

---

## 🔐 Authentication

All API calls require authentication via one of these methods:

### **Option 1: Bearer Token (Recommended)**
```http
Authorization: Bearer your-api-key-here
```

### **Option 2: API Key Header**
```http
X-API-Key: your-api-key-here
```

---

## 💻 Implementation Examples

### **1. JavaScript/React - Using Fetch API**

#### **Basic Example (Monthly View)**
```javascript
async function getWorstGPProducts(pharmacyId, fromDate, toDate, threshold = 20, excludePdst = true) {
  const API_KEY = 'your-api-key-here';
  const API_BASE_URL = 'https://pharmacy-api-webservice.onrender.com';
  
  // Build query parameters
  const params = new URLSearchParams({
    from: fromDate,           // "2025-10-01"
    to: toDate,               // "2025-10-29"
    threshold: threshold.toString(),  // "20"
    limit: '50',
    exclude_pdst: excludePdst.toString()  // "true" or "false"
  });
  
  const url = `${API_BASE_URL}/pharmacies/${pharmacyId}/stock-activity/low-gp/range?${params}`;
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.items; // Array of products
  } catch (error) {
    console.error('Error fetching worst GP products:', error);
    throw error;
  }
}

// Usage Example
async function loadWorstGPForMonth() {
  const pharmacyId = 1; // Reitz
  const fromDate = '2025-10-01';  // First day of month
  const toDate = '2025-10-29';    // Today/selected date
  const threshold = 20;           // GP% ≤ 20%
  
  try {
    const products = await getWorstGPProducts(pharmacyId, fromDate, toDate, threshold, true);
    console.log(`Found ${products.length} products with low GP`);
    
    // Display products
    products.forEach(product => {
      console.log(`${product.product_name}: GP% = ${product.gp_percent}%`);
    });
    
    return products;
  } catch (error) {
    console.error('Failed to load worst GP products:', error);
    return [];
  }
}
```

#### **With Error Handling & Loading States**
```javascript
function WorstGPComponent() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const fetchWorstGP = async (pharmacyId, fromDate, toDate) => {
    setLoading(true);
    setError(null);
    
    try {
      const API_KEY = 'your-api-key-here';
      const params = new URLSearchParams({
        from: fromDate,
        to: toDate,
        threshold: '20',
        limit: '50',
        exclude_pdst: 'true'
      });
      
      const url = `https://pharmacy-api-webservice.onrender.com/pharmacies/${pharmacyId}/stock-activity/low-gp/range?${params}`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setProducts(data.items || []);
    } catch (err) {
      setError(err.message);
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      {loading && <div>Loading worst GP products...</div>}
      {error && <div className="error">Error: {error}</div>}
      {!loading && !error && (
        <div>
          <h3>Worst GP Products: {products.length}</h3>
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>GP%</th>
                <th>Quantity</th>
                <th>Sales</th>
              </tr>
            </thead>
            <tbody>
              {products.map((product, index) => (
                <tr key={index}>
                  <td>{product.product_name}</td>
                  <td>{product.gp_percent}%</td>
                  <td>{product.quantity_sold}</td>
                  <td>R{product.total_sales.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

---

### **2. Using Axios**

```javascript
import axios from 'axios';

async function getWorstGPProducts(pharmacyId, fromDate, toDate) {
  const API_KEY = 'your-api-key-here';
  const API_BASE_URL = 'https://pharmacy-api-webservice.onrender.com';
  
  try {
    const response = await axios.get(
      `${API_BASE_URL}/pharmacies/${pharmacyId}/stock-activity/low-gp/range`,
      {
        params: {
          from: fromDate,
          to: toDate,
          threshold: 20,
          limit: 50,
          exclude_pdst: true
        },
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    return response.data.items;
  } catch (error) {
    console.error('API Error:', error.response?.data || error.message);
    throw error;
  }
}
```

---

### **3. Complete Monthly Summary Integration**

```javascript
// Example: Load worst GP products for monthly summary view
async function loadMonthlyWorstGP(selectedDate, pharmacyId) {
  // Calculate date range: First day of month to selected date
  const date = new Date(selectedDate);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  
  const fromDate = `${year}-${month}-01`;        // First day of month
  const toDate = `${year}-${month}-${day}`;      // Selected date
  
  const API_KEY = 'your-api-key-here';
  const params = new URLSearchParams({
    from: fromDate,
    to: toDate,
    threshold: '20',
    limit: '50',
    exclude_pdst: 'true'
  });
  
  const url = `https://pharmacy-api-webservice.onrender.com/pharmacies/${pharmacyId}/stock-activity/low-gp/range?${params}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }
    
    const data = await response.json();
    return data.items || [];
  } catch (error) {
    console.error('Failed to load worst GP:', error);
    return [];
  }
}

// Usage in your dashboard component
document.getElementById('loadWorstGP').addEventListener('click', async () => {
  const selectedDate = document.getElementById('datePicker').value; // "2025-10-29"
  const pharmacyId = 1; // Reitz
  
  const products = await loadMonthlyWorstGP(selectedDate, pharmacyId);
  
  // Display top 5 worst GP products
  const top5 = products.slice(0, 5);
  displayWorstGP(top5);
});
```

---

## 📦 Response Format

### **Success Response (200 OK)**

```json
{
  "items": [
    {
      "product_name": "ULTIMAG ADVANCED EFF TABS 10",
      "nappi_code": "LP9120710",
      "quantity_sold": 2.0,
      "total_sales": 121.66,
      "total_cost": 127.06,
      "gp_value": -5.4,
      "gp_percent": -4.44
    },
    {
      "product_name": "GAVISCON LIQUID 150ML ANISEED",
      "nappi_code": "LP9038884",
      "quantity_sold": 2.0,
      "total_sales": 125.14,
      "total_cost": 127.8,
      "gp_value": -2.66,
      "gp_percent": -2.13
    }
    // ... more products
  ]
}
```

### **Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | Array of product objects (sorted by GP% ascending - worst first) |
| `items[].product_name` | string | Product description/name |
| `items[].nappi_code` | string | Product NAPPI code |
| `items[].quantity_sold` | number | Total quantity sold across date range |
| `items[].total_sales` | number | Total sales value (R) |
| `items[].total_cost` | number | Total cost of sales (R) |
| `items[].gp_value` | number | Gross profit value (R) |
| `items[].gp_percent` | number | Gross profit percentage (can be negative) |

---

## 🎯 Common Use Cases

### **1. Monthly Summary View**
```javascript
// Get worst GP for the month (1st to selected date)
const fromDate = '2025-10-01';  // First of month
const toDate = '2025-10-29';    // Selected/today
const threshold = 20;           // GP% ≤ 20%
const excludePdst = true;       // Exclude PDST departments

// Shows products with low GP that need attention
```

### **2. Custom Date Range**
```javascript
// Get worst GP for any custom range
const fromDate = '2025-09-15';
const toDate = '2025-10-15';
const threshold = 15;  // Stricter threshold - GP% ≤ 15%

// Shows very low GP products in the range
```

### **3. Include PDST Products**
```javascript
// Set exclude_pdst to false to see ALL low GP products
const excludePdst = false;

// Shows ALL products including PDST/KSAA departments
```

---

## ⚠️ Error Handling

### **Error Responses**

#### **400 Bad Request**
```json
{
  "detail": "Missing required parameter: 'from'"
}
```

#### **401 Unauthorized**
```json
{
  "detail": "Invalid or missing API key"
}
```

#### **404 Not Found**
```json
{
  "detail": "No products found matching criteria"
}
```

### **Error Handling Example**
```javascript
async function getWorstGPWithErrorHandling(pharmacyId, fromDate, toDate) {
  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    });
    
    // Check for HTTP errors
    if (response.status === 401) {
      throw new Error('Invalid API key. Please check your authentication.');
    }
    
    if (response.status === 400) {
      const error = await response.json();
      throw new Error(error.detail || 'Invalid request parameters');
    }
    
    if (response.status === 404) {
      // No products found - this is OK, return empty array
      return [];
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    return data.items || [];
    
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      // Network error
      console.error('Network error - check your internet connection');
    } else {
      console.error('API Error:', error.message);
    }
    return []; // Return empty array on error
  }
}
```

---

## 🔧 Backend Proxy Approach (Your Current Setup)

If you're calling through your backend proxy (`/api/worst-gp`), the approach is the same:

```javascript
// Backend proxy endpoint
async function getWorstGPViaProxy(pharmacyId, fromDate, toDate) {
  const params = new URLSearchParams({
    pid: pharmacyId.toString(),
    from_date: fromDate,
    to_date: toDate,
    threshold: '20',
    limit: '50',
    exclude_pdst: 'true'
  });
  
  const url = `/api/worst-gp?${params}`;
  
  const response = await fetch(url);
  const data = await response.json();
  
  // Your backend transforms it to:
  // { pharmacy_id, date, worst_gp_products: [...] }
  return data.worst_gp_products || [];
}
```

**Note:** Your backend proxy handles authentication, so you don't need to include API keys in frontend code when using this approach.

---

## ✅ Testing Checklist

Before going live, test these scenarios:

- [ ] ✅ Correct date range (e.g., Oct 1-29)
- [ ] ✅ Different thresholds (10, 15, 20, 25)
- [ ] ✅ With `exclude_pdst=true` (should exclude PDST products)
- [ ] ✅ With `exclude_pdst=false` (should include ALL products)
- [ ] ✅ Different pharmacy IDs (1, 2, 101, etc.)
- [ ] ✅ Empty results (when no products match)
- [ ] ✅ Error handling (invalid dates, missing auth, etc.)
- [ ] ✅ Limit parameter (10, 50, 100, 500)
- [ ] ✅ Sorting (should be worst GP first - lowest GP% values)

---

## 🧪 Quick Test URLs

### **Test 1: Reitz, October, GP ≤ 20%, Exclude PDST**
```
https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity/low-gp/range?from=2025-10-01&to=2025-10-29&threshold=20&limit=50&exclude_pdst=true
```

### **Test 2: Umdoni, October, GP ≤ 15%, Include All**
```
https://pharmacy-api-webservice.onrender.com/pharmacies/101/stock-activity/low-gp/range?from=2025-10-01&to=2025-10-28&threshold=15&limit=100&exclude_pdst=false
```

### **Test 3: TLC Group (All Pharmacies), GP ≤ 10%**
```
https://pharmacy-api-webservice.onrender.com/pharmacies/100/stock-activity/low-gp/range?from=2025-10-01&to=2025-10-29&threshold=10&limit=100&exclude_pdst=true
```

---

## 📊 Expected Results

For **Reitz (pharmacy_id=1), October 1-29, GP% ≤ 20%, exclude PDST**:
- **Expected:** ~50 products
- **Worst GP:** -4.44% (ULTIMAG ADVANCED EFF TABS 10)
- **Best GP in results:** 20% (threshold limit)

---

## 🎨 UI Display Recommendations

```javascript
function displayWorstGP(products) {
  // Sort by GP% (already sorted by API, but ensure ascending)
  const sorted = products.sort((a, b) => (a.gp_percent || 0) - (b.gp_percent || 0));
  
  // Color coding
  const getGPColor = (gpPercent) => {
    if (gpPercent < 0) return 'red';        // Negative GP (loss)
    if (gpPercent < 5) return 'orange';     // Very low GP
    if (gpPercent < 10) return 'yellow';    // Low GP
    if (gpPercent < 20) return 'light-yellow'; // Moderate low
    return 'green';                          // Acceptable
  };
  
  // Display
  sorted.forEach(product => {
    const color = getGPColor(product.gp_percent);
    console.log(`${product.product_name}: ${product.gp_percent}% (${color})`);
  });
}
```

---

## 📞 Support

If you encounter issues:

1. **Check API Status:** `https://pharmacy-api-webservice.onrender.com/health`
2. **Verify Authentication:** Ensure API key is correct
3. **Check Parameters:** Verify date format (YYYY-MM-DD) and pharmacy ID
4. **Check Network:** Verify CORS is enabled for your domain
5. **Review Response:** Check browser DevTools Network tab for actual response

---

## 📚 Related Endpoints

- **Best Sellers by Quantity:** `/pharmacies/{id}/stock-activity/by-quantity/range`
- **Daily Worst GP:** `/pharmacies/{id}/stock-activity/worst-gp?date={YYYY-MM-DD}`
- **API Documentation:** `https://pharmacy-api-webservice.onrender.com/docs`

---

**Last Updated:** October 29, 2025
**API Version:** v1
**Status:** ✅ Production Ready

