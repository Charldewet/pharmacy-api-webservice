# Stock On Hand (SOH) API Guide for Frontend Team

## 📦 Overview

Stock On Hand (SOH) data is extracted from **GP (Gross Profit) reports** and stored in the database. All stock activity endpoints include the `on_hand` field in their responses.

---

## 🔍 Available Endpoints with SOH Data

### **1. General Stock Activity (Single Date) - Includes SOH**

**Endpoint:** `GET /pharmacies/{pharmacyId}/stock-activity`

**Use Case:** Get all products with their stock on hand for a specific date

**Example:**
```javascript
// Get stock activity for Oct 28, 2025 (includes SOH)
const url = `https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity?date=2025-10-28&limit=100`;

const response = await fetch(url, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
// data.items[].on_hand contains the stock on hand value
```

**Response Format:**
```json
{
  "items": [
    {
      "department_code": "PDOE04",
      "product_code": "LP9037679",
      "description": "ALLERGEX TABS 30",
      "qty_sold": 3.0,
      "sales_val": 54.66,
      "cost_of_sales": 52.50,
      "gp_value": 2.16,
      "gp_pct": 3.90,
      "on_hand": 116.7,  // ← Stock On Hand
      "product_id": 12345
    }
  ],
  "nextCursor": "54.66:12345"
}
```

---

### **2. Stock Activity by Quantity (Single Date) - Includes SOH**

**Endpoint:** `GET /pharmacies/{pharmacyId}/stock-activity/by-quantity`

**Use Case:** Get products sorted by quantity sold, includes SOH

**Example:**
```javascript
const url = `https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity/by-quantity?date=2025-10-28&limit=50`;

const response = await fetch(url, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
data.items.forEach(product => {
  console.log(`${product.description}: SOH = ${product.on_hand} units`);
});
```

---

### **3. Negative Stock On Hand (Out of Stock Items)**

**Endpoint:** `GET /pharmacies/{pharmacyId}/stock-activity/negative-soh`

**Use Case:** Find products with negative stock (out of stock situations)

**Example:**
```javascript
const url = `https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity/negative-soh?date=2025-10-28&limit=100`;

const response = await fetch(url, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
// Returns only products where on_hand < 0
data.items.forEach(product => {
  console.log(`${product.description}: Out of stock (SOH: ${product.on_hand})`);
});
```

**Response:** Only products with `on_hand < 0`, sorted by most negative first

---

### **4. Worst GP Products (Single Date) - Includes SOH**

**Endpoint:** `GET /pharmacies/{pharmacyId}/stock-activity/worst-gp`

**Use Case:** Get products with worst GP%, includes SOH data

**Example:**
```javascript
const url = `https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity/worst-gp?date=2025-10-28&limit=50`;

const response = await fetch(url, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
// All items include on_hand field
```

---

## 📊 SOH Field Details

### **Field Name:** `on_hand`
- **Type:** `number` (can be `null`)
- **Description:** Stock on hand quantity for the product on the specified date
- **Units:** Product units (e.g., tablets, bottles, boxes)
- **Can be negative:** Yes (indicates out of stock/backorder situation)
- **Source:** Extracted from GP (Gross Profit) reports

### **Example Values:**
- `116.7` - 116.7 units in stock
- `0.0` - Zero stock
- `-5.3` - Negative stock (out of stock, 5.3 units backordered)
- `null` - No SOH data available for this product/date

---

## 💻 Complete JavaScript Example

```javascript
/**
 * Get Stock On Hand for a specific product on a specific date
 */
async function getProductSOH(pharmacyId, productCode, date) {
  const API_KEY = 'your-api-key-here';
  const API_BASE_URL = 'https://pharmacy-api-webservice.onrender.com';
  
  const url = `${API_BASE_URL}/pharmacies/${pharmacyId}/stock-activity?date=${date}&limit=500`;
  
  try {
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
    
    // Find the specific product
    const product = data.items.find(item => item.product_code === productCode);
    
    if (product) {
      return {
        productCode: product.product_code,
        productName: product.description,
        stockOnHand: product.on_hand,
        quantitySold: product.qty_sold,
        salesValue: product.sales_val,
        date: date
      };
    }
    
    return null; // Product not found
  } catch (error) {
    console.error('Error fetching SOH:', error);
    throw error;
  }
}

// Usage
const sohData = await getProductSOH(1, 'LP9037679', '2025-10-28');
if (sohData) {
  console.log(`${sohData.productName}: ${sohData.stockOnHand} units in stock`);
}
```

---

## 📈 Tracking SOH Over Time

To track stock on hand changes over multiple days, call the endpoint for each date:

```javascript
/**
 * Get SOH history for a product over a date range
 */
async function getSOHHistory(pharmacyId, productCode, fromDate, toDate) {
  const API_KEY = 'your-api-key-here';
  const API_BASE_URL = 'https://pharmacy-api-webservice.onrender.com';
  
  const history = [];
  const start = new Date(fromDate);
  const end = new Date(toDate);
  
  // Iterate through each date
  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split('T')[0]; // YYYY-MM-DD
    
    const url = `${API_BASE_URL}/pharmacies/${pharmacyId}/stock-activity?date=${dateStr}&limit=500`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const product = data.items.find(item => item.product_code === productCode);
        
        if (product && product.on_hand !== null) {
          history.push({
            date: dateStr,
            stockOnHand: product.on_hand,
            quantitySold: product.qty_sold
          });
        }
      }
    } catch (error) {
      console.error(`Error fetching SOH for ${dateStr}:`, error);
    }
  }
  
  return history;
}

// Usage: Get SOH history for October
const history = await getSOHHistory(1, 'LP9037679', '2025-10-01', '2025-10-29');
console.table(history);
```

---

## 🚨 Negative Stock Alert

Use the negative SOH endpoint to find out-of-stock items:

```javascript
/**
 * Get all products with negative stock (out of stock)
 */
async function getOutOfStockProducts(pharmacyId, date) {
  const API_KEY = 'your-api-key-here';
  const API_BASE_URL = 'https://pharmacy-api-webservice.onrender.com';
  
  const url = `${API_BASE_URL}/pharmacies/${pharmacyId}/stock-activity/negative-soh?date=${date}&limit=200`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${API_KEY}`,
      'Content-Type': 'application/json'
    }
  });
  
  const data = await response.json();
  
  return data.items.map(item => ({
    productCode: item.product_code,
    productName: item.description,
    stockOnHand: item.on_hand,  // Will be negative
    department: item.department_code
  }));
}

// Usage
const outOfStock = await getOutOfStockProducts(1, '2025-10-28');
console.log(`Found ${outOfStock.length} out-of-stock products`);
outOfStock.forEach(product => {
  console.log(`${product.productName}: ${product.stockOnHand} units (out of stock)`);
});
```

---

## 📋 Response Field Reference

All stock activity endpoints return items with this structure:

```typescript
interface StockItem {
  department_code?: string;      // Department code (e.g., "PDOE04")
  product_code: string;          // NAPPI code (e.g., "LP9037679")
  description?: string;          // Product name
  qty_sold?: number;            // Quantity sold on this date
  sales_val?: number;            // Sales value (R)
  cost_of_sales?: number;        // Cost of sales (R)
  gp_value?: number;            // Gross profit value (R)
  gp_pct?: number;              // Gross profit percentage
  on_hand?: number | null;       // Stock on hand (units) ⭐
  product_id: number;            // Internal product ID
}
```

---

## ✅ Quick Reference

| Endpoint | SOH Included? | Use Case |
|----------|---------------|----------|
| `/stock-activity` | ✅ Yes | General stock activity for a date |
| `/stock-activity/by-quantity` | ✅ Yes | Top sellers by quantity |
| `/stock-activity/worst-gp` | ✅ Yes | Worst GP products |
| `/stock-activity/negative-soh` | ✅ Yes | **Only** products with negative SOH |
| `/stock-activity/by-quantity/range` | ❌ No | Best sellers over date range (aggregated) |
| `/stock-activity/low-gp/range` | ❌ No | Low GP products over date range (aggregated) |

**Note:** Date range endpoints (`/range`) aggregate data across multiple days, so they don't include `on_hand` (which is a point-in-time value). Use single-date endpoints to get SOH.

---

## 🎯 Common Use Cases

### **1. Display Current Stock Level**
```javascript
// Get SOH for today
const today = new Date().toISOString().split('T')[0];
const url = `/pharmacies/1/stock-activity?date=${today}&limit=500`;

// Find your product and display SOH
const product = data.items.find(p => p.product_code === 'LP9037679');
if (product) {
  displayStockLevel(product.on_hand); // Show in UI
}
```

### **2. Low Stock Alert**
```javascript
const LOW_STOCK_THRESHOLD = 10;

data.items.forEach(product => {
  if (product.on_hand !== null && product.on_hand < LOW_STOCK_THRESHOLD && product.on_hand >= 0) {
    showLowStockAlert(product);
  }
});
```

### **3. Out of Stock Detection**
```javascript
// Use the negative-soh endpoint
const outOfStock = await getOutOfStockProducts(pharmacyId, date);
if (outOfStock.length > 0) {
  showOutOfStockNotification(outOfStock);
}
```

### **4. Stock Trend Chart**
```javascript
// Get SOH history for last 30 days
const history = await getSOHHistory(pharmacyId, productCode, startDate, endDate);
plotStockChart(history); // Create a chart showing stock levels over time
```

---

## 🔗 Related Endpoints

- **Product Sales:** `/products/{productCode}/sales` - Get product performance (doesn't include SOH)
- **Best Sellers:** `/pharmacies/{id}/stock-activity/by-quantity/range` - Top products by quantity (no SOH)
- **Low GP:** `/pharmacies/{id}/stock-activity/low-gp/range` - Low GP products (no SOH)

---

## 📝 Notes

1. **SOH is point-in-time data** - It represents stock level at the end of the business day
2. **Updated daily** - SOH is updated when GP reports are processed (usually daily)
3. **Can be null** - Some products may not have SOH data if they weren't in the GP report
4. **Negative values** - Negative SOH indicates out-of-stock/backorder situations
5. **Source:** Extracted from GP reports (Gross Profit reports), not from inventory systems

---

## 🧪 Test URLs

### **Get SOH for Reitz, Oct 28:**
```
https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity?date=2025-10-28&limit=100
```

### **Get Out of Stock Products:**
```
https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity/negative-soh?date=2025-10-28&limit=100
```

### **Get SOH for Specific Product (search in results):**
```
https://pharmacy-api-webservice.onrender.com/pharmacies/1/stock-activity?date=2025-10-28&limit=500
```
Then filter results by `product_code` in your frontend code.

---

**Last Updated:** October 29, 2025  
**API Version:** v1  
**Status:** ✅ Production Ready



