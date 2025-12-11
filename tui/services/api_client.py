"""
API Client Service for TUI

Communicates with the FastAPI backend for real-time operations.
Provides WebSocket support for live updates.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import aiohttp
import socket

logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with the FastAPI backend"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client"""
        self.base_url = base_url
        self.session = None
        self.websocket = None
        self.client_id = None
        self.connected = False
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def connect(self) -> bool:
        """Connect to the API server"""
        try:
            # Create HTTP session
            if self.session is None:
                self.session = aiohttp.ClientSession()

            # Test HTTP connection
            async with self.session.get(f"{self.base_url}/api/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    logger.info(f"Connected to API server: {health_data}")
                    self.connected = True
                    self.reconnect_attempts = 0
                    return True
                else:
                    logger.error(f"API server returned status {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to connect to API server: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from the API server"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            if self.session:
                await self.session.close()
                self.session = None

            self.connected = False
            logger.info("Disconnected from API server")

        except Exception as e:
            logger.error(f"Error disconnecting from API server: {e}")

    async def connect_websocket(self, client_id: str) -> bool:
        """Connect to WebSocket for real-time updates"""
        try:
            if self.websocket:
                await self.websocket.close()

            # Construct WebSocket URL
            ws_url = self.base_url.replace("http://", "ws://")
            ws_url = f"{ws_url}/ws/{client_id}"

            # Connect to WebSocket
            self.websocket = await self.session.ws_connect(ws_url)
            self.client_id = client_id
            logger.info(f"Connected to WebSocket: {ws_url}")

            # Start message listener
            asyncio.create_task(self._listen_websocket())
            return True

        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def _listen_websocket(self):
        """Listen for WebSocket messages"""
        try:
            while self.websocket and not self.websocket.closed:
                message = await self.websocket.receive_text()
                await self._handle_websocket_message(message)

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self.websocket = None

            # Attempt to reconnect
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                await asyncio.sleep(2 ** self.reconnect_attempts)  # Exponential backoff
                if self.client_id:
                    await self.connect_websocket(self.client_id)

    async def _handle_websocket_message(self, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get('type', 'unknown')

            # Call registered handlers
            if message_type in self.message_handlers:
                for handler in self.message_handlers[message_type]:
                    try:
                        await handler(data)
                    except Exception as e:
                        logger.error(f"Error in message handler: {e}")

            # Log the message
            if message_type == 'log_message':
                level = data.get('level', 'info')
                msg = data.get('message', '')
                task_id = data.get('task_id', 'unknown')
                logger.info(f"[Task {task_id}] {level.upper()}: {msg}")
            elif message_type == 'task_update':
                task_id = data.get('task', {}).get('task_id', 'unknown')
                status = data.get('task', {}).get('status', 'unknown')
                progress = data.get('task', {}).get('progress', 0)
                logger.info(f"[Task {task_id}] Status: {status}, Progress: {progress}%")

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for WebSocket messages"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)

    async def get_devices(self) -> List[Dict[str, Any]]:
        """Get all devices"""
        try:
            async with self.session.get(f"{self.base_url}/api/devices") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get devices: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return []

    async def get_device(self, device_ip: str) -> Optional[Dict[str, Any]]:
        """Get specific device"""
        try:
            async with self.session.get(f"{self.base_url}/api/devices/{device_ip}") as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                else:
                    logger.error(f"Failed to get device {device_ip}: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error getting device {device_ip}: {e}")
            return None

    async def connect_devices(self, device_ips: List[str]) -> Optional[str]:
        """Connect to devices"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/devices/connect",
                json=device_ips
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('task_id')
                else:
                    logger.error(f"Failed to connect devices: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error connecting devices: {e}")
            return None

    async def deploy_config(self, device_ips: List[str], config: str, message: str = "Deployed from TUI") -> Optional[str]:
        """Deploy configuration to devices"""
        try:
            payload = {
                "device_ips": device_ips,
                "config": config,
                "message": message
            }

            async with self.session.post(
                f"{self.base_url}/api/config/deploy",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('task_id')
                else:
                    logger.error(f"Failed to deploy config: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error deploying config: {e}")
            return None

    async def rollback_config(self, device_ips: List[str], rollback_id: int = 1) -> Optional[str]:
        """Rollback configuration on devices"""
        try:
            payload = {
                "device_ips": device_ips,
                "rollback_id": rollback_id
            }

            async with self.session.post(
                f"{self.base_url}/api/config/rollback",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('task_id')
                else:
                    logger.error(f"Failed to rollback config: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error rolling back config: {e}")
            return None

    async def get_device_facts(self, device_ips: List[str]) -> Optional[str]:
        """Get facts from devices"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/devices/facts",
                json=device_ips
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('task_id')
                else:
                    logger.error(f"Failed to get device facts: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error getting device facts: {e}")
            return None

    async def ping_test(self, device_ips: List[str], target: str = "8.8.8.8") -> Optional[str]:
        """Run ping test from devices"""
        try:
            params = {"target": target}
            async with self.session.post(
                f"{self.base_url}/api/devices/ping",
                json=device_ips,
                params=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('task_id')
                else:
                    logger.error(f"Failed to run ping test: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error running ping test: {e}")
            return None

    async def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        try:
            async with self.session.get(f"{self.base_url}/api/tasks") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get tasks: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get specific task"""
        try:
            async with self.session.get(f"{self.base_url}/api/tasks/{task_id}") as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                else:
                    logger.error(f"Failed to get task {task_id}: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error getting task {task_id}: {e}")
            return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        try:
            async with self.session.post(f"{self.base_url}/api/tasks/{task_id}/cancel") as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error cancelling task {task_id}: {e}")
            return False

    async def send_message(self, message: str):
        """Send message to WebSocket server"""
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.send_text(message)
                return True
            return False

        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to API server"""
        return self.connected

    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.websocket is not None and not self.websocket.closed


class APIService:
    """High-level API service for TUI components"""

    def __init__(self):
        """Initialize the API service"""
        self.client = APIClient()
        self.status_check_interval = 30  # seconds
        self.status_task = None

    async def start(self) -> bool:
        """Start the API service"""
        try:
            # Connect to API server
            if not await self.client.connect():
                logger.error("Failed to connect to API server")
                return False

            # Connect to WebSocket
            client_id = f"tui_{int(datetime.now().timestamp())}"
            if not await self.client.connect_websocket(client_id):
                logger.error("Failed to connect to WebSocket")
                # Continue without WebSocket for basic functionality

            # Start status monitoring
            self.status_task = asyncio.create_task(self._monitor_status())

            logger.info("API service started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting API service: {e}")
            return False

    async def stop(self):
        """Stop the API service"""
        try:
            if self.status_task:
                self.status_task.cancel()
                try:
                    await self.status_task
                except asyncio.CancelledError:
                    pass

            await self.client.disconnect()
            logger.info("API service stopped")

        except Exception as e:
            logger.error(f"Error stopping API service: {e}")

    async def _monitor_status(self):
        """Monitor API server status"""
        while True:
            try:
                await asyncio.sleep(self.status_check_interval)

                # Check connection status
                if not self.client.is_connected():
                    logger.warning("Lost connection to API server, attempting to reconnect...")
                    if await self.client.connect():
                        logger.info("Reconnected to API server")
                    else:
                        logger.error("Failed to reconnect to API server")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in status monitoring: {e}")