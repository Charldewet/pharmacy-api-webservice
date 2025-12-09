#!/usr/bin/env python
"""
Test script to check for and import a new Reitz debtor report from emails.
"""

import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from psycopg import connect
from psycopg.rows import dict_row

# Ensure project root for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(find_dotenv(), override=False)

from scripts.live_import_5h import fetch_recent_attachments
from src.classify import classify_file, classify_email_subject
from src.parsers.debtor_report import parse_debtor_report

# Use same env vars as live_import_5h
IMAP_USER = os.environ.get("REITZ_GMAIL_USERNAME")
IMAP_PASS = os.environ.get("REITZ_GMAIL_APP_PASSWORD")
GMAIL_LABEL = os.environ.get("GMAIL_LABEL", "pharmacy-reports")
LOOKBACK_HOURS = 24  # Check last 24 hours

DSN = os.environ.get("DATABASE_URL")
if not DSN:
    print("ERROR: DATABASE_URL environment variable is required")
    sys.exit(1)
if not IMAP_USER:
    print("ERROR: REITZ_GMAIL_USERNAME environment variable is required")
    sys.exit(1)
if not IMAP_PASS:
    print("ERROR: REITZ_GMAIL_APP_PASSWORD environment variable is required")
    sys.exit(1)

def main():
    print("=" * 70)
    print("CHECKING FOR NEW REITZ DEBTOR REPORTS")
    print("=" * 70)
    
    # Fetch recent attachments
    print(f"\n[1] Fetching attachments from last {LOOKBACK_HOURS} hours...")
    atts = fetch_recent_attachments(GMAIL_LABEL, LOOKBACK_HOURS, 500)
    print(f"    Found {len(atts)} attachments")
    
    # Filter for Reitz and debtor reports
    reitz_debtor_reports = []
    for att in atts:
        # Classify email subject
        email_classification = classify_email_subject(att.subject or "")
        if email_classification.pharmacy_id == 1:  # Reitz is ID 1
            # Classify the PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(att.data)
                tmp.flush()
                tmp_path = tmp.name
            
            try:
                classification = classify_file(tmp_path)
                if classification.report_type == "debtor_report":
                    # Keep the temp file for later processing
                    reitz_debtor_reports.append((att, tmp_path, classification))
                    print(f"\n    ✓ Found Reitz debtor report: {att.filename}")
                    print(f"      Subject: {att.subject}")
                    print(f"      Received: {att.received_at}")
            except Exception as e:
                print(f"    ⚠️  Error classifying {att.filename}: {e}")
                try:
                    os.unlink(tmp_path)
                except:
                    pass
    
    if not reitz_debtor_reports:
        print("\n❌ No Reitz debtor reports found in the last 24 hours")
        return
    
    # Clean up temp files for reports we're not processing
    for i in range(1, len(reitz_debtor_reports)):
        try:
            os.unlink(reitz_debtor_reports[i][1])
        except:
            pass
    
    # Process the most recent one
    att, pdf_path, classification = reitz_debtor_reports[0]
    print(f"\n[2] Processing most recent report: {att.filename}")
    
    # Parse the PDF
    print(f"    Parsing PDF...")
    try:
        parsed_data = parse_debtor_report(Path(pdf_path))
        print(f"    ✓ Parsed successfully")
        print(f"      - Report type: {parsed_data.get('report_type')}")
        print(f"      - Total accounts: {parsed_data.get('total_accounts', 0)}")
        print(f"      - Total outstanding: R {parsed_data.get('total_outstanding', 0):,.2f}")
        print(f"      - Debtors list length: {len(parsed_data.get('debtors', []))}")
        
        if parsed_data.get('debtors'):
            print(f"\n    Sample debtor (first one):")
            sample = parsed_data['debtors'][0]
            for key, value in sample.items():
                print(f"      {key}: {value}")
    except Exception as e:
        print(f"    ❌ Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check database insertion
    print(f"\n[3] Testing database insertion...")
    print(f"    Pharmacy ID: {classification.pharmacy_id}")
    
    # Import the load_debtor_report function
    from scripts.live_import_5h import load_debtor_report
    
    with connect(DSN, row_factory=dict_row, autocommit=False) as conn:
        cur = conn.cursor()
        
        try:
            # Create a mock attachment record
            from scripts.live_import_5h import AttachmentRec, sha256_bytes
            att_rec = AttachmentRec(
                message_uid=0,
                filename=att.filename,
                data=att.data,
                sha256=sha256_bytes(att.data),
                received_at=att.received_at,
                subject=att.subject or "",
                pharmacy_id=classification.pharmacy_id
            )
            
            # Add pharmacy_id to parsed_data
            parsed_data['pharmacy_id'] = classification.pharmacy_id
            
            # Use the existing PDF path
            temp_path = pdf_path
            
            print(f"    Calling load_debtor_report...")
            print(f"    Debtors to insert: {len(parsed_data.get('debtors', []))}")
            debtor_rows = load_debtor_report(cur, att_rec, parsed_data, temp_path)
            
            conn.commit()
            
            print(f"\n✓ SUCCESS!")
            print(f"  - Debtors inserted: {debtor_rows}")
            
            # Verify insertion
            cur.execute("""
                SELECT COUNT(*) as count, SUM(balance) as total
                FROM pharma.debtors
                WHERE pharmacy_id = %s
            """, (classification.pharmacy_id,))
            
            result = cur.fetchone()
            print(f"  - Total debtors in DB for Reitz: {result['count']}")
            print(f"  - Total outstanding: R {float(result['total'] or 0):,.2f}")
            
            # Don't delete temp_path here - it's still needed for the list
                
        except Exception as e:
            conn.rollback()
            print(f"\n❌ ERROR inserting into database: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up temp file
            try:
                os.unlink(pdf_path)
            except:
                pass

if __name__ == "__main__":
    main()

