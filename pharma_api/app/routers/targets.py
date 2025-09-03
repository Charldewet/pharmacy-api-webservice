from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime, date
from ..db import get_conn
from ..auth import get_current_user_id
import calendar

router = APIRouter(prefix="/api/targets", tags=["targets"])

class TargetValue(BaseModel):
    date: date = Field(..., description="Target date (YYYY-MM-DD)")
    value: float = Field(..., ge=0, description="Target value (must be >= 0)")

class SaveTargetsRequest(BaseModel):
    pharmacy_id: int = Field(..., description="Pharmacy ID")
    targets: List[TargetValue] = Field(..., description="List of target values")

class SaveTargetsResponse(BaseModel):
    success: bool
    message: str
    saved_count: int

class TargetResponse(BaseModel):
    date: date
    value: float

class LoadTargetsResponse(BaseModel):
    pharmacy_id: int
    month: str
    targets: List[TargetResponse]


def _validate_pharmacy_access(cur, user_id: int, pharmacy_id: int) -> None:
    """Validate user has access to the pharmacy"""
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM pharma.user_pharmacies
        WHERE user_id = %s AND pharmacy_id = %s
        """,
        (user_id, pharmacy_id),
    )
    result = cur.fetchone()
    if not result or result["cnt"] == 0:
        raise HTTPException(403, f"Access denied to pharmacy {pharmacy_id}")


@router.post("", response_model=SaveTargetsResponse)
async def save_targets(request: SaveTargetsRequest, user_id: int = Depends(get_current_user_id)):
    """
    Save target values for a pharmacy
    
    - **pharmacy_id**: The pharmacy ID to save targets for
    - **targets**: List of date/value pairs to save
    """
    if not request.targets:
        raise HTTPException(400, "At least one target value is required")
    
    with get_conn() as conn, conn.cursor() as cur:
        # Validate pharmacy access
        _validate_pharmacy_access(cur, user_id, request.pharmacy_id)
        
        # Upsert each target value
        saved_count = 0
        for target in request.targets:
            cur.execute(
                """
                INSERT INTO pharma.pharmacy_targets (pharmacy_id, target_date, target_value, updated_at)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (pharmacy_id, target_date) DO UPDATE SET
                    target_value = EXCLUDED.target_value,
                    updated_at = now()
                """,
                (request.pharmacy_id, target.date, target.value)
            )
            saved_count += 1
        
        conn.commit()
        
        return SaveTargetsResponse(
            success=True,
            message=f"Targets saved successfully for pharmacy {request.pharmacy_id}",
            saved_count=saved_count
        )


@router.get("", response_model=LoadTargetsResponse)
async def load_targets(
    pharmacy_id: int,
    month: str,
    user_id: int = Depends(get_current_user_id)
):
    """
    Load target values for a pharmacy and month
    
    - **pharmacy_id**: The pharmacy ID to load targets for
    - **month**: Month in YYYY-MM format (e.g., "2025-09")
    """
    # Validate month format
    try:
        year, month_num = month.split("-")
        year = int(year)
        month_num = int(month_num)
        if not (1 <= month_num <= 12):
            raise ValueError("Invalid month")
    except (ValueError, IndexError):
        raise HTTPException(400, "Month must be in YYYY-MM format")
    
    # Calculate date range for the month
    first_day = date(year, month_num, 1)
    last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])
    
    with get_conn() as conn, conn.cursor() as cur:
        # Validate pharmacy access
        _validate_pharmacy_access(cur, user_id, pharmacy_id)
        
        # Load targets for the month
        cur.execute(
            """
            SELECT target_date, target_value
            FROM pharma.pharmacy_targets
            WHERE pharmacy_id = %s
              AND target_date >= %s
              AND target_date <= %s
            ORDER BY target_date
            """,
            (pharmacy_id, first_day, last_day)
        )
        
        rows = cur.fetchall()
        targets = [
            TargetResponse(date=row["target_date"], value=float(row["target_value"]))
            for row in rows
        ]
        
        return LoadTargetsResponse(
            pharmacy_id=pharmacy_id,
            month=month,
            targets=targets
        )


@router.delete("")
async def delete_targets(
    pharmacy_id: int,
    target_date: Optional[date] = None,
    month: Optional[str] = None,
    user_id: int = Depends(get_current_user_id)
):
    """
    Delete target values
    
    - **pharmacy_id**: The pharmacy ID
    - **target_date**: Specific date to delete (optional)
    - **month**: Month in YYYY-MM format to delete all targets for that month (optional)
    
    Either target_date or month must be provided.
    """
    if not target_date and not month:
        raise HTTPException(400, "Either target_date or month must be provided")
    
    if target_date and month:
        raise HTTPException(400, "Cannot specify both target_date and month")
    
    with get_conn() as conn, conn.cursor() as cur:
        # Validate pharmacy access
        _validate_pharmacy_access(cur, user_id, pharmacy_id)
        
        if target_date:
            # Delete specific date
            cur.execute(
                """
                DELETE FROM pharma.pharmacy_targets
                WHERE pharmacy_id = %s AND target_date = %s
                """,
                (pharmacy_id, target_date)
            )
            deleted_count = cur.rowcount
            message = f"Deleted target for {target_date}"
        
        else:
            # Delete entire month
            try:
                year, month_num = month.split("-")
                year = int(year)
                month_num = int(month_num)
                if not (1 <= month_num <= 12):
                    raise ValueError("Invalid month")
            except (ValueError, IndexError):
                raise HTTPException(400, "Month must be in YYYY-MM format")
            
            first_day = date(year, month_num, 1)
            last_day = date(year, month_num, calendar.monthrange(year, month_num)[1])
            
            cur.execute(
                """
                DELETE FROM pharma.pharmacy_targets
                WHERE pharmacy_id = %s
                  AND target_date >= %s
                  AND target_date <= %s
                """,
                (pharmacy_id, first_day, last_day)
            )
            deleted_count = cur.rowcount
            message = f"Deleted {deleted_count} targets for {month}"
        
        conn.commit()
        
        return {
            "success": True,
            "message": message,
            "deleted_count": deleted_count
        } 