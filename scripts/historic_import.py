#!/usr/bin/env python
from __future__ import annotations
import os, io, sys, json, hashlib, tempfile, argparse, time
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any, Iterable
from datetime import date, datetime, timedelta, timezone

# --- ensure project root on sys.path (so `src.*` imports work when running from scripts/)
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv, find_dotenv
from imapclient import IMAPClient
from email import message_from_bytes
from psycopg import connect
from psycopg.rows import dict_row

# ====== ENV
load_dotenv(find_dotenv(), override=False)

DSN          = os.environ.get("DATABASE_URL")
IMAP_USER    = os.environ.get("REITZ_GMAIL_USERNAME")
IMAP_PASS    = os.environ.get("REITZ_GMAIL_APP_PASSWORD")
IMAP_FOLDER  = os.environ.get("IMAP_FOLDER", "INBOX")
GMAIL_LABEL  = os.environ.get("GMAIL_LABEL")  # optional

# ====== Parsers & classifier (adjust paths if needed)
from src.classify import classify_file
from src.parsers.turnover import parse_turnover_summary
from src.parsers.trading_account import parse_trading_account
from src.parsers.scripts import parse_scripts

REPORT_MAP = {
    "turnover_summary": parse_turnover_summary,   # INV249
    "trading_account":  parse_trading_account,    # STK261
    "dispensary_scripts": parse_scripts,          # PHM080
}
COVERAGE_COL = {
    "turnover_summary": "inv249_turnover",
    "trading_account":  "stk261_trading",
    "dispensary_scripts": "phm080_scripts",
}

def _pretty_rtype(rt: Optional[str]) -> str:
    return {
        "turnover_summary": "turnover",
        "trading_account": "trading",
        "dispensary_scripts": "dispensary",
    }.get(rt or "", rt or "unknown")

# ====== SQL (historical mode: fill NULLs only)
UPSERT_DAILY_SALES_HIST = """
INSERT INTO pharma.fact_daily_sales AS f (
  pharmacy_id, business_date,
  turnover, sales_cash, sales_account, sales_cod, type_r_sales,
  transaction_count, avg_basket,
  purchases, cost_of_sales, closing_stock,
  dispensary_turnover, scripts_qty, avg_script_value
) VALUES (
  %(pharmacy_id)s, %(business_date)s,
  %(turnover)s, %(sales_cash)s, %(sales_account)s, %(sales_cod)s, %(type_r_sales)s,
  %(transaction_count)s, %(avg_basket)s,
  %(purchases)s, %(cost_of_sales)s, %(closing_stock)s,
  %(dispensary_turnover)s, %(scripts_qty)s, %(avg_script_value)s
)
ON CONFLICT (pharmacy_id, business_date) DO UPDATE
SET turnover            = COALESCE(f.turnover,            EXCLUDED.turnover),
    sales_cash          = COALESCE(f.sales_cash,          EXCLUDED.sales_cash),
    sales_account       = COALESCE(f.sales_account,       EXCLUDED.sales_account),
    sales_cod           = COALESCE(f.sales_cod,           EXCLUDED.sales_cod),
    type_r_sales        = COALESCE(f.type_r_sales,        EXCLUDED.type_r_sales),
    transaction_count   = COALESCE(f.transaction_count,   EXCLUDED.transaction_count),
    avg_basket          = COALESCE(f.avg_basket,          EXCLUDED.avg_basket),
    purchases           = COALESCE(f.purchases,           EXCLUDED.purchases),
    cost_of_sales       = COALESCE(f.cost_of_sales,       EXCLUDED.cost_of_sales),
    closing_stock       = COALESCE(f.closing_stock,       EXCLUDED.closing_stock),
    dispensary_turnover = COALESCE(f.dispensary_turnover, EXCLUDED.dispensary_turnover),
    scripts_qty         = COALESCE(f.scripts_qty,         EXCLUDED.scripts_qty),
    avg_script_value    = COALESCE(f.avg_script_value,    EXCLUDED.avg_script_value),
    last_updated_at     = now();
"""

INSERT_RECEIPT = """
INSERT INTO pharma.report_receipts
  (pharmacy_id, business_date, report_type, filename, sha256, byte_size, received_at, processed_at)
VALUES
  (%(pharmacy_id)s, %(business_date)s, %(report_type)s, %(filename)s, %(sha256)s, %(byte_size)s, %(received_at)s, now())
ON CONFLICT (pharmacy_id, business_date, report_type, sha256) DO NOTHING;
"""

UPSERT_COVERAGE = """
INSERT INTO pharma.report_coverage
  (pharmacy_id, business_date, inv249_turnover, stk261_trading, phm080_scripts, stk260_gp, last_updated)
VALUES
  (%(pharmacy_id)s, %(business_date)s,
   (%(report_type)s='turnover_summary'),
   (%(report_type)s='trading_account'),
   (%(report_type)s='dispensary_scripts'),
   FALSE, now())
ON CONFLICT (pharmacy_id, business_date) DO UPDATE
SET inv249_turnover = pharma.report_coverage.inv249_turnover OR EXCLUDED.inv249_turnover,
    stk261_trading  = pharma.report_coverage.stk261_trading  OR EXCLUDED.stk261_trading,
    phm080_scripts  = pharma.report_coverage.phm080_scripts  OR EXCLUDED.phm080_scripts,
    last_updated    = now();
"""

def coverage_has(cur, pharmacy_id: int, bdate: str, report_type: str) -> bool:
    col = COVERAGE_COL[report_type]
    cur.execute(f"""
      SELECT {col}
      FROM pharma.report_coverage
      WHERE pharmacy_id = %s AND business_date = %s
    """, (pharmacy_id, bdate))
    row = cur.fetchone()
    return bool(row and row[col])

def receipt_sha_seen(cur, sha256: str) -> bool:
    cur.execute("SELECT 1 FROM pharma.report_receipts WHERE sha256 = %s LIMIT 1", (sha256,))
    return cur.fetchone() is not None

# ====== Email models & helpers
@dataclass
class AttachmentRec:
    uid: int
    received_at: datetime  # UTC
    filename: str
    data: bytes
    sha256: str

def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def to_iso(d: date) -> str:
    return d.isoformat()

def parse_args():
    ap = argparse.ArgumentParser(description="Historical backfill for Turnover/Trading/Scripts.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--days-back", type=int, help="Look back N days from today (inclusive)")
    g.add_argument("--since", type=str, help="Start date YYYY-MM-DD (inclusive)")
    ap.add_argument("--until", type=str, help="End date YYYY-MM-DD (inclusive, defaults today)", default=None)
    ap.add_argument("--label", type=str, default=os.environ.get("GMAIL_LABEL"),
                    help="Gmail label to filter (optional).")
    ap.add_argument("--folder", type=str, default=os.environ.get("IMAP_FOLDER", "INBOX"),
                    help="IMAP folder to search (default INBOX).")
    ap.add_argument("--max-messages", type=int, default=2000, help="Safety cap on messages to inspect.")
    ap.add_argument("--force", action="store_true",
                    help="Do NOT skip days already covered; still upsert (fills only NULLs).")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()

def build_query(label: Optional[str], since_d: date, until_d: date) -> str:
    # Gmail's 'before:' is exclusive → use until + 1 day
    after = since_d.isoformat()
    before = (until_d + timedelta(days=1)).isoformat()
    parts = ["has:attachment", "filename:pdf", f"after:{after}", f"before:{before}"]
    if label:
        parts.insert(0, f'label:"{label}"')
    # You can optionally narrow by sender:
    # parts.append('from:postmaster@reitzphy.co.za')
    return " ".join(parts)

def fetch_attachments_range(folder: str, label: Optional[str], since_d: date, until_d: date,
                            max_messages: int, verbose: bool) -> List[AttachmentRec]:
    """
    Robust Gmail fetch:
      - Search by label (optional) + has:attachment + filename:pdf (+ coarse newer_than)
      - Then filter by INTERNALDATE between since..until (UTC)
      - Fallback without label if primary search finds nothing
    """
    # precise window (UTC)
    cutoff_start = datetime.combine(since_d, datetime.min.time()).replace(tzinfo=timezone.utc)
    cutoff_end   = datetime.combine(until_d,   datetime.max.time()).replace(tzinfo=timezone.utc)

    def build_raw(label_val: Optional[str]) -> str:
        terms = ["has:attachment", "filename:pdf"]
        # coarse recency limiter so Gmail doesn’t scan entire mailbox
        span_days = (until_d - since_d).days + 1
        # add a small buffer
        terms.append(f"newer_than:{min(max(span_days + 3, 2), 365)}d")
        if label_val:
            terms.insert(0, f'label:"{label_val}"')
        # you can narrow by sender if helpful:
        # terms.append('from:postmaster@reitzphy.co.za')
        return " ".join(terms)

    out: List[AttachmentRec] = []

    with IMAPClient("imap.gmail.com", ssl=True) as server:
        server.login(IMAP_USER, IMAP_PASS)
        server.select_folder(folder)

        raw1 = build_raw(label)
        uids = server.search(["X-GM-RAW", raw1])
        uids.sort(reverse=True)
        if verbose:
            print(f"[hist] primary X-GM-RAW matched {len(uids)} UIDs (folder={folder}, label={label!r})")
            print(f"[hist] raw query: {raw1}")

        if max_messages:
            uids = uids[:max_messages]

        if uids:
            meta = server.fetch(uids, ["INTERNALDATE"])
            candidates = [u for u in uids
                          if cutoff_start <= meta[u][b"INTERNALDATE"].astimezone(timezone.utc) <= cutoff_end]
        else:
            candidates = []

        if verbose:
            print(f"[hist] candidates in window {since_d}..{until_d}: {len(candidates)}")

        # Fallback without label if nothing found
        if not candidates and label:
            raw2 = build_raw(None)
            uids2 = server.search(["X-GM-RAW", raw2])
            uids2.sort(reverse=True)
            if verbose:
                print(f"[hist] fallback X-GM-RAW matched {len(uids2)} UIDs (no label)")
                print(f"[hist] fallback raw: {raw2}")
            if max_messages:
                uids2 = uids2[:max_messages]
            meta2 = server.fetch(uids2, ["INTERNALDATE"])
            candidates = [u for u in uids2
                          if cutoff_start <= meta2[u][b"INTERNALDATE"].astimezone(timezone.utc) <= cutoff_end]
            meta = meta2  # for use below
            uids = uids2
            if verbose:
                print(f"[hist] fallback candidates in window: {len(candidates)}")

        if not candidates:
            return out

        # Fetch messages in one batch and pull PDF attachments
        fetch_map = server.fetch(candidates, ["RFC822"])
        for uid in candidates:
            msg_bytes = fetch_map[uid][b"RFC822"]
            msg = message_from_bytes(msg_bytes)
            received = (meta[uid][b"INTERNALDATE"]).astimezone(timezone.utc)
            for part in msg.walk():
                cd = part.get_content_disposition()
                fn = part.get_filename() or ""
                if cd == "attachment" and fn.lower().endswith(".pdf"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        out.append(AttachmentRec(uid, received, fn, payload, sha256_bytes(payload)))
    return out

def classify_and_parse_bytes(filename: str, data: bytes) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data); tmp.flush()
        path = tmp.name
    c = classify_file(path)
    if not c.report_type: return {"status": "skipped_unclassified"}
    if c.report_type not in REPORT_MAP:  # ignore GP for 2a
        return {"status": "skipped_non_daily"}
    parser = REPORT_MAP[c.report_type]
    rec = parser(path)
    rec["status"] = "parsed"
    rec["report_type"] = c.report_type
    return rec

def bdate(rec: Dict[str, Any]) -> Optional[str]:
    return rec.get("business_date") or rec.get("date_from") or rec.get("date_to")

def upsert_daily_hist(cur, rec: Dict[str, Any]):
    params = {
        "pharmacy_id": rec.get("pharmacy_id"),
        "business_date": bdate(rec),
        "turnover": rec.get("turnover"),
        "sales_cash": rec.get("sales_cash"),
        "sales_account": rec.get("sales_account"),
        "sales_cod": rec.get("sales_cod"),
        "type_r_sales": rec.get("type_r_sales"),
        "transaction_count": rec.get("transaction_count"),
        "avg_basket": rec.get("avg_basket"),
        "purchases": rec.get("purchases"),
        "cost_of_sales": rec.get("cost_of_sales"),
        "closing_stock": rec.get("closing_stock"),
        "dispensary_turnover": rec.get("dispensary_turnover"),
        "scripts_qty": rec.get("scripts_qty"),
        "avg_script_value": rec.get("avg_script_value"),
    }
    cur.execute(UPSERT_DAILY_SALES_HIST, params)

def insert_receipt_and_coverage(cur, att: AttachmentRec, rec: Dict[str, Any]):
    params = {
        "pharmacy_id": rec["pharmacy_id"],
        "business_date": bdate(rec),
        "report_type": rec["report_type"],
        "filename": att.filename,
        "sha256": att.sha256,
        "byte_size": len(att.data),
        "received_at": att.received_at,
    }
    cur.execute(INSERT_RECEIPT, params)
    cur.execute(UPSERT_COVERAGE, params)

def print_coverage(cur, since_d: date, until_d: date):
    cur.execute("""
      SELECT pharmacy_id, business_date, inv249_turnover, stk261_trading, phm080_scripts
      FROM pharma.report_coverage
      WHERE business_date BETWEEN %s AND %s
      ORDER BY business_date, pharmacy_id
    """, (since_d, until_d))
    rows = cur.fetchall()
    if not rows:
        print("[hist] coverage: no rows in the window yet.")
        return
    print("\n[hist] Coverage logbook:")
    print("pharmacy_id | date       | INV249 | STK261 | PHM080 | missing")
    for r in rows:
        miss = []
        if not r["inv249_turnover"]: miss.append("INV249")
        if not r["stk261_trading"]:  miss.append("STK261")
        if not r["phm080_scripts"]:  miss.append("PHM080")
        print(f"{r['pharmacy_id']:>11} | {r['business_date']} | "
              f"{'Y' if r['inv249_turnover'] else ' ' :^6}|"
              f"{'Y' if r['stk261_trading']  else ' ' :^7}|"
              f"{'Y' if r['phm080_scripts']  else ' ' :^7}| "
              f"{','.join(miss) if miss else '-'}")

def main():
    if not (DSN and IMAP_USER and IMAP_PASS):
        raise SystemExit("Missing DATABASE_URL or Gmail IMAP creds in env.")

    args = parse_args()
    if args.days_back:
        until_d = date.today() if not args.until else date.fromisoformat(args.until)
        since_d = until_d - timedelta(days=args.days_back-1)
    else:
        since_d = date.fromisoformat(args.since)
        until_d = date.today() if not args.until else date.fromisoformat(args.until)

    t0 = time.time()
    print(f"[hist] scanning folder={args.folder} label={args.label!r} range={since_d}..{until_d}")
    atts = fetch_attachments_range(args.folder, args.label, since_d, until_d, args.max_messages, args.verbose)
    print(f"[hist] attachments found: {len(atts)}")

    if not atts:
        return

    # Connect once; keep a single transaction for the whole batch
    dsn = DSN if "connect_timeout=" in DSN else (DSN + ("&" if "?" in DSN else "?") + "connect_timeout=10")
    with connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = 0;")
        cur.execute("SET LOCAL synchronous_commit = off;")

        parsed = kept = skipped_sha = skipped_covered = 0
        total = len(atts)

        for idx, att in enumerate(atts, start=1):
            # default status
            status = "skipped"
            reason = None

            # 1) quick dedupe by sha before parsing
            if receipt_sha_seen(cur, att.sha256):
                skipped_sha += 1
                reason = "duplicate"
                print(f"[hist] processed {idx}/{total} - {status} ({reason})", flush=True)
                continue

            # 2) classify + parse; only 3 daily report types
            rec = classify_and_parse_bytes(att.filename, att.data)
            if rec.get("status") != "parsed":
                reason = rec.get("status", "unparsed")
                print(f"[hist] processed {idx}/{total} - {status} ({reason})", flush=True)
                continue

            rtype = rec["report_type"]
            pid   = rec.get("pharmacy_id")
            bdt   = bdate(rec)
            if not (pid and bdt):
                reason = "missing pharmacy/date"
                print(f"[hist] processed {idx}/{total} - {status} ({reason})", flush=True)
                continue

            parsed += 1
            pretty = _pretty_rtype(rtype)

            # 3) skip if already covered for this report/day (unless --force)
            if not args.force and coverage_has(cur, pid, bdt, rtype):
                insert_receipt_and_coverage(cur, att, rec)  # still record in logbook
                skipped_covered += 1
                status = "skipped"
                reason = f"already covered ({pretty})"
                print(f"[hist] processed {idx}/{total} - {status} ({reason})", flush=True)
                continue

            # 4) historical upsert (fill NULLs only), then receipt+coverage
            upsert_daily_hist(cur, rec)
            insert_receipt_and_coverage(cur, att, rec)
            kept += 1
            status = pretty
            print(f"[hist] processed {idx}/{total} - {status}", flush=True)

        conn.commit()

    print(f"[hist] Done in {time.time()-t0:.2f}s | parsed={parsed} kept={kept} skipped_sha={skipped_sha} skipped_covered={skipped_covered}")

    # Show coverage snapshot
    with connect(dsn, row_factory=dict_row) as conn:
        print_coverage(conn.cursor(), since_d, until_d)

if __name__ == "__main__":
    main()
