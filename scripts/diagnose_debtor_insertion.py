#!/usr/bin/env python
"""
Diagnose why debtors aren't being inserted into the database.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from psycopg import connect
from psycopg.rows import dict_row

# Ensure project root for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(find_dotenv(), override=False)

DSN = os.environ.get("DATABASE_URL")
if not DSN:
    print("ERROR: DATABASE_URL environment variable is required")
    sys.exit(1)

def main():
    with connect(DSN, row_factory=dict_row) as conn:
        cur = conn.cursor()
        
        # Check reports that claim to have accounts but have no debtors
        cur.execute("""
            SELECT 
                dr.id,
                dr.pharmacy_id,
                p.name as pharmacy_name,
                dr.filename,
                dr.uploaded_at,
                dr.total_accounts,
                dr.total_outstanding,
                dr.status,
                dr.error_message,
                COUNT(d.id) as actual_debtor_count
            FROM pharma.debtor_reports dr
            LEFT JOIN pharma.pharmacies p ON dr.pharmacy_id = p.pharmacy_id
            LEFT JOIN pharma.debtors d ON d.report_id = dr.id
            WHERE dr.total_accounts > 0
            GROUP BY dr.id, dr.pharmacy_id, p.name, dr.filename, dr.uploaded_at, 
                     dr.total_accounts, dr.total_outstanding, dr.status, dr.error_message
            HAVING COUNT(d.id) = 0
            ORDER BY dr.uploaded_at DESC
            LIMIT 5
        """)
        
        problematic_reports = cur.fetchall()
        
        print("=" * 70)
        print("PROBLEMATIC REPORTS (Claim accounts but have no debtors)")
        print("=" * 70)
        
        if problematic_reports:
            for report in problematic_reports:
                print(f"\nReport ID: {report['id']}")
                print(f"  Pharmacy: {report['pharmacy_name']} (ID: {report['pharmacy_id']})")
                print(f"  Filename: {report['filename']}")
                print(f"  Uploaded: {report['uploaded_at']}")
                print(f"  Expected Accounts: {report['total_accounts']}")
                print(f"  Actual Debtors: 0")
                print(f"  Status: {report['status']}")
                if report['error_message']:
                    print(f"  Error: {report['error_message']}")
        else:
            print("\n✓ No problematic reports found")
        
        # Check the most recent successful insertion (if any)
        cur.execute("""
            SELECT 
                dr.id,
                p.name as pharmacy_name,
                dr.uploaded_at,
                dr.total_accounts,
                COUNT(d.id) as actual_debtor_count
            FROM pharma.debtor_reports dr
            JOIN pharma.pharmacies p ON dr.pharmacy_id = p.pharmacy_id
            JOIN pharma.debtors d ON d.report_id = dr.id
            GROUP BY dr.id, p.name, dr.uploaded_at, dr.total_accounts
            HAVING COUNT(d.id) > 0
            ORDER BY dr.uploaded_at DESC
            LIMIT 1
        """)
        
        successful = cur.fetchone()
        
        print("\n" + "=" * 70)
        print("LAST SUCCESSFUL INSERTION")
        print("=" * 70)
        if successful:
            print(f"Report ID: {successful['id']}")
            print(f"Pharmacy: {successful['pharmacy_name']}")
            print(f"Uploaded: {successful['uploaded_at']}")
            print(f"Expected: {successful['total_accounts']} accounts")
            print(f"Actual: {successful['actual_debtor_count']} debtors")
        else:
            print("❌ No successful insertions found - all reports have 0 debtors!")
        
        # Check database schema for debtors table
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'pharma' AND table_name = 'debtors'
            ORDER BY ordinal_position
        """)
        
        columns = cur.fetchall()
        
        print("\n" + "=" * 70)
        print("DEBTORS TABLE SCHEMA")
        print("=" * 70)
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
        
        # Check if there are any constraints that might prevent insertion
        cur.execute("""
            SELECT 
                conname as constraint_name,
                contype as constraint_type,
                pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'pharma.debtors'::regclass
        """)
        
        constraints = cur.fetchall()
        
        print("\n" + "=" * 70)
        print("DEBTORS TABLE CONSTRAINTS")
        print("=" * 70)
        if constraints:
            for con in constraints:
                print(f"  {con['constraint_name']} ({con['constraint_type']}): {con['definition']}")
        else:
            print("  No constraints found")

if __name__ == "__main__":
    main()

