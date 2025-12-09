"""
Custom pharmacy profiles for dummy data generation.

Copy this file and modify the profiles to match your testing needs.
"""

from dataclasses import dataclass
from typing import List

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


# ============================================================================
# EXAMPLE PROFILES - Customize these for your needs!
# ============================================================================

# Small Rural Pharmacy
SMALL_RURAL = PharmacyProfile(
    name="DUMMY PHARMACY RURAL",
    avg_turnover=25000.0,
    turnover_std=4000.0,
    dispensary_pct_avg=45.0,
    gp_pct_avg=32.0,
    avg_transactions=60,
    transaction_std=15,
    avg_scripts=40,
    script_std=10,
    closing_stock_months=3.0,
    weekday_multipliers=[0.9, 1.0, 1.1, 1.05, 1.0, 0.7, 0.5]  # Very quiet weekends
)

# Medium Urban Pharmacy
MEDIUM_URBAN = PharmacyProfile(
    name="DUMMY PHARMACY URBAN",
    avg_turnover=45000.0,
    turnover_std=7000.0,
    dispensary_pct_avg=55.0,
    gp_pct_avg=35.0,
    avg_transactions=120,
    transaction_std=20,
    avg_scripts=85,
    script_std=15,
    closing_stock_months=2.5,
    weekday_multipliers=[1.0, 1.05, 1.1, 1.08, 1.05, 0.85, 0.75]
)

# Large Shopping Center Pharmacy
LARGE_SHOPPING_CENTER = PharmacyProfile(
    name="DUMMY PHARMACY MALL",
    avg_turnover=75000.0,
    turnover_std=12000.0,
    dispensary_pct_avg=50.0,  # More frontshop due to foot traffic
    gp_pct_avg=36.0,
    avg_transactions=200,
    transaction_std=35,
    avg_scripts=120,
    script_std=20,
    closing_stock_months=2.0,
    weekday_multipliers=[1.1, 1.1, 1.05, 1.05, 1.2, 1.3, 1.2]  # Busy weekends!
)

# Medical Center Pharmacy (High Script Focus)
MEDICAL_CENTER = PharmacyProfile(
    name="DUMMY PHARMACY MEDICAL",
    avg_turnover=55000.0,
    turnover_std=8000.0,
    dispensary_pct_avg=75.0,  # Very high dispensary focus
    gp_pct_avg=38.0,
    avg_transactions=90,
    transaction_std=15,
    avg_scripts=140,
    script_std=25,
    closing_stock_months=2.5,
    weekday_multipliers=[1.1, 1.15, 1.2, 1.15, 1.1, 0.6, 0.4]  # Follows doctor schedules
)

# Budget/Discount Pharmacy
DISCOUNT_PHARMACY = PharmacyProfile(
    name="DUMMY PHARMACY DISCOUNT",
    avg_turnover=65000.0,
    turnover_std=11000.0,
    dispensary_pct_avg=40.0,  # More frontshop/retail
    gp_pct_avg=28.0,  # Lower margins due to competitive pricing
    avg_transactions=250,  # High transaction count
    transaction_std=45,
    avg_scripts=70,
    script_std=12,
    closing_stock_months=3.5,  # Higher stock levels
    weekday_multipliers=[1.0, 1.0, 1.0, 1.0, 1.1, 1.3, 1.4]  # Strong weekend sales
)

# Seasonal Tourist Area Pharmacy
TOURIST_PHARMACY = PharmacyProfile(
    name="DUMMY PHARMACY BEACH",
    avg_turnover=40000.0,
    turnover_std=15000.0,  # High variation (seasonal)
    dispensary_pct_avg=35.0,  # Lots of sundries/sunscreen/etc
    gp_pct_avg=34.0,
    avg_transactions=180,
    transaction_std=60,  # High variation
    avg_scripts=50,
    script_std=20,
    closing_stock_months=2.0,
    weekday_multipliers=[0.8, 0.8, 0.9, 0.9, 1.0, 1.5, 1.6]  # Weekend tourists
)

# 24-Hour Pharmacy
TWENTY_FOUR_HOUR = PharmacyProfile(
    name="DUMMY PHARMACY 24HR",
    avg_turnover=58000.0,
    turnover_std=9000.0,
    dispensary_pct_avg=60.0,
    gp_pct_avg=36.0,
    avg_transactions=150,
    transaction_std=25,
    avg_scripts=100,
    script_std=18,
    closing_stock_months=2.5,
    weekday_multipliers=[1.0, 1.0, 1.0, 1.0, 1.05, 1.1, 1.05]  # More balanced
)

# Hospital Outpatient Pharmacy
HOSPITAL_OUTPATIENT = PharmacyProfile(
    name="DUMMY PHARMACY HOSPITAL",
    avg_turnover=90000.0,
    turnover_std=15000.0,
    dispensary_pct_avg=85.0,  # Almost all scripts
    gp_pct_avg=40.0,
    avg_transactions=120,
    transaction_std=20,
    avg_scripts=200,
    script_std=35,
    closing_stock_months=2.0,
    weekday_multipliers=[1.15, 1.2, 1.15, 1.1, 1.0, 0.5, 0.3]  # Hospital schedules
)

# ============================================================================
# PROFILE COLLECTIONS
# ============================================================================

# Mix of different pharmacy types
DIVERSE_MIX = [
    SMALL_RURAL,
    MEDIUM_URBAN,
    LARGE_SHOPPING_CENTER,
    MEDICAL_CENTER,
    DISCOUNT_PHARMACY,
]

# Similar pharmacies (for chain testing)
PHARMACY_CHAIN = [
    PharmacyProfile(
        name=f"DUMMY PHARMACY CHAIN {i+1}",
        avg_turnover=50000.0 + (i * 5000),  # Slight variation
        turnover_std=8000.0,
        dispensary_pct_avg=55.0,
        gp_pct_avg=35.0,
        avg_transactions=130 + (i * 10),
        avg_scripts=90 + (i * 5),
    )
    for i in range(5)
]

# All types for comprehensive testing
ALL_TYPES = [
    SMALL_RURAL,
    MEDIUM_URBAN,
    LARGE_SHOPPING_CENTER,
    MEDICAL_CENTER,
    DISCOUNT_PHARMACY,
    TOURIST_PHARMACY,
    TWENTY_FOUR_HOUR,
    HOSPITAL_OUTPATIENT,
]

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

"""
To use these profiles, modify generate_dummy_data.py:

1. Import this file:
   from dummy_pharmacy_profiles import DIVERSE_MIX, ALL_TYPES

2. Replace DEFAULT_PROFILES with your chosen profile collection:
   DEFAULT_PROFILES = DIVERSE_MIX
   # or
   DEFAULT_PROFILES = ALL_TYPES
   # or create your own list
   DEFAULT_PROFILES = [SMALL_RURAL, LARGE_SHOPPING_CENTER]

3. Run the script normally:
   python scripts/generate_dummy_data.py --num-pharmacies 5
""" 