import argparse
import os
import sys
from datetime import datetime, date, timedelta

# Ensure project root on import path when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure logs flush promptly when piped
try:
	sys.stdout.reconfigure(line_buffering=True)
except Exception:
	pass

from src.mail.gmail_client import GmailClient
from src.mail.imap_client import ImapClient
from src.ingest.orchestrator import (
	classify_and_parse_bytes, process_record, write_receipts, sha256_bytes
)
from src.db.conn import get_cursor


def receipts_seen(pharmacy_id: int, business_date: str, report_type: str, sha256: str) -> bool:
	with get_cursor() as cur:
		cur.execute(
			"""
			SELECT 1 FROM pharma.report_receipts
			WHERE pharmacy_id=%(p)s AND business_date=%(d)s AND report_type=%(t)s AND sha256=%(h)s
			LIMIT 1;
			""",
			{"p": pharmacy_id, "d": business_date, "t": report_type, "h": sha256},
		)
		return cur.fetchone() is not None


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--mode", choices=["historical", "live"], required=True)
	ap.add_argument("--label", default="pharmacy-reports", help="Label to restrict searches (Gmail/IMAP raw)")
	ap.add_argument("--since", help="Historical: YYYY-MM-DD")
	ap.add_argument("--until", help="Historical: YYYY-MM-DD (inclusive)")
	ap.add_argument("--poll-seconds", type=int, default=120, help="Live: poll interval")
	ap.add_argument("--transport", choices=["gmail_api", "imap"], default="gmail_api")
	ap.add_argument("--imap-user", help="IMAP username (if transport=imap)")
	ap.add_argument("--imap-pass", help="IMAP app password (if transport=imap)")
	ap.add_argument("--max-emails", type=int, default=100, help="Cap emails scanned per run")
	ap.add_argument("--simple-filter", action="store_true", help="Skip BODYSTRUCTURE prefilter, fetch all emails")
	args = ap.parse_args()

	def search_query_for_range(since: str, until: str) -> str:
		parts = [
			f'label:{args.label}',
			'has:attachment',
			'filename:pdf',
			'(subject:"Turnover" OR subject:"Trading" OR subject:"Script Statistics" OR subject:"Gross Profit")',
			f'after:{since}',
			f'before:{(datetime.fromisoformat(until) + timedelta(days=1)).date().isoformat()}'
		]
		return " ".join(parts)

	def iter_attachments_for_range(since: str, until: str):
		if args.transport == "gmail_api":
			client = GmailClient()
			q = search_query_for_range(since, until)
			ids = client.search_messages(query=q, max_results=args.max_emails)
			print(f"{len(ids)} emails found for {since}..{until} (Gmail API)", flush=True)
			for msg_id in ids:
				for filename, data in client.fetch_pdf_attachments(msg_id):
					yield filename, data
		else:
			user = args.imap_user or os.environ.get("IMAP_USER")
			pwd = args.imap_pass or os.environ.get("IMAP_PASS")
			if not user or not pwd:
				raise SystemExit("IMAP credentials required: --imap-user / --imap-pass or IMAP_USER / IMAP_PASS env")
			with ImapClient(user, pwd) as client:
				uids = client.search_by_date(since, until, max_results=args.max_emails)
				print(f"{len(uids)} emails found for {since}..{until} (IMAP)", flush=True)
				if not uids:
					return
				if args.simple_filter:
					# Skip BODYSTRUCTURE parsing, just fetch all emails
					print(f"Using simple filter: fetching all {len(uids)} emails", flush=True)
					pdf_uids = uids
				else:
					# Fast prefilter: BODYSTRUCTURE indicates pdf parts; avoids downloading full bodies unnecessarily
					pdf_uids = client.filter_pdf_uids_by_bodystructure(uids)
					print(f"{len(pdf_uids)} emails appear to have PDF attachments", flush=True)
				for uid in pdf_uids:
					for filename, data in client.fetch_pdf_attachments(uid):
						yield filename, data

	if args.mode == "historical":
		if not args.since or not args.until:
			raise SystemExit("--since and --until are required for historical mode")
		print(f"Starting historical ingestion for {args.since}..{args.until}", flush=True)
		attachments = list(iter_attachments_for_range(args.since, args.until))
		print(f"{len(attachments)} PDF attachments to consider. Processing…", flush=True)
		processed = 0
		skipped = 0
		report_types: list[str] = []
		for filename, data in attachments:
			rec = classify_and_parse_bytes(filename, data)
			if rec.get("status") != "parsed":
				skipped += 1
				continue
			pid = rec.get("pharmacy_id"); bdate = rec.get("date_from") or rec.get("date_to")
			rt = rec.get("report_type")
			report_types.append(rt)
			sha = sha256_bytes(data)
			if receipts_seen(pid, bdate, rt, sha):
				skipped += 1
				continue
			process_record(rec, mode="historical")
			write_receipts(pid, bdate, rt, filename, sha, len(data))
			processed += 1
		if report_types:
			unique = sorted(set(report_types))
			print("Reports found: " + ", ".join(unique), flush=True)
		print(f"Done. {processed} processed, {skipped} skipped.", flush=True)

	if args.mode == "live":
		import time
		print(f"Polling every {args.poll_seconds}s… (Ctrl+C to stop)", flush=True)
		while True:
			today = date.today().isoformat()
			attachments = list(iter_attachments_for_range(today, today))
			print(f"{len(attachments)} PDF attachments to consider for {today}. Processing…", flush=True)
			processed = 0
			skipped = 0
			report_types: list[str] = []
			for filename, data in attachments:
				print(f"Processing {filename}...", flush=True)
				rec = classify_and_parse_bytes(filename, data)
				if rec.get("status") != "parsed":
					print(f"  Skipped: {rec.get('status')} - {rec.get('error', '')}", flush=True)
					skipped += 1
					continue
				pid = rec.get("pharmacy_id"); bdate = rec.get("date_from") or rec.get("date_to")
				rt = rec.get("report_type")
				print(f"  Parsed: {rt} for pharmacy {pid} on {bdate}", flush=True)
				report_types.append(rt)
				sha = sha256_bytes(data)
				process_record(rec, mode="live")
				if not receipts_seen(pid, bdate, rt, sha):
					write_receipts(pid, bdate, rt, filename, sha, len(data))
					processed += 1
					print(f"  Added to database and receipts", flush=True)
				else:
					skipped += 1
					print(f"  Already seen, skipped", flush=True)
			if report_types:
				unique = sorted(set(report_types))
				print("Reports found: " + ", ".join(unique), flush=True)
			print(f"Done. {processed} processed, {skipped} skipped.", flush=True)
			time.sleep(args.poll_seconds)


if __name__ == "__main__":
	main() 