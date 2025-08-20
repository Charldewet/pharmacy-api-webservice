from fastapi import APIRouter, Depends, Query
from typing import List
from ..db import get_conn
from ..schemas import CoverageRow
from ..auth import require_api_key

router = APIRouter(prefix="/pharmacies/{pid}/logbook", tags=["logbook"], dependencies=[Depends(require_api_key)])

@router.get("", response_model=List[CoverageRow])
def logbook(pid: int, from_: str = Query(..., alias="from"), to: str = Query(..., alias="to"),
            missingOnly: bool = True):
    where = [
        "pharmacy_id = %s",
        "business_date BETWEEN %s AND %s",
        "(inv249_turnover OR stk261_trading OR phm080_scripts OR stk260_gp)"
    ]
    params = [pid, from_, to]
    if missingOnly:
        where.append("NOT (inv249_turnover AND stk261_trading AND phm080_scripts AND stk260_gp)")
    sql = f"""
    SELECT business_date, pharmacy_id, inv249_turnover, stk261_trading, phm080_scripts, stk260_gp, last_updated
    FROM pharma.report_coverage
    WHERE {' AND '.join(where)}
    ORDER BY business_date DESC
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return cur.fetchall()
