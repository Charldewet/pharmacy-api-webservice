#!/usr/bin/env python
import os, io, json, time, hashlib, tempfile
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional, Iterable
from datetime import datetime, timedelta, timezone, date as _date
from pathlib import Path
import sys

from dotenv import load_dotenv, find_dotenv
from imapclient import IMAPClient
from email import message_from_bytes
from psycopg import connect
from psycopg.rows import dict_row

# Ensure project root for src.* imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---- Load env
load_dotenv(find_dotenv(), override=False)

DSN = os.environ.get("DATABASE_URL")
IMAP_USER = os.environ.get("REITZ_GMAIL_USERNAME")
IMAP_PASS = os.environ.get("REITZ_GMAIL_APP_PASSWORD")
IMAP_FOLDER = os.environ.get("IMAP_FOLDER", "INBOX")
GMAIL_LABEL = os.environ.get("GMAIL_LABEL")
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "5"))
MAX_MESSAGES = int(os.environ.get("MAX_MESSAGES", "10"))  # safety cap

# ---- Import your existing parsers & classifier
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

# =========================
# Gmail (IMAP) helpers
# =========================
def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

@dataclass
class AttachmentRec:
    message_uid: int
    received_at: datetime  # UTC
    filename: str
    data: bytes
    sha256: str

def fetch_recent_attachments(label: Optional[str], lookback_hours: int, max_messages: int) -> List[AttachmentRec]:
    """
    Search for PDF attachments received in the last `lookback_hours`.
    Tries (folder, label) in this order:
      (IMAP_FOLDER, label) → (IMAP_FOLDER, no label) → ("[Gmail]/All Mail", label) → ("[Gmail]/All Mail", no label)
    Accepts PDFs even if content-disposition is 'inline' (some systems do that).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    def build_raw(label_val: Optional[str]) -> str:
        # coarse limiter; we filter precisely by INTERNALDATE afterwards
        terms = ["has:attachment", "filename:pdf", "newer_than:2d"]
        if label_val:
            terms.insert(0, f'label:"{label_val}"')
        return " ".join(terms)

    def is_pdf_part(part) -> bool:
        fn = (part.get_filename() or "").lower()
        ctype = (part.get_content_type() or "").lower()
        return fn.endswith(".pdf") or ctype in ("application/pdf", "application/x-pdf")

    out: List[AttachmentRec] = []
    folders_to_try = [IMAP_FOLDER]
    if IMAP_FOLDER != "[Gmail]/All Mail":
        folders_to_try.append("[Gmail]/All Mail")

    with IMAPClient("imap.gmail.com", ssl=True) as server:
        server.login(IMAP_USER, IMAP_PASS)

        for folder in folders_to_try:
            server.select_folder(folder)
            for label_try in ([label, None] if label else [None]):
                raw = build_raw(label_try)
                uids = server.search(["X-GM-RAW", raw])
                uids.sort(reverse=True)
                print(f"[live] search: folder={folder} label={label_try!r} matched={len(uids)}")

                if not uids:
                    continue

                meta = server.fetch(uids, ["INTERNALDATE"])
                candidates = [u for u in uids if meta[u][b"INTERNALDATE"].astimezone(timezone.utc) >= cutoff]
                print(f"[live] candidates in last {lookback_hours}h (UTC cutoff {cutoff.isoformat()}): {len(candidates)}")

                if max_messages:
                    candidates = candidates[:max_messages]

                if not candidates:
                    continue

                # Download raw messages
                fetch_map = server.fetch(candidates, ["BODY.PEEK[]"])
                found_here = 0
                for uid in candidates:
                    msg_bytes = fetch_map[uid].get(b"BODY[]") or fetch_map[uid].get(b"RFC822")
                    if not msg_bytes:
                        continue
                    msg = message_from_bytes(msg_bytes)
                    received = meta[uid][b"INTERNALDATE"].astimezone(timezone.utc)
                    for part in msg.walk():
                        cd = (part.get_content_disposition() or "").lower()  # 'attachment', 'inline', or ''
                        if is_pdf_part(part) and cd in ("attachment", "inline", ""):
                            payload = part.get_payload(decode=True)
                            fn = part.get_filename() or "attachment.pdf"
                            if payload:
                                out.append(AttachmentRec(uid, received, fn, payload, sha256_bytes(payload)))
                                found_here += 1

                print(f"[live] attachments pulled from folder={folder} label={label_try!r}: {found_here}")
                if found_here:
                    return out  # stop at first successful combination

    return out

# =========================
# Parse & group (latest per key)
# =========================
def classify_and_parse_bytes(filename: str, data: bytes) -> Dict[str, Any]:
    # Use temp file for parsers that expect a path; ensure cleanup
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data); tmp.flush()
        path = tmp.name
    try:
        c = classify_file(Path(path))
        if not c.report_type:
            return {"status": "skipped_unclassified", "path": path}
        parser = REPORT_MAP.get(c.report_type)
        if not parser:
            return {"status": "skipped_no_parser", "report_type": c.report_type, "path": path}
        rec = parser(Path(path))
        rec["status"] = "parsed"
        rec["report_type"] = c.report_type
        return rec
    finally:
        try: os.unlink(path)
        except Exception: pass

def biz_date(rec: Dict[str, Any]) -> Optional[str]:
    return rec.get("business_date") or rec.get("date_from") or rec.get("date_to")

Key = Tuple[int, str, str]  # (pharmacy_id, business_date, report_type)

def latest_per_key(atts: List[AttachmentRec]) -> Dict[Key, Tuple[AttachmentRec, Dict[str, Any]]]:
    """
    Parse all attachments, keep only the latest (by received_at) per (pharmacy_id, business_date, report_type).
    """
    chosen: Dict[Key, Tuple[AttachmentRec, Dict[str, Any]]] = {}
    for att in atts:
        rec = classify_and_parse_bytes(att.filename, att.data)
        if rec.get("status") != "parsed":
            continue
        pid = rec.get("pharmacy_id")
        bdt = biz_date(rec)
        rtype = rec.get("report_type")
        if not (pid and bdt and rtype):
            continue
        key: Key = (int(pid), str(bdt), str(rtype))
        cur = chosen.get(key)
        if (cur is None) or (att.received_at > cur[0].received_at):
            chosen[key] = (att, rec)
    return chosen

# =========================
# DB SQL
# =========================
UPSERT_DAILY_SALES_LIVE_MAX = """
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
SET
  -- Monotonic fields: never go backwards (treat NULL as 0)
  turnover            = GREATEST(COALESCE(f.turnover,0),            COALESCE(EXCLUDED.turnover,0)),
  sales_cash          = GREATEST(COALESCE(f.sales_cash,0),          COALESCE(EXCLUDED.sales_cash,0)),
  sales_account       = GREATEST(COALESCE(f.sales_account,0),       COALESCE(EXCLUDED.sales_account,0)),
  sales_cod           = GREATEST(COALESCE(f.sales_cod,0),           COALESCE(EXCLUDED.sales_cod,0)),
  type_r_sales        = GREATEST(COALESCE(f.type_r_sales,0),        COALESCE(EXCLUDED.type_r_sales,0)),
  transaction_count   = GREATEST(COALESCE(f.transaction_count,0),   COALESCE(EXCLUDED.transaction_count,0)),
  purchases           = GREATEST(COALESCE(f.purchases,0),           COALESCE(EXCLUDED.purchases,0)),
  cost_of_sales       = GREATEST(COALESCE(f.cost_of_sales,0),       COALESCE(EXCLUDED.cost_of_sales,0)),
  closing_stock       = GREATEST(COALESCE(f.closing_stock,0),       COALESCE(EXCLUDED.closing_stock,0)),
  dispensary_turnover = GREATEST(COALESCE(f.dispensary_turnover,0), COALESCE(EXCLUDED.dispensary_turnover,0)),
  scripts_qty         = GREATEST(COALESCE(f.scripts_qty,0),         COALESCE(EXCLUDED.scripts_qty,0)),
  -- Derived/ratio fields: use latest computed value
  avg_basket          = COALESCE(EXCLUDED.avg_basket, f.avg_basket),
  avg_script_value    = COALESCE(EXCLUDED.avg_script_value, f.avg_script_value),
  last_updated_at     = now();
"""

INSERT_RECEIPT = """
INSERT INTO pharma.report_receipts
(pharmacy_id, business_date, report_type, filename, sha256, byte_size, received_at, processed_at)
VALUES (%(pharmacy_id)s, %(business_date)s, %(report_type)s, %(filename)s, %(sha256)s, %(byte_size)s, %(received_at)s, now())
ON CONFLICT (pharmacy_id, business_date, report_type, sha256) DO NOTHING;
"""

UPSERT_COVERAGE = """
INSERT INTO pharma.report_coverage
(pharmacy_id, business_date, inv249_turnover, stk261_trading, phm080_scripts, stk260_gp, last_updated)
VALUES (
  %(pharmacy_id)s, %(business_date)s,
  (%(report_type)s='turnover_summary'),
  (%(report_type)s='trading_account'),
  (%(report_type)s='dispensary_scripts'),
  (%(report_type)s='gross_profit'),
  now()
)
ON CONFLICT (pharmacy_id, business_date) DO UPDATE
SET inv249_turnover = pharma.report_coverage.inv249_turnover OR EXCLUDED.inv249_turnover,
    stk261_trading  = pharma.report_coverage.stk261_trading  OR EXCLUDED.stk261_trading,
    phm080_scripts  = pharma.report_coverage.phm080_scripts  OR EXCLUDED.phm080_scripts,
    stk260_gp       = pharma.report_coverage.stk260_gp       OR EXCLUDED.stk260_gp,
    last_updated    = now();
"""

# ---- GP bulk staging (TEMP + replace-the-day)
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
  d.department_id,
  sg.qty_sold, sg.sales_val, sg.cost_of_sales, sg.gp_value, sg.gp_pct, sg.on_hand
FROM stage_gp sg
JOIN pharma.products p ON p.product_code = sg.product_code
LEFT JOIN pharma.departments d ON d.department_code = sg.department_code;
"""

# --- MTD / YTD aggregate upserts (idempotent) ------------------------------
UPSERT_AGG_MTD = """
INSERT INTO pharma.agg_sales_mtd AS m (
  pharmacy_id, month_start,
  turnover, purchases, cost_of_sales, type_r_sales,
  dispensary_turnover, scripts_qty, transaction_count,
  frontshop_turnover, gp_value, last_refreshed
)
SELECT
  d.pharmacy_id,
  date_trunc('month', %(month_start)s::date)::date AS month_start,
  SUM(d.turnover),
  SUM(d.purchases),
  SUM(d.cost_of_sales),
  SUM(d.type_r_sales),
  SUM(d.dispensary_turnover),
  SUM(d.scripts_qty),
  SUM(d.transaction_count),
  SUM( (d.turnover - COALESCE(d.type_r_sales,0) - COALESCE(d.dispensary_turnover,0)) ),
  SUM( d.turnover - d.cost_of_sales - COALESCE(d.type_r_sales,0) ),
  now()
FROM pharma.fact_daily_sales d
WHERE d.pharmacy_id = %(pharmacy_id)s
  AND d.business_date >= date_trunc('month', %(month_start)s::date)
  AND d.business_date <  (date_trunc('month', %(month_start)s::date) + INTERVAL '1 month')
GROUP BY d.pharmacy_id, date_trunc('month', %(month_start)s::date)
ON CONFLICT (pharmacy_id, month_start) DO UPDATE
SET turnover            = EXCLUDED.turnover,
    purchases           = EXCLUDED.purchases,
    cost_of_sales       = EXCLUDED.cost_of_sales,
    type_r_sales        = EXCLUDED.type_r_sales,
    dispensary_turnover = EXCLUDED.dispensary_turnover,
    scripts_qty         = EXCLUDED.scripts_qty,
    transaction_count   = EXCLUDED.transaction_count,
    frontshop_turnover  = EXCLUDED.frontshop_turnover,
    gp_value            = EXCLUDED.gp_value,
    last_refreshed      = now();
"""

UPSERT_AGG_YTD = """
INSERT INTO pharma.agg_sales_ytd AS y (
  pharmacy_id, year_start,
  turnover, purchases, cost_of_sales, type_r_sales,
  dispensary_turnover, scripts_qty, transaction_count,
  frontshop_turnover, gp_value, last_refreshed
)
SELECT
  d.pharmacy_id,
  make_date(date_part('year', %(year_start)s::date)::int, 1, 1) AS year_start,
  SUM(d.turnover),
  SUM(d.purchases),
  SUM(d.cost_of_sales),
  SUM(d.type_r_sales),
  SUM(d.dispensary_turnover),
  SUM(d.scripts_qty),
  SUM(d.transaction_count),
  SUM( (d.turnover - COALESCE(d.type_r_sales,0) - COALESCE(d.dispensary_turnover,0)) ),
  SUM( d.turnover - d.cost_of_sales - COALESCE(d.type_r_sales,0) ),
  now()
FROM pharma.fact_daily_sales d
WHERE d.pharmacy_id = %(pharmacy_id)s
  AND d.business_date >= make_date(date_part('year', %(year_start)s::date)::int, 1, 1)
  AND d.business_date <  make_date(date_part('year', %(year_start)s::date)::int + 1, 1, 1)
GROUP BY d.pharmacy_id, make_date(date_part('year', %(year_start)s::date)::int, 1, 1)
ON CONFLICT (pharmacy_id, year_start) DO UPDATE
SET turnover            = EXCLUDED.turnover,
    purchases           = EXCLUDED.purchases,
    cost_of_sales       = EXCLUDED.cost_of_sales,
    type_r_sales        = EXCLUDED.type_r_sales,
    dispensary_turnover = EXCLUDED.dispensary_turnover,
    scripts_qty         = EXCLUDED.scripts_qty,
    transaction_count   = EXCLUDED.transaction_count,
    frontshop_turnover  = EXCLUDED.frontshop_turnover,
    gp_value            = EXCLUDED.gp_value,
    last_refreshed      = now();
"""

def to_csv_rows(rows: List[Tuple]) -> io.StringIO:
    buf = io.StringIO()
    for r in rows:
        out = []
        for v in r:
            if v is None:
                out.append("")
            else:
                s = str(v)
                if '"' in s or ',' in s or '\n' in s:
                    s = '"' + s.replace('"', '""') + '"'
                out.append(s)
        buf.write(",".join(out) + "\n")
    buf.seek(0); return buf

# =========================
# Loaders
# =========================
def upsert_daily_max(cur, rec: Dict[str, Any]):
    params = {
        "pharmacy_id": rec.get("pharmacy_id"),
        "business_date": biz_date(rec),
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
    cur.execute(UPSERT_DAILY_SALES_LIVE_MAX, params)

def insert_receipt_and_coverage(cur, att: AttachmentRec, rec: Dict[str, Any]):
    params = {
        "pharmacy_id": rec["pharmacy_id"],
        "business_date": biz_date(rec),
        "report_type": rec["report_type"],
        "filename": att.filename,
        "sha256": att.sha256,
        "byte_size": len(att.data),
        "received_at": att.received_at,
    }
    cur.execute(INSERT_RECEIPT, params)
    cur.execute(UPSERT_COVERAGE, params)

def rows_from_rec(rec: Dict[str, Any]) -> Iterable[Tuple]:
    pid = rec.get("pharmacy_id")
    bdt = biz_date(rec)
    for line in rec.get("lines") or []:
        dept_code = line.get("department_code") or line.get("dept_code")
        product_code = line.get("product_code")
        if not product_code:
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

def load_gp_bulk_latest(conn, latest: Dict[Key, Tuple[AttachmentRec, Dict[str, Any]]], verbose: bool = True):
    """
    Stage ONLY the latest GP report per (pharmacy_id, business_date), replace the day,
    and record receipts + coverage entries for the GP reports.
    Returns: (gp_attachments, gp_rows)
    """
    # Keep only GP items
    gp_items: List[Tuple[AttachmentRec, Dict[str, Any]]] = [
        (att, rec) for (_k, (att, rec)) in latest.items() if rec.get("report_type") == "gross_profit"
    ]

    # Build stage rows
    rows: List[Tuple] = []
    for att, rec in gp_items:
        rows.extend(list(rows_from_rec(rec)))

    if not rows:
        if verbose: print("[live] no GP rows to load.")
        return 0, 0

    with conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout = 0;")
        cur.execute(STAGE_SQL)

        if verbose: print(f"[live] GP COPY rows: {len(rows)} …")
        with cur.copy(COPY_IN) as cp:
            cp.write(to_csv_rows(rows).read())

        if verbose: print("[live] upserting departments …")
        cur.execute(UPSERT_DEPTS)
        if verbose: print("[live] upserting products …")
        cur.execute(UPSERT_PRODUCTS)

        cur.execute("SET LOCAL synchronous_commit = off;")
        if verbose: print("[live] replace-day fact insert …")
        cur.execute(REPLACE_FACT_DELETE)
        cur.execute(REPLACE_FACT_INSERT)

        # Write logbook entries (receipt + coverage) for each GP attachment
        for att, rec in gp_items:
            insert_receipt_and_coverage(cur, att, rec)

    return len(gp_items), len(rows)

# =========================
# Orchestrator
# =========================
def _month_start_str(dstr: str) -> str:
    d = _date.fromisoformat(dstr)
    return f"{d.year:04d}-{d.month:02d}-01"

def _year_start_str(dstr: str) -> str:
    d = _date.fromisoformat(dstr)
    return f"{d.year:04d}-01-01"

def run_live_import(verbose: bool = True):
    print(f"[live] fetching attachments for last {LOOKBACK_HOURS}h … (folder={IMAP_FOLDER}, label={GMAIL_LABEL!r})")
    if not (DSN and IMAP_USER and IMAP_PASS):
        raise SystemExit("Missing DATABASE_URL or Gmail IMAP creds in env.")

    t0 = time.time()
    atts = fetch_recent_attachments(GMAIL_LABEL, LOOKBACK_HOURS, MAX_MESSAGES)
    if verbose:
        print(f"[live] attachments found: {len(atts)}")
    if not atts:
        print("[live] nothing to process.")
        return

    latest = latest_per_key(atts)
    if verbose:
        print(f"[live] unique latest keys: {len(latest)}")

    # Track which (pharmacy_id, date) were updated in fact_daily_sales
    touched_days: set[Tuple[int, str]] = set()

    # Connect once, single transaction for daily + GP
    dsn = DSN if "connect_timeout=" in DSN else (DSN + ("&" if "?" in DSN else "?") + "connect_timeout=10")
    with connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        cur = conn.cursor()
        cur.execute("SET LOCAL statement_timeout = 0;")
        cur.execute("SET LOCAL synchronous_commit = off;")

        # 1) Daily reports (turnover/trading/scripts) with monotonic max
        daily_count = 0
        for (_key, (att, rec)) in latest.items():
            if rec["report_type"] in ("turnover_summary","trading_account","dispensary_scripts"):
                upsert_daily_max(cur, rec)
                insert_receipt_and_coverage(cur, att, rec)
                pid = rec.get("pharmacy_id")
                bdt = biz_date(rec)
                if pid and bdt:
                    touched_days.add((int(pid), str(bdt)))
                daily_count += 1
        if verbose:
            print(f"[live] daily upserts: {daily_count}")

        # 2) GP bulk (latest only per day+pharmacy), replace-day
        gp_files, gp_rows = load_gp_bulk_latest(conn, latest, verbose=verbose)
        if verbose:
            print(f"[live] gp receipts: {gp_files} | gp rows loaded: {gp_rows}")

        conn.commit()

    # 3) Refresh MTD/YTD aggregates for touched months/years (separate short txn)
    if touched_days:
        months = {(pid, _month_start_str(bd)) for (pid, bd) in touched_days}
        years  = {(pid, _year_start_str(bd))  for (pid, bd) in touched_days}

        with connect(dsn, row_factory=dict_row, autocommit=False) as conn2:
            cur2 = conn2.cursor()
            cur2.execute("SET LOCAL statement_timeout = 10000;")
            cur2.execute("SET LOCAL synchronous_commit = off;")

            for pid, ms in sorted(months):
                cur2.execute(UPSERT_AGG_MTD, {"pharmacy_id": pid, "month_start": ms})
            for pid, ys in sorted(years):
                cur2.execute(UPSERT_AGG_YTD, {"pharmacy_id": pid, "year_start": ys})

            conn2.commit()
        if verbose:
            print(f"[live] aggregates refreshed: months={len(months)} years={len(years)}")
    else:
        if verbose:
            print("[live] aggregates refreshed: nothing to do (no daily rows touched).")

    print(f"[live] Done in {time.time()-t0:.2f}s")

if __name__ == "__main__":
    run_live_import(verbose=True)