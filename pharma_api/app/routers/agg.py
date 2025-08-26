from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import date
from psycopg import Connection
from ..db import get_conn
from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies/{pid}", tags=["aggregates"], dependencies=[Depends(require_api_key)])

@router.get("/mtd")
def get_mtd(
    pid: int,
    month: str,
    through: date | None = Query(None, description="Optional cutoff date (inclusive). Must be in the same month)."),
):
    """
    If `through` is provided, compute MTD up to that date (inclusive) directly
    from pharma.fact_daily_sales. Otherwise, return the pre-aggregated row from
    pharma.agg_sales_mtd for the given month.

    Supports TLC GROUP (pharmacy_id=100) by aggregating across all pharmacies.
    """
    # Parse month parameter (YYYY-MM format)
    try:
        year, month_num = month.split('-')
        year = int(year)
        month_num = int(month_num)
        if month_num < 1 or month_num > 12:
            raise ValueError("Month must be between 1 and 12")
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format")
    
    month_start = date(year, month_num, 1)
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            if through is not None:
                if through.year != year or through.month != month_num:
                    raise HTTPException(status_code=400, detail="`through` date must be in the same month as specified in `month` parameter.")
                
                # Aggregate from fact table (pid==100 → all pharmacies)
                cur.execute(
                    (
                        """
                        SELECT
                          %s::date                           AS month_start,
                          COALESCE(SUM(d.turnover), 0)       AS turnover,
                          COALESCE(SUM(d.purchases), 0)      AS purchases,
                          COALESCE(SUM(d.cost_of_sales), 0)  AS cost_of_sales,
                          COALESCE(SUM(d.type_r_sales), 0)   AS type_r_sales,
                          COALESCE(SUM(d.dispensary_turnover), 0) AS dispensary_turnover,
                          COALESCE(SUM(d.scripts_qty), 0)    AS scripts_qty,
                          COALESCE(SUM(d.transaction_count), 0) AS transaction_count,
                          COALESCE(SUM(d.turnover - COALESCE(d.type_r_sales,0)
                                       - COALESCE(d.dispensary_turnover,0)), 0) AS frontshop_turnover,
                          COALESCE(SUM(d.turnover - d.cost_of_sales
                                       - COALESCE(d.type_r_sales,0)), 0)        AS gp_value
                        FROM pharma.fact_daily_sales d
                        WHERE d.business_date >= %s
                          AND d.business_date <= %s
                        """
                    ) if pid == 100 else (
                        """
                        SELECT
                          %s::date                           AS month_start,
                          COALESCE(SUM(d.turnover), 0)       AS turnover,
                          COALESCE(SUM(d.purchases), 0)      AS purchases,
                          COALESCE(SUM(d.cost_of_sales), 0)  AS cost_of_sales,
                          COALESCE(SUM(d.type_r_sales), 0)   AS type_r_sales,
                          COALESCE(SUM(d.dispensary_turnover), 0) AS dispensary_turnover,
                          COALESCE(SUM(d.scripts_qty), 0)    AS scripts_qty,
                          COALESCE(SUM(d.transaction_count), 0) AS transaction_count,
                          COALESCE(SUM(d.turnover - COALESCE(d.type_r_sales,0)
                                       - COALESCE(d.dispensary_turnover,0)), 0) AS frontshop_turnover,
                          COALESCE(SUM(d.turnover - d.cost_of_sales
                                       - COALESCE(d.type_r_sales,0)), 0)        AS gp_value
                        FROM pharma.fact_daily_sales d
                        WHERE d.pharmacy_id = %s
                          AND d.business_date >= %s
                          AND d.business_date <= %s
                        """
                    ),
                    (month_start, month_start, through) if pid == 100 else (month_start, pid, month_start, through),
                )
                row = cur.fetchone()
                # If no data in that range, return {}
                return {} if row is None or all(v is None for v in row.values()) else row

            # Fallback to pre-aggregated MTD (as of your last refresh)
            if pid == 100:
                # Sum all pharmacies for that month
                cur.execute(
                    """
                    SELECT
                      %s::date                           AS month_start,
                      COALESCE(SUM(turnover), 0)         AS turnover,
                      COALESCE(SUM(purchases), 0)        AS purchases,
                      COALESCE(SUM(cost_of_sales), 0)    AS cost_of_sales,
                      COALESCE(SUM(type_r_sales), 0)     AS type_r_sales,
                      COALESCE(SUM(dispensary_turnover), 0) AS dispensary_turnover,
                      COALESCE(SUM(scripts_qty), 0)      AS scripts_qty,
                      COALESCE(SUM(transaction_count), 0) AS transaction_count,
                      COALESCE(SUM(frontshop_turnover), 0) AS frontshop_turnover,
                      COALESCE(SUM(gp_value), 0)         AS gp_value
                    FROM pharma.agg_sales_mtd
                    WHERE month_start = %s
                    """,
                    (month_start, month_start),
                )
                row = cur.fetchone()
                return row or {}
            else:
                cur.execute(
                    """
                    SELECT *
                    FROM pharma.agg_sales_mtd
                    WHERE pharmacy_id = %s AND month_start = %s
                    """,
                    (pid, month_start),
                )
                row = cur.fetchone()
                return row or {}

@router.get("/ytd")
def get_ytd(
    pid: int,
    year: int,
    through: date | None = Query(None, description="Optional cutoff date (inclusive). Must be in the same year)."),
):
    """
    If `through` is provided, compute YTD up to that date (inclusive) directly
    from pharma.fact_daily_sales. Otherwise, return the pre-aggregated row from
    pharma.agg_sales_ytd for the given year.

    Supports TLC GROUP (pharmacy_id=100) by aggregating across all pharmacies.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            if through is not None:
                if through.year != year:
                    raise HTTPException(status_code=400, detail="`through` year must match `year`.")
                cur.execute(
                    (
                        """
                        WITH yr AS (
                          SELECT make_date(%(year)s, 1, 1)::date AS year_start
                        )
                        SELECT
                          (SELECT year_start FROM yr)                           AS year_start,
                          COALESCE(SUM(d.turnover), 0)                          AS turnover,
                          COALESCE(SUM(d.purchases), 0)                         AS purchases,
                          COALESCE(SUM(d.cost_of_sales), 0)                     AS cost_of_sales,
                          COALESCE(SUM(d.type_r_sales), 0)                      AS type_r_sales,
                          COALESCE(SUM(d.dispensary_turnover), 0)               AS dispensary_turnover,
                          COALESCE(SUM(d.scripts_qty), 0)                       AS scripts_qty,
                          COALESCE(SUM(d.transaction_count), 0)                 AS transaction_count,
                          COALESCE(SUM(d.turnover - COALESCE(d.type_r_sales,0)
                                       - COALESCE(d.dispensary_turnover,0)), 0) AS frontshop_turnover,
                          COALESCE(SUM(d.turnover - d.cost_of_sales
                                       - COALESCE(d.type_r_sales,0)), 0)        AS gp_value
                        FROM pharma.fact_daily_sales d, yr
                        WHERE d.business_date >= (SELECT year_start FROM yr)
                          AND d.business_date <= %(through)s
                        """
                    ) if pid == 100 else (
                        """
                        WITH yr AS (
                          SELECT make_date(%(year)s, 1, 1)::date AS year_start
                        )
                        SELECT
                          (SELECT year_start FROM yr)                           AS year_start,
                          COALESCE(SUM(d.turnover), 0)                          AS turnover,
                          COALESCE(SUM(d.purchases), 0)                         AS purchases,
                          COALESCE(SUM(d.cost_of_sales), 0)                     AS cost_of_sales,
                          COALESCE(SUM(d.type_r_sales), 0)                      AS type_r_sales,
                          COALESCE(SUM(d.dispensary_turnover), 0)               AS dispensary_turnover,
                          COALESCE(SUM(d.scripts_qty), 0)                       AS scripts_qty,
                          COALESCE(SUM(d.transaction_count), 0)                 AS transaction_count,
                          COALESCE(SUM(d.turnover - COALESCE(d.type_r_sales,0)
                                       - COALESCE(d.dispensary_turnover,0)), 0) AS frontshop_turnover,
                          COALESCE(SUM(d.turnover - d.cost_of_sales
                                       - COALESCE(d.type_r_sales,0)), 0)        AS gp_value
                        FROM pharma.fact_daily_sales d, yr
                        WHERE d.pharmacy_id = %(pharmacy_id)s
                          AND d.business_date >= (SELECT year_start FROM yr)
                          AND d.business_date <= %(through)s
                        """
                    ),
                    {"pharmacy_id": pid, "year": year, "through": through},
                )
                row = cur.fetchone()
                # If no data in that range, return {}
                return {} if row is None or all(v is None for v in row.values()) else row

            # Fallback to pre-aggregated YTD (as of your last refresh)
            if pid == 100:
                cur.execute(
                    """
                    SELECT
                      make_date(%s,1,1)::date              AS year_start,
                      COALESCE(SUM(turnover), 0)           AS turnover,
                      COALESCE(SUM(purchases), 0)          AS purchases,
                      COALESCE(SUM(cost_of_sales), 0)      AS cost_of_sales,
                      COALESCE(SUM(type_r_sales), 0)       AS type_r_sales,
                      COALESCE(SUM(dispensary_turnover), 0) AS dispensary_turnover,
                      COALESCE(SUM(scripts_qty), 0)        AS scripts_qty,
                      COALESCE(SUM(transaction_count), 0)  AS transaction_count,
                      COALESCE(SUM(frontshop_turnover), 0) AS frontshop_turnover,
                      COALESCE(SUM(gp_value), 0)           AS gp_value,
                      MAX(last_refreshed)                  AS last_refreshed
                    FROM pharma.agg_sales_ytd
                    WHERE year_start = make_date(%s,1,1)::date
                    """,
                    (year, year),
                )
                row = cur.fetchone()
                return row or {}
            else:
                cur.execute(
                    """
                    SELECT
                      year_start, turnover, purchases, cost_of_sales, type_r_sales,
                      dispensary_turnover, scripts_qty, transaction_count,
                      frontshop_turnover, gp_value, last_refreshed
                    FROM pharma.agg_sales_ytd
                    WHERE pharmacy_id = %s AND year_start = make_date(%s,1,1)::date
                    """,
                    (pid, year),
                )
                row = cur.fetchone()
                return row or {}
