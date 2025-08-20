# Pharmacy API Webservice

A comprehensive FastAPI-based webservice for pharmacy management and analytics, providing real-time access to sales data, inventory, and business intelligence.

## 🚀 Features

### Core Endpoints
- **Health Check**: `/health` - Service status
- **Pharmacies**: `/pharmacies` - Pharmacy information
- **Daily Sales**: `/pharmacies/{id}/days` - Daily performance data
- **Stock Activity**: `/pharmacies/{id}/stock-activity` - Product movement
- **Aggregates**: `/pharmacies/{id}/mtd` & `/pharmacies/{id}/ytd` - Monthly/Yearly totals
- **Product Analytics**: `/products/{code}/sales` - Product performance tracking

### Smart Aggregation
- **Pre-aggregated Data**: Fast access to cached MTD/YTD data
- **On-demand Calculation**: Real-time calculations for specific date ranges
- **Performance Optimized**: Database indexes for fast queries

## 📊 API Endpoints

### Authentication
All endpoints require API key authentication via Bearer token:
```bash
Authorization: Bearer your-api-key-here
```

### 1. Health Check
```bash
GET /health
Response: {"ok": true}
```

### 2. Pharmacies
```bash
GET /pharmacies
Response: List of active pharmacies with IDs and names
```

### 3. Daily Sales
```bash
# Get sales for date range
GET /pharmacies/{id}/days?from=2025-08-01&to=2025-08-19

# Get sales for specific date
GET /pharmacies/{id}/days/{date}
```

### 4. Stock Activity
```bash
# Top sellers by sales value
GET /pharmacies/{id}/stock-activity?date=2025-08-19&limit=20

# Top sellers by quantity
GET /pharmacies/{id}/stock-activity/by-quantity?date=2025-08-19&limit=20

# Worst GP% items
GET /pharmacies/{id}/stock-activity/worst-gp?date=2025-08-19&limit=20
```

### 5. Aggregates (MTD/YTD)
```bash
# MTD with specific cutoff date
GET /pharmacies/{id}/mtd?month=2025-08&through=2025-08-19

# YTD with specific cutoff date
GET /pharmacies/{id}/ytd?year=2025&through=2025-08-19

# Pre-aggregated data (as of last refresh)
GET /pharmacies/{id}/mtd?month=2025-08
GET /pharmacies/{id}/ytd?year=2025
```

### 6. Product Analytics
```bash
# Detailed product sales with daily breakdown
GET /products/{code}/sales?from_date=2025-08-01&to_date=2025-08-19

# Product sales summary only
GET /products/{code}/sales/summary?from_date=2025-08-01&to_date=2025-08-19
```

### 7. Logbook (Coverage Reports)
```bash
# Missing reports only
GET /pharmacies/{id}/logbook?from=2025-08-01&to=2025-08-19&missingOnly=true

# All reports
GET /pharmacies/{id}/logbook?from=2025-08-01&to=2025-08-19
```

## 🛠️ Setup & Deployment

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Environment variables configured

### Installation
```bash
# Clone repository
git clone <your-repo-url>
cd pharmacy_ingest

# Install dependencies
pip install -r pharma_api/requirements.txt

# Configure environment
cp pharma_api/.env.example pharma_api/.env
# Edit .env with your database credentials and API key
```

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# API Security
API_KEY=your-secret-api-key

# CORS (optional)
CORS_ALLOW_ORIGINS=*
CORS_ALLOW_CREDENTIALS=false
```

### Running the Service
```bash
cd pharma_api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📈 Data Models

### Pharmacy
```json
{
  "pharmacy_id": 1,
  "name": "REITZ APTEEK"
}
```

### Daily Sales
```json
{
  "business_date": "2025-08-19",
  "pharmacy_id": 1,
  "turnover": 76888.39,
  "dispensary_turnover": 51053.73,
  "frontshop_turnover": 25834.66,
  "scripts_qty": 124,
  "transaction_count": 317,
  "gp_value": 19287.48
}
```

### Product Sales
```json
{
  "product_code": "LP9040024",
  "description": "LEVEMIR FLEXPEN 5X3ML",
  "total_qty_sold": 1.0,
  "total_sales_value": 978.97,
  "total_gp_value": 34.33,
  "avg_gp_percentage": 3.51,
  "sales_days": 1
}
```

## 🔒 Security

- **API Key Authentication**: Required for all endpoints
- **Input Validation**: Comprehensive parameter validation
- **SQL Injection Protection**: Parameterized queries
- **Error Handling**: Secure error messages without data leakage

## 📊 Performance Features

- **Database Indexes**: Optimized for fast queries
- **Smart Caching**: Uses pre-aggregated data when available
- **Connection Pooling**: Efficient database connection management
- **Query Optimization**: Minimal database round trips

## 🚀 Frontend Integration

### Example API Calls
```javascript
// Get daily sales for August 19, 2025
const response = await fetch('/pharmacies/1/days/2025-08-19', {
  headers: {
    'Authorization': 'Bearer your-api-key'
  }
});

// Get product performance
const productData = await fetch('/products/LP9040024/sales?from_date=2025-08-01&to_date=2025-08-19', {
  headers: {
    'Authorization': 'Bearer your-api-key'
  }
});

// Get MTD with specific cutoff
const mtdData = await fetch('/pharmacies/1/mtd?month=2025-08&through=2025-08-19', {
  headers: {
    'Authorization': 'Bearer your-api-key'
  }
});
```

### Error Handling
```javascript
try {
  const response = await fetch('/api/endpoint');
  if (!response.ok) {
    const error = await response.json();
    console.error('API Error:', error.detail);
  }
} catch (error) {
  console.error('Network Error:', error);
}
```

## 🔧 Development

### Adding New Endpoints
1. Create router in `app/routers/`
2. Define Pydantic models in `app/schemas.py`
3. Add to `app/main.py`
4. Update this README

### Database Changes
- Update `schema.sql` for structural changes
- Use migrations for production deployments
- Test with sample data

## 📝 License

[Your License Here]

## 🤝 Support

For API support and questions, contact your development team. 