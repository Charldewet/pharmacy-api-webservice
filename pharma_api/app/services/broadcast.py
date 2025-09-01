import asyncio
from typing import List, Dict, Any, Optional, Tuple
import json
from ..db import get_conn
from ..utils.crypto import decrypt_token
from .scheduler import _send_push_notifications


class BroadcastService:
    """Service for sending broadcast push notifications to multiple users"""
    
    @staticmethod
    async def send_broadcast(
        title: str,
        body: str,
        data: Dict[str, Any] = None,
        target_audience: str = 'all',
        pharmacy_ids: List[int] = None,
        access_type: str = None,
        created_by: str = 'system'
    ) -> Dict[str, Any]:
        """
        Send a broadcast push notification
        
        Args:
            title: Notification title
            body: Notification body
            data: Additional notification data
            target_audience: 'all', 'pharmacy_specific', or 'access_based'
            pharmacy_ids: List of pharmacy IDs for targeted sends
            access_type: 'read' or 'write' for access-based targeting
            created_by: Username of who sent the broadcast
            
        Returns:
            Dict with success status, sent count, failed count, and total devices
        """
        if data is None:
            data = {}
        if pharmacy_ids is None:
            pharmacy_ids = []
            
        # Get target devices based on audience type
        devices = BroadcastService._get_target_devices(
            target_audience, pharmacy_ids, access_type
        )
        
        if not devices:
            return {
                'success': True,
                'sent': 0,
                'failed': 0,
                'totalDevices': 0,
                'message': 'No devices found for target audience'
            }
        
        # Prepare notification messages
        messages = []
        for device in devices:
            messages.append({
                "to": device['push_token'],
                "sound": "default",
                "title": title,
                "body": body,
                "data": {
                    "type": "BROADCAST",
                    "category": data.get("category", "general"),
                    "showModal": True,  # Flag to trigger modal opening
                    "modalType": data.get("modalType", "broadcast"),  # Type of modal to show
                    "modalData": {
                        "title": title,
                        "body": body,
                        "category": data.get("category", "general"),
                        "timestamp": data.get("timestamp"),
                        "source": data.get("source", "system"),
                        **data
                    },
                    **data
                }
            })
        
        # Send notifications in batches
        sent_count = 0
        failed_count = 0
        
        for i in range(0, len(messages), 100):
            batch = messages[i:i+100]
            try:
                results = await _send_push_notifications(batch)
                for idx, result in enumerate(results):
                    device_info = devices[i + idx] if i + idx < len(devices) else {'push_token': 'unknown'}
                    token_preview = device_info['push_token'][:20] + "..." if len(device_info['push_token']) > 20 else device_info['push_token']
                    
                    if result.get("status") == "success":
                        print(f"BROADCAST SUCCESS: {token_preview} - APNS-ID: {result.get('apns_id', 'N/A')}")
                        sent_count += 1
                    else:
                        error_msg = result.get("error", "Unknown error")
                        status = result.get("status", "unknown")
                        print(f"BROADCAST FAILED: {token_preview} - Status: {status}, Error: {error_msg}")
                        failed_count += 1
            except Exception as e:
                print(f"Broadcast batch error: {e}")
                failed_count += len(batch)
        
        # Store broadcast record
        BroadcastService._store_broadcast_record(
            title=title,
            body=body,
            data=data,
            target_audience=target_audience,
            pharmacy_ids=pharmacy_ids,
            access_type=access_type,
            sent_count=sent_count,
            failed_count=failed_count,
            created_by=created_by
        )
        
        return {
            'success': True,
            'sent': sent_count,
            'failed': failed_count,
            'totalDevices': len(devices)
        }
    
    @staticmethod
    def _get_target_devices(
        target_audience: str,
        pharmacy_ids: List[int],
        access_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get target devices based on audience criteria"""
        
        with get_conn() as conn, conn.cursor() as cur:
            if target_audience == 'all':
                # Get all active devices
                cur.execute("""
                    SELECT d.push_token_enc, d.platform
                    FROM pharma.devices d
                    WHERE d.disabled_at IS NULL
                """)
                
            elif target_audience == 'pharmacy_specific' and pharmacy_ids:
                # Get devices for users with access to specific pharmacies
                placeholders = ','.join(['%s'] * len(pharmacy_ids))
                cur.execute(f"""
                    SELECT DISTINCT d.push_token_enc, d.platform
                    FROM pharma.devices d
                    JOIN pharma.user_pharmacies up ON d.user_id = up.user_id
                    WHERE d.disabled_at IS NULL
                    AND up.pharmacy_id IN ({placeholders})
                """, pharmacy_ids)
                
            elif target_audience == 'access_based' and pharmacy_ids and access_type:
                # Get devices for users with specific access type to pharmacies
                placeholders = ','.join(['%s'] * len(pharmacy_ids))
                access_column = 'can_read' if access_type == 'read' else 'can_write'
                cur.execute(f"""
                    SELECT DISTINCT d.push_token_enc, d.platform
                    FROM pharma.devices d
                    JOIN pharma.user_pharmacies up ON d.user_id = up.user_id
                    WHERE d.disabled_at IS NULL
                    AND up.pharmacy_id IN ({placeholders})
                    AND up.{access_column} = true
                """, pharmacy_ids)
                
            else:
                return []
            
            rows = cur.fetchall()
            
            # Decrypt tokens and return device info
            devices = []
            for row in rows:
                try:
                    decrypted_token = decrypt_token(row['push_token_enc'])
                    devices.append({
                        'push_token': decrypted_token,
                        'platform': row['platform']
                    })
                except Exception as e:
                    print(f"Failed to decrypt token: {e}")
                    continue
            
            return devices
    
    @staticmethod
    def _store_broadcast_record(
        title: str,
        body: str,
        data: Dict[str, Any],
        target_audience: str,
        pharmacy_ids: List[int],
        access_type: str,
        sent_count: int,
        failed_count: int,
        created_by: str
    ) -> None:
        """Store broadcast notification record in database"""
        
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO pharma.broadcast_notifications 
                (title, body, data, target_audience, pharmacy_ids, access_type, 
                 sent_count, failed_count, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                title, body, json.dumps(data), target_audience,
                pharmacy_ids, access_type, sent_count, failed_count, created_by
            ])
            conn.commit() 