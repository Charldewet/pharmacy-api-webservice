# Frontshop vs Dispensary GP Breakdown API Guide

Quick reference guide for the GP breakdown endpoints that show separate Gross Profit for dispensary (PDST departments) and frontshop (all other departments).

---

## Endpoints

### 1. Single Date GP Breakdown
**GET** `/pharmacies/{pharmacy_id}/days/{date}/gp-breakdown`

Get GP breakdown for a specific date.

### 2. Date Range GP Breakdown
**GET** `/pharmacies/{pharmacy_id}/days/gp-breakdown?from={start_date}&to={end_date}`

Get aggregated GP breakdown across a date range.

---

## Authentication

Both endpoints require API key authentication:
```
Authorization: Bearer YOUR_API_KEY
```
or
```
X-API-Key: YOUR_API_KEY
```

---

## Examples

### Single Date Example

**Request:**
```bash
GET /pharmacies/1/days/2025-12-08/gp-breakdown
```

**cURL:**
```bash
curl -X GET "https://api.example.com/pharmacies/1/days/2025-12-08/gp-breakdown" \
  -H "X-API-Key: YOUR_API_KEY"
```

**JavaScript:**
```javascript
const response = await fetch('/pharmacies/1/days/2025-12-08/gp-breakdown', {
  headers: {
    'X-API-Key': 'YOUR_API_KEY'
  }
});
const data = await response.json();
```

### Date Range Example

**Request:**
```bash
GET /pharmacies/1/days/gp-breakdown?from=2025-12-01&to=2025-12-08
```

**cURL:**
```bash
curl -X GET "https://api.example.com/pharmacies/1/days/gp-breakdown?from=2025-12-01&to=2025-12-08" \
  -H "X-API-Key: YOUR_API_KEY"
```

**JavaScript:**
```javascript
const fromDate = '2025-12-01';
const toDate = '2025-12-08';
const response = await fetch(
  `/pharmacies/1/days/gp-breakdown?from=${fromDate}&to=${toDate}`,
  {
    headers: {
      'X-API-Key': 'YOUR_API_KEY'
    }
  }
);
const data = await response.json();
```

---

## Response Structure

```json
{
  "business_date": "2025-12-08",
  "pharmacy_id": 1,
  "dispensary": {
    "product_count": 55,
    "sales_value": 7418.92,
    "cost_of_sales": 5861.45,
    "gross_profit": 1557.47,
    "gp_percentage": 20.99,
    "gp_percentage_of_total": 38.02
  },
  "frontshop": {
    "product_count": 89,
    "sales_value": 8418.67,
    "cost_of_sales": 5880.03,
    "gross_profit": 2538.64,
    "gp_percentage": 30.15,
    "gp_percentage_of_total": 61.98
  },
  "total": {
    "product_count": 144,
    "sales_value": 15837.59,
    "cost_of_sales": 11741.48,
    "gross_profit": 4096.11,
    "gp_percentage": 25.86
  },
  "daily_summary_gp": 4143.09,
  "difference": 46.98
}
```

### Response Fields

**Top Level:**
- `business_date`: Date (for single date) or start date (for range)
- `pharmacy_id`: Pharmacy ID
- `dispensary`: GP breakdown for dispensary (PDST departments)
- `frontshop`: GP breakdown for frontshop (all other departments)
- `total`: Total GP breakdown across all products
- `daily_summary_gp`: GP from daily sales summary (for comparison)
- `difference`: Difference between line-level GP and daily summary GP

**GP Breakdown Object (dispensary/frontshop/total):**
- `product_count`: Number of products (unique products for date range)
- `sales_value`: Total sales value (R)
- `cost_of_sales`: Total cost of sales (R)
- `gross_profit`: Total gross profit (R)
- `gp_percentage`: GP percentage (gross_profit / sales_value * 100)
- `gp_percentage_of_total`: Percentage of total GP (for dispensary/frontshop only)

---

## Use Cases

### Single Date
- **Daily performance analysis**: Compare frontshop vs dispensary GP for a specific day
- **Troubleshooting**: Investigate GP performance on a particular date
- **Daily reports**: Include in daily dashboard or reports

### Date Range
- **Weekly analysis**: Get GP breakdown for the week
- **Monthly analysis**: Get GP breakdown for the month
- **Period comparison**: Compare different time periods
- **Trend analysis**: See how frontshop vs dispensary GP changes over time

---

## How It Works

1. **Dispensary GP**: Calculated from all products in departments starting with "PDST" (PDST08, PDST22, PDST13, etc.)
2. **Frontshop GP**: Calculated from all products in all other departments
3. **Data Source**: Uses line-level GP report data (`fact_stock_activity` table)
4. **Aggregation**: For date ranges, sums all sales, costs, and GP across all dates in the range

---

## Error Responses

### 404 Not Found
```json
{
  "detail": "No GP report data found for pharmacy 1 on 2025-12-08. The GP report may not have been imported yet."
}
```

**Cause**: No GP report data exists for the specified date(s). The GP report may not have been imported yet.

### 400 Bad Request
```json
{
  "detail": "Invalid date format or range: Start date must be before or equal to end date"
}
```

**Cause**: Invalid date format or start date is after end date.

---

## Notes

- **Product Count**: For date ranges, this is the count of **unique products** across all dates, not the sum of products per day
- **GP Percentage**: Calculated as `(gross_profit / sales_value) * 100`
- **GP Percentage of Total**: Shows what percentage of total GP comes from dispensary vs frontshop
- **Comparison**: The `daily_summary_gp` field allows you to compare line-level GP with the daily summary GP for verification
- **Data Availability**: Requires GP reports to be imported. Check report coverage if data is missing.

---

## Quick Examples

### Get today's GP breakdown
```bash
GET /pharmacies/1/days/2025-12-08/gp-breakdown
```

### Get this week's GP breakdown
```bash
GET /pharmacies/1/days/gp-breakdown?from=2025-12-01&to=2025-12-08
```

### Get this month's GP breakdown
```bash
GET /pharmacies/1/days/gp-breakdown?from=2025-12-01&to=2025-12-31
```

### Get last 7 days GP breakdown
```bash
GET /pharmacies/1/days/gp-breakdown?from=2025-12-01&to=2025-12-07
```

---

## Frontend Integration Example

```javascript
async function getGPBreakdown(pharmacyId, fromDate, toDate) {
  const url = toDate 
    ? `/pharmacies/${pharmacyId}/days/gp-breakdown?from=${fromDate}&to=${toDate}`
    : `/pharmacies/${pharmacyId}/days/${fromDate}/gp-breakdown`;
  
  const response = await fetch(url, {
    headers: {
      'X-API-Key': API_KEY
    }
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  
  return await response.json();
}

// Usage
const breakdown = await getGPBreakdown(1, '2025-12-01', '2025-12-08');
console.log(`Dispensary GP: R ${breakdown.dispensary.gross_profit.toFixed(2)}`);
console.log(`Frontshop GP: R ${breakdown.frontshop.gross_profit.toFixed(2)}`);
console.log(`Dispensary GP %: ${breakdown.dispensary.gp_percentage}%`);
console.log(`Frontshop GP %: ${breakdown.frontshop.gp_percentage}%`);
```

---

**Last Updated**: December 2025

