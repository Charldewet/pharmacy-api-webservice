from typing import Dict, Any, Tuple
from .conn import get_cursor
from . import sql


def upsert_daily_sales(payload: Dict[str, Any], mode: str = "live") -> None:
    """
    payload contains keys from any of the 3 daily sources (turnover/trading/scripts).
    Must include: pharmacy_id, date_from/date_to (use date_from for business_date).
    """
    biz_date = payload.get("date_from") or payload.get("business_date") or payload.get("date_to")
    params = {
        "pharmacy_id": payload.get("pharmacy_id"),
        "business_date": biz_date,
        "turnover": payload.get("turnover"),
        "sales_cash": payload.get("sales_cash"),
        "sales_account": payload.get("sales_account"),
        "sales_cod": payload.get("sales_cod"),
        "type_r_sales": payload.get("type_r_sales"),
        "transaction_count": payload.get("transaction_count"),
        "avg_basket": payload.get("avg_basket"),
        "purchases": payload.get("purchases"),
        "cost_of_sales": payload.get("cost_of_sales"),
        "closing_stock": payload.get("closing_stock"),
        "dispensary_turnover": payload.get("dispensary_turnover"),
        "scripts_qty": payload.get("scripts_qty"),
        "avg_script_value": payload.get("avg_script_value"),
    }
    stmt = sql.UPSERT_DAILY_SALES_LIVE if mode == "live" else sql.UPSERT_DAILY_SALES_HISTORICAL
    with get_cursor() as cur:
        cur.execute(stmt, params)


def insert_receipt_and_coverage(meta: Dict[str, Any]) -> None:
    params = {
        "pharmacy_id": meta["pharmacy_id"],
        "business_date": meta["business_date"],
        "report_type": meta["report_type"],
        "filename": meta.get("filename"),
        "sha256": meta["sha256"],
        "byte_size": meta.get("byte_size"),
    }
    with get_cursor() as cur:
        cur.execute(sql.INSERT_RECEIPT, params)
        cur.execute(sql.UPSERT_COVERAGE, params)


def ensure_department(dept_code: str) -> int:
    with get_cursor() as cur:
        cur.execute(sql.ENSURE_DEPT, {"department_code": dept_code})
        row = cur.fetchone()
        return row["department_id"]


def upsert_department(code: str, name: str | None) -> int:
    with get_cursor() as cur:
        cur.execute(sql.UPSERT_DEPARTMENT, {"department_code": code, "department_name": name})
        row = cur.fetchone()
        return row["department_id"]


def ensure_product(product_code: str, description: str | None, department_id: int | None) -> int:
    with get_cursor() as cur:
        cur.execute(sql.ENSURE_PRODUCT, {
            "product_code": product_code,
            "description": description,
            "department_id": department_id
        })
        row = cur.fetchone()
        return row["product_id"]


def upsert_stock_activity_line(pharmacy_id: int, business_date: str, line: Dict[str, Any]) -> Tuple[int, int | None]:
    dept_id = ensure_department(line["dept_code"]) if line.get("dept_code") else None
    prod_id = ensure_product(line["product_code"], line.get("description"), dept_id)
    params = {
        "pharmacy_id": pharmacy_id,
        "business_date": business_date,
        "product_id": prod_id,
        "department_id": dept_id,
        "qty_sold": line.get("qty_sold") or line.get("sales_qty"),
        "sales_val": line.get("sales_val") or line.get("sales_value"),
        "cost_of_sales": line.get("cost_of_sales"),
        "gp_value": line.get("gp_value") or line.get("gross_profit"),
        "gp_pct": line.get("gp_pct"),
        "on_hand": line.get("on_hand"),
    }
    with get_cursor() as cur:
        cur.execute(sql.UPSERT_STOCK_ACTIVITY, params)
    return prod_id, dept_id


def refresh_product_usage(pharmacy_id: int, product_id: int, asof: str) -> None:
    with get_cursor() as cur:
        cur.execute(sql.REFRESH_PRODUCT_USAGE, {
            "pharmacy_id": pharmacy_id,
            "product_id": product_id,
            "asof": asof
        })


def refresh_mtd(pharmacy_id: int, month_start: str) -> None:
    with get_cursor() as cur:
        cur.execute(sql.REFRESH_MTD, {
            "pharmacy_id": pharmacy_id,
            "month_start": month_start
        })


def refresh_ytd(pharmacy_id: int, year_start: str) -> None:
    with get_cursor() as cur:
        cur.execute(sql.REFRESH_YTD, {
            "pharmacy_id": pharmacy_id,
            "year_start": year_start
        }) 