"""
Monitoring API Endpoints

REST API endpoints for network monitoring, metrics collection, and alerting.
Provides real-time telemetry and historical data access.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# Import Phase 3 services
from phase3.services.monitoring_service import (
    MonitoringService, InterfaceMetric, BgpMetric, SystemMetric, Alert
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

# Global service instance (in production, would use dependency injection)
monitoring_service = MonitoringService()

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time monitoring updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        import json
        message_str = json.dumps(message, default=str)

        # Create a list of connections to remove if they fail
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Failed to send broadcast message: {e}")
                to_remove.append(connection)

        # Remove failed connections
        for connection in to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

# Global connection manager
connection_manager = ConnectionManager()

# Register WebSocket callback with monitoring service
async def websocket_callback(message: Dict[str, Any]):
    """Callback for monitoring service to send WebSocket updates"""
    await connection_manager.broadcast(message)

monitoring_service.register_websocket_callback(websocket_callback)


# Pydantic models for API
class DeviceRegistrationRequest(BaseModel):
    """Request model for device registration"""
    device_info: Dict[str, Any] = Field(..., description="Device connection information")


class MonitoringConfigRequest(BaseModel):
    """Request model for monitoring configuration"""
    interval: int = Field(60, description="Monitoring interval in seconds")
    thresholds: Optional[Dict[str, float]] = Field(None, description="Alert thresholds")


class AlertAckRequest(BaseModel):
    """Request model for alert acknowledgment"""
    acknowledged_by: str = Field(..., description="User acknowledging the alert")


class MetricsResponse(BaseModel):
    """Response model for device metrics"""
    device_id: str
    system_metrics: Optional[List[Dict[str, Any]]] = None
    interface_metrics: Optional[List[Dict[str, Any]]] = None
    bgp_metrics: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime


class AlertResponse(BaseModel):
    """Response model for alert information"""
    alert_id: str
    device_id: str
    metric_type: str
    severity: str
    title: str
    message: str
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None


# WebSocket endpoint for real-time updates
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time monitoring updates"""
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # Echo back or handle incoming messages if needed
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)


@router.post("/devices/register")
async def register_device(request: DeviceRegistrationRequest):
    """Register a device for monitoring"""
    try:
        monitoring_service.add_device(request.device_info)

        return {
            "status": "success",
            "message": f"Device {request.device_info.get('host_ip')} registered for monitoring",
            "device_id": request.device_info.get('host_ip')
        }

    except Exception as e:
        logger.error(f"Failed to register device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/devices/{device_id}")
async def unregister_device(device_id: str):
    """Unregister a device from monitoring"""
    try:
        monitoring_service.remove_device(device_id)

        return {
            "status": "success",
            "message": f"Device {device_id} unregistered from monitoring"
        }

    except Exception as e:
        logger.error(f"Failed to unregister device: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_monitoring(request: MonitoringConfigRequest):
    """Start monitoring service"""
    try:
        monitoring_service.start_monitoring(interval=request.interval)

        # Update thresholds if provided
        if request.thresholds:
            monitoring_service.update_thresholds(request.thresholds)

        return {
            "status": "success",
            "message": "Monitoring started",
            "interval": request.interval,
            "monitored_devices": monitoring_service.get_monitoring_status()['monitored_devices']
        }

    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_monitoring():
    """Stop monitoring service"""
    try:
        monitoring_service.stop_monitoring()

        return {
            "status": "success",
            "message": "Monitoring stopped"
        }

    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_monitoring_status():
    """Get current monitoring service status"""
    try:
        status = monitoring_service.get_monitoring_status()
        return status

    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/metrics", response_model=MetricsResponse)
async def get_device_metrics(device_id: str):
    """Get current metrics for a specific device"""
    try:
        metrics_data = monitoring_service.get_current_metrics(device_id)

        return MetricsResponse(
            device_id=device_id,
            system_metrics=[dict(metrics_data['system'])] if metrics_data['system'] else None,
            interface_metrics=[dict(row) for row in metrics_data['interfaces']] if metrics_data['interfaces'] else None,
            bgp_metrics=[dict(row) for row in metrics_data['bgp']] if metrics_data['bgp'] else None,
            timestamp=datetime.now()
        )

    except Exception as e:
        logger.error(f"Failed to get device metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/metrics/historical")
async def get_historical_metrics(
    device_id: str,
    metric_type: str,
    start_time: datetime,
    end_time: datetime
):
    """Get historical metrics for a device"""
    try:
        metrics = monitoring_service.get_historical_metrics(
            device_id=device_id,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "device_id": device_id,
            "metric_type": metric_type,
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "data_points": len(metrics),
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Failed to get historical metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts", response_model=List[AlertResponse])
async def get_active_alerts(device_id: Optional[str] = None):
    """Get active (unacknowledged) alerts"""
    try:
        alerts_data = monitoring_service.get_active_alerts(device_id)

        alert_responses = []
        for alert_data in alerts_data:
            alert_response = AlertResponse(
                alert_id=alert_data['alert_id'],
                device_id=alert_data['device_id'],
                metric_type=alert_data['metric_type'],
                severity=alert_data['severity'],
                title=alert_data['title'],
                message=alert_data['message'],
                current_value=alert_data.get('current_value'),
                threshold_value=alert_data.get('threshold_value'),
                timestamp=datetime.fromisoformat(alert_data['timestamp']),
                acknowledged=alert_data['acknowledged'],
                acknowledged_by=alert_data.get('acknowledged_by')
            )
            alert_responses.append(alert_response)

        return alert_responses

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, request: AlertAckRequest):
    """Acknowledge an alert"""
    try:
        success = await monitoring_service.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=request.acknowledged_by
        )

        if success:
            return {
                "status": "success",
                "message": f"Alert {alert_id} acknowledged by {request.acknowledged_by}",
                "alert_id": alert_id
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Alert {alert_id} not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard summary data"""
    try:
        # Get current monitoring status
        status = monitoring_service.get_monitoring_status()

        # Get active alerts
        alerts = monitoring_service.get_active_alerts()

        # Calculate alert statistics
        total_alerts = len(alerts)
        critical_alerts = len([a for a in alerts if a['severity'] == 'critical'])
        warning_alerts = len([a for a in alerts if a['severity'] == 'warning'])

        # Get device counts
        monitored_devices = status['monitored_devices']

        # Mock device health data (would come from actual metrics)
        import random
        device_health = []
        for device_id in monitored_devices:
            health = {
                'device_id': device_id,
                'health_score': random.randint(70, 100),
                'cpu_usage': random.uniform(10, 80),
                'memory_usage': random.uniform(20, 90),
                'interface_status': 'up' if random.random() > 0.1 else 'down'
            }
            device_health.append(health)

        return {
            "monitoring_status": {
                "active": status['active'],
                "monitored_devices": len(monitored_devices),
                "collection_interval": status['interval']
            },
            "alert_summary": {
                "total_alerts": total_alerts,
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "unacknowledged_alerts": len([a for a in alerts if not a['acknowledged']])
            },
            "device_health": device_health,
            "system_thresholds": status['thresholds']
        }

    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/thresholds")
async def update_thresholds(thresholds: Dict[str, float]):
    """Update monitoring thresholds"""
    try:
        monitoring_service.update_thresholds(thresholds)

        return {
            "status": "success",
            "message": "Monitoring thresholds updated",
            "updated_thresholds": thresholds
        }

    except Exception as e:
        logger.error(f"Failed to update thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}/health")
async def get_device_health_summary(device_id: str):
    """Get health summary for a specific device"""
    try:
        # Get current metrics
        current_metrics = monitoring_service.get_current_metrics(device_id)

        # Get recent alerts for this device
        device_alerts = monitoring_service.get_active_alerts(device_id)

        # Calculate health score (simplified)
        health_score = 100
        issues = []

        # Check for alerts
        if device_alerts:
            critical_alerts = len([a for a in device_alerts if a['severity'] == 'critical'])
            warning_alerts = len([a for a in device_alerts if a['severity'] == 'warning'])

            health_score -= (critical_alerts * 20) + (warning_alerts * 10)
            issues.extend([f"{a['severity']}: {a['title']}" for a in device_alerts[:5]])

        # Check system metrics
        if current_metrics['system']:
            system_data = current_metrics['system']
            memory_usage = system_data[3] if len(system_data) > 3 else 0  # memory_usage index
            memory_total = system_data[4] if len(system_data) > 4 else 1  # memory_total index
            memory_percent = (memory_usage / memory_total * 100) if memory_total > 0 else 0

            if memory_percent > 90:
                health_score -= 15
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            elif memory_percent > 80:
                health_score -= 5
                issues.append(f"Elevated memory usage: {memory_percent:.1f}%")

        # Check interface status
        if current_metrics['interfaces']:
            down_interfaces = len([
                iface for iface in current_metrics['interfaces']
                if iface[2] == 'down'  # status index
            ])

            if down_interfaces > 0:
                health_score -= (down_interfaces * 10)
                issues.append(f"{down_interfaces} interfaces down")

        health_score = max(0, health_score)  # Ensure score doesn't go negative

        return {
            "device_id": device_id,
            "health_score": health_score,
            "status": "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical",
            "issues": issues,
            "active_alerts": len(device_alerts),
            "last_checked": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get device health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function to get monitoring service (for dependency injection)
def get_monitoring_service() -> MonitoringService:
    """Dependency injection for monitoring service"""
    return monitoring_service