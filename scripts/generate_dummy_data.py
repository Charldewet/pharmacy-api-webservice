#!/usr/bin/env python3
"""
Generate dummy pharmacy data with realistic, configurable parameters.

This script creates dummy pharmacies and generates random but realistic data
that aligns with existing pharmacy data patterns.

Usage:
    python scripts/generate_dummy_data.py --num-pharmacies 3 --start-date 2024-01-01 --end-date 2024-12-31
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import random
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Tuple
import numpy as np
from dataclasses import dataclass

from src.db.conn import get_conn

# ============================================================================
# CONFIGURABLE PARAMETERS
# ============================================================================

@dataclass
class PharmacyProfile:
    """Configuration profile for a dummy pharmacy"""
    name: str
    # Daily sales parameters (in ZAR)
    avg_turnover: float = 45000.0
    turnover_std: float = 8000.0
    # Sales breakdown percentages
    dispensary_pct_avg: float = 55.0  # % of sales from dispensary
    dispensary_pct_std: float = 8.0
    # Gross profit margins
    gp_pct_avg: float = 35.0
    gp_pct_std: float = 5.0
    # Transaction patterns
    avg_transactions: int = 120
    transaction_std: int = 25
    # Script patterns
    avg_scripts: int = 85
    script_std: int = 15
    # Closing stock (typically 2-3 months of sales)
    closing_stock_months: float = 2.5
    # Weekday patterns (Mon=0, Sun=6) - multiplier for business
    weekday_multipliers: List[float] = None
    
    def __post_init__(self):
        if self.weekday_multipliers is None:
            # Default: busier mid-week, slower weekends
            self.weekday_multipliers = [1.0, 1.05, 1.1, 1.08, 1.05, 0.85, 0.75]


# Default pharmacy profiles - you can customize these!
DEFAULT_PROFILES = [
    PharmacyProfile(
        name="DUMMY PHARMACY CENTRAL",
        avg_turnover=50000.0,
        turnover_std=9000.0,
        dispensary_pct_avg=60.0,
        gp_pct_avg=38.0,
        avg_transactions=140,
        avg_scripts=95
    ),
    PharmacyProfile(
        name="DUMMY PHARMACY EAST",
        avg_turnover=35000.0,
        turnover_std=6000.0,
        dispensary_pct_avg=50.0,
        gp_pct_avg=33.0,
        avg_transactions=95,
        avg_scripts=70
    ),
    PharmacyProfile(
        name="DUMMY PHARMACY WEST",
        avg_turnover=60000.0,
        turnover_std=12000.0,
        dispensary_pct_avg=55.0,
        gp_pct_avg=36.0,
        avg_transactions=160,
        avg_scripts=110
    ),
]

# Product templates for generating stock activity
PRODUCT_TEMPLATES = [
    # Dispensary items
    {"prefix": "RX", "count": 200, "dept": "DISP", "avg_price": 180, "is_script": True},
    {"prefix": "GEN", "count": 150, "dept": "DISP", "avg_price": 95, "is_script": True},
    # OTC medications
    {"prefix": "OTC", "count": 100, "dept": "OTC", "avg_price": 85, "is_script": False},
    {"prefix": "VIT", "count": 50, "dept": "VITAMINS", "avg_price": 120, "is_script": False},
    # Frontshop
    {"prefix": "COSM", "count": 80, "dept": "COSMETICS", "avg_price": 145, "is_script": False},
    {"prefix": "BABY", "count": 60, "dept": "BABY", "avg_price": 95, "is_script": False},
    {"prefix": "FOOD", "count": 40, "dept": "GROCERY", "avg_price": 45, "is_script": False},
]

# ============================================================================
# DATA GENERATION FUNCTIONS
# ============================================================================

def get_next_pharmacy_id(cur) -> int:
    """Get the next available pharmacy ID"""
    cur.execute("SELECT COALESCE(MAX(pharmacy_id), 0) + 1 AS next_id FROM pharma.pharmacies")
    return cur.fetchone()["next_id"]


def create_dummy_pharmacies(cur, profiles: List[PharmacyProfile], start_id: int = None) -> List[Tuple[int, PharmacyProfile]]:
    """Create dummy pharmacies and return their IDs with profiles"""
    if start_id is None:
        start_id = get_next_pharmacy_id(cur)
    
    pharmacy_mappings = []
    for i, profile in enumerate(profiles):
        pharmacy_id = start_id + i
        cur.execute(
            """
            INSERT INTO pharma.pharmacies (pharmacy_id, name, is_active)
            VALUES (%(pharmacy_id)s, %(name)s, true)
            ON CONFLICT (pharmacy_id) DO UPDATE
            SET name = EXCLUDED.name, is_active = true
            """,
            {"pharmacy_id": pharmacy_id, "name": profile.name}
        )
        pharmacy_mappings.append((pharmacy_id, profile))
        print(f"✓ Created pharmacy: {profile.name} (ID: {pharmacy_id})")
    
    return pharmacy_mappings


def ensure_departments_and_products(cur) -> Dict[str, int]:
    """Ensure all departments and products exist, return dept_code -> dept_id mapping"""
    dept_mapping = {}
    
    # Create departments
    for template in PRODUCT_TEMPLATES:
        dept_code = template["dept"]
        cur.execute(
            """
            INSERT INTO pharma.departments (department_code)
            VALUES (%(code)s)
            ON CONFLICT (department_code) DO NOTHING
            RETURNING department_id
            """,
            {"code": dept_code}
        )
        result = cur.fetchone()
        if result:
            dept_id = result["department_id"]
        else:
            cur.execute(
                "SELECT department_id FROM pharma.departments WHERE department_code = %(code)s",
                {"code": dept_code}
            )
            dept_id = cur.fetchone()["department_id"]
        
        dept_mapping[dept_code] = dept_id
    
    # Create products
    product_count = 0
    for template in PRODUCT_TEMPLATES:
        dept_id = dept_mapping[template["dept"]]
        for i in range(template["count"]):
            product_code = f"{template['prefix']}{i+1:04d}"
            description = f"{template['dept']} Product {i+1}"
            
            cur.execute(
                """
                INSERT INTO pharma.products (product_code, description, department_id)
                VALUES (%(code)s, %(desc)s, %(dept_id)s)
                ON CONFLICT (product_code) DO NOTHING
                """,
                {"code": product_code, "desc": description, "dept_id": dept_id}
            )
            product_count += 1
    
    print(f"✓ Ensured {len(dept_mapping)} departments and {product_count} products exist")
    return dept_mapping


def generate_daily_sales(
    pharmacy_id: int,
    profile: PharmacyProfile,
    business_date: date
) -> Dict[str, Any]:
    """Generate realistic daily sales data for a pharmacy"""
    
    # Apply weekday multiplier
    weekday = business_date.weekday()
    weekday_mult = profile.weekday_multipliers[weekday]
    
    # Generate turnover with normal distribution and weekday pattern
    turnover = max(0, np.random.normal(profile.avg_turnover * weekday_mult, profile.turnover_std))
    
    # Dispensary vs frontshop split
    disp_pct = np.clip(np.random.normal(profile.dispensary_pct_avg, profile.dispensary_pct_std), 20, 80)
    dispensary_turnover = turnover * (disp_pct / 100)
    
    # Payment method split (realistic percentages)
    cash_pct = np.random.uniform(0.15, 0.30)
    cod_pct = np.random.uniform(0.05, 0.15)
    account_pct = 1.0 - cash_pct - cod_pct
    
    sales_cash = turnover * cash_pct
    sales_cod = turnover * cod_pct
    sales_account = turnover * account_pct
    
    # Type R sales (typically small percentage)
    type_r_sales = turnover * np.random.uniform(0.01, 0.05)
    
    # Transaction count
    transaction_count = max(1, int(np.random.normal(
        profile.avg_transactions * weekday_mult,
        profile.transaction_std
    )))
    avg_basket = turnover / transaction_count if transaction_count > 0 else 0
    
    # GP calculation
    gp_pct = np.clip(np.random.normal(profile.gp_pct_avg, profile.gp_pct_std), 15, 60)
    cost_of_sales = turnover * (1 - gp_pct / 100)
    
    # Purchases (varies around cost of sales)
    purchases = cost_of_sales * np.random.uniform(0.85, 1.15)
    
    # Closing stock
    monthly_turnover = profile.avg_turnover * 30
    closing_stock = monthly_turnover * profile.closing_stock_months
    closing_stock *= np.random.uniform(0.9, 1.1)  # Add some variation
    
    # Scripts
    scripts_qty = max(0, int(np.random.normal(
        profile.avg_scripts * weekday_mult,
        profile.script_std
    )))
    avg_script_value = dispensary_turnover / scripts_qty if scripts_qty > 0 else 0
    
    return {
        "pharmacy_id": pharmacy_id,
        "business_date": business_date,
        "turnover": round(Decimal(turnover), 2),
        "sales_cash": round(Decimal(sales_cash), 2),
        "sales_account": round(Decimal(sales_account), 2),
        "sales_cod": round(Decimal(sales_cod), 2),
        "type_r_sales": round(Decimal(type_r_sales), 2),
        "transaction_count": transaction_count,
        "avg_basket": round(Decimal(avg_basket), 2),
        "purchases": round(Decimal(purchases), 2),
        "cost_of_sales": round(Decimal(cost_of_sales), 2),
        "closing_stock": round(Decimal(closing_stock), 2),
        "dispensary_turnover": round(Decimal(dispensary_turnover), 2),
        "scripts_qty": scripts_qty,
        "avg_script_value": round(Decimal(avg_script_value), 2),
    }


def insert_daily_sales(cur, sales_data: Dict[str, Any]) -> None:
    """Insert daily sales data into fact_daily_sales table"""
    cur.execute(
        """
        INSERT INTO pharma.fact_daily_sales (
            pharmacy_id, business_date,
            turnover, sales_cash, sales_account, sales_cod, type_r_sales,
            transaction_count, avg_basket,
            purchases, cost_of_sales, closing_stock,
            dispensary_turnover, scripts_qty, avg_script_value
        ) VALUES (
            %(pharmacy_id)s, %(business_date)s,
            %(turnover)s, %(sales_cash)s, %(sales_account)s, %(sales_cod)s, %(type_r_sales)s,
            %(transaction_count)s, %(avg_basket)s,
            %(purchases)s, %(cost_of_sales)s, %(closing_stock)s,
            %(dispensary_turnover)s, %(scripts_qty)s, %(avg_script_value)s
        )
        ON CONFLICT (pharmacy_id, business_date) DO UPDATE
        SET turnover = EXCLUDED.turnover,
            sales_cash = EXCLUDED.sales_cash,
            sales_account = EXCLUDED.sales_account,
            sales_cod = EXCLUDED.sales_cod,
            type_r_sales = EXCLUDED.type_r_sales,
            transaction_count = EXCLUDED.transaction_count,
            avg_basket = EXCLUDED.avg_basket,
            purchases = EXCLUDED.purchases,
            cost_of_sales = EXCLUDED.cost_of_sales,
            closing_stock = EXCLUDED.closing_stock,
            dispensary_turnover = EXCLUDED.dispensary_turnover,
            scripts_qty = EXCLUDED.scripts_qty,
            avg_script_value = EXCLUDED.avg_script_value,
            last_updated_at = now()
        """,
        sales_data
    )


def generate_stock_activity(
    cur,
    pharmacy_id: int,
    business_date: date,
    daily_sales: Dict[str, Any],
    num_products: int = 50
) -> List[Dict[str, Any]]:
    """Generate stock activity for random products based on daily sales"""
    
    # Get random products
    cur.execute(
        """
        SELECT p.product_id, p.product_code, p.department_id
        FROM pharma.products p
        ORDER BY RANDOM()
        LIMIT %(limit)s
        """,
        {"limit": num_products}
    )
    products = cur.fetchall()
    
    if not products:
        return []
    
    total_turnover = float(daily_sales["turnover"])
    dispensary_turnover = float(daily_sales["dispensary_turnover"])
    
    activities = []
    remaining_turnover = total_turnover
    
    for i, product in enumerate(products):
        # Determine if this is a dispensary item
        cur.execute(
            "SELECT department_code FROM pharma.departments WHERE department_id = %(id)s",
            {"id": product["department_id"]}
        )
        dept = cur.fetchone()
        is_dispensary = dept and dept["department_code"] in ["DISP"]
        
        # Allocate sales value (use decreasing random allocation)
        if i == len(products) - 1:
            # Last product gets remaining
            sales_val = max(0, remaining_turnover)
        else:
            # Random allocation with exponential decay
            max_allocation = remaining_turnover * 0.15  # Max 15% per product
            sales_val = np.random.uniform(0, max_allocation)
            remaining_turnover -= sales_val
        
        if sales_val < 1:  # Skip negligible sales
            continue
        
        # Generate quantity sold (depends on product type)
        if is_dispensary:
            avg_unit_price = 180
            qty_sold = max(1, sales_val / np.random.uniform(avg_unit_price * 0.5, avg_unit_price * 1.5))
        else:
            avg_unit_price = 95
            qty_sold = max(1, sales_val / np.random.uniform(avg_unit_price * 0.5, avg_unit_price * 1.5))
        
        # GP calculation
        gp_pct = np.random.normal(38 if is_dispensary else 32, 8)
        gp_pct = np.clip(gp_pct, 10, 70)
        cost_of_sales = sales_val * (1 - gp_pct / 100)
        gp_value = sales_val - cost_of_sales
        
        # On-hand stock (random between 10-100 units)
        on_hand = np.random.uniform(10, 100)
        
        activities.append({
            "pharmacy_id": pharmacy_id,
            "business_date": business_date,
            "product_id": product["product_id"],
            "department_id": product["department_id"],
            "qty_sold": round(Decimal(qty_sold), 3),
            "sales_val": round(Decimal(sales_val), 2),
            "cost_of_sales": round(Decimal(cost_of_sales), 2),
            "gp_value": round(Decimal(gp_value), 2),
            "gp_pct": round(Decimal(gp_pct), 2),
            "on_hand": round(Decimal(on_hand), 3),
        })
    
    return activities


def insert_stock_activity(cur, activity: Dict[str, Any]) -> None:
    """Insert stock activity data"""
    cur.execute(
        """
        INSERT INTO pharma.fact_stock_activity (
            pharmacy_id, business_date, product_id, department_id,
            qty_sold, sales_val, cost_of_sales, gp_value, gp_pct, on_hand
        ) VALUES (
            %(pharmacy_id)s, %(business_date)s, %(product_id)s, %(department_id)s,
            %(qty_sold)s, %(sales_val)s, %(cost_of_sales)s, %(gp_value)s, %(gp_pct)s, %(on_hand)s
        )
        ON CONFLICT (pharmacy_id, business_date, product_id) DO UPDATE
        SET department_id = EXCLUDED.department_id,
            qty_sold = EXCLUDED.qty_sold,
            sales_val = EXCLUDED.sales_val,
            cost_of_sales = EXCLUDED.cost_of_sales,
            gp_value = EXCLUDED.gp_value,
            gp_pct = EXCLUDED.gp_pct,
            on_hand = EXCLUDED.on_hand,
            last_updated_at = now()
        """,
        activity
    )


def daterange(start_date: date, end_date: date):
    """Generate dates between start and end (inclusive)"""
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate dummy pharmacy data with realistic patterns"
    )
    parser.add_argument(
        "--num-pharmacies",
        type=int,
        default=3,
        help="Number of dummy pharmacies to create (default: 3)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2024-01-01",
        help="Start date for data generation (YYYY-MM-DD, default: 2024-01-01)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2024-12-31",
        help="End date for data generation (YYYY-MM-DD, default: 2024-12-31)"
    )
    parser.add_argument(
        "--products-per-day",
        type=int,
        default=50,
        help="Number of products to generate activity for per day (default: 50)"
    )
    parser.add_argument(
        "--skip-stock-activity",
        action="store_true",
        help="Skip generating stock activity data (faster, but less complete)"
    )
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    
    # Use default profiles (limit to requested number)
    profiles = DEFAULT_PROFILES[:args.num_pharmacies]
    if len(profiles) < args.num_pharmacies:
        # Generate additional generic profiles if needed
        for i in range(len(profiles), args.num_pharmacies):
            profiles.append(PharmacyProfile(
                name=f"DUMMY PHARMACY {i+1}",
                avg_turnover=np.random.uniform(30000, 60000),
                turnover_std=np.random.uniform(5000, 10000),
                dispensary_pct_avg=np.random.uniform(45, 65),
                gp_pct_avg=np.random.uniform(30, 40),
                avg_transactions=int(np.random.uniform(80, 150)),
                avg_scripts=int(np.random.uniform(60, 120))
            ))
    
    print("=" * 70)
    print("PHARMACY DUMMY DATA GENERATOR")
    print("=" * 70)
    print(f"Pharmacies to create: {args.num_pharmacies}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Days to generate: {(end_date - start_date).days + 1}")
    print(f"Products per day: {args.products_per_day}")
    print("=" * 70)
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Step 1: Create pharmacies
            print("\n[1/4] Creating dummy pharmacies...")
            pharmacy_mappings = create_dummy_pharmacies(cur, profiles)
            conn.commit()
            
            # Step 2: Ensure departments and products exist
            print("\n[2/4] Ensuring departments and products exist...")
            dept_mapping = ensure_departments_and_products(cur)
            conn.commit()
            
            # Step 3: Generate daily sales data
            print("\n[3/4] Generating daily sales data...")
            total_days = (end_date - start_date).days + 1
            days_processed = 0
            
            for current_date in daterange(start_date, end_date):
                for pharmacy_id, profile in pharmacy_mappings:
                    sales_data = generate_daily_sales(pharmacy_id, profile, current_date)
                    insert_daily_sales(cur, sales_data)
                
                days_processed += 1
                if days_processed % 30 == 0 or days_processed == total_days:
                    print(f"  ✓ Generated {days_processed}/{total_days} days of data...")
                    conn.commit()
            
            conn.commit()
            print(f"  ✓ Completed {days_processed} days of sales data!")
            
            # Step 4: Generate stock activity
            if not args.skip_stock_activity:
                print("\n[4/4] Generating stock activity data...")
                days_processed = 0
                
                for current_date in daterange(start_date, end_date):
                    for pharmacy_id, profile in pharmacy_mappings:
                        # Get the daily sales for context
                        cur.execute(
                            """
                            SELECT * FROM pharma.fact_daily_sales
                            WHERE pharmacy_id = %(phid)s AND business_date = %(date)s
                            """,
                            {"phid": pharmacy_id, "date": current_date}
                        )
                        daily_sales = cur.fetchone()
                        
                        if daily_sales:
                            activities = generate_stock_activity(
                                cur, pharmacy_id, current_date,
                                dict(daily_sales), args.products_per_day
                            )
                            for activity in activities:
                                insert_stock_activity(cur, activity)
                    
                    days_processed += 1
                    if days_processed % 30 == 0 or days_processed == total_days:
                        print(f"  ✓ Generated {days_processed}/{total_days} days of stock activity...")
                        conn.commit()
                
                conn.commit()
                print(f"  ✓ Completed {days_processed} days of stock activity!")
            else:
                print("\n[4/4] Skipping stock activity data (--skip-stock-activity flag)")
            
    print("\n" + "=" * 70)
    print("✓ DUMMY DATA GENERATION COMPLETE!")
    print("=" * 70)
    print(f"\nGenerated data for {len(pharmacy_mappings)} pharmacies:")
    for phid, profile in pharmacy_mappings:
        print(f"  • {profile.name} (ID: {phid})")
    print(f"\nDate range: {start_date} to {end_date}")
    print(f"Total days: {(end_date - start_date).days + 1}")
    print("\nYou can now query this data through your API or database!")


if __name__ == "__main__":
    main() 