"""
VTube Studio client for the VTuber AI Bot.
"""

import json
import logging
import asyncio
import math
import websockets

logger = logging.getLogger(__name__)

class VTubeStudioClient:
    """Client for interacting with VTube Studio via WebSocket."""
    
    def __init__(self, config):
        """Initialize the VTube Studio client.
        
        Args:
            config: Configuration object containing VTube Studio settings
        """
        self.config = config
        self.ws_url = config.vtube_studio_ws_url
        self.ws = None
    
    async def initialize(self):
        """Initialize VTube Studio WebSocket connection."""
        try:
            # Set ping interval to 20 seconds to prevent timeout
            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=10,   # Wait 10 seconds for pong response
                close_timeout=5    # Wait 5 seconds for close handshake
            )
            logger.info("Connected to VTube Studio WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to VTube Studio: {e}")
            self.ws = None
            return False
    
    async def trigger_animation(self, hotkey_name="AI Response"):
        """Trigger an animation in VTube Studio.
        
        Args:
            hotkey_name: Name of the hotkey to trigger
        """
        if not self.ws:
            logger.warning("VTube Studio WebSocket not connected")
            return False
            
        try:
            await self.ws.send(json.dumps({
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": "someID",
                "messageType": "TriggerHotkeyByName",
                "data": {
                    "hotkeyName": hotkey_name
                }
            }))
            return True
        except Exception as e:
            logger.error(f"Error triggering avatar animation: {e}")
            return False
    
    # Lip sync methods have been removed as requested
    
    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
