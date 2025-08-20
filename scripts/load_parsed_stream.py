#!/usr/bin/env python
import os, sys, json, argparse, time
from typing import Dict, Any, Iterable
from psycopg import connect
from psycopg.rows import dict_row
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=False)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl", nargs="+", help="parsed_reports.jsonl or '-' for stdin")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"),
                    help="Postgres DSN; overrides DATABASE_URL if provided")
    ap.add_argument("--skip-gp", action="store_true",
                    help="Skip loading GP (stock activity) lines")
    ap.add_argument("--limit-gp", type=int, default=None,
                    help="Only load first N GP lines (helps testing speed)")
    ap.add_argument("--verbose", action="store_true", help="Print progress")
    return ap.parse_args()

UPSERT_DAILY_SALES_LIVE = """
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
SET turnover            = COALESCE(EXCLUDED.turnover,            f.turnover),
    sales_cash          = COALESCE(EXCLUDED.sales_cash,          f.sales_cash),
    sales_account       = COALESCE(EXCLUDED.sales_account,       f.sales_account),
    sales_cod           = COALESCE(EXCLUDED.sales_cod,           f.sales_cod),
    type_r_sales        = COALESCE(EXCLUDED.type_r_sales,        f.type_r_sales),
    transaction_count   = COALESCE(EXCLUDED.transaction_count,   f.transaction_count),
    avg_basket          = COALESCE(EXCLUDED.avg_basket,          f.avg_basket),
    purchases           = COALESCE(EXCLUDED.purchases,           f.purchases),
    cost_of_sales       = COALESCE(EXCLUDED.cost_of_sales,       f.cost_of_sales),
    closing_stock       = COALESCE(EXCLUDED.closing_stock,       f.closing_stock),
    dispensary_turnover = COALESCE(EXCLUDED.dispensary_turnover, f.dispensary_turnover),
    scripts_qty         = COALESCE(EXCLUDED.scripts_qty,         f.scripts_qty),
    avg_script_value    = COALESCE(EXCLUDED.avg_script_value,    f.avg_script_value),
    last_updated_at     = now();
"""

ENSURE_DEPT = """
WITH ins AS (
  INSERT INTO pharma.departments (department_code)
  VALUES (%(department_code)s)
  ON CONFLICT (department_code) DO NOTHING
  RETURNING department_id
)
SELECT COALESCE(
  (SELECT department_id FROM ins),
  (SELECT department_id FROM pharma.departments WHERE department_code = %(department_code)s)
) AS department_id;
"""

ENSURE_PRODUCT = """
WITH ins AS (
  INSERT INTO pharma.products (product_code, description, department_id)
  VALUES (%(product_code)s, %(description)s, %(department_id)s)
  ON CONFLICT (product_code) DO UPDATE
    SET description = EXCLUDED.description,
        department_id = COALESCE(EXCLUDED.department_id, pharma.products.department_id)
  RETURNING product_id
)
SELECT COALESCE(
  (SELECT product_id FROM ins),
  (SELECT product_id FROM pharma.products WHERE product_code = %(product_code)s)
) AS product_id;
"""

UPSERT_STOCK_ACTIVITY = """
INSERT INTO pharma.fact_stock_activity AS s (
  pharmacy_id, business_date, product_id, department_id,
  qty_sold, sales_val, cost_of_sales, gp_value, gp_pct, on_hand
) VALUES (
  %(pharmacy_id)s, %(business_date)s, %(product_id)s, %(department_id)s,
  %(qty_sold)s, %(sales_val)s, %(cost_of_sales)s, %(gp_value)s, %(gp_pct)s, %(on_hand)s
)
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

def as_date(rec: Dict[str, Any]) -> str | None:
    return rec.get("business_date") or rec.get("date_from") or rec.get("date_to")

def params_daily(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "pharmacy_id": rec.get("pharmacy_id"),
        "business_date": as_date(rec),
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

def norm_line(line: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "dept_code": line.get("department_code") or line.get("dept_code"),
        "product_code": line.get("product_code"),
        "description": line.get("description"),
        "qty_sold": line.get("qty_sold") if line.get("qty_sold") is not None else line.get("sales_qty"),
        "sales_val": line.get("sales_val") if line.get("sales_val") is not None else line.get("sales_value"),
        "cost_of_sales": line.get("cost_of_sales"),
        "gp_value": line.get("gp_value") if line.get("gp_value") is not None else line.get("gross_profit"),
        "gp_pct": line.get("gp_pct"),
        "on_hand": line.get("on_hand"),
    }

def load_json_sources(paths: list[str]) -> Iterable[Dict[str, Any]]:
    for p in paths:
        f = sys.stdin if p == "-" else open(p, "r", encoding="utf-8")
        with f:
            for i, line in enumerate(f, 1):
                if not line.strip(): continue
                try:
                    rec = json.loads(line)
                except Exception as e:
                    print(f"[WARN] Bad JSON in {p}:{i}: {e}", file=sys.stderr)
                    continue
                if rec.get("status") == "parsed":
                    yield rec

def main():
    args = parse_args()
    if not args.dsn:
        raise SystemExit("DATABASE_URL not set; pass --dsn or set it in .env")

    # add connect timeout (seconds) if not present
    dsn = args.dsn if "connect_timeout" in args.dsn else (
        args.dsn + ("&" if "?" in args.dsn else "?") + "connect_timeout=10"
    )

    t0 = time.time()
    print("[loader] connecting to DB…")
    with connect(dsn, row_factory=dict_row, autocommit=False) as conn:
        cur = conn.cursor()
        print("[loader] connected. reading JSON…")

        daily_ct = gp_files = gp_lines = 0
        for rec in load_json_sources(args.jsonl):
            rt = rec.get("report_type")
            pid = rec.get("pharmacy_id")
            bdt = as_date(rec)
            if not (rt and pid and bdt):
                print("[SKIP] Missing report_type/pharmacy_id/date", file=sys.stderr)
                continue

            if rt in ("turnover_summary", "trading_account", "dispensary_scripts"):
                cur.execute(UPSERT_DAILY_SALES_LIVE, params_daily(rec))
                daily_ct += 1
                if args.verbose and daily_ct % 10 == 0:
                    print(f"[loader] daily upserts: {daily_ct}")

            elif rt == "gross_profit":
                if args.skip_gp:
                    continue
                gp_files += 1
                for idx, raw in enumerate(rec.get("lines") or [], start=1):
                    if args.limit_gp and gp_lines >= args.limit_gp:
                        break
                    line = norm_line(raw)
                    if not line.get("product_code"):
                        continue
                    dept_id = None
                    if line.get("dept_code"):
                        cur.execute(ENSURE_DEPT, {"department_code": line["dept_code"]})
                        dept_id = cur.fetchone()["department_id"]
                    cur.execute(ENSURE_PRODUCT, {
                        "product_code": line["product_code"],
                        "description": line.get("description"),
                        "department_id": dept_id
                    })
                    prod_id = cur.fetchone()["product_id"]
                    cur.execute(UPSERT_STOCK_ACTIVITY, {
                        "pharmacy_id": pid,
                        "business_date": bdt,
                        "product_id": prod_id,
                        "department_id": dept_id,
                        "qty_sold": line.get("qty_sold"),
                        "sales_val": line.get("sales_val"),
                        "cost_of_sales": line.get("cost_of_sales"),
                        "gp_value": line.get("gp_value"),
                        "gp_pct": line.get("gp_pct"),
                        "on_hand": line.get("on_hand"),
                    })
                    gp_lines += 1
                    if args.verbose and gp_lines % 100 == 0:
                        print(f"[loader] gp lines upserted: {gp_lines}")

        conn.commit()
    print(f"[loader] Done in {time.time()-t0:.2f}s  daily_rows={daily_ct}  gp_files={gp_files}  gp_lines={gp_lines}")

if __name__ == "__main__":
    main()
