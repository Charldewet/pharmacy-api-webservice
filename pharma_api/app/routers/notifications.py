from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from ..db import get_conn
from ..auth import get_current_user_id
from ..config import settings
from ..utils.crypto import encrypt_token

router = APIRouter(prefix="", tags=["notifications"])  # base paths per spec

class PushRegisterRequest(BaseModel):
    deviceId: str
    platform: str  # ios | android
    pushToken: str
    timezone: str
    appVersion: Optional[str] = None
    deviceModel: Optional[str] = None
    osVersion: Optional[str] = None
    locale: Optional[str] = None

class PushRegisterResponse(BaseModel):
    status: str = "ok"
    deviceId: str
    disabledAt: Optional[datetime] = None

class PushUnregisterRequest(BaseModel):
    deviceId: Optional[str] = None
    pushToken: Optional[str] = None

class DailySummarySettings(BaseModel):
    enabled: bool
    time: str
    pharmacyIds: List[int]

class LowGpSettings(BaseModel):
    enabled: bool
    time: str
    pharmacyIds: List[int]
    threshold: float

class NotificationSettings(BaseModel):
    dailySummary: DailySummarySettings
    lowGpAlerts: LowGpSettings

class SaveSettingsResponse(BaseModel):
    status: str
    settings: NotificationSettings
    savedAt: datetime


def _validate_time(t: str) -> None:
    if len(t) != 5 or t[2] != ":":
        raise HTTPException(400, "time must be HH:mm")
    hh, mm = t.split(":", 1)
    if not (hh.isdigit() and mm.isdigit()):
        raise HTTPException(400, "time must be HH:mm")
    h, m = int(hh), int(mm)
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise HTTPException(400, "time must be HH:mm")


def _authorize_pharmacies(cur, user_id: int, pharmacy_ids: List[int]) -> None:
    if not pharmacy_ids:
        return
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM pharma.user_pharmacies
        WHERE user_id = %s AND pharmacy_id = ANY(%s)
        """,
        (user_id, pharmacy_ids),
    )
    cnt = cur.fetchone()["cnt"]
    if cnt != len(pharmacy_ids):
        raise HTTPException(403, "One or more pharmacyIds are not permitted for this user")


@router.post("/push/register", response_model=PushRegisterResponse)
def push_register(req: PushRegisterRequest, user_id: int = Depends(get_current_user_id)):
    _validate_time("00:00")  # no-op, keeps helper import usage
    enc = encrypt_token(req.pushToken)
    with get_conn() as conn, conn.cursor() as cur:
        # upsert device
        cur.execute(
            """
            INSERT INTO pharma.devices (user_id, device_id, platform, push_token_enc, timezone,
                                        device_model, os_version, app_version, locale, last_seen_at, disabled_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), NULL)
            ON CONFLICT (device_id) DO UPDATE SET
              user_id = EXCLUDED.user_id,
              platform = EXCLUDED.platform,
              push_token_enc = EXCLUDED.push_token_enc,
              timezone = EXCLUDED.timezone,
              device_model = EXCLUDED.device_model,
              os_version = EXCLUDED.os_version,
              app_version = EXCLUDED.app_version,
              locale = EXCLUDED.locale,
              last_seen_at = now(),
              disabled_at = NULL,
              updated_at = now()
            RETURNING disabled_at
            """,
            (
                user_id,
                req.deviceId,
                req.platform,
                enc,
                req.timezone,
                req.deviceModel,
                req.osVersion,
                req.appVersion,
                req.locale,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return PushRegisterResponse(deviceId=req.deviceId, disabledAt=row["disabled_at"])  # type: ignore


@router.post("/push/unregister")
def push_unregister(req: PushUnregisterRequest, user_id: int = Depends(get_current_user_id)):
    if not req.deviceId and not req.pushToken:
        raise HTTPException(400, "Provide deviceId or pushToken")
    with get_conn() as conn, conn.cursor() as cur:
        if req.deviceId:
            cur.execute(
                """
                UPDATE pharma.devices
                SET disabled_at = now(), updated_at = now()
                WHERE device_id = %s AND user_id = %s
                """,
                (req.deviceId, user_id),
            )
        else:
            enc = encrypt_token(req.pushToken or "")
            cur.execute(
                """
                UPDATE pharma.devices
                SET disabled_at = now(), updated_at = now()
                WHERE user_id = %s AND push_token_enc = %s
                """,
                (user_id, enc),
            )
        conn.commit()
        return {"status": "unregistered"}


@router.put("/notifications/settings", response_model=SaveSettingsResponse)
def save_settings(req: NotificationSettings, user_id: int = Depends(get_current_user_id)):
    _validate_time(req.dailySummary.time)
    _validate_time(req.lowGpAlerts.time)
    with get_conn() as conn, conn.cursor() as cur:
        _authorize_pharmacies(cur, user_id, req.dailySummary.pharmacyIds)
        _authorize_pharmacies(cur, user_id, req.lowGpAlerts.pharmacyIds)
        cur.execute(
            """
            INSERT INTO pharma.notification_settings (
              user_id, daily_enabled, daily_time, daily_pharmacy_ids,
              lowgp_enabled, lowgp_time, lowgp_pharmacy_ids, lowgp_threshold, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now())
            ON CONFLICT (user_id) DO UPDATE SET
              daily_enabled = EXCLUDED.daily_enabled,
              daily_time = EXCLUDED.daily_time,
              daily_pharmacy_ids = EXCLUDED.daily_pharmacy_ids,
              lowgp_enabled = EXCLUDED.lowgp_enabled,
              lowgp_time = EXCLUDED.lowgp_time,
              lowgp_pharmacy_ids = EXCLUDED.lowgp_pharmacy_ids,
              lowgp_threshold = EXCLUDED.lowgp_threshold,
              updated_at = now()
            RETURNING user_id
            """,
            (
                user_id,
                req.dailySummary.enabled,
                req.dailySummary.time,
                req.dailySummary.pharmacyIds,
                req.lowGpAlerts.enabled,
                req.lowGpAlerts.time,
                req.lowGpAlerts.pharmacyIds,
                req.lowGpAlerts.threshold,
            ),
        )
        conn.commit()
        return SaveSettingsResponse(status="ok", settings=req, savedAt=datetime.utcnow()) 