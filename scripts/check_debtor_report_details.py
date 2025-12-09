#!/usr/bin/env python
"""
Check details of the most recent debtor report import.
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
        
        # Get the 5 most recent debtor reports with details
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
            GROUP BY dr.id, dr.pharmacy_id, p.name, dr.filename, dr.uploaded_at, 
                     dr.total_accounts, dr.total_outstanding, dr.status, dr.error_message
            ORDER BY dr.uploaded_at DESC
            LIMIT 5
        """)
        
        reports = cur.fetchall()
        
        print("=" * 70)
        print("RECENT DEBTOR REPORTS (Last 5)")
        print("=" * 70)
        
        for i, report in enumerate(reports, 1):
            print(f"\n[{i}] Report ID: {report['id']}")
            print(f"    Pharmacy: {report['pharmacy_name']} (ID: {report['pharmacy_id']})")
            print(f"    Filename: {report['filename']}")
            print(f"    Uploaded: {report['uploaded_at']}")
            print(f"    Status: {report['status']}")
            print(f"    Expected Accounts: {report['total_accounts']}")
            print(f"    Actual Debtors in DB: {report['actual_debtor_count']}")
            print(f"    Total Outstanding: R {float(report['total_outstanding']):,.2f}")
            if report['error_message']:
                print(f"    ⚠️  ERROR: {report['error_message']}")
            if report['total_accounts'] > 0 and report['actual_debtor_count'] == 0:
                print(f"    ⚠️  WARNING: Report says {report['total_accounts']} accounts but 0 debtors inserted!")

if __name__ == "__main__":
    main()

