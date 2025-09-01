import asyncio
import json
import logging
import time
import jwt
from typing import List, Dict, Any, Optional
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)

class ApplePushService:
    def __init__(self, team_id: str, key_id: str, private_key_path: str, bundle_id: str):
        """
        Initialize Apple Push Notification service using HTTP/2
        
        Args:
            team_id: Apple Developer Team ID
            key_id: Key ID from Apple Developer account
            private_key_path: Path to .p8 private key file
            bundle_id: Your app's bundle identifier
        """
        self.team_id = team_id
        self.key_id = key_id
        self.private_key_path = private_key_path
        self.bundle_id = bundle_id
        self.token = None
        self.token_expiry = 0
        self._load_private_key()
    
    def _load_private_key(self):
        """Load the private key from file"""
        try:
            with open(self.private_key_path, 'r') as f:
                private_key_data = f.read()
            
            self.private_key = serialization.load_pem_private_key(
                private_key_data.encode(),
                password=None
            )
            logger.info("Apple APNs private key loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Apple APNs private key: {e}")
            self.private_key = None
    
    def _generate_token(self):
        """Generate JWT token for Apple APNs authentication"""
        if not self.private_key:
            return None
        
        now = int(time.time())
        if self.token and now < self.token_expiry:
            return self.token
        
        # Token expires in 1 hour
        expiry = now + 3600
        
        payload = {
            'iss': self.team_id,
            'iat': now,
            'exp': expiry
        }
        
        headers = {
            'kid': self.key_id,
            'alg': 'ES256'
        }
        
        try:
            self.token = jwt.encode(payload, self.private_key, algorithm='ES256', headers=headers)
            self.token_expiry = expiry
            return self.token
        except Exception as e:
            logger.error(f"Failed to generate Apple APNs token: {e}")
            return None
    
    async def send_notification(
        self, 
        device_token: str, 
        title: str, 
        body: str, 
        data: Dict[str, Any],
        sound: str = "default",
        badge: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a push notification to an Apple device using HTTP/2
        
        Args:
            device_token: The device push token
            title: Notification title
            body: Notification body
            data: Custom data payload
            sound: Sound to play (default: "default")
            badge: Badge number to display
            
        Returns:
            Dict with status and any error information
        """
        if not self.private_key:
            return {"status": "error", "error": "APNs private key not loaded"}
        
        # Generate authentication token
        auth_token = self._generate_token()
        if not auth_token:
            return {"status": "error", "error": "Failed to generate APNs auth token"}
        
        # Create notification payload
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body
                },
                "sound": sound,
                "badge": badge
            }
        }
        
        # Add custom data
        if data:
            payload.update(data)
        
        # Apple APNs HTTP/2 endpoint
        url = f"https://api.push.apple.com/3/device/{device_token}"
        
        headers = {
            "authorization": f"bearer {auth_token}",
            "apns-topic": self.bundle_id,
            "apns-push-type": "alert",
            "content-type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                # Log the full response for debugging
                logger.info(f"APNs Response - Status: {response.status_code}, Headers: {dict(response.headers)}, Body: {response.text}")
                
                if response.status_code == 200:
                    apns_id = response.headers.get("apns-id")
                    logger.info(f"APNs SUCCESS - Token: {device_token[:20]}..., APNS-ID: {apns_id}")
                    return {"status": "success", "apns_id": apns_id}
                elif response.status_code == 410:
                    # Device token is invalid/expired
                    logger.warning(f"APNs UNREGISTERED - Token: {device_token[:20]}..., Response: {response.text}")
                    return {"status": "unregistered", "error": "Device token is invalid or expired"}
                elif response.status_code == 400:
                    # Bad request (bad token format, etc.)
                    logger.error(f"APNs BAD_TOKEN - Token: {device_token[:20]}..., Response: {response.text}")
                    return {"status": "bad_token", "error": "Bad device token format"}
                else:
                    logger.error(f"APNs ERROR - Status: {response.status_code}, Token: {device_token[:20]}..., Response: {response.text}")
                    return {"status": "error", "error": f"APNs error: {response.status_code} - {response.text}"}
                    
        except Exception as e:
            logger.error(f"Error sending Apple push notification to {device_token[:20]}...: {e}")
            return {"status": "error", "error": str(e)}
    
    async def send_batch_notifications(
        self, 
        notifications: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Send multiple notifications in batch
        
        Args:
            notifications: List of notification dicts with device_token, title, body, data
            
        Returns:
            List of results for each notification
        """
        if not self.private_key:
            return [{"status": "error", "error": "APNs private key not loaded"} for _ in notifications]
        
        results = []
        for notification in notifications:
            result = await self.send_notification(
                device_token=notification["device_token"],
                title=notification["title"],
                body=notification["body"],
                data=notification["data"],
                sound=notification.get("sound", "default"),
                badge=notification.get("badge")
            )
            results.append(result)
        
        return results

# Factory function to create the service
def create_apple_push_service() -> Optional[ApplePushService]:
    """
    Create Apple Push service if credentials are available
    
    Returns:
        ApplePushService instance or None if credentials missing
    """
    import os
    
    team_id = os.getenv("APPLE_TEAM_ID")
    key_id = os.getenv("APPLE_KEY_ID")
    private_key_path = os.getenv("APPLE_PRIVATE_KEY_PATH")
    bundle_id = os.getenv("APPLE_BUNDLE_ID")
    
    if not all([team_id, key_id, private_key_path, bundle_id]):
        logger.warning("Apple APNs credentials not configured - skipping Apple push service")
        return None
    
    try:
        return ApplePushService(team_id, key_id, private_key_path, bundle_id)
    except Exception as e:
        logger.error(f"Failed to create Apple Push service: {e}")
        return None 