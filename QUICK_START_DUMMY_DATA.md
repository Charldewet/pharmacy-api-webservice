# Quick Start: Generate Dummy Pharmacy Data

## TL;DR - Get Started in 30 Seconds

```bash
# Generate 3 dummy pharmacies with 1 year of data (default settings)
python scripts/generate_dummy_data.py

# That's it! Check your database:
# SELECT * FROM pharma.pharmacies WHERE name LIKE 'DUMMY%';
```

## Common Use Cases

### 1. Quick Test (1 Month of Data)

For rapid testing, generate just 1 month of data without stock details:

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 2 \
  --start-date 2024-12-01 \
  --end-date 2024-12-31 \
  --skip-stock-activity
```

**Time:** ~5 seconds  
**Use for:** API testing, UI development

---

### 2. Full Year Testing Dataset

Generate a complete year of realistic data:

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 5 \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --products-per-day 75
```

**Time:** ~5-10 minutes  
**Use for:** Analytics testing, dashboard development, reporting

---

### 3. Recent Data (Last 3 Months)

Generate recent data to test current-period features:

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 3 \
  --start-date 2024-07-01 \
  --end-date 2024-09-30
```

**Time:** ~2 minutes  
**Use for:** MTD/YTD calculations, recent trends

---

### 4. Large Dataset (Multiple Pharmacies, Full Details)

For comprehensive testing:

```bash
python scripts/generate_dummy_data.py \
  --num-pharmacies 10 \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --products-per-day 100
```

**Time:** ~15-20 minutes  
**Use for:** Performance testing, multi-pharmacy scenarios

---

## What You Get

After running the script, you'll have:

✅ **Pharmacies** - Named "DUMMY PHARMACY CENTRAL", "DUMMY PHARMACY EAST", etc.  
✅ **Daily Sales** - Realistic turnover, scripts, transactions, GP  
✅ **Stock Activity** - Product-level sales data  
✅ **Departments** - DISP, OTC, VITAMINS, COSMETICS, BABY, GROCERY  
✅ **Products** - 600+ products across all departments  

## Verify Your Data

```sql
-- Check pharmacies created
SELECT pharmacy_id, name 
FROM pharma.pharmacies 
WHERE name LIKE 'DUMMY%';

-- Summary of sales data
SELECT 
    p.name,
    COUNT(*) as days_of_data,
    ROUND(AVG(f.turnover), 2) as avg_daily_sales,
    ROUND(SUM(f.turnover), 2) as total_sales
FROM pharma.fact_daily_sales f
JOIN pharma.pharmacies p ON p.pharmacy_id = f.pharmacy_id
WHERE p.name LIKE 'DUMMY%'
GROUP BY p.name;

-- Check recent data
SELECT 
    business_date,
    turnover,
    scripts_qty,
    transaction_count
FROM pharma.fact_daily_sales
WHERE pharmacy_id IN (SELECT pharmacy_id FROM pharma.pharmacies WHERE name LIKE 'DUMMY%')
ORDER BY business_date DESC
LIMIT 10;
```

## Key Parameters Explained

### `--num-pharmacies`
How many dummy pharmacies to create. Each gets unique but realistic data patterns.

**Example:** `--num-pharmacies 5`

---

### `--start-date` and `--end-date`
Date range for data generation (YYYY-MM-DD format).

**Example:** `--start-date 2024-01-01 --end-date 2024-12-31`

---

### `--products-per-day`
How many products have activity each day. Higher = more detailed but slower.

**Example:** `--products-per-day 100` (default is 50)

---

### `--skip-stock-activity`
Skip product-level data for faster generation (only daily summaries).

**Example:** `--skip-stock-activity`

---

## Customizing Pharmacy Profiles

Want different pharmacy types? Edit the profiles in `generate_dummy_data.py`:

```python
DEFAULT_PROFILES = [
    PharmacyProfile(
        name="MY CUSTOM PHARMACY",
        avg_turnover=70000.0,     # R70k average daily sales
        dispensary_pct_avg=65.0,  # 65% from dispensary
        gp_pct_avg=38.0,          # 38% gross profit
        avg_transactions=150,     # 150 transactions/day
        avg_scripts=100,          # 100 scripts/day
    ),
]
```

Or use pre-built profiles from `dummy_pharmacy_profiles.py`:

```python
from dummy_pharmacy_profiles import DIVERSE_MIX, ALL_TYPES

DEFAULT_PROFILES = DIVERSE_MIX  # Mix of rural, urban, mall, etc.
```

## Real-World Patterns Included

### 📊 Business Patterns
- **Weekday variations** - Busier mid-week, quieter weekends
- **Dispensary split** - 45-65% of sales from scripts
- **GP margins** - 30-40% realistic margins
- **Transaction sizes** - Correlated with turnover
- **Stock levels** - 2-3 months coverage

### 🎲 Randomization
- Normal distribution for realistic variation
- No negative values (business logic enforced)
- Correlated metrics (e.g., more scripts = more dispensary sales)

## Testing Your App

Once data is generated, you can test:

1. **API Endpoints**
   ```bash
   curl http://localhost:8000/api/pharmacies
   curl http://localhost:8000/api/sales?pharmacy_id=100&date=2024-06-15
   ```

2. **Dashboard**
   - Login and view dummy pharmacies
   - Check MTD/YTD calculations
   - Test graphs and charts

3. **Notifications**
   - Set up notification preferences for dummy pharmacies
   - Test daily summaries and low-GP alerts

4. **User Access**
   - Assign test users to dummy pharmacies
   - Test multi-pharmacy access

## Clean Up

When done testing:

```sql
-- Find dummy pharmacy IDs
SELECT pharmacy_id FROM pharma.pharmacies WHERE name LIKE 'DUMMY%';

-- Delete everything for a specific dummy pharmacy
DELETE FROM pharma.fact_stock_activity WHERE pharmacy_id = 100;
DELETE FROM pharma.fact_daily_sales WHERE pharmacy_id = 100;
DELETE FROM pharma.report_coverage WHERE pharmacy_id = 100;
DELETE FROM pharma.report_receipts WHERE pharmacy_id = 100;
DELETE FROM pharma.pharmacies WHERE pharmacy_id = 100;
```

## Troubleshooting

### Script fails with "DATABASE_URL not set"
Make sure your `.env` file exists with:
```
DATABASE_URL=postgresql://user:password@host:port/database
```

### Data doesn't match expected patterns
Adjust the pharmacy profiles in the script to match your real pharmacy patterns.

### Script is too slow
Use `--skip-stock-activity` for faster generation, or reduce the date range.

### Need different pharmacy types
Check out `dummy_pharmacy_profiles.py` for pre-built profiles:
- Small rural pharmacies
- Large shopping center pharmacies
- Medical center pharmacies
- 24-hour pharmacies
- And more!

## Need Help?

- Full documentation: `DUMMY_DATA_GENERATION.md`
- Profile examples: `scripts/dummy_pharmacy_profiles.py`
- Script source: `scripts/generate_dummy_data.py`

Happy testing! 🎉 