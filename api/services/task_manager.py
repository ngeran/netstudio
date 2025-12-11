"""
Task Manager for Asynchronous Operations

Manages background tasks, progress tracking, and result storage.
Provides WebSocket communication for real-time updates.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import uuid
import json
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Task:
    """Represents an asynchronous task"""

    def __init__(
        self,
        task_id: str,
        name: str,
        description: str,
        device_count: int = 0
    ):
        self.task_id = task_id
        self.name = name
        self.description = description
        self.status = TaskStatus.PENDING
        self.device_count = device_count
        self.progress = 0
        self.current_device = ""
        self.message = "Task pending"
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.results: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.devices_processed = 0
        self.devices_succeeded = 0
        self.devices_failed = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'device_count': self.device_count,
            'progress': self.progress,
            'current_device': self.current_device,
            'message': self.message,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'devices_processed': self.devices_processed,
            'devices_succeeded': self.devices_succeeded,
            'devices_failed': self.devices_failed,
            'error': self.error,
            'results': self.results
        }


class TaskManager:
    """Manages asynchronous tasks with WebSocket support"""

    def __init__(self):
        """Initialize the task manager"""
        self.tasks: Dict[str, Task] = {}
        self.websocket_connections: Dict[str, Any] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}

    def create_task(
        self,
        name: str,
        description: str,
        device_count: int = 0
    ) -> str:
        """Create a new task and return its ID"""
        task_id = str(uuid.uuid4())
        task = Task(task_id, name, description, device_count)
        self.tasks[task_id] = task
        logger.info(f"Created task {task_id}: {name}")
        return task_id

    async def execute_task(
        self,
        task_id: str,
        device_manager,
        devices: List,
        operation: str,
        **kwargs
    ):
        """Execute a task on multiple devices"""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        try:
            # Mark task as running
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.message = f"Starting {operation} on {len(devices)} devices"

            # Notify WebSocket clients
            await self.notify_task_update(task)

            # Connect to devices in parallel
            if operation == "connect":
                connection_results = await device_manager.connect_to_devices(devices)
                task.results['connections'] = connection_results
                task.devices_succeeded = sum(1 for success in connection_results.values() if success)
                task.devices_failed = len(connection_results) - task.devices_succeeded

            elif operation == "deploy_config":
                # Deploy configuration to devices
                config = kwargs.get('config', '')
                if not config:
                    raise ValueError("Configuration required for deploy operation")

                deploy_results = {}
                for i, device in enumerate(devices):
                    task.current_device = device.ip_address
                    task.progress = int((i / len(devices)) * 100)
                    task.message = f"Deploying config to {device.ip_address}"
                    await self.notify_task_update(task)

                    result = await device_manager.deploy_configuration(device, config)
                    deploy_results[device.ip_address] = result
                    task.devices_processed += 1

                    if result['success']:
                        task.devices_succeeded += 1
                    else:
                        task.devices_failed += 1

                task.results['deployments'] = deploy_results

            elif operation == "get_facts":
                # Get facts from devices
                facts_results = {}
                for i, device in enumerate(devices):
                    task.current_device = device.ip_address
                    task.progress = int((i / len(devices)) * 100)
                    task.message = f"Getting facts from {device.ip_address}"
                    await self.notify_task_update(task)

                    result = await device_manager.get_device_facts(device)
                    facts_results[device.ip_address] = result
                    task.devices_processed += 1

                    if result['success']:
                        task.devices_succeeded += 1
                    else:
                        task.devices_failed += 1

                task.results['facts'] = facts_results

            elif operation == "rollback":
                # Rollback configurations
                rollback_id = kwargs.get('rollback_id', 1)
                rollback_results = {}
                for i, device in enumerate(devices):
                    task.current_device = device.ip_address
                    task.progress = int((i / len(devices)) * 100)
                    task.message = f"Rolling back config on {device.ip_address}"
                    await self.notify_task_update(task)

                    result = await device_manager.rollback_configuration(device, rollback_id)
                    rollback_results[device.ip_address] = result
                    task.devices_processed += 1

                    if result['success']:
                        task.devices_succeeded += 1
                    else:
                        task.devices_failed += 1

                task.results['rollbacks'] = rollback_results

            elif operation == "ping_test":
                # Test connectivity from devices
                target = kwargs.get('target', '8.8.8.8')
                ping_results = {}
                for i, device in enumerate(devices):
                    task.current_device = device.ip_address
                    task.progress = int((i / len(devices)) * 100)
                    task.message = f"Pinging {target} from {device.ip_address}"
                    await self.notify_task_update(task)

                    result = await device_manager.ping_from_device(device, target)
                    ping_results[device.ip_address] = result
                    task.devices_processed += 1

                    if result['success']:
                        task.devices_succeeded += 1
                    else:
                        task.devices_failed += 1

                task.results['pings'] = ping_results

            else:
                raise ValueError(f"Unknown operation: {operation}")

            # Mark task as completed
            task.status = TaskStatus.SUCCESS
            task.progress = 100
            task.message = f"{operation.capitalize()} completed: {task.devices_succeeded}/{len(devices)} successful"
            task.completed_at = datetime.now()

        except Exception as e:
            # Mark task as failed
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.message = f"Task failed: {str(e)}"
            task.completed_at = datetime.now()
            logger.error(f"Task {task_id} failed: {e}")

        finally:
            # Notify final update
            await self.notify_task_update(task)

            # Clean up from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    async def start_task(
        self,
        task_id: str,
        device_manager,
        devices: List,
        operation: str,
        **kwargs
    ) -> bool:
        """Start a task in the background"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        # Create background task
        background_task = asyncio.create_task(
            self.execute_task(task_id, device_manager, devices, operation, **kwargs)
        )
        self.active_tasks[task_id] = background_task

        logger.info(f"Started task {task_id} in background")
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.cancel()
            del self.active_tasks[task_id]

            # Update task status
            if task_id in self.tasks:
                self.tasks[task_id].status = TaskStatus.CANCELLED
                self.tasks[task_id].completed_at = datetime.now()
                await self.notify_task_update(self.tasks[task_id])

            logger.info(f"Cancelled task {task_id}")
            return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks"""
        return list(self.tasks.values())

    def get_active_tasks(self) -> List[Task]:
        """Get all active tasks"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.RUNNING]

    def add_websocket_connection(self, websocket, connection_id: str):
        """Add a WebSocket connection for updates"""
        self.websocket_connections[connection_id] = websocket
        logger.info(f"Added WebSocket connection {connection_id}")

    def remove_websocket_connection(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.websocket_connections:
            del self.websocket_connections[connection_id]
            logger.info(f"Removed WebSocket connection {connection_id}")

    async def notify_task_update(self, task: Task):
        """Send task update to all WebSocket connections"""
        message = {
            'type': 'task_update',
            'task': task.to_dict()
        }

        # Send to all connected clients
        disconnected = []
        for connection_id, websocket in self.websocket_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send update to {connection_id}: {e}")
                disconnected.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected:
            self.remove_websocket_connection(connection_id)

    async def send_log_message(self, task_id: str, message: str, level: str = "info"):
        """Send a log message for a task"""
        log_message = {
            'type': 'log_message',
            'task_id': task_id,
            'level': level,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }

        # Send to all connected clients
        disconnected = []
        for connection_id, websocket in self.websocket_connections.items():
            try:
                await websocket.send_text(json.dumps(log_message))
            except Exception as e:
                logger.warning(f"Failed to send log to {connection_id}: {e}")
                disconnected.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected:
            self.remove_websocket_connection(connection_id)

    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed tasks"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task.completed_at and task.completed_at < cutoff_time):
                to_remove.append(task_id)

        for task_id in to_remove:
            del self.tasks[task_id]
            logger.info(f"Cleaned up old task {task_id}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get task manager statistics"""
        all_tasks = list(self.tasks.values())
        active_tasks = [t for t in all_tasks if t.status == TaskStatus.RUNNING]

        return {
            'total_tasks': len(all_tasks),
            'active_tasks': len(active_tasks),
            'websocket_connections': len(self.websocket_connections),
            'tasks_by_status': {
                status.value: len([t for t in all_tasks if t.status == status])
                for status in TaskStatus
            }
        }