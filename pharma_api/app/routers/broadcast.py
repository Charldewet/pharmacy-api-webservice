from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from ..auth import require_api_key
from ..services.broadcast import BroadcastService

router = APIRouter(prefix="/push", tags=["broadcast"], dependencies=[Depends(require_api_key)])


class BroadcastRequest(BaseModel):
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional notification data")
    targetAudience: Optional[str] = Field(default='all', description="Target audience: 'all', 'pharmacy_specific', or 'access_based'")
    pharmacyIds: Optional[List[int]] = Field(default_factory=list, description="Array of pharmacy IDs for targeted sends")
    accessType: Optional[str] = Field(default=None, description="Access type: 'read' or 'write' for access-based targeting")


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
        result = await BroadcastService.send_broadcast(
            title=request.title,
            body=request.body,
            data=request.data,
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