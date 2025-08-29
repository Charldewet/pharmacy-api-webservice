import asyncio
import os
from datetime import datetime, timezone, time as dtime, timedelta, date
from zoneinfo import ZoneInfo
from typing import List, Dict, Any, Optional
import httpx
from ..db import get_conn
from ..utils.crypto import decrypt_token

EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_due_now(user_tz: str, hhmm: str, window_minutes: int = 3) -> tuple[bool, Optional[date]]:
    """Return (is_due, local_date) using a tolerance window to avoid misses on minute drift."""
    try:
        now_local = _utcnow().astimezone(ZoneInfo(user_tz))
    except Exception:
        return (False, None)
    try:
        hh, mm = map(int, hhmm.split(":"))
    except Exception:
        return (False, None)
    target_dt = datetime.combine(now_local.date(), dtime(hh, mm, tzinfo=now_local.tzinfo))
    delta = now_local - target_dt
    return (timedelta(0) <= delta < timedelta(minutes=window_minutes), now_local.date())


def _idempotency_key(user_id: int, kind: str, pharmacy_id: int, day_key: str, version: str) -> str:
    return f"{user_id}:{kind}:{pharmacy_id}:{day_key}:{version}"


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


def _fetch_low_gp_items(cur, pharmacy_id: int, local_day: date, threshold: float) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT p.product_code AS product_code,
               COALESCE(p.description,'') AS description,
               f.gp_pct
        FROM pharma.fact_stock_activity f
        JOIN pharma.products p ON p.product_id = f.product_id
        WHERE f.pharmacy_id = %s
          AND f.business_date = %s
          AND f.gp_pct IS NOT NULL
          AND f.gp_pct < %s
        ORDER BY f.gp_pct ASC
        """,
        (pharmacy_id, local_day, threshold),
    )
    rows = cur.fetchall() or []
    return [{"product_code": r["product_code"], "description": r["description"], "gp_pct": float(r["gp_pct"]) } for r in rows]


async def run_once() -> None:
    to_send: List[Dict[str, Any]] = []
    tickets: List[tuple[int, str, int, str]] = []  # (user_id, kind, pharmacy_id, idempotency_key)

    with get_conn() as conn, conn.cursor() as cur:
        # load candidates: user devices + settings
        cur.execute(
            """
            SELECT d.user_id, d.device_id, d.push_token_enc, d.timezone,
                   s.daily_enabled, s.daily_time, s.daily_pharmacy_ids,
                   s.lowgp_enabled, s.lowgp_time, s.lowgp_pharmacy_ids, s.lowgp_threshold,
                   s.updated_at AS settings_updated_at
            FROM pharma.devices d
            JOIN pharma.notification_settings s ON s.user_id = d.user_id
            WHERE d.disabled_at IS NULL
            """
        )
        rows = cur.fetchall()

        queued = 0
        for r in rows:
            user_id = r["user_id"]
            tz = r["timezone"]
            token = decrypt_token(r["push_token_enc"])
            settings_ver = str(int(r["settings_updated_at"].timestamp())) if r["settings_updated_at"] else "0"

            # DAILY SUMMARY
            if r["daily_enabled"] and r["daily_time"]:
                due, local_day = _is_due_now(tz, r["daily_time"])  
                if due and local_day is not None:
                    day_key = local_day.isoformat()
                    for pid in (r["daily_pharmacy_ids"] or []):
                        idem = _idempotency_key(user_id, "DAILY_SUMMARY", pid, day_key, settings_ver)
                        cur.execute("SELECT 1 FROM pharma.notification_log WHERE idempotency_key=%s", (idem,))
                        if cur.fetchone():
                            continue
                        cur.execute("SELECT name FROM pharma.pharmacies WHERE pharmacy_id=%s", (pid,))
                        ph = cur.fetchone()
                        pname = ph["name"] if ph else str(pid)
                        pcode = str(pid)  # Use pharmacy_id as the code
                        to_send.append({
                            "to": token,
                            "sound": "default",
                            "title": "TLC PharmaSight",
                            "body": f"Daily Summary for {pname}",
                            "data": {"type": "DAILY_SUMMARY", "pharmacyCode": pcode, "pharmacyName": pname},
                        })
                        tickets.append((user_id, "DAILY_SUMMARY", pid, idem))
                        queued += 1

            # LOW GP ALERTS
            if r["lowgp_enabled"] and r["lowgp_time"]:
                due, local_day = _is_due_now(tz, r["lowgp_time"])  
                if due and local_day is not None:
                    day_key = local_day.isoformat()
                    threshold = float(r["lowgp_threshold"]) if r["lowgp_threshold"] is not None else 10.0
                    for pid in (r["lowgp_pharmacy_ids"] or []):
                        idem = _idempotency_key(user_id, "LOW_GP_ALERT", pid, day_key, settings_ver)
                        cur.execute("SELECT 1 FROM pharma.notification_log WHERE idempotency_key=%s", (idem,))
                        if cur.fetchone():
                            continue
                        
                        # Only send low GP alerts if there are actually items below threshold
                        low_items = _fetch_low_gp_items(cur, pid, local_day, threshold)
                        if not low_items:
                            continue  # Skip this pharmacy if no low GP items
                        
                        cur.execute("SELECT name FROM pharma.pharmacies WHERE pharmacy_id=%s", (pid,))
                        ph = cur.fetchone()
                        pname = ph["name"] if ph else str(pid)
                        pcode = str(pid)  # Use pharmacy_id as the code
                        # Create a detailed body with product names and GP percentages
                        product_details = []
                        for item in low_items:
                            product_details.append(f"{item['description']} ({item['gp_pct']:.1f}%)")
                        body_text = f"Low GP Alert - {pname}\n" + "\n".join(product_details)
                        
                        to_send.append({
                            "to": token,
                            "sound": "default",
                            "title": f"Low GP Alert - {pname}",
                            "body": "\n".join(product_details),
                            "data": {"type": "LOW_GP_ALERT", "pharmacyCode": pcode, "pharmacyName": pname, "lowGPItems": low_items, "threshold": threshold},
                        })
                        tickets.append((user_id, "LOW_GP_ALERT", pid, idem))
                        queued += 1

        # send in batches of 100
        sent = 0
        failed = 0
        for i in range(0, len(to_send), 100):
            batch = to_send[i:i+100]
            batch_meta = tickets[i:i+100]
            try:
                results = await _send_expo_batch(batch)
                for meta, res in zip(batch_meta, results or []):
                    uid, kind, pid, idem = meta
                    ticket_id = res.get("id") if isinstance(res, dict) else None
                    _insert_log(cur, uid, kind, pid, idem, "SENT", None, ticket_id)
                    sent += 1
            except Exception as e:
                for meta in batch_meta:
                    uid, kind, pid, idem = meta
                    _insert_log(cur, uid, kind, pid, idem, "FAILED", str(e), None)
                    failed += 1
        conn.commit()

        print(f"[scheduler] queued={queued} sent={sent} failed={failed} at {_utcnow().isoformat()}")


async def main_loop() -> None:
    while True:
        try:
            await run_once()
        except Exception as e:
            print(f"[scheduler] error: {e}")
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main_loop()) 