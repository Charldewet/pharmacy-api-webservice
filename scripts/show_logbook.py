#!/usr/bin/env python
from __future__ import annotations
import os, sys, argparse, csv, json
from datetime import date, timedelta
from typing import Optional, List, Dict, Any

from psycopg import connect
from psycopg.rows import dict_row
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=False)

def parse_args():
    ap = argparse.ArgumentParser(
        description="Show report coverage (logbook) for days with at least one report present."
    )
    # date range
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--days-back", type=int, help="Look back N days from today (inclusive). Default 30.")
    g.add_argument("--since", type=str, help="Start date YYYY-MM-DD (inclusive).")
    ap.add_argument("--until", type=str, help="End date YYYY-MM-DD (inclusive). Defaults to today.")
    # filters / options
    ap.add_argument("--pharmacy-id", type=int, help="Filter by pharmacy_id.")
    ap.add_argument("--pharmacy-like", type=str, help="Filter pharmacy name ILIKE %%value%%.")
    ap.add_argument("--missing-only", action="store_true",
                    help="Only show days still missing at least one report.")
    ap.add_argument("--order-asc", action="store_true", help="Sort oldest first (default newest first).")
    # output
    ap.add_argument("--csv", type=str, help="Write results to CSV file (path).")
    ap.add_argument("--json", type=str, help="Write results to JSON file (path).")
    ap.add_argument("--dsn", type=str, default=os.environ.get("DATABASE_URL"),
                    help="Postgres DSN; uses DATABASE_URL if not provided.")
    return ap.parse_args()

def compute_range(days_back: Optional[int], since: Optional[str], until: Optional[str]) -> tuple[date, date]:
    if days_back:
        end = date.today() if not until else date.fromisoformat(until)
        start = end - timedelta(days=days_back - 1)
        return start, end
    if since:
        start = date.fromisoformat(since)
        end = date.today() if not until else date.fromisoformat(until)
        return start, end
    # default last 30 days
    end = date.today()
    start = end - timedelta(days=29)
    return start, end

def fetch_logbook(dsn: str, start: date, end: date,
                  pharmacy_id: Optional[int], pharmacy_like: Optional[str],
                  missing_only: bool, ascending: bool) -> List[Dict[str, Any]]:
    if not dsn:
        raise SystemExit("DATABASE_URL not set; pass --dsn or set it in .env")

    order = "ASC" if ascending else "DESC"
    where = [
        "rc.business_date BETWEEN %(start)s AND %(end)s",
        # show only rows where at least one report is present
        "(rc.inv249_turnover OR rc.stk261_trading OR rc.phm080_scripts OR rc.stk260_gp)"
    ]
    params = {"start": start, "end": end}

    if pharmacy_id is not None:
        where.append("rc.pharmacy_id = %(pid)s")
        params["pid"] = pharmacy_id
    if pharmacy_like:
        where.append("p.name ILIKE %(patt)s")
        params["patt"] = f"%{pharmacy_like}%"
    if missing_only:
        where.append("NOT (rc.inv249_turnover AND rc.stk261_trading AND rc.phm080_scripts AND rc.stk260_gp)")

    sql = f"""
    SELECT
      rc.business_date,
      rc.pharmacy_id,
      p.name AS pharmacy,
      rc.inv249_turnover  AS inv249,
      rc.stk261_trading   AS stk261,
      rc.phm080_scripts   AS phm080,
      rc.stk260_gp        AS stk260_gp
    FROM pharma.report_coverage rc
    JOIN pharma.pharmacies p USING (pharmacy_id)
    WHERE {' AND '.join(where)}
    ORDER BY rc.business_date {order}, rc.pharmacy_id
    """

    # ensure connect_timeout
    dsn2 = dsn if "connect_timeout=" in dsn else (dsn + ("&" if "?" in dsn else "?") + "connect_timeout=10")
    with connect(dsn2, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() or []

def yn(b: Optional[bool]) -> str:
    return "Y" if b else " "

def main():
    args = parse_args()
    start, end = compute_range(args.days_back, args.since, args.until)

    rows = fetch_logbook(
        args.dsn, start, end,
        args.pharmacy_id, args.pharmacy_like,
        args.missing_only, args.order_asc
    )

    # Nothing to show?
    if not rows:
        print("No rows found for the chosen filters.")
        return

    # Print human-friendly table
    print(f"Logbook: {start} .. {end}")
    print("date        | pharmacy_id | pharmacy                     | INV249 | STK261 | PHM080 | STK260_GP | missing")
    print("-"*106)
    out_rows = []
    for r in rows:
        missing = []
        if not r["inv249"]:   missing.append("INV249")
        if not r["stk261"]:   missing.append("STK261")
        if not r["phm080"]:   missing.append("PHM080")
        if not r["stk260_gp"]: missing.append("STK260_GP")
        miss_str = ",".join(missing) if missing else "-"
        print(f"{r['business_date']} | {r['pharmacy_id']:>11} | {r['pharmacy'][:27]:<27} |"
              f"   {yn(r['inv249'])}   |   {yn(r['stk261'])}   |   {yn(r['phm080'])}   |"
              f"    {yn(r['stk260_gp'])}     | {miss_str}")
        # keep for export
        out_rows.append({
            "business_date": str(r["business_date"]),
            "pharmacy_id": r["pharmacy_id"],
            "pharmacy": r["pharmacy"],
            "inv249": bool(r["inv249"]),
            "stk261": bool(r["stk261"]),
            "phm080": bool(r["phm080"]),
            "stk260_gp": bool(r["stk260_gp"]),
            "missing": missing or []
        })

    # Optional exports
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        print(f"\nWrote CSV: {args.csv}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out_rows, f, ensure_ascii=False, indent=2)
        print(f"Wrote JSON: {args.json}")

if __name__ == "__main__":
    main()
