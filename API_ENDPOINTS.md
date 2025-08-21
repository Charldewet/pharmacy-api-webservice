# 🚀 Pharmacy API - Complete Endpoints Reference

**Base URL**: `https://pharmacy-api-webservice.onrender.com`

**Authentication**: All endpoints require `Authorization: Bearer your-api-key` header

---

## 📊 **Core Business Intelligence Endpoints**

### **1. Health Check**
```http
GET /health
Response: {"ok": true}
Use Case: Service status monitoring
```

### **2. Pharmacies**
```http
GET /pharmacies
Response: List of all pharmacies with IDs and names
Use Case: Get pharmacy selection dropdown
```

---

## 📈 **Sales & Performance Analytics**

### **3. Daily Sales Data**
```http
# Get sales for specific date range
GET /pharmacies/{pharmacy_id}/days?from={start_date}&to={end_date}

# Examples:
GET /pharmacies/1/days?from=2025-08-01&to=2025-08-19
GET /pharmacies/1/days?from=2025-07-01&to=2025-07-31

Response: Array of daily sales records with:
- turnover, dispensary_turnover, frontshop_turnover
- gp_value, gp_pct, scripts_qty, transaction_count
- sales_cash, sales_account, avg_basket
Use Case: Daily performance dashboards, trend analysis
```

### **4. Month-to-Date (MTD) Analytics**
```http
# Get MTD with specific cutoff date (on-the-fly calculation)
GET /pharmacies/{pharmacy_id}/mtd?month={YYYY-MM}&through={YYYY-MM-DD}

# Get pre-aggregated MTD (as of last refresh)
GET /pharmacies/{pharmacy_id}/mtd?month={YYYY-MM}

# Examples:
GET /pharmacies/1/mtd?month=2025-08&through=2025-08-19
GET /pharmacies/1/mtd?month=2025-08

Response: MTD totals including:
- turnover, dispensary_turnover, frontshop_turnover
- gp_value, scripts_qty, transaction_count
Use Case: Monthly performance summaries, progress tracking
```

### **5. Year-to-Date (YTD) Analytics**
```http
# Get YTD with specific cutoff date (on-the-fly calculation)
GET /pharmacies/{pharmacy_id}/ytd?year={YYYY}&through={YYYY-MM-DD}

# Get pre-aggregated YTD (as of last refresh)
GET /pharmacies/{pharmacy_id}/ytd?year={YYYY}

# Examples:
GET /pharmacies/1/ytd?year=2025&through=2025-08-19
GET /pharmacies/1/ytd?year=2025

Response: YTD totals including:
- turnover, dispensary_turnover, frontshop_turnover
- gp_value, scripts_qty, transaction_count
Use Case: Annual performance summaries, year-over-year comparisons
```

---

## 🏥 **Product & Stock Analytics**

### **6. Stock Activity - Top Sellers by Value**
```http
GET /pharmacies/{pharmacy_id}/stock-activity?date={YYYY-MM-DD}&limit={number}

# Examples:
GET /pharmacies/1/stock-activity?date=2025-08-19&limit=20
GET /pharmacies/1/stock-activity?date=2025-08-19&limit=50

Response: Top selling products sorted by sales value with:
- product_code, description, department_code
- qty_sold, sales_val, cost_of_sales, gp_value, gp_pct
Use Case: Best performing products, revenue analysis
```

### **7. Stock Activity - Top Sellers by Quantity**
```http
GET /pharmacies/{pharmacy_id}/stock-activity/by-quantity?date={YYYY-MM-DD}&limit={number}

# Examples:
GET /pharmacies/1/stock-activity/by-quantity?date=2025-08-19&limit=20
GET /pharmacies/1/stock-activity/by-quantity?date=2025-08-19&limit=50

Response: Top selling products sorted by quantity sold with:
- product_code, description, department_code
- qty_sold, sales_val, cost_of_sales, gp_value, gp_pct
Use Case: Volume analysis, inventory planning
```

### **8. Stock Activity - Worst GP% Items**
```http
GET /pharmacies/{pharmacy_id}/stock-activity/worst-gp?date={YYYY-MM-DD}&limit={number}

# Examples:
GET /pharmacies/1/stock-activity/worst-gp?date=2025-08-19&limit=20
GET /pharmacies/1/stock-activity/worst-gp?date=2025-08-19&limit=50

Response: Products with lowest gross profit percentage with:
- product_code, description, department_code
- qty_sold, sales_val, cost_of_sales, gp_value, gp_pct
Use Case: Margin analysis, pricing optimization
```

---

## 📋 **Product Performance Analytics**

### **9. Product Sales - Detailed with Daily Breakdown**
```http
GET /products/{product_code}/sales?from_date={YYYY-MM-DD}&to_date={YYYY-MM-DD}&pharmacy_id={id}

# Examples:
GET /products/LP9040024/sales?from_date=2025-08-01&to_date=2025-08-19&pharmacy_id=1
GET /products/ABC123/sales?from_date=2025-07-01&to_date=2025-07-31&pharmacy_id=1

Response: Complete product performance including:
- Summary: total_qty_sold, total_sales_value, total_gp_value, avg_gp_percentage
- Daily breakdown: daily sales data for each date
Use Case: Product performance tracking, trend analysis
```

### **10. Product Sales - Summary Only**
```http
GET /products/{product_code}/sales/summary?from_date={YYYY-MM-DD}&to_date={YYYY-MM-DD}&pharmacy_id={id}

# Examples:
GET /products/LP9040024/sales/summary?from_date=2025-08-01&to_date=2025-08-19&pharmacy_id=1

Response: Product performance summary only (no daily breakdown)
Use Case: Quick product overviews, summary dashboards
```

### **11. Product Search - Find Products**
```http
GET /products/search?query={search_term}&page={page}&page_size={size}&pharmacy_id={id}

# Examples:
GET /products/search?query=ADCO&page=1&page_size=20
GET /products/search?query=LP906&page=1&page_size=50
GET /products/search?query=PARACETAMOL

Response: Paginated list of products matching search term with:
- product_code, description, department_code, department_name
- total_count, page, page_size, has_more
Use Case: Product discovery, search functionality, product lookup
```

### **12. Product Information - Basic Details**
```http
GET /products/{product_code}?pharmacy_id={id}

# Examples:
GET /products/LP9066287
GET /products/LP9040024

Response: Basic product information including:
- product_code, description, department_code, department_name
Use Case: Product details without requiring date ranges, product lookup
```

---

## 📊 **Reporting & Coverage**

### **11. Logbook - Report Coverage**
```http
# Get missing reports only
GET /pharmacies/{pharmacy_id}/logbook?from={YYYY-MM-DD}&to={YYYY-MM-DD}&missingOnly=true

# Get all reports
GET /pharmacies/{pharmacy_id}/logbook?from={YYYY-MM-DD}&to={YYYY-MM-DD}

# Examples:
GET /pharmacies/1/logbook?from=2025-08-01&to=2025-08-19&missingOnly=true
GET /pharmacies/1/logbook?from=2025-08-01&to=2025-08-19

Response: Report coverage status including:
- business_date, pharmacy_id
- inv249_turnover, stk261_trading, phm080_scripts, stk260_gp
- last_updated
Use Case: Report completion tracking, data quality monitoring
```

---

## 🔐 **Authentication & Headers**

### **Required Headers for All Endpoints:**
```http
Authorization: Bearer your-api-key-here
Content-Type: application/json
```

### **Example Request:**
```javascript
const response = await fetch('https://pharmacy-api-webservice.onrender.com/pharmacies', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer your-api-key-here',
    'Content-Type': 'application/json'
  }
});
```

---

## 📱 **Frontend Integration Examples**

### **JavaScript/TypeScript Examples:**

#### **Get Daily Sales for Date Range:**
```javascript
const getDailySales = async (pharmacyId, fromDate, toDate) => {
  const response = await fetch(
    `https://pharmacy-api-webservice.onrender.com/pharmacies/${pharmacyId}/days?from=${fromDate}&to=${toDate}`,
    {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  );
  return response.json();
};
```

#### **Get MTD with Specific Cutoff:**
```javascript
const getMTD = async (pharmacyId, month, throughDate) => {
  const response = await fetch(
    `https://pharmacy-api-webservice.onrender.com/pharmacies/${pharmacyId}/mtd?month=${month}&through=${throughDate}`,
    {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  );
  return response.json();
};
```

#### **Get Product Performance:**
```javascript
const getProductSales = async (productCode, fromDate, toDate, pharmacyId = 1) => {
  const response = await fetch(
    `https://pharmacy-api-webservice.onrender.com/products/${productCode}/sales?from_date=${fromDate}&to_date=${toDate}&pharmacy_id=${pharmacyId}`,
    {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  );
  return response.json();
};
```

#### **Search for Products:**
```javascript
const searchProducts = async (query, page = 1, pageSize = 50, pharmacyId = 1) => {
  const response = await fetch(
    `https://pharmacy-api-webservice.onrender.com/products/search?query=${encodeURIComponent(query)}&page=${page}&page_size=${pageSize}&pharmacy_id=${pharmacyId}`,
    {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  );
  return response.json();
};
```

#### **Get Product Information:**
```javascript
const getProductInfo = async (productCode, pharmacyId = 1) => {
  const response = await fetch(
    `https://pharmacy-api-webservice.onrender.com/products/${productCode}?pharmacy_id=${pharmacyId}`,
    {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json'
      }
    }
  );
  return response.json();
};
```

---

## 🎯 **Common Use Cases by Endpoint**

| Use Case | Recommended Endpoints |
|----------|----------------------|
| **Dashboard Overview** | `/health`, `/pharmacies`, `/pharmacies/{id}/mtd` |
| **Daily Performance** | `/pharmacies/{id}/days` |
| **Monthly Tracking** | `/pharmacies/{id}/mtd` |
| **Annual Summary** | `/pharmacies/{id}/ytd` |
| **Product Analysis** | `/products/{code}/sales`, `/pharmacies/{id}/stock-activity` |
| **Best Sellers** | `/pharmacies/{id}/stock-activity` (by value/quantity) |
| **Margin Analysis** | `/pharmacies/{id}/stock-activity/worst-gp` |
| **Report Monitoring** | `/pharmacies/{id}/logbook` |

---

## 🚨 **Error Handling**

### **Common HTTP Status Codes:**
- **200**: Success
- **400**: Bad Request (invalid parameters)
- **401**: Unauthorized (missing/invalid API key)
- **404**: Not Found (no data for parameters)
- **500**: Internal Server Error (server issue)

### **Error Response Format:**
```json
{
  "detail": "Error description message"
}
```

---

## 📊 **Data Models Reference**

### **Pharmacy:**
```json
{
  "pharmacy_id": 1,
  "name": "REITZ APTEEK"
}
```

### **Daily Sales:**
```json
{
  "business_date": "2025-08-19",
  "pharmacy_id": 1,
  "turnover": 76888.39,
  "dispensary_turnover": 51053.73,
  "frontshop_turnover": 25834.66,
  "gp_value": 19287.48,
  "gp_pct": 25.09,
  "scripts_qty": 124,
  "transaction_count": 317
}
```

### **Product Sales:**
```json
{
  "product_code": "LP9040024",
  "description": "LEVEMIR FLEXPEN 5X3ML",
  "total_qty_sold": 1.0,
  "total_sales_value": 978.97,
  "total_gp_value": 34.33,
  "avg_gp_percentage": 3.51
}
```

---

## 🔗 **Quick Links**

- **Live API**: https://pharmacy-api-webservice.onrender.com
- **API Documentation**: https://pharmacy-api-webservice.onrender.com/docs
- **Health Check**: https://pharmacy-api-webservice.onrender.com/health
- **GitHub Repository**: https://github.com/Charldewet/pharmacy-api-webservice

---

**🎯 Your frontend team now has everything needed to build powerful pharmacy management dashboards!** 