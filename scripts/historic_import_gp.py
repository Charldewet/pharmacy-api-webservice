#!/usr/bin/env python
from __future__ import annotations
import os, sys, io, time, json, hashlib, tempfile, argparse
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

# ====== Classifier & GP parser
from src.classify import classify_file
from src.parsers.gp_report import parse_gp_report

# ====== SQL
INSERT_RECEIPT = """
INSERT INTO pharma.report_receipts
  (pharmacy_id, business_date, report_type, filename, sha256, byte_size, received_at, processed_at)
VALUES
  (%(pharmacy_id)s, %(business_date)s, 'gross_profit', %(filename)s, %(sha256)s, %(byte_size)s, %(received_at)s, now())
ON CONFLICT (pharmacy_id, business_date, report_type, sha256) DO NOTHING;
"""

UPSERT_COVERAGE_GP = """
INSERT INTO pharma.report_coverage
  (pharmacy_id, business_date, inv249_turnover, stk261_trading, phm080_scripts, stk260_gp, last_updated)
VALUES
  (%(pharmacy_id)s, %(business_date)s, FALSE, FALSE, FALSE, TRUE, now())
ON CONFLICT (pharmacy_id, business_date) DO UPDATE
SET stk260_gp    = TRUE,
    last_updated = now();
"""

def coverage_has_gp(cur, pid: int, bdate: str) -> bool:
    cur.execute("""
      SELECT stk260_gp FROM pharma.report_coverage
      WHERE pharmacy_id = %s AND business_date = %s
    """, (pid, bdate))
    row = cur.fetchone()
    return bool(row and row["stk260_gp"])

def receipt_sha_seen(cur, sha256: str) -> bool:
    cur.execute("SELECT 1 FROM pharma.report_receipts WHERE sha256 = %s LIMIT 1", (sha256,))
    return cur.fetchone() is not None

# ====== TEMP stage + merges
STAGE_SQL = """
CREATE TEMP TABLE stage_gp (
  pharmacy_id     integer,
  business_date   date,
  department_code text,
  product_code    text,
  description     text,
  qty_sold        numeric(18,3),
  sales_val       numeric(18,2),
  cost_of_sales   numeric(18,2),
  gp_value        numeric(18,2),
  gp_pct          numeric(9,2),
  on_hand         numeric(18,3)
) ON COMMIT DROP;
"""

COPY_IN = """
COPY stage_gp (
  pharmacy_id,business_date,department_code,product_code,description,
  qty_sold,sales_val,cost_of_sales,gp_value,gp_pct,on_hand
) FROM STDIN WITH (FORMAT CSV, NULL '')
"""

UPSERT_DEPTS = """
INSERT INTO pharma.departments (department_code)
SELECT DISTINCT department_code
FROM stage_gp
WHERE department_code IS NOT NULL
ON CONFLICT (department_code) DO NOTHING;
"""

UPSERT_PRODUCTS = """
WITH src AS (
  SELECT
    sg.product_code,
    MAX(sg.description) FILTER (WHERE sg.description IS NOT NULL) AS description,
    MAX(d.department_id) AS department_id
  FROM stage_gp sg
  LEFT JOIN pharma.departments d ON d.department_code = sg.department_code
  WHERE sg.product_code IS NOT NULL
  GROUP BY sg.product_code
)
INSERT INTO pharma.products (product_code, description, department_id)
SELECT product_code, description, department_id
FROM src
ON CONFLICT (product_code) DO UPDATE
SET description   = COALESCE(EXCLUDED.description, pharma.products.description),
    department_id = COALESCE(EXCLUDED.department_id, pharma.products.department_id);
"""

REPLACE_FACT_DELETE = """
DELETE FROM pharma.fact_stock_activity s
USING (
  SELECT DISTINCT pharmacy_id, business_date FROM stage_gp
) d
WHERE s.pharmacy_id = d.pharmacy_id
  AND s.business_date = d.business_date;
"""

REPLACE_FACT_INSERT = """
INSERT INTO pharma.fact_stock_activity (
  pharmacy_id, business_date, product_id, department_id,
  qty_sold, sales_val, cost_of_sales, gp_value, gp_pct, on_hand
)
SELECT
  sg.pharmacy_id,
  sg.business_date,
  p.product_id,
  -- choose the department with the largest sales for that product/day
  (ARRAY_AGG(d.department_id ORDER BY COALESCE(sg.sales_val,0) DESC NULLS LAST))[1] AS department_id,
  SUM(COALESCE(sg.qty_sold,0))                                    AS qty_sold,
  SUM(COALESCE(sg.sales_val,0))                                   AS sales_val,
  SUM(COALESCE(sg.cost_of_sales,0))                               AS cost_of_sales,
  SUM(COALESCE(sg.gp_value,0))                                    AS gp_value,
  CASE WHEN SUM(COALESCE(sg.sales_val,0)) <> 0
       THEN ROUND(SUM(COALESCE(sg.gp_value,0)) / SUM(COALESCE(sg.sales_val,0)) * 100, 2)
       ELSE NULL
  END                                                             AS gp_pct,
  MAX(sg.on_hand)                                                 AS on_hand
FROM stage_gp sg
JOIN pharma.products p ON p.product_code = sg.product_code
LEFT JOIN pharma.departments d ON d.department_code = sg.department_code
GROUP BY sg.pharmacy_id, sg.business_date, p.product_id;
"""

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

def bdate(rec: Dict[str, Any]) -> Optional[str]:
    return rec.get("business_date") or rec.get("date_from") or rec.get("date_to")

def classify_and_parse_bytes(filename: str, data: bytes) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data); tmp.flush()
        path = tmp.name
    c = classify_file(path)
    if c.report_type != "gross_profit":
        return {"status": "skipped_non_gp"}
    rec = parse_gp_report(path)
    rec["status"] = "parsed"
    rec["report_type"] = "gross_profit"
    return rec

# ====== Fetch PDFs in a date window (same style as 2a)
def fetch_attachments_range(folder: str, label: Optional[str], since_d: date, until_d: date,
                            max_messages: int, verbose: bool) -> List[AttachmentRec]:
    """
    Robust Gmail fetch:
      - Search by label (optional) + has:attachment + filename:pdf (+ coarse newer_than)
      - Then filter by INTERNALDATE between since..until (UTC)
      - Fallback without label if primary finds nothing
    """
    cutoff_start = datetime.combine(since_d, datetime.min.time()).replace(tzinfo=timezone.utc)
    cutoff_end   = datetime.combine(until_d,   datetime.max.time()).replace(tzinfo=timezone.utc)

    def build_raw(label_val: Optional[str]) -> str:
        terms = ["has:attachment", "filename:pdf"]
        span_days = (until_d - since_d).days + 1
        terms.append(f"newer_than:{min(max(span_days + 3, 2), 365)}d")
        if label_val:
            terms.insert(0, f'label:"{label_val}"')
        return " ".join(terms)

    out: List[AttachmentRec] = []

    with IMAPClient("imap.gmail.com", ssl=True) as server:
        server.login(IMAP_USER, IMAP_PASS)
        server.select_folder(folder)

        raw1 = build_raw(label)
        uids = server.search(["X-GM-RAW", raw1])
        uids.sort(reverse=True)
        if verbose:
            print(f"[gp-hist] primary X-GM-RAW matched {len(uids)} UIDs (folder={folder}, label={label!r})")
            print(f"[gp-hist] raw query: {raw1}")

        if max_messages:
            uids = uids[:max_messages]

        if uids:
            meta = server.fetch(uids, ["INTERNALDATE"])
            candidates = [u for u in uids
                          if cutoff_start <= meta[u][b"INTERNALDATE"].astimezone(timezone.utc) <= cutoff_end]
        else:
            candidates = []

        if verbose:
            print(f"[gp-hist] candidates in window {since_d}..{until_d}: {len(candidates)}")

        # Fallback without label if nothing found
        if not candidates and label:
            raw2 = build_raw(None)
            uids2 = server.search(["X-GM-RAW", raw2])
            uids2.sort(reverse=True)
            if verbose:
                print(f"[gp-hist] fallback X-GM-RAW matched {len(uids2)} UIDs (no label)")
                print(f"[gp-hist] fallback raw: {raw2}")
            if max_messages:
                uids2 = uids2[:max_messages]
            meta2 = server.fetch(uids2, ["INTERNALDATE"])
            candidates = [u for u in uids2
                          if cutoff_start <= meta2[u][b"INTERNALDATE"].astimezone(timezone.utc) <= cutoff_end]
            meta = meta2
            uids = uids2
            if verbose:
                print(f"[gp-hist] fallback candidates in window: {len(candidates)}")

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

# ====== CSV helper for COPY
def to_csv_rows(rows: List[Tuple]) -> io.StringIO:
    buf = io.StringIO()
    for r in rows:
        out = []
        for v in r:
            if v is None: out.append("")
            else:
                s = str(v)
                if '"' in s or ',' in s or '\n' in s:
                    s = '"' + s.replace('"', '""') + '"'
                out.append(s)
        buf.write(",".join(out) + "\n")
    buf.seek(0); return buf

# Build stage rows from parsed GP record
def rows_from_rec(rec: Dict[str, Any]) -> Iterable[Tuple]:
    pid = rec.get("pharmacy_id")
    bdt = bdate(rec)
    for line in rec.get("lines") or []:
        dept_code = line.get("department_code") or line.get("dept_code")
        product_code = line.get("product_code")
        if not product_code:  # skip malformed lines
            continue
        description   = line.get("description")
        qty_sold      = line.get("qty_sold", line.get("sales_qty"))
        sales_val     = line.get("sales_val", line.get("sales_value"))
        cost_of_sales = line.get("cost_of_sales")
        gp_value      = line.get("gp_value", line.get("gross_profit"))
        gp_pct        = line.get("gp_pct")
        on_hand       = line.get("on_hand")
        yield (pid, bdt, dept_code, product_code, description,
               qty_sold, sales_val, cost_of_sales, gp_value, gp_pct, on_hand)

# ====== CLI args
def parse_args():
    ap = argparse.ArgumentParser(description="Historical backfill for GP (gross_profit) reports only.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--days-back", type=int, help="Look back N days from today (inclusive)")
    g.add_argument("--since", type=str, help="Start date YYYY-MM-DD (inclusive)")
    ap.add_argument("--until", type=str, help="End date YYYY-MM-DD (inclusive); default today", default=None)
    ap.add_argument("--label", type=str, default=os.environ.get("GMAIL_LABEL"),
                    help="Gmail label filter (optional).")
    ap.add_argument("--folder", type=str, default=os.environ.get("IMAP_FOLDER", "INBOX"),
                    help="IMAP folder to search (default INBOX).")
    ap.add_argument("--max-messages", type=int, default=2000, help="Safety cap on messages to inspect.")
    ap.add_argument("--force", action="store_true",
                    help="Process even if stk260_gp already covered for that day (will replace-the-day).")
    ap.add_argument("--verbose", action="store_true")
    return ap.parse_args()

# ====== Main
def main():
    if not (DSN and IMAP_USER and IMAP_PASS):
        raise SystemExit("Missing DATABASE_URL or Gmail IMAP creds in env.")

    args = parse_args()
    if args.days_back:
        until_d = date.today() if not args.until else date.fromisoformat(args.until)
        since_d = until_d - timedelta(days=args.days_back - 1)
    else:
        since_d = date.fromisoformat(args.since)
        until_d = date.today() if not args.until else date.fromisoformat(args.until)

    print(f"[gp-hist] scanning folder={args.folder} label={args.label!r} range={since_d}..{until_d}")
    atts = fetch_attachments_range(args.folder, args.label, since_d, until_d, args.max_messages, args.verbose)
    print(f"[gp-hist] attachments found: {len(atts)}")
    if not atts:
        return

    # Connect and process in one transaction
    dsn = DSN if "connect_timeout=" in DSN else (DSN + ("&" if "?" in DSN else "?") + "connect_timeout=10")
    with connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = 0;")
        cur.execute("SET LOCAL synchronous_commit = off;")

        kept = skipped_sha = skipped_covered = parsed = 0
        selected: List[Tuple[AttachmentRec, Dict[str, Any]]] = []
        total = len(atts)

        for idx, att in enumerate(atts, start=1):
            status = "skipped"
            reason = None

            # 1) dedupe by sha (before parse)
            if receipt_sha_seen(cur, att.sha256):
                skipped_sha += 1
                reason = "duplicate"
                print(f"[gp-hist] processed {idx}/{total} - {status} ({reason})", flush=True)
                continue

            # 2) classify + parse GP only
            rec = classify_and_parse_bytes(att.filename, att.data)
            if rec.get("status") != "parsed":
                reason = rec.get("status", "unparsed")
                print(f"[gp-hist] processed {idx}/{total} - {status} ({reason})", flush=True)
                continue

            pid = rec.get("pharmacy_id")
            bdt = bdate(rec)
            if not (pid and bdt):
                reason = "missing pharmacy/date"
                print(f"[gp-hist] processed {idx}/{total} - {status} ({reason})", flush=True)
                continue

            parsed += 1

            # 3) skip if already covered GP for this day unless --force
            if not args.force and coverage_has_gp(cur, pid, bdt):
                # still write receipt + coverage (no-op coverage)
                params = {
                    "pharmacy_id": pid,
                    "business_date": bdt,
                    "filename": att.filename,
                    "sha256": att.sha256,
                    "byte_size": len(att.data),
                    "received_at": att.received_at,
                }
                cur.execute(INSERT_RECEIPT, params)
                cur.execute(UPSERT_COVERAGE_GP, params)
                skipped_covered += 1
                print(f"[gp-hist] processed {idx}/{total} - skipped (already covered)", flush=True)
                continue

            selected.append((att, rec))
            kept += 1
            print(f"[gp-hist] processed {idx}/{total} - gross_profit", flush=True)

        # Stage + replace-day for all selected items at once
        if selected:
            rows: List[Tuple] = []
            for _att, rec in selected:
                rows.extend(list(rows_from_rec(rec)))

            cur.execute(STAGE_SQL)
            with cur.copy(COPY_IN) as cp:
                cp.write(to_csv_rows(rows).read())

            if args.verbose: print(f"[gp-hist] staged rows: {len(rows)}")
            cur.execute(UPSERT_DEPTS)
            cur.execute(UPSERT_PRODUCTS)
            cur.execute(REPLACE_FACT_DELETE)
            cur.execute(REPLACE_FACT_INSERT)

            # receipts + coverage for the selected ones
            for att, rec in selected:
                params = {
                    "pharmacy_id": rec["pharmacy_id"],
                    "business_date": bdate(rec),
                    "filename": att.filename,
                    "sha256": att.sha256,
                    "byte_size": len(att.data),
                    "received_at": att.received_at,
                }
                cur.execute(INSERT_RECEIPT, params)
                cur.execute(UPSERT_COVERAGE_GP, params)

        conn.commit()

    print(f"[gp-hist] Done | parsed={parsed} kept={kept} skipped_sha={skipped_sha} skipped_covered={skipped_covered}")

if __name__ == "__main__":
    # optional: unbuffered prints & a quick env sanity line
    try:
        print(f"[gp-hist] DSN={bool(DSN)} USER={bool(IMAP_USER)} PASS={bool(IMAP_PASS)} "
              f"FOLDER={IMAP_FOLDER!r} LABEL={GMAIL_LABEL!r}", flush=True)
        main()
    except SystemExit as e:
        if e.code not in (0, None):
            print(str(e), flush=True)
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise
