# Dummy Data Generation for Pharmacy Database

This guide explains how to generate realistic dummy pharmacy data for testing and development.

## Overview

The `generate_dummy_data.py` script creates:
- Dummy pharmacy records
- Realistic daily sales data with seasonal and weekday patterns
- Product-level stock activity data
- Proper department and product hierarchies

All data is generated with **configurable parameters** that align with real pharmacy business patterns.

## Quick Start

### Basic Usage

Generate 3 dummy pharmacies with a full year of data:

```bash
python scripts/generate_dummy_data.py
```

### Custom Date Range

Generate data for a specific period:

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 5 \
  --start-date 2024-06-01 \
  --end-date 2024-12-31
```

### Fast Mode (Skip Stock Activity)

Generate only daily sales data (much faster):

```bash
python scripts/generate_dummy_data.py \
  --skip-stock-activity
```

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--num-pharmacies` | 3 | Number of dummy pharmacies to create |
| `--start-date` | 2024-01-01 | Start date (YYYY-MM-DD) |
| `--end-date` | 2024-12-31 | End date (YYYY-MM-DD) |
| `--products-per-day` | 50 | Products with activity per day |
| `--skip-stock-activity` | false | Skip product-level data generation |

## Configurable Parameters

The script uses realistic profiles that you can customize. Edit `scripts/generate_dummy_data.py` to adjust:

### Pharmacy Profiles

Each pharmacy has a configurable profile:

```python
PharmacyProfile(
    name="DUMMY PHARMACY CENTRAL",
    avg_turnover=50000.0,        # Average daily sales (ZAR)
    turnover_std=9000.0,          # Standard deviation
    dispensary_pct_avg=60.0,      # % of sales from dispensary
    dispensary_pct_std=8.0,       # Variation in dispensary %
    gp_pct_avg=38.0,              # Average gross profit %
    gp_pct_std=5.0,               # GP variation
    avg_transactions=140,         # Average daily transactions
    transaction_std=25,           # Transaction count variation
    avg_scripts=95,               # Average daily scripts
    script_std=15,                # Script count variation
    closing_stock_months=2.5,     # Stock holding period
    weekday_multipliers=[1.0, 1.05, 1.1, 1.08, 1.05, 0.85, 0.75]  # Mon-Sun
)
```

### Product Templates

Control what types of products are generated:

```python
PRODUCT_TEMPLATES = [
    {"prefix": "RX", "count": 200, "dept": "DISP", "avg_price": 180, "is_script": True},
    {"prefix": "OTC", "count": 100, "dept": "OTC", "avg_price": 85, "is_script": False},
    # Add more product categories as needed
]
```

## What Gets Generated

### 1. Pharmacies Table
- Unique pharmacy IDs (auto-incremented from existing max)
- Pharmacy names
- Active status

### 2. Daily Sales Data (`fact_daily_sales`)
- **Turnover** - Total sales with normal distribution and weekday patterns
- **Payment splits** - Cash, account, COD (realistic percentages)
- **Dispensary vs frontshop** - Configurable split
- **Transaction counts** - Based on profile
- **Scripts** - Prescription count and value
- **GP calculations** - Cost of sales, gross profit
- **Stock levels** - Closing stock based on turnover

### 3. Stock Activity Data (`fact_stock_activity`)
- Product-level sales per day
- Quantity sold and sales value
- GP per product
- On-hand quantities
- Realistic distribution across products

### 4. Supporting Data
- **Departments** - DISP, OTC, VITAMINS, COSMETICS, BABY, GROCERY
- **Products** - Hundreds of products across departments

## Realistic Patterns Included

### 📅 Weekday Patterns
- Higher sales mid-week (Tuesday-Thursday)
- Lower sales on weekends
- Configurable multipliers per day

### 📊 Business Rules
- Dispensary typically 45-65% of sales
- GP margins realistic per product type (30-40%)
- Transaction counts correlate with turnover
- Scripts align with dispensary sales
- Stock levels maintain 2-3 months coverage

### 🎲 Randomization
- Normal distribution for core metrics
- Realistic variation (standard deviation)
- Correlated values (e.g., scripts match dispensary sales)
- Edge cases handled (no negative values)

## Examples

### Generate 5 Pharmacies for Q1 2024

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 5 \
  --start-date 2024-01-01 \
  --end-date 2024-03-31 \
  --products-per-day 75
```

### Generate Large Dataset (Full Year, Detailed)

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 10 \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --products-per-day 100
```

### Generate Fast Test Data (1 Month, No Stock)

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 2 \
  --start-date 2024-12-01 \
  --end-date 2024-12-31 \
  --skip-stock-activity
```

## Verifying Generated Data

After generation, you can query the data:

```sql
-- Check created pharmacies
SELECT * FROM pharma.pharmacies WHERE name LIKE 'DUMMY%';

-- View sales data
SELECT 
    pharmacy_id,
    COUNT(*) as days,
    AVG(turnover) as avg_turnover,
    SUM(turnover) as total_turnover
FROM pharma.fact_daily_sales
WHERE pharmacy_id >= 100  -- Adjust based on your IDs
GROUP BY pharmacy_id;

-- Check stock activity
SELECT 
    business_date,
    COUNT(DISTINCT product_id) as products,
    SUM(sales_val) as total_sales
FROM pharma.fact_stock_activity
WHERE pharmacy_id = 100  -- Your dummy pharmacy ID
GROUP BY business_date
ORDER BY business_date DESC
LIMIT 10;
```

## Customization Guide

### Adding New Pharmacy Profiles

Edit `DEFAULT_PROFILES` in the script:

```python
DEFAULT_PROFILES = [
    PharmacyProfile(
        name="MY CUSTOM PHARMACY",
        avg_turnover=70000.0,
        dispensary_pct_avg=70.0,  # High dispensary focus
        gp_pct_avg=40.0,           # High margin
        avg_transactions=200,
        avg_scripts=150
    ),
    # ... more profiles
]
```

### Adding Product Categories

Edit `PRODUCT_TEMPLATES`:

```python
PRODUCT_TEMPLATES = [
    # Existing templates...
    {"prefix": "SPORTS", "count": 50, "dept": "SPORTS_NUTRITION", "avg_price": 250, "is_script": False},
    {"prefix": "PET", "count": 30, "dept": "PET_CARE", "avg_price": 120, "is_script": False},
]
```

### Adjusting Seasonality

Modify weekday multipliers for seasonal patterns:

```python
# Summer pattern (busier overall)
weekday_multipliers=[1.2, 1.25, 1.3, 1.28, 1.25, 1.0, 0.9]

# Winter pattern (more balanced)
weekday_multipliers=[1.0, 1.05, 1.1, 1.08, 1.05, 0.85, 0.75]
```

## Performance Considerations

| Duration | With Stock Activity | Without Stock Activity |
|----------|---------------------|------------------------|
| 1 month  | ~30 seconds | ~5 seconds |
| 1 year   | ~5-10 minutes | ~30 seconds |

**Tip**: Use `--skip-stock-activity` for initial testing, then generate full data when needed.

## Cleaning Up

To remove dummy data:

```sql
-- Find dummy pharmacy IDs
SELECT pharmacy_id, name FROM pharma.pharmacies WHERE name LIKE 'DUMMY%';

-- Delete all data for a dummy pharmacy (replace ID)
DELETE FROM pharma.fact_stock_activity WHERE pharmacy_id = 100;
DELETE FROM pharma.fact_daily_sales WHERE pharmacy_id = 100;
DELETE FROM pharma.pharmacies WHERE pharmacy_id = 100;
```

## Troubleshooting

### "Module not found" errors
Make sure you're in the project root and have installed dependencies:
```bash
pip install -r requirements.txt
```

### Database connection errors
Ensure your `.env` file has the correct `DATABASE_URL`:
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

### Data doesn't look realistic
Adjust the profile parameters in the script to match your expected patterns. The defaults are based on typical South African pharmacy operations.

## Integration with Your App

The generated data works seamlessly with your existing:
- ✅ API endpoints (`/api/sales`, `/api/pharmacies`)
- ✅ Dashboard views
- ✅ Notification system
- ✅ User access controls (just assign users to dummy pharmacies)
- ✅ Target tracking

Simply create users and assign them access to the dummy pharmacies to test the full system! 