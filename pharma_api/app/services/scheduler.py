import asyncio
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Any
import httpx
from ..db import get_conn
from ..utils.crypto import decrypt_token

EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _should_send_now(user_tz: str, hhmm: str) -> bool:
    try:
        now_local = _utcnow().astimezone(ZoneInfo(user_tz))
    except Exception:
        return False
    target_h, target_m = map(int, hhmm.split(":"))
    return now_local.hour == target_h and now_local.minute == target_m


def _idempotency_key(user_id: int, kind: str, pharmacy_id: int, day_key: str) -> str:
    return f"{user_id}:{kind}:{pharmacy_id}:{day_key}"


async def _send_expo_batch(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not messages:
        return []
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(EXPO_URL, json=messages)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data") or []


def _insert_log(cur, user_id: int, kind: str, pharmacy_id: int, idem: str, status: str, error: str | None, ticket_id: str | None):
    cur.execute(
        """
        INSERT INTO pharma.notification_log (user_id, kind, pharmacy_id, idempotency_key, status, error, ticket_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (idempotency_key) DO NOTHING
        """,
        (user_id, kind, pharmacy_id, idem, status, error, ticket_id),
    )


async def run_once() -> None:
    today_key = _utcnow().astimezone(timezone.utc).strftime("%Y-%m-%d")
    to_send: List[Dict[str, Any]] = []
    tickets: List[tuple[int, str, int, str]] = []  # (user_id, kind, pharmacy_id, idempotency_key)

    with get_conn() as conn, conn.cursor() as cur:
        # load candidates: user devices + settings
        cur.execute(
            """
            SELECT d.user_id, d.device_id, d.push_token_enc, d.timezone,
                   s.daily_enabled, s.daily_time, s.daily_pharmacy_ids,
                   s.lowgp_enabled, s.lowgp_time, s.lowgp_pharmacy_ids, s.lowgp_threshold
            FROM pharma.devices d
            JOIN pharma.notification_settings s ON s.user_id = d.user_id
            WHERE d.disabled_at IS NULL
            """
        )
        rows = cur.fetchall()

        for r in rows:
            user_id = r["user_id"]
            tz = r["timezone"]
            token = decrypt_token(r["push_token_enc"])

            # DAILY SUMMARY
            if r["daily_enabled"] and r["daily_time"] and _should_send_now(tz, r["daily_time"]):
                for pid in (r["daily_pharmacy_ids"] or []):
                    idem = _idempotency_key(user_id, "DAILY_SUMMARY", pid, today_key)
                    # Skip if already logged
                    cur.execute("SELECT 1 FROM pharma.notification_log WHERE idempotency_key=%s", (idem,))
                    if cur.fetchone():
                        continue
                    # Resolve pharmacy name
                    cur.execute("SELECT name FROM pharma.pharmacies WHERE pharmacy_id=%s", (pid,))
                    ph = cur.fetchone()
                    pname = ph["name"] if ph else str(pid)
                    to_send.append({
                        "to": token,
                        "sound": "default",
                        "title": "TLC PharmaSight",
                        "body": "Daily Summary",
                        "data": {"type": "DAILY_SUMMARY", "pharmacyId": pid, "pharmacyName": pname},
                    })
                    tickets.append((user_id, "DAILY_SUMMARY", pid, idem))

            # LOW GP ALERTS
            if r["lowgp_enabled"] and r["lowgp_time"] and _should_send_now(tz, r["lowgp_time"]):
                for pid in (r["lowgp_pharmacy_ids"] or []):
                    idem = _idempotency_key(user_id, "LOW_GP_ALERT", pid, today_key)
                    cur.execute("SELECT 1 FROM pharma.notification_log WHERE idempotency_key=%s", (idem,))
                    if cur.fetchone():
                        continue
                    cur.execute("SELECT name FROM pharma.pharmacies WHERE pharmacy_id=%s", (pid,))
                    ph = cur.fetchone()
                    pname = ph["name"] if ph else str(pid)
                    # TODO: compute low GP items; placeholder empty list
                    to_send.append({
                        "to": token,
                        "sound": "default",
                        "title": "TLC PharmaSight - Low GP Alert",
                        "body": "Low GP products available",
                        "data": {"type": "LOW_GP_ALERT", "pharmacyId": pid, "pharmacyName": pname, "lowGPItems": [], "threshold": float(r["lowgp_threshold"]) if r["lowgp_threshold"] is not None else None},
                    })
                    tickets.append((user_id, "LOW_GP_ALERT", pid, idem))

        # send in batches of 100
        for i in range(0, len(to_send), 100):
            batch = to_send[i:i+100]
            batch_meta = tickets[i:i+100]
            try:
                results = await _send_expo_batch(batch)
                for meta, res in zip(batch_meta, results or []):
                    uid, kind, pid, idem = meta
                    ticket_id = res.get("id") if isinstance(res, dict) else None
                    _insert_log(cur, uid, kind, pid, idem, "SENT", None, ticket_id)
            except Exception as e:
                for meta in batch_meta:
                    uid, kind, pid, idem = meta
                    _insert_log(cur, uid, kind, pid, idem, "FAILED", str(e), None)
        conn.commit()


async def main_loop() -> None:
    # Simple every-minute loop
    while True:
        try:
            await run_once()
        except Exception:
            pass
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main_loop()) 