#!/usr/bin/env python3
"""
Delete all dummy pharmacies and their associated data from the database.

This script will remove:
- Dummy pharmacy records
- All daily sales data
- All stock activity data
- Report receipts and coverage
- User access records
- Any other associated data

Usage:
    python scripts/delete_dummy_pharmacies.py [--confirm]
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
from src.db.conn import get_conn

def get_dummy_pharmacies():
    """Get all dummy pharmacies and their associated data counts"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Get dummy pharmacies
            cur.execute("""
                SELECT pharmacy_id, name 
                FROM pharma.pharmacies 
                WHERE name LIKE 'DUMMY%' 
                ORDER BY pharmacy_id
            """)
            dummy_pharmacies = cur.fetchall()
            
            if not dummy_pharmacies:
                return [], {}
            
            # Count associated data
            pharmacy_ids = [p['pharmacy_id'] for p in dummy_pharmacies]
            pharmacy_ids_str = ','.join(map(str, pharmacy_ids))
            
            cur.execute(f"""
                SELECT 
                    (SELECT COUNT(*) FROM pharma.fact_daily_sales WHERE pharmacy_id IN ({pharmacy_ids_str})) as daily_sales,
                    (SELECT COUNT(*) FROM pharma.fact_stock_activity WHERE pharmacy_id IN ({pharmacy_ids_str})) as stock_activity,
                    (SELECT COUNT(*) FROM pharma.report_receipts WHERE pharmacy_id IN ({pharmacy_ids_str})) as receipts,
                    (SELECT COUNT(*) FROM pharma.report_coverage WHERE pharmacy_id IN ({pharmacy_ids_str})) as coverage,
                    (SELECT COUNT(*) FROM pharma.user_pharmacies WHERE pharmacy_id IN ({pharmacy_ids_str})) as user_access,
                    (SELECT COUNT(*) FROM pharma.agg_sales_mtd WHERE pharmacy_id IN ({pharmacy_ids_str})) as mtd_agg,
                    (SELECT COUNT(*) FROM pharma.agg_sales_ytd WHERE pharmacy_id IN ({pharmacy_ids_str})) as ytd_agg,
                    (SELECT COUNT(*) FROM pharma.product_usage WHERE pharmacy_id IN ({pharmacy_ids_str})) as product_usage,
                    (SELECT COUNT(*) FROM pharma.pharmacy_targets WHERE pharmacy_id IN ({pharmacy_ids_str})) as targets
            """)
            counts = cur.fetchone()
            
            return dummy_pharmacies, dict(counts)

def delete_dummy_pharmacies(confirm=False):
    """Delete all dummy pharmacies and associated data"""
    dummy_pharmacies, counts = get_dummy_pharmacies()
    
    if not dummy_pharmacies:
        print("✓ No dummy pharmacies found to delete.")
        return
    
    print("DUMMY PHARMACIES TO DELETE:")
    print("=" * 70)
    for p in dummy_pharmacies:
        print(f"  ID {p['pharmacy_id']}: {p['name']}")
    
    print(f"\nASSOCIATED DATA TO DELETE:")
    print("=" * 70)
    total_records = 0
    for key, count in counts.items():
        if count > 0:
            label = key.replace('_', ' ').title()
            print(f"  {label}: {count:,}")
            total_records += count
    
    print(f"\n  TOTAL RECORDS TO DELETE: {total_records:,}")
    print(f"  PHARMACIES TO DELETE: {len(dummy_pharmacies)}")
    
    if not confirm:
        print(f"\n⚠️  This will permanently delete {len(dummy_pharmacies)} dummy pharmacies")
        print(f"   and {total_records:,} associated records!")
        print(f"\n   Run with --confirm to proceed with deletion.")
        return
    
    print(f"\n🗑️  PROCEEDING WITH DELETION...")
    print("=" * 70)
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            pharmacy_ids = [p['pharmacy_id'] for p in dummy_pharmacies]
            
            # Delete in proper order (respecting foreign key constraints)
            tables_to_clean = [
                ("pharma.product_usage", "Product usage data"),
                ("pharma.pharmacy_targets", "Pharmacy targets"),
                ("pharma.agg_sales_ytd", "YTD aggregates"),
                ("pharma.agg_sales_mtd", "MTD aggregates"),
                ("pharma.fact_stock_activity", "Stock activity"),
                ("pharma.fact_daily_sales", "Daily sales"),
                ("pharma.report_coverage", "Report coverage"),
                ("pharma.report_receipts", "Report receipts"),
                ("pharma.user_pharmacies", "User access"),
            ]
            
            for table, description in tables_to_clean:
                cur.execute(f"SELECT COUNT(*) as count FROM {table} WHERE pharmacy_id = ANY(%s)", (pharmacy_ids,))
                count = cur.fetchone()['count']
                
                if count > 0:
                    cur.execute(f"DELETE FROM {table} WHERE pharmacy_id = ANY(%s)", (pharmacy_ids,))
                    print(f"  ✓ Deleted {count:,} records from {description}")
            
            # Finally delete the pharmacies themselves
            cur.execute("DELETE FROM pharma.pharmacies WHERE pharmacy_id = ANY(%s)", (pharmacy_ids,))
            print(f"  ✓ Deleted {len(dummy_pharmacies)} dummy pharmacies")
            
            conn.commit()
    
    print(f"\n" + "=" * 70)
    print(f"✅ DELETION COMPLETE!")
    print(f"=" * 70)
    print(f"Successfully deleted:")
    print(f"  • {len(dummy_pharmacies)} dummy pharmacies")
    print(f"  • {total_records:,} associated data records")
    print(f"\nYour database is now clean of dummy data! 🎉")

def main():
    parser = argparse.ArgumentParser(
        description="Delete all dummy pharmacies and their associated data"
    )
    parser.add_argument(
        "--confirm", 
        action="store_true", 
        help="Confirm deletion (required to actually delete data)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show what would be deleted without actually deleting (default behavior)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("DUMMY PHARMACY DELETION TOOL")
    print("=" * 70)
    
    if args.dry_run or not args.confirm:
        print("🔍 DRY RUN MODE - No data will be deleted")
        print("=" * 70)
    
    try:
        delete_dummy_pharmacies(confirm=args.confirm)
    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 