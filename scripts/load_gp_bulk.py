#!/usr/bin/env python
import os, sys, io, json, time, argparse
from typing import List, Tuple, Iterable, Dict, Any, Optional
from psycopg import connect
from psycopg.rows import dict_row
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=False)

def parse_args():
    ap = argparse.ArgumentParser(
        description="Bulk load GP (stock activity) from parsed JSONL via staging+merge."
    )
    ap.add_argument("jsonl", nargs="+", help="parsed_reports.jsonl (or '-' for stdin)")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"),
                    help="Postgres DSN; overrides DATABASE_URL if provided")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--chunk", type=int, default=10000,
                    help="Flush to DB every N staged rows (default: 10000)")
    ap.add_argument("--replace-day", action="store_true",
                    help="Faster: delete existing fact rows for staged days, then insert")
    return ap.parse_args()

def as_date(rec: Dict[str, Any]) -> Optional[str]:
    return rec.get("business_date") or rec.get("date_from") or rec.get("date_to")

def rows_from_record(rec: Dict[str, Any]) -> Iterable[Tuple]:
    """Yield typed rows for staging table from one GP record."""
    pid = rec.get("pharmacy_id")
    bdt = as_date(rec)
    if not (pid and bdt):
        return
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
        yield (
            pid, bdt,
            dept_code, product_code, description,
            qty_sold, sales_val, cost_of_sales, gp_value, gp_pct, on_hand
        )

def load_json_sources(paths: List[str]) -> Iterable[Dict[str, Any]]:
    for p in paths:
        f = sys.stdin if p == "-" else open(p, "r", encoding="utf-8")
        with f:
            for i, line in enumerate(f, 1):
                if not line.strip(): 
                    continue
                try:
                    rec = json.loads(line)
                except Exception as e:
                    print(f"[WARN] Bad JSON in {p}:{i}: {e}", file=sys.stderr)
                    continue
                if rec.get("status") == "parsed" and rec.get("report_type") == "gross_profit":
                    yield rec

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

# Dedup products so each product_code appears once in the statement
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

UPSERT_FACT = """
INSERT INTO pharma.fact_stock_activity AS s (
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
LEFT JOIN pharma.departments d ON d.department_code = sg.department_code
ON CONFLICT (pharmacy_id, business_date, product_id) DO UPDATE
SET department_id   = COALESCE(EXCLUDED.department_id, s.department_id),
    qty_sold        = EXCLUDED.qty_sold,
    sales_val       = EXCLUDED.sales_val,
    cost_of_sales   = EXCLUDED.cost_of_sales,
    gp_value        = EXCLUDED.gp_value,
    gp_pct          = EXCLUDED.gp_pct,
    on_hand         = EXCLUDED.on_hand,
    last_updated_at = now();
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

def to_csv_rows(batch: List[Tuple]) -> io.StringIO:
    """Serialize rows to CSV text for psycopg COPY. Empty string -> NULL by COPY setting."""
    buf = io.StringIO()
    for r in batch:
        row = []
        for v in r:
            if v is None:
                row.append("")
            else:
                s = str(v)
                if '"' in s or ',' in s or '\n' in s:
                    s = '"' + s.replace('"', '""') + '"'
                row.append(s)
        buf.write(",".join(row) + "\n")
    buf.seek(0)
    return buf

def main():
    args = parse_args()
    if not args.dsn:
        raise SystemExit("DATABASE_URL not set; pass --dsn or set it in .env")

    # add connect timeout if missing
    dsn = args.dsn if "connect_timeout=" in args.dsn else (
        args.dsn + ("&" if "?" in args.dsn else "?") + "connect_timeout=10"
    )

    t0 = time.time()
    staged_total = 0

    print("[gp-bulk] connecting to DB…")
    with connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        cur = conn.cursor()
        # remove statement timeout for big merges; keep within txn scope
        cur.execute("SET LOCAL statement_timeout = 0;")
        cur.execute(STAGE_SQL)

        batch: List[Tuple] = []
        for rec in load_json_sources(args.jsonl):
            for row in rows_from_record(rec):
                batch.append(row)
                if len(batch) >= args.chunk:
                    if args.verbose:
                        print(f"[gp-bulk] COPY chunk {len(batch)} …")
                    with cur.copy(COPY_IN) as cp:
                        cp.write(to_csv_rows(batch).read())
                    staged_total += len(batch)
                    batch.clear()

        if batch:
            if args.verbose:
                print(f"[gp-bulk] COPY final chunk {len(batch)} …")
            with cur.copy(COPY_IN) as cp:
                cp.write(to_csv_rows(batch).read())
            staged_total += len(batch)

        if args.verbose:
            print(f"[gp-bulk] staged rows: {staged_total}")

        if staged_total == 0:
            print("[gp-bulk] No GP rows found in input. Nothing to do.")
            conn.rollback()
            return

        if args.verbose: print("[gp-bulk] upserting departments …")
        cur.execute(UPSERT_DEPTS)

        if args.verbose: print("[gp-bulk] upserting products …")
        cur.execute(UPSERT_PRODUCTS)

        # Speed up commit on cloud DBs; safe because we don't depend on immediate WAL flush to replicas
        cur.execute("SET LOCAL synchronous_commit = off;")

        if args.replace_day:
            if args.verbose: print("[gp-bulk] replace-day: deleting existing fact rows …")
            cur.execute(REPLACE_FACT_DELETE)
            if args.verbose: print("[gp-bulk] replace-day: inserting fact rows …")
            cur.execute(REPLACE_FACT_INSERT)
        else:
            if args.verbose: print("[gp-bulk] upserting fact_stock_activity …")
            cur.execute(UPSERT_FACT)

        conn.commit()

    print(f"[gp-bulk] Done in {time.time()-t0:.2f}s; staged_rows={staged_total}")

if __name__ == "__main__":
    main()
