import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from apns2.client import APNsClient
from apns2.payload import Payload
from apns2.credentials import TokenCredentials
from apns2.errors import UnregisteredError, BadDeviceTokenError

logger = logging.getLogger(__name__)

class ApplePushService:
    def __init__(self, team_id: str, key_id: str, private_key_path: str, bundle_id: str):
        """
        Initialize Apple Push Notification service
        
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
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the APNs client with credentials"""
        try:
            credentials = TokenCredentials(
                auth_key_path=self.private_key_path,
                auth_key_id=self.key_id,
                team_id=self.team_id
            )
            self.client = APNsClient(
                credentials=credentials,
                use_sandbox=False  # Use production for TestFlight
            )
            logger.info("Apple APNs client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Apple APNs client: {e}")
            self.client = None
    
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
        Send a push notification to an Apple device
        
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
        if not self.client:
            return {"status": "error", "error": "APNs client not initialized"}
        
        try:
            # Create the notification payload
            payload = Payload(
                alert={
                    "title": title,
                    "body": body
                },
                sound=sound,
                badge=badge,
                custom=data
            )
            
            # Send the notification
            result = self.client.send_notification(
                device_token=device_token,
                notification=payload,
                topic=self.bundle_id
            )
            
            # Check the result
            if result.is_successful:
                return {"status": "success", "apns_id": result.apns_id}
            else:
                return {"status": "error", "error": str(result.reason)}
                
        except UnregisteredError:
            # Device token is invalid/expired
            return {"status": "unregistered", "error": "Device token is invalid or expired"}
        except BadDeviceTokenError:
            # Bad device token format
            return {"status": "bad_token", "error": "Bad device token format"}
        except Exception as e:
            logger.error(f"Error sending Apple push notification: {e}")
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
        if not self.client:
            return [{"status": "error", "error": "APNs client not initialized"} for _ in notifications]
        
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