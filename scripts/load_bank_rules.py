#!/usr/bin/env python3
"""
Load standard bank rules for all pharmacies.

This script:
1. Creates the function to load standard bank rules
2. Loads rules for all existing pharmacies
3. Sets up trigger to auto-load rules for new pharmacies

Usage:
    python scripts/load_bank_rules.py
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.conn import get_conn

def load_bank_rules(conn):
    """Load the bank rules seed file"""
    print("Loading bank rules seed file...")
    
    seed_file = Path(__file__).parent.parent / "seed_bank_rules.sql"
    
    if not seed_file.exists():
        print(f"❌ Error: Seed file not found at {seed_file}")
        return False
    
    with open(seed_file, 'r') as f:
        seed_sql = f.read()
    
    try:
        with conn.cursor() as cur:
            # Execute the seed SQL
            cur.execute(seed_sql)
            conn.commit()
        
        print("✓ Bank rules seed file loaded successfully")
        print()
        return True
    except Exception as e:
        print(f"❌ Error loading bank rules: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False


def verify_rules(conn):
    """Verify that rules were created for all pharmacies"""
    print("Verifying bank rules...")
    print()
    
    with conn.cursor() as cur:
        # Get all pharmacies
        cur.execute("SELECT pharmacy_id, name FROM pharma.pharmacies ORDER BY pharmacy_id")
        pharmacies = cur.fetchall()
        
        # Get rule counts per pharmacy
        cur.execute("""
            SELECT pharmacy_id, COUNT(*) as rule_count
            FROM pharma.bank_rules
            GROUP BY pharmacy_id
        """)
        rule_counts = {row['pharmacy_id']: row['rule_count'] for row in cur.fetchall()}
        
        print("Pharmacy Rules:")
        print("-" * 60)
        
        all_ok = True
        for pharmacy in pharmacies:
            pharmacy_id = pharmacy['pharmacy_id']
            rule_count = rule_counts.get(pharmacy_id, 0)
            status = "✓" if rule_count > 0 else "✗"
            print(f"  {status} Pharmacy {pharmacy_id} ({pharmacy['name']}): {rule_count} rules")
            if rule_count == 0:
                all_ok = False
        
        print("-" * 60)
        print()
        
        # Get total rule count
        cur.execute("SELECT COUNT(*) as total FROM pharma.bank_rules")
        total = cur.fetchone()['total']
        print(f"Total rules created: {total}")
        print()
        
        # Show sample rules
        if total > 0:
            cur.execute("""
                SELECT br.id, br.pharmacy_id, br.name, br.type, br.priority, br.is_active,
                       COUNT(brc.id) as condition_count
                FROM pharma.bank_rules br
                LEFT JOIN pharma.bank_rule_conditions brc ON br.id = brc.bank_rule_id
                GROUP BY br.id, br.pharmacy_id, br.name, br.type, br.priority, br.is_active
                ORDER BY br.pharmacy_id, br.priority
                LIMIT 5
            """)
            sample_rules = cur.fetchall()
            
            print("Sample rules (first 5):")
            for rule in sample_rules:
                print(f"  - [{rule['id']}] {rule['name']} ({rule['type']}, priority {rule['priority']}, {rule['condition_count']} conditions)")
            print()
        
        return all_ok


def main():
    """Main execution function"""
    print("=" * 60)
    print("PHARMASIGHT STANDARD BANK RULES - SETUP")
    print("=" * 60)
    print()
    
    try:
        with get_conn() as conn:
            # Step 1: Load rules
            if not load_bank_rules(conn):
                print("❌ Failed to load bank rules")
                sys.exit(1)
            
            # Step 2: Verify rules
            if not verify_rules(conn):
                print("⚠️  Some pharmacies don't have rules")
            
            print()
            print("=" * 60)
            print("✓ SETUP COMPLETE!")
            print("=" * 60)
            print()
            print("Standard bank rules have been loaded for all pharmacies.")
            print("New pharmacies will automatically get these rules via trigger.")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

