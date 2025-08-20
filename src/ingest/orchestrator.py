import hashlib
import signal
from pathlib import Path
from typing import Dict, Any, Optional
import os

from src.mail.gmail_client import GmailClient
from src.db.loader import (
	upsert_daily_sales,
	insert_receipt_and_coverage,
	upsert_stock_activity_line,
	refresh_product_usage,
	refresh_mtd,
	refresh_ytd,
)
from src.classify import classify_file
from src.parsers.turnover import parse_turnover_summary
from src.parsers.trading_account import parse_trading_account
from src.parsers.scripts import parse_scripts
from src.parsers.gp_report import parse_gp_report

REPORT_MAP = {
	"turnover_summary": parse_turnover_summary,
	"trading_account": parse_trading_account,
	"dispensary_scripts": parse_scripts,
	"gross_profit": parse_gp_report,
}


def timeout_handler(signum, frame):
	raise TimeoutError("PDF processing timed out")


def classify_and_parse_bytes_with_timeout(filename: str, data: bytes, timeout_seconds: int = 30) -> Dict[str, Any]:
	"""Process PDF with timeout to prevent hangs."""
	# Save to a tmp file for pdfminer/classifier
	tmp = Path(".tmp")
	tmp.mkdir(exist_ok=True)
	path = tmp / filename
	
	try:
		with open(path, "wb") as f:
			f.write(data)
		
		# Set timeout for the entire processing
		old_handler = signal.signal(signal.SIGALRM, timeout_handler)
		signal.alarm(timeout_seconds)
		
		try:
			c = classify_file(path)
			if not c.report_type:
				return {"status": "skipped_unclassified", "path": str(path)}
			
			parser = REPORT_MAP.get(c.report_type)
			if not parser:
				return {"status": "skipped_no_parser", "report_type": c.report_type, "path": str(path)}
			
			rec = parser(path)
			rec["status"] = "parsed"
			rec["report_type"] = c.report_type
			return rec
		finally:
			signal.alarm(0)
			signal.signal(signal.SIGALRM, old_handler)
	except TimeoutError:
		return {"status": "timeout", "path": str(path), "error": f"Processing took longer than {timeout_seconds}s"}
	except Exception as e:
		return {"status": "error", "path": str(path), "error": str(e)}
	finally:
		# Clean up temp file
		try:
			if path.exists():
				os.unlink(path)
		except Exception:
			pass


def sha256_bytes(b: bytes) -> str:
	h = hashlib.sha256()
	h.update(b)
	return h.hexdigest()


def classify_and_parse_bytes(filename: str, data: bytes) -> Dict[str, Any]:
	"""Legacy function - use classify_and_parse_bytes_with_timeout instead."""
	return classify_and_parse_bytes_with_timeout(filename, data)


def to_business_date(rec: Dict[str, Any]) -> Optional[str]:
	return rec.get("date_from") or rec.get("business_date") or rec.get("date_to")


def process_record(rec: Dict[str, Any], mode: str) -> None:
	rt = rec.get("report_type")
	pid = rec.get("pharmacy_id")
	bdate = to_business_date(rec)
	if not (rt and pid and bdate):
		return

	if rt in ("turnover_summary", "trading_account", "dispensary_scripts"):
		upsert_daily_sales(rec, mode=mode)
	elif rt == "gross_profit":
		for line in rec.get("lines", []):
			prod_id, _ = upsert_stock_activity_line(pid, bdate, line)
			refresh_product_usage(pid, prod_id, bdate)


def write_receipts(pharmacy_id: int, business_date: str, report_type: str, filename: str, sha256: str, byte_size: int):
	insert_receipt_and_coverage({
		"pharmacy_id": pharmacy_id,
		"business_date": business_date,
		"report_type": report_type,
		"filename": filename,
		"sha256": sha256,
		"byte_size": byte_size,
	}) 