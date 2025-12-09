#!/usr/bin/env python
"""
Check when the last debtor report was imported.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
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
        
        # Get the most recent debtor report
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
                u.username as uploaded_by_username
            FROM pharma.debtor_reports dr
            LEFT JOIN pharma.pharmacies p ON dr.pharmacy_id = p.pharmacy_id
            LEFT JOIN pharma.users u ON dr.uploaded_by = u.user_id
            ORDER BY dr.uploaded_at DESC
            LIMIT 1
        """)
        
        latest = cur.fetchone()
        
        if not latest:
            print("No debtor reports found in the database.")
            return
        
        print("=" * 70)
        print("LAST DEBTOR REPORT IMPORT")
        print("=" * 70)
        print(f"Report ID: {latest['id']}")
        print(f"Pharmacy: {latest['pharmacy_name']} (ID: {latest['pharmacy_id']})")
        print(f"Filename: {latest['filename']}")
        print(f"Uploaded At: {latest['uploaded_at']}")
        print(f"Total Accounts: {latest['total_accounts']}")
        print(f"Total Outstanding: R {float(latest['total_outstanding']):,.2f}")
        print(f"Status: {latest['status']}")
        if latest['uploaded_by_username']:
            print(f"Uploaded By: {latest['uploaded_by_username']}")
        if latest['error_message']:
            print(f"Error: {latest['error_message']}")
        
        # Get all debtor reports count by pharmacy
        cur.execute("""
            SELECT 
                p.name as pharmacy_name,
                COUNT(*) as report_count,
                MAX(dr.uploaded_at) as last_import
            FROM pharma.debtor_reports dr
            JOIN pharma.pharmacies p ON dr.pharmacy_id = p.pharmacy_id
            GROUP BY p.name, dr.pharmacy_id
            ORDER BY last_import DESC
        """)
        
        all_reports = cur.fetchall()
        
        print("\n" + "=" * 70)
        print("DEBTOR REPORTS BY PHARMACY")
        print("=" * 70)
        for report in all_reports:
            print(f"{report['pharmacy_name']}: {report['report_count']} report(s), last import: {report['last_import']}")
        
        # Get total debtors count
        cur.execute("""
            SELECT 
                COUNT(DISTINCT pharmacy_id) as pharmacy_count,
                COUNT(*) as total_debtors,
                SUM(balance) as total_outstanding
            FROM pharma.debtors
        """)
        
        totals = cur.fetchone()
        
        print("\n" + "=" * 70)
        print("TOTAL DEBTORS SUMMARY")
        print("=" * 70)
        print(f"Pharmacies with debtors: {totals['pharmacy_count']}")
        print(f"Total debtor accounts: {totals['total_debtors']}")
        print(f"Total outstanding: R {float(totals['total_outstanding'] or 0):,.2f}")

if __name__ == "__main__":
    main()

