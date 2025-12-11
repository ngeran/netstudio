"""
FastAPI Backend for Network Automation TUI

Provides REST API and WebSocket endpoints for real-time device management.
Integrates with PyEZ for Juniper device operations.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# Add project root to path for imports
project_root = Path(__file__).parent.parent
import sys
sys.path.insert(0, str(project_root))

from api.services.device_manager import EnhancedDeviceManager
from api.services.task_manager import TaskManager, TaskStatus
from tui.services.inventory_service import InventoryService

# Phase 3 services
from phase3.services.jsnapy_service import JSNAPyService
from phase3.services.monitoring_service import MonitoringService
from phase3.services.topology_service import TopologyService
from phase3.services.reporting_service import ReportingService

# Phase 3 API endpoints
from phase3.api.endpoints.validation import router as validation_router
from phase3.api.endpoints.monitoring import router as monitoring_router
from phase3.api.endpoints.topology import router as topology_router
from phase3.api.endpoints.reports import router as reports_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Network Automation API",
    description="FastAPI backend for Network Automation TUI with PyEZ integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
device_manager = EnhancedDeviceManager()
task_manager = TaskManager()
inventory_service = InventoryService()

# Phase 3 services
jsnapy_service = JSNAPyService()
monitoring_service = MonitoringService()
topology_service = TopologyService()
reporting_service = ReportingService()


# Pydantic models for API
class DeviceResponse(BaseModel):
    """Device response model"""
    host_name: str
    ip_address: str
    vendor: str
    platform: str
    location: Optional[str] = None
    device_type: str
    status: str
    last_check: Optional[str] = None
    is_connected: bool = False


class ConfigDeploymentRequest(BaseModel):
    """Configuration deployment request"""
    device_ips: List[str]
    config: str = Field(..., description="Junos configuration to deploy")
    message: str = "Deployed from TUI"


class TaskCreateRequest(BaseModel):
    """Task creation request"""
    operation: str = Field(..., description="Operation to perform")
    device_ips: List[str] = Field(..., description="List of device IPs")
    description: Optional[str] = None
    config: Optional[str] = None
    rollback_id: Optional[int] = 1
    ping_target: Optional[str] = "8.8.8.8"


class TaskResponse(BaseModel):
    """Task response model"""
    task_id: str
    name: str
    description: str
    status: str
    device_count: int
    progress: int
    current_device: str
    message: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    devices_processed: int
    devices_succeeded: int
    devices_failed: int
    error: Optional[str] = None


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)

        for client_id in disconnected:
            self.disconnect(client_id)


connection_manager = ConnectionManager()


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Network Automation API - Phase 3",
        "version": "3.0.0",
        "status": "running",
        "phase": "3",
        "pyez_available": device_manager.connections is not None,
        "phase3_services": {
            "validation": "jsnapy_validation",
            "monitoring": "real_time_telemetry",
            "topology": "network_discovery",
            "reporting": "analytics_reports"
        },
        "endpoints": {
            "phase2": ["/api/devices", "/api/config", "/api/tasks"],
            "phase3": ["/api/validation", "/api/monitoring", "/api/topology", "/api/reports"]
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    stats = task_manager.get_statistics()
    monitoring_status = monitoring_service.get_monitoring_status()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "services": {
            "device_manager": "running",
            "task_manager": "running",
            "inventory_service": "running",
            "validation_service": "active",
            "monitoring_service": monitoring_status.get("status", "inactive"),
            "topology_service": "active",
            "reporting_service": "active"
        },
        "pyez_available": True,
        "monitoring": {
            "active_devices": monitoring_status["monitored_devices"],
            "collection_interval": monitoring_status["interval"],
            "monitoring_active": monitoring_status["active"]
        },
        "statistics": stats
    }


@app.get("/api/devices", response_model=List[DeviceResponse])
async def get_devices():
    """Get all devices from inventory"""
    try:
        devices = inventory_service.get_all_devices()
        return [
            DeviceResponse(
                host_name=device.host_name,
                ip_address=device.ip_address,
                vendor=device.vendor,
                platform=device.platform,
                location=device.location,
                device_type=device.device_type,
                status=device.status,
                last_check=device.last_check.isoformat() if device.last_check else None,
                is_connected=device.is_connected
            )
            for device in devices
        ]
    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/devices/{device_ip}")
async def get_device(device_ip: str):
    """Get specific device information"""
    try:
        device = inventory_service.get_device_by_ip(device_ip)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        facts = await device_manager.get_device_facts(device)
        return {
            "device": device.__dict__,
            "facts": facts
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_ip}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/devices/connect")
async def connect_devices(device_ips: List[str]):
    """Connect to multiple devices"""
    try:
        devices = []
        for ip in device_ips:
            device = inventory_service.get_device_by_ip(ip)
            if device:
                devices.append(device)

        if not devices:
            raise HTTPException(status_code=400, detail="No valid devices found")

        # Create connection task
        task_id = task_manager.create_task(
            name="Connect to Devices",
            description=f"Connecting to {len(devices)} devices",
            device_count=len(devices)
        )

        # Start background task
        await task_manager.start_task(
            task_id,
            device_manager,
            devices,
            "connect"
        )

        return {
            "task_id": task_id,
            "message": f"Connection task started for {len(devices)} devices",
            "devices": [d.ip_address for d in devices]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting to devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/deploy")
async def deploy_config(request: ConfigDeploymentRequest):
    """Deploy configuration to devices"""
    try:
        devices = []
        for ip in request.device_ips:
            device = inventory_service.get_device_by_ip(ip)
            if device:
                devices.append(device)

        if not devices:
            raise HTTPException(status_code=400, detail="No valid devices found")

        # Create deployment task
        task_id = task_manager.create_task(
            name="Deploy Configuration",
            description=f"Deploying config to {len(devices)} devices",
            device_count=len(devices)
        )

        # Start background task
        await task_manager.start_task(
            task_id,
            device_manager,
            devices,
            "deploy_config",
            config=request.config,
            message=request.message
        )

        return {
            "task_id": task_id,
            "message": f"Configuration deployment started for {len(devices)} devices",
            "devices": [d.ip_address for d in devices]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/rollback")
async def rollback_config(device_ips: List[str], rollback_id: int = 1):
    """Rollback configuration on devices"""
    try:
        devices = []
        for ip in device_ips:
            device = inventory_service.get_device_by_ip(ip)
            if device:
                devices.append(device)

        if not devices:
            raise HTTPException(status_code=400, detail="No valid devices found")

        # Create rollback task
        task_id = task_manager.create_task(
            name="Rollback Configuration",
            description=f"Rolling back config on {len(devices)} devices to {rollback_id}",
            device_count=len(devices)
        )

        # Start background task
        await task_manager.start_task(
            task_id,
            device_manager,
            devices,
            "rollback",
            rollback_id=rollback_id
        )

        return {
            "task_id": task_id,
            "message": f"Configuration rollback started for {len(devices)} devices",
            "rollback_id": rollback_id,
            "devices": [d.ip_address for d in devices]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks")
async def get_tasks():
    """Get all tasks"""
    try:
        tasks = task_manager.get_all_tasks()
        return [task.to_dict() for task in tasks]
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get specific task"""
    try:
        task = task_manager.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a running task"""
    try:
        success = await task_manager.cancel_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or not running")
        return {"message": f"Task {task_id} cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/devices/facts")
async def get_device_facts(device_ips: List[str]):
    """Get facts from multiple devices"""
    try:
        devices = []
        for ip in device_ips:
            device = inventory_service.get_device_by_ip(ip)
            if device:
                devices.append(device)

        if not devices:
            raise HTTPException(status_code=400, detail="No valid devices found")

        # Create facts task
        task_id = task_manager.create_task(
            name="Get Device Facts",
            description=f"Getting facts from {len(devices)} devices",
            device_count=len(devices)
        )

        # Start background task
        await task_manager.start_task(
            task_id,
            device_manager,
            devices,
            "get_facts"
        )

        return {
            "task_id": task_id,
            "message": f"Facts collection started for {len(devices)} devices",
            "devices": [d.ip_address for d in devices]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device facts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/devices/ping")
async def ping_test(device_ips: List[str], target: str = "8.8.8.8"):
    """Ping target from devices"""
    try:
        devices = []
        for ip in device_ips:
            device = inventory_service.get_device_by_ip(ip)
            if device:
                devices.append(device)

        if not devices:
            raise HTTPException(status_code=400, detail="No valid devices found")

        # Create ping test task
        task_id = task_manager.create_task(
            name="Ping Test",
            description=f"Ping {target} from {len(devices)} devices",
            device_count=len(devices)
        )

        # Start background task
        await task_manager.start_task(
            task_id,
            device_manager,
            devices,
            "ping_test",
            target=target
        )

        return {
            "task_id": task_id,
            "message": f"Ping test started from {len(devices)} devices to {target}",
            "target": target,
            "devices": [d.ip_address for d in devices]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running ping test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Include Phase 3 routers
app.include_router(validation_router)
app.include_router(monitoring_router)
app.include_router(topology_router)
app.include_router(reports_router)


# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await connection_manager.connect(websocket, client_id)
    task_manager.add_websocket_connection(websocket, client_id)

    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            logger.info(f"Received message from {client_id}: {data}")

            # Echo back for now (can handle client commands here)
            await connection_manager.send_message(f"Echo: {data}", client_id)

    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
        task_manager.remove_websocket_connection(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        connection_manager.disconnect(client_id)
        task_manager.remove_websocket_connection(client_id)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Network Automation API starting up...")
    logger.info(f"PyEZ available: True (system installation)")

    # Phase 3 services initialization
    logger.info("Initializing Phase 3 services...")
    logger.info("JSNAPy Validation Service: Ready")
    logger.info("Monitoring Service: Ready (real-time telemetry)")
    logger.info("Topology Service: Ready (network discovery)")
    logger.info("Reporting Service: Ready (analytics)")

    # Include Phase 3 routers
    logger.info("Including Phase 3 API endpoints:")
    logger.info("  - /api/validation/*")
    logger.info("  - /api/monitoring/*")
    logger.info("  - /api/topology/*")
    logger.info("  - /api/reports/*")

    logger.info("Network Automation API v3.0 ready for connections")
    logger.info("Phase 3 features enabled: Validation, Monitoring, Topology, Reporting")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Network Automation API shutting down...")
    device_manager.cleanup_connections()
    logger.info("API shutdown complete")


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )