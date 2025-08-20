import argparse
import json
import sys
from pathlib import Path
from datetime import date
import os
# Ensure project root is on sys.path when running as a script
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.db.loader import (
    upsert_daily_sales,
    insert_receipt_and_coverage,
    upsert_stock_activity_line,
    refresh_product_usage,
    refresh_mtd,
    refresh_ytd,
)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", nargs="+", help="One or more parsed_reports.jsonl files")
    p.add_argument("--mode", choices=["live","historical"], default="live")
    p.add_argument("--refresh-aggregates", action="store_true", help="Refresh MTD/YTD after load")
    return p.parse_args()


def handle_record(rec, mode):
    rt = rec.get("report_type")
    pharmacy_id = rec.get("pharmacy_id")
    biz_date = rec.get("date_from") or rec.get("business_date") or rec.get("date_to")
    if not (rt and pharmacy_id and biz_date):
        return

    # 1) Upsert daily sales depending on type
    if rt in ("turnover_summary","trading_account","dispensary_scripts"):
        upsert_daily_sales(rec, mode=mode)

    # 2) GP report lines
    if rt == "gross_profit":
        lines = rec.get("lines") or []
        for line in lines:
            prod_id, _ = upsert_stock_activity_line(pharmacy_id, biz_date, line)
            # refresh usage for touched product (optional, can batch)
            refresh_product_usage(pharmacy_id, prod_id, biz_date)

    # 3) receipts/coverage (optional here; if you do it earlier during Gmail fetch, skip this)
    # requires filename/hash/size to be present in rec
    # if rec.get("sha256"):
    #     insert_receipt_and_coverage({
    #         "pharmacy_id": pharmacy_id,
    #         "business_date": biz_date,
    #         "report_type": rt,
    #         "filename": rec.get("filename"),
    #         "sha256": rec.get("sha256"),
    #         "byte_size": rec.get("byte_size"),
    #     })


def main():
    args = parse_args()
    for path in args.jsonl:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("status") == "parsed":
                    handle_record(rec, args.mode)

    if args.refresh_aggregates:
        # naive: refresh for the past month/year for both pharmacies (customize as needed)
        for pid in (1, 2):
            today = date.today()
            month_start = today.replace(day=1).isoformat()
            year_start = today.replace(month=1, day=1).isoformat()
            refresh_mtd(pid, month_start)
            refresh_ytd(pid, year_start)


if __name__ == "__main__":
    sys.exit(main()) 