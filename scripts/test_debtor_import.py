#!/usr/bin/env python
"""
Test script to import a debtor report PDF into the database.
"""

import os
import sys
import hashlib
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

from src.classify import classify_file
from src.parsers.debtor_report import parse_debtor_report
from PDF_PARSER_COMPLETE import is_medical_aid_control_account

DSN = os.environ.get("DATABASE_URL")
if not DSN:
    print("ERROR: DATABASE_URL environment variable is required")
    sys.exit(1)

# SQL statements
INSERT_DEBTOR_REPORT = """
INSERT INTO pharma.debtor_reports (
    pharmacy_id, filename, file_path, uploaded_at, uploaded_by,
    total_accounts, total_outstanding, status
)
VALUES (
    %(pharmacy_id)s, %(filename)s, %(file_path)s, %(uploaded_at)s, %(uploaded_by)s,
    %(total_accounts)s, %(total_outstanding)s, 'completed'
)
RETURNING id;
"""

DELETE_PHARMACY_DEBTORS = """
DELETE FROM pharma.debtors
WHERE pharmacy_id = %(pharmacy_id)s;
"""

INSERT_DEBTOR = """
INSERT INTO pharma.debtors (
    pharmacy_id, report_id, acc_no, name,
    current, d30, d60, d90, d120, d150, d180, balance,
    email, phone, is_medical_aid_control
)
VALUES (
    %(pharmacy_id)s, %(report_id)s, %(acc_no)s, %(name)s,
    %(current)s, %(d30)s, %(d60)s, %(d90)s, %(d120)s, %(d150)s, %(d180)s, %(balance)s,
    %(email)s, %(phone)s, %(is_medical_aid_control)s
);
"""

def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def load_debtor_report(cur, pdf_path: Path, rec: dict, pharmacy_id: int):
    """Load debtor report into database"""
    
    # Step 1: Delete ALL existing debtors for this pharmacy
    cur.execute(DELETE_PHARMACY_DEBTORS, {"pharmacy_id": pharmacy_id})
    deleted_count = cur.rowcount
    print(f"  Deleted {deleted_count} existing debtors for pharmacy {pharmacy_id}")
    
    # Step 2: Insert new debtor report record
    report_params = {
        "pharmacy_id": pharmacy_id,
        "filename": pdf_path.name,
        "file_path": str(pdf_path),
        "uploaded_at": datetime.now(),
        "uploaded_by": None,
        "total_accounts": rec.get("total_accounts", 0),
        "total_outstanding": rec.get("total_outstanding", 0.0),
    }
    
    cur.execute(INSERT_DEBTOR_REPORT, report_params)
    result = cur.fetchone()
    report_id = result["id"] if isinstance(result, dict) else result[0]
    print(f"  Created debtor report record (ID: {report_id})")
    
    # Step 3: Insert new debtors
    debtors = rec.get("debtors", [])
    inserted_count = 0
    for debtor in debtors:
        debtor_params = {
            "pharmacy_id": pharmacy_id,
            "report_id": report_id,
            "acc_no": str(debtor.get("acc_no", "")),
            "name": str(debtor.get("name", "")),
            "current": float(debtor.get("current", 0.0)),
            "d30": float(debtor.get("d30", 0.0)),
            "d60": float(debtor.get("d60", 0.0)),
            "d90": float(debtor.get("d90", 0.0)),
            "d120": float(debtor.get("d120", 0.0)),
            "d150": float(debtor.get("d150", 0.0)),
            "d180": float(debtor.get("d180", 0.0)),
            "balance": float(debtor.get("balance", 0.0)),
            "email": debtor.get("email") or None,
            "phone": debtor.get("phone") or None,
            "is_medical_aid_control": is_medical_aid_control_account(debtor.get("name", "")),
        }
        cur.execute(INSERT_DEBTOR, debtor_params)
        inserted_count += 1
    
    return deleted_count, inserted_count, report_id

def main():
    pdf_path = Path("testPDFs/20251116-11h39m35s-Complete.pdf")
    
    if not pdf_path.exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 70)
    print("TESTING DEBTOR REPORT IMPORT")
    print("=" * 70)
    print(f"\nPDF File: {pdf_path}")
    
    # Step 1: Classify
    print("\n[1] Classifying PDF...")
    classification = classify_file(pdf_path)
    print(f"  ✓ Report Type: {classification.report_type}")
    print(f"  ✓ Pharmacy ID: {classification.pharmacy_id}")
    print(f"  ✓ Pharmacy Name: {classification.pharmacy_name}")
    
    if classification.report_type != "debtor_report":
        print(f"\nERROR: Expected debtor_report, got {classification.report_type}")
        sys.exit(1)
    
    if not classification.pharmacy_id:
        print("\nERROR: Could not determine pharmacy_id")
        sys.exit(1)
    
    # Step 2: Parse
    print("\n[2] Parsing PDF...")
    parsed_data = parse_debtor_report(pdf_path)
    print(f"  ✓ Total Accounts: {parsed_data['total_accounts']}")
    print(f"  ✓ Total Outstanding: R {parsed_data['total_outstanding']:,.2f}")
    
    # Set pharmacy_id from classification
    parsed_data["pharmacy_id"] = classification.pharmacy_id
    
    # Show sample debtors
    print(f"\n  Sample Debtors (first 5):")
    for i, debtor in enumerate(parsed_data['debtors'][:5], 1):
        email = debtor.get("email", "") or "N/A"
        phone = debtor.get("phone", "") or "N/A"
        print(f"    {i}. {debtor['acc_no']} | {debtor['name'][:35]:35s} | R {debtor['balance']:>10,.2f} | {email[:25]:25s} | {phone}")
    
    # Step 3: Insert into database
    print(f"\n[3] Inserting into database...")
    print(f"  Pharmacy ID: {classification.pharmacy_id}")
    
    with connect(DSN, row_factory=dict_row, autocommit=False) as conn:
        cur = conn.cursor()
        
        try:
            deleted, inserted, report_id = load_debtor_report(
                cur, pdf_path, parsed_data, classification.pharmacy_id
            )
            
            conn.commit()
            
            print(f"\n✓ SUCCESS!")
            print(f"  - Deleted {deleted} existing debtors")
            print(f"  - Inserted {inserted} new debtors")
            print(f"  - Report ID: {report_id}")
            
            # Query summary
            cur.execute("""
                SELECT 
                    COUNT(*) as total_debtors,
                    SUM(balance) as total_balance,
                    COUNT(CASE WHEN email IS NOT NULL AND email != '' THEN 1 END) as with_email,
                    COUNT(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 END) as with_phone,
                    COUNT(CASE WHEN is_medical_aid_control THEN 1 END) as medical_aid_accounts
                FROM pharma.debtors
                WHERE pharmacy_id = %s
            """, (classification.pharmacy_id,))
            
            summary = cur.fetchone()
            
            print(f"\n[4] Database Summary for Pharmacy {classification.pharmacy_id}:")
            print(f"  ✓ Total Debtors: {summary['total_debtors']}")
            print(f"  ✓ Total Outstanding: R {summary['total_balance']:,.2f}")
            print(f"  ✓ With Email: {summary['with_email']}")
            print(f"  ✓ With Phone: {summary['with_phone']}")
            print(f"  ✓ Medical Aid Accounts: {summary['medical_aid_accounts']}")
            
        except Exception as e:
            conn.rollback()
            print(f"\n✗ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()

