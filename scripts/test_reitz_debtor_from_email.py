#!/usr/bin/env python
"""
Test Reitz debtor report from email inbox.
"""

import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv, find_dotenv

# Ensure project root for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(find_dotenv(), override=True)

from src.classify import classify_file, classify_email_subject
from PDF_PARSER_COMPLETE import extract_debtors_strictest_names
from imapclient import IMAPClient
from email import message_from_bytes
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import pandas as pd

IMAP_USER = os.environ.get("REITZ_GMAIL_USERNAME")
IMAP_PASS = os.environ.get("REITZ_GMAIL_APP_PASSWORD")
GMAIL_LABEL = os.environ.get("GMAIL_LABEL", "pharmacy-reports")
IMAP_FOLDER = os.environ.get("IMAP_FOLDER", "INBOX")
LOOKBACK_HOURS = 48  # Check last 48 hours (yesterday + today)

if not IMAP_USER or not IMAP_PASS:
    print("ERROR: REITZ_GMAIL_USERNAME and REITZ_GMAIL_APP_PASSWORD environment variables required")
    sys.exit(1)

@dataclass
class AttachmentRec:
    message_uid: int
    received_at: datetime
    filename: str
    data: bytes
    sha256: str
    subject: str
    pharmacy_id: int = None

def sha256_bytes(b: bytes) -> str:
    import hashlib
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def fetch_recent_attachments(label: str, lookback_hours: int, max_messages: int):
    """Fetch recent PDF attachments from email"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    out = []
    
    with IMAPClient("imap.gmail.com", ssl=True) as server:
        server.login(IMAP_USER, IMAP_PASS)
        server.select_folder(IMAP_FOLDER)
        
        # Build search query
        raw_query = f'label:"{label}" has:attachment filename:pdf newer_than:2d' if label else 'has:attachment filename:pdf newer_than:2d'
        uids = server.search(["X-GM-RAW", raw_query])
        uids.sort(reverse=True)
        
        if not uids:
            return out
        
        # Filter by date
        meta = server.fetch(uids, ["INTERNALDATE"])
        candidates = [u for u in uids if meta[u][b"INTERNALDATE"].astimezone(timezone.utc) >= cutoff]
        candidates = candidates[:max_messages] if max_messages else candidates
        
        if not candidates:
            return out
        
        # Fetch messages
        fetch_map = server.fetch(candidates, ["BODY.PEEK[]"])
        for uid in candidates:
            msg_bytes = fetch_map[uid].get(b"BODY[]") or fetch_map[uid].get(b"RFC822")
            if not msg_bytes:
                continue
            
            msg = message_from_bytes(msg_bytes)
            received = meta[uid][b"INTERNALDATE"].astimezone(timezone.utc)
            subject = msg.get("subject", "")
            
            # Pre-classify by email subject
            pharmacy_info = classify_email_subject(subject)
            pharmacy_id = pharmacy_info.pharmacy_id if pharmacy_info else None
            
            # Extract PDF attachments
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                filename = part.get_filename()
                if filename and filename.lower().endswith('.pdf'):
                    payload = part.get_payload(decode=True)
                    if payload:
                        out.append(AttachmentRec(
                            message_uid=uid,
                            received_at=received,
                            filename=filename,
                            data=payload,
                            sha256=sha256_bytes(payload),
                            subject=subject,
                            pharmacy_id=pharmacy_id
                        ))
    
    return out

def main():
    print("=" * 70)
    print("SEARCHING FOR REITZ DEBTOR REPORTS IN EMAIL")
    print("=" * 70)
    print(f"Looking back: {LOOKBACK_HOURS} hours")
    print()
    
    # Fetch recent attachments
    print("[1] Fetching attachments from email...")
    atts = fetch_recent_attachments(GMAIL_LABEL, LOOKBACK_HOURS, 500)
    print(f"    Found {len(atts)} total attachments")
    
    # Filter for Reitz debtor reports
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
        print("\n❌ No Reitz debtor reports found in the last 48 hours")
        return
    
    # Sort by received_at (most recent first)
    reitz_debtor_reports.sort(key=lambda x: x[0].received_at, reverse=True)
    
    # Process the most recent one
    att, pdf_path, classification = reitz_debtor_reports[0]
    print(f"\n[2] Processing most recent report: {att.filename}")
    print(f"    Received: {att.received_at}")
    
    # Parse the PDF
    print(f"\n[3] Parsing PDF with extract_debtors_strictest_names...")
    try:
        df = extract_debtors_strictest_names(pdf_path)
        print(f"    ✓ Parsed successfully")
        print(f"      - Total debtors extracted: {len(df)}")
        
        # Check for contact details
        with_email = df[df['email'].notna() & (df['email'] != '')]
        with_phone = df[df['phone'].notna() & (df['phone'] != '')]
        with_both = df[(df['email'].notna() & (df['email'] != '')) & (df['phone'].notna() & (df['phone'] != ''))]
        
        print(f"\n[4] CONTACT DETAILS EXTRACTION RESULTS")
        print("=" * 70)
        print(f"Total debtors: {len(df)}")
        print(f"With email: {len(with_email)} ({len(with_email)/len(df)*100:.1f}%)")
        print(f"With phone: {len(with_phone)} ({len(with_phone)/len(df)*100:.1f}%)")
        print(f"With both: {len(with_both)} ({len(with_both)/len(df)*100:.1f}%)")
        
        if len(with_email) > 0:
            print(f"\n[5] SAMPLE DEBTORS WITH EMAIL")
            print("=" * 70)
            for idx, row in with_email.head(10).iterrows():
                print(f"Acc: {row['acc_no']}, Name: {row['name'][:40]}")
                print(f"  Email: {row['email']}")
                print(f"  Phone: {row['phone'] or 'N/A'}")
                print(f"  Balance: R {float(row['balance']):,.2f}")
                print()
        
        if len(with_phone) > 0:
            print(f"\n[6] SAMPLE DEBTORS WITH PHONE")
            print("=" * 70)
            for idx, row in with_phone.head(10).iterrows():
                print(f"Acc: {row['acc_no']}, Name: {row['name'][:40]}")
                print(f"  Email: {row['email'] or 'N/A'}")
                print(f"  Phone: {row['phone']}")
                print(f"  Balance: R {float(row['balance']):,.2f}")
                print()
        
        # Calculate totals
        total_outstanding = float(df['balance'].sum()) if not df.empty else 0.0
        print(f"\n[7] SUMMARY")
        print("=" * 70)
        print(f"Total Accounts: {len(df)}")
        print(f"Total Outstanding: R {total_outstanding:,.2f}")
        print(f"Contact Details Available:")
        print(f"  - {len(with_email)} debtors have email addresses")
        print(f"  - {len(with_phone)} debtors have phone numbers")
        print(f"  - {len(with_both)} debtors have both")
        
    except Exception as e:
        print(f"    ❌ Error parsing PDF: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up temp file
        try:
            os.unlink(pdf_path)
        except:
            pass
        
        # Clean up other temp files
        for _, tmp_path, _ in reitz_debtor_reports[1:]:
            try:
                os.unlink(tmp_path)
            except:
                pass

if __name__ == "__main__":
    main()

