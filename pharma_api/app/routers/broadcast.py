from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..auth import require_api_key
from ..services.broadcast import BroadcastService
import os
from ..db import get_conn
from ..utils.crypto import decrypt_token
from ..services.scheduler import _send_push_notifications

router = APIRouter(prefix="/push", tags=["broadcast"], dependencies=[Depends(require_api_key)])


class BroadcastRequest(BaseModel):
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional notification data")
    targetAudience: Optional[str] = Field(default='all', description="Target audience: 'all', 'pharmacy_specific', or 'access_based'")
    pharmacyIds: Optional[List[int]] = Field(default_factory=list, description="Array of pharmacy IDs for targeted sends")
    accessType: Optional[str] = Field(default=None, description="Access type: 'read' or 'write' for access-based targeting")
    modalType: Optional[str] = Field(default='broadcast', description="Modal type: 'broadcast', 'alert', 'promotion', etc.")
    showModal: Optional[bool] = Field(default=True, description="Whether to show modal when notification is tapped")


class BroadcastResponse(BaseModel):
    success: bool
    sent: int
    failed: int
    totalDevices: int
    message: Optional[str] = None


class PharmacyBroadcastRequest(BaseModel):
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional notification data")


class AccessBroadcastRequest(BaseModel):
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional notification data")
    pharmacyIds: Optional[List[int]] = Field(default_factory=list, description="Array of pharmacy IDs for targeted sends")


@router.post("/broadcast", response_model=BroadcastResponse)
async def broadcast_to_all(request: BroadcastRequest):
    """
    Send a broadcast notification to users based on targeting criteria
    
    - **title**: Notification title
    - **body**: Notification body  
    - **data**: Additional notification data (optional)
    - **targetAudience**: Target audience type ('all', 'pharmacy_specific', 'access_based')
    - **pharmacyIds**: Array of pharmacy IDs for targeted sends (required for pharmacy_specific/access_based)
    - **accessType**: Access type ('read' or 'write') for access-based targeting
    """
    try:
        # Add modal configuration to data
        broadcast_data = {
            **request.data,
            "modalType": request.modalType,
            "showModal": request.showModal,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        result = await BroadcastService.send_broadcast(
            title=request.title,
            body=request.body,
            data=broadcast_data,
            target_audience=request.targetAudience,
            pharmacy_ids=request.pharmacyIds,
            access_type=request.accessType,
            created_by='api'
        )
        
        return BroadcastResponse(**result)
        
    except Exception as error:
        print(f'Broadcast error: {error}')
        raise HTTPException(status_code=500, detail='Broadcast failed')


@router.post("/broadcast/pharmacy/{pharmacy_id}", response_model=BroadcastResponse)
async def broadcast_to_pharmacy(pharmacy_id: int, request: PharmacyBroadcastRequest):
    """
    Send a broadcast notification to users with access to a specific pharmacy
    
    - **pharmacy_id**: The pharmacy ID to target
    - **title**: Notification title
    - **body**: Notification body
    - **data**: Additional notification data (optional)
    """
    try:
        result = await BroadcastService.send_broadcast(
            title=request.title,
            body=request.body,
            data=request.data,
            target_audience='pharmacy_specific',
            pharmacy_ids=[pharmacy_id],
            created_by='api'
        )
        
        return BroadcastResponse(**result)
        
    except Exception as error:
        print(f'Pharmacy broadcast error: {error}')
        raise HTTPException(status_code=500, detail='Pharmacy broadcast failed')


@router.post("/broadcast/access/read", response_model=BroadcastResponse)
async def broadcast_to_read_access_users(request: AccessBroadcastRequest):
    """
    Send a broadcast notification to users with read access to specified pharmacies
    
    - **title**: Notification title
    - **body**: Notification body
    - **data**: Additional notification data (optional)
    - **pharmacyIds**: Array of pharmacy IDs to target (defaults to all pharmacies if empty)
    """
    try:
        # If no pharmacy IDs specified, get all pharmacy IDs
        pharmacy_ids = request.pharmacyIds
        if not pharmacy_ids:
            from ..db import get_conn
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE is_active = true")
                pharmacy_ids = [row['pharmacy_id'] for row in cur.fetchall()]
        
        result = await BroadcastService.send_broadcast(
            title=request.title,
            body=request.body,
            data=request.data,
            target_audience='access_based',
            pharmacy_ids=pharmacy_ids,
            access_type='read',
            created_by='api'
        )
        
        return BroadcastResponse(**result)
        
    except Exception as error:
        print(f'Read access broadcast error: {error}')
        raise HTTPException(status_code=500, detail='Read access broadcast failed')


@router.post("/broadcast/access/write", response_model=BroadcastResponse)
async def broadcast_to_write_access_users(request: AccessBroadcastRequest):
    """
    Send a broadcast notification to users with write access to specified pharmacies
    
    - **title**: Notification title
    - **body**: Notification body
    - **data**: Additional notification data (optional)
    - **pharmacyIds**: Array of pharmacy IDs to target (defaults to all pharmacies if empty)
    """
    try:
        # If no pharmacy IDs specified, get all pharmacy IDs
        pharmacy_ids = request.pharmacyIds
        if not pharmacy_ids:
            from ..db import get_conn
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute("SELECT pharmacy_id FROM pharma.pharmacies WHERE is_active = true")
                pharmacy_ids = [row['pharmacy_id'] for row in cur.fetchall()]
        
        result = await BroadcastService.send_broadcast(
            title=request.title,
            body=request.body,
            data=request.data,
            target_audience='access_based',
            pharmacy_ids=pharmacy_ids,
            access_type='write',
            created_by='api'
        )
        
        return BroadcastResponse(**result)
        
    except Exception as error:
        print(f'Write access broadcast error: {error}')
        raise HTTPException(status_code=500, detail='Write access broadcast failed') 


@router.get("/apns-config")
async def get_apns_config():
    """Get Apple APNs configuration details for debugging"""
    
    config = {
        "team_id": os.getenv("APPLE_TEAM_ID", "NOT_SET"),
        "key_id": os.getenv("APPLE_KEY_ID", "NOT_SET"), 
        "bundle_id": os.getenv("APPLE_BUNDLE_ID", "NOT_SET"),
        "private_key_path": os.getenv("APPLE_PRIVATE_KEY_PATH", "NOT_SET"),
        "private_key_exists": False
    }
    
    # Check if private key file exists
    if config["private_key_path"] != "NOT_SET":
        try:
            with open(config["private_key_path"], 'r') as f:
                key_content = f.read()
                config["private_key_exists"] = True
                config["private_key_preview"] = key_content[:100] + "..." if len(key_content) > 100 else key_content
        except Exception as e:
            config["private_key_error"] = str(e)
    
    return config


class TestUserPushRequest(BaseModel):
    title: str = Field("Test Push", description="Notification title")
    body: str = Field("Hello from test endpoint", description="Notification body")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional data payload")
    modalType: Optional[str] = Field(default='test', description="Modal type to show")
    showModal: Optional[bool] = Field(default=True, description="Whether to show modal")


@router.post("/broadcast/test/user/{user_id}")
async def send_test_push_to_user(user_id: int, request: TestUserPushRequest):
    """Send a one-off test notification to all active devices for a specific user."""
    messages: list[dict[str, Any]] = []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT device_id, platform, push_token_enc
            FROM pharma.devices
            WHERE user_id = %s AND disabled_at IS NULL
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall() or []
        for r in rows:
            token_plain = decrypt_token(r["push_token_enc"])  # app handles decryption key
            messages.append({
                "to": token_plain,
                "sound": "default",
                "title": request.title,
                "body": request.body,
                "data": {
                    **(request.data or {}),
                    "type": "TEST",
                    "showModal": request.showModal,
                    "modalType": request.modalType,
                    "modalData": {
                        "title": request.title,
                        "body": request.body,
                        "type": "TEST",
                        "modalType": request.modalType,
                        "timestamp": datetime.utcnow().isoformat(),
                        **(request.data or {})
                    }
                },
            })

    if not messages:
        return {"success": True, "sent": 0, "failed": 0, "totalDevices": 0, "message": "No active devices for user"}

    results = await _send_push_notifications(messages)
    # Summarize
    sent = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
    failed = len(results) - sent
    return {"success": True, "sent": sent, "failed": failed, "totalDevices": len(messages), "results": results} 