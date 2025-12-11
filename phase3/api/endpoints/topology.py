"""
Topology API Endpoints

REST API endpoints for network topology discovery, visualization, and analysis.
Provides network mapping and connectivity information.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Import Phase 3 services
from phase3.services.topology_service import (
    TopologyService, TopologyData, NetworkNode, NetworkLink
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/topology", tags=["topology"])

# Global service instance (in production, would use dependency injection)
topology_service = TopologyService()

# Pydantic models for API
class TopologyDiscoveryRequest(BaseModel):
    """Request model for topology discovery"""
    seed_devices: List[Dict[str, Any]] = Field(..., description="Seed devices for discovery")
    discovery_method: str = Field("auto", description="Discovery method to use")
    max_depth: Optional[int] = Field(5, description="Maximum discovery depth")


class TopologyDiscoveryResponse(BaseModel):
    """Response model for topology discovery"""
    topology_id: str
    discovery_time: datetime
    total_nodes: int
    total_links: int
    discovery_method: str
    metadata: Dict[str, Any]
    status: str


class NetworkNodeResponse(BaseModel):
    """Response model for network node"""
    device_id: str
    hostname: str
    device_type: str
    vendor: str
    model: str
    os_version: str
    management_ip: str
    site: Optional[str] = None
    role: Optional[str] = None
    coordinates: Optional[List[float]] = None


class NetworkLinkResponse(BaseModel):
    """Response model for network link"""
    source_device: str
    source_interface: str
    destination_device: str
    destination_interface: str
    link_type: str
    bandwidth: Optional[int] = None
    status: str = "unknown"
    protocol: Optional[str] = None


class TopologyDataResponse(BaseModel):
    """Response model for complete topology data"""
    topology_id: str
    nodes: List[NetworkNodeResponse]
    links: List[NetworkLinkResponse]
    discovery_time: datetime
    discovery_method: str
    metadata: Dict[str, Any]


# Background task for topology discovery
async def discover_topology_background(request: TopologyDiscoveryRequest):
    """Background task to discover topology"""
    try:
        topology = await topology_service.discover_topology(
            seed_devices=request.seed_devices,
            discovery_method=request.discovery_method
        )
        logger.info(f"Background topology discovery completed: {topology.topology_id}")
        return topology
    except Exception as e:
        logger.error(f"Background topology discovery failed: {e}")
        raise


@router.post("/discover", response_model=TopologyDiscoveryResponse)
async def start_topology_discovery(request: TopologyDiscoveryRequest, background_tasks: BackgroundTasks):
    """Start network topology discovery (runs in background)"""
    try:
        # Validate seed devices
        if not request.seed_devices:
            raise HTTPException(
                status_code=400,
                detail="At least one seed device is required"
            )

        # Start topology discovery in background
        background_tasks.add_task(discover_topology_background, request)

        # Return immediate response
        return TopologyDiscoveryResponse(
            topology_id="discovering",
            discovery_time=datetime.now(),
            total_nodes=0,
            total_links=0,
            discovery_method=request.discovery_method,
            metadata={"status": "discovery_started"},
            status="running"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start topology discovery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}", response_model=TopologyDataResponse)
async def get_topology(topology_id: Optional[str] = None):
    """Get topology data"""
    try:
        topology = topology_service.get_topology(topology_id)

        if not topology:
            raise HTTPException(
                status_code=404,
                detail=f"Topology {topology_id or 'latest'} not found"
            )

        # Convert nodes to response format
        nodes = []
        for node in topology.nodes:
            node_response = NetworkNodeResponse(
                device_id=node.device_id,
                hostname=node.hostname,
                device_type=node.device_type,
                vendor=node.vendor,
                model=node.model,
                os_version=node.os_version,
                management_ip=node.management_ip,
                site=node.site,
                role=node.role,
                coordinates=list(node.coordinates) if node.coordinates else None
            )
            nodes.append(node_response)

        # Convert links to response format
        links = []
        for link in topology.links:
            link_response = NetworkLinkResponse(
                source_device=link.source_device,
                source_interface=link.source_interface,
                destination_device=link.destination_device,
                destination_interface=link.destination_interface,
                link_type=link.link_type,
                bandwidth=link.bandwidth,
                status=link.status,
                protocol=link.protocol
            )
            links.append(link_response)

        return TopologyDataResponse(
            topology_id=topology.topology_id,
            nodes=nodes,
            links=links,
            discovery_time=topology.discovery_time,
            discovery_method=topology.discovery_method,
            metadata=topology.metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/summary")
async def get_topology_summary(topology_id: Optional[str] = None):
    """Get topology summary statistics"""
    try:
        summary = topology_service.get_topology_summary()

        if not summary and topology_id:
            # Try to load specific topology
            topology = topology_service.get_topology(topology_id)
            if topology:
                summary = {
                    'topology_id': topology.topology_id,
                    'discovery_time': topology.discovery_time.isoformat(),
                    'total_nodes': len(topology.nodes),
                    'total_links': len(topology.links)
                }

        if not summary:
            raise HTTPException(
                status_code=404,
                detail="No topology data available"
            )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get topology summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/path/{source_device}/{destination_device}")
async def get_device_path(
    topology_id: Optional[str] = None,
    source_device: str = "",
    destination_device: str = ""
):
    """Get path between two devices"""
    try:
        path = topology_service.get_device_path(source_device, destination_device)

        if not path:
            return {
                "source_device": source_device,
                "destination_device": destination_device,
                "path": [],
                "path_found": False,
                "message": "No path found between devices"
            }

        return {
            "source_device": source_device,
            "destination_device": destination_device,
            "path": path,
            "path_found": True,
            "hop_count": len(path) - 1,
            "topology_id": topology_id
        }

    except Exception as e:
        logger.error(f"Failed to get device path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/neighbors/{device_id}")
async def get_device_neighbors(
    topology_id: Optional[str] = None,
    device_id: str = "",
    depth: int = 1
):
    """Get neighboring devices within specified depth"""
    try:
        neighbors = topology_service.get_device_neighbors(device_id, depth)

        return {
            "device_id": device_id,
            "depth": depth,
            "neighbors": neighbors,
            "neighbor_count": len(neighbors),
            "topology_id": topology_id
        }

    except Exception as e:
        logger.error(f"Failed to get device neighbors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/critical-devices")
async def get_critical_devices(topology_id: Optional[str] = None):
    """Get critical devices based on network centrality"""
    try:
        critical_devices = topology_service.find_critical_devices()

        return {
            "critical_devices": critical_devices,
            "count": len(critical_devices),
            "analysis_method": "betweenness_centrality",
            "topology_id": topology_id
        }

    except Exception as e:
        logger.error(f"Failed to get critical devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/export/{format}")
async def export_topology(
    topology_id: Optional[str] = None,
    format: str = "json"
):
    """Export topology to various formats"""
    try:
        if format not in ["json", "graphml", "gexf"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {format}"
            )

        # Get topology data
        topology = topology_service.get_topology(topology_id)
        if not topology:
            raise HTTPException(
                status_code=404,
                detail=f"Topology {topology_id or 'latest'} not found"
            )

        # Export topology
        try:
            filepath = topology_service.export_topology(format)
            filename = f"topology_{topology.topology_id}.{format}"

            return FileResponse(
                filepath,
                filename=filename,
                media_type="application/octet-stream"
            )

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export topology: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_topology_history(limit: int = 10):
    """Get topology discovery history"""
    try:
        history = topology_service.get_topology_history(limit)

        return {
            "history": history,
            "total": len(history),
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Failed to get topology history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/visualization-data")
async def get_visualization_data(topology_id: Optional[str] = None):
    """Get topology data formatted for visualization libraries"""
    try:
        topology = topology_service.get_topology(topology_id)

        if not topology:
            raise HTTPException(
                status_code=404,
                detail=f"Topology {topology_id or 'latest'} not found"
            )

        # Format for D3.js or similar visualization libraries
        nodes = []
        for node in topology.nodes:
            node_data = {
                "id": node.device_id,
                "label": node.hostname,
                "group": node.device_type,
                "site": node.site or "unknown",
                "role": node.role or "unknown",
                "x": node.coordinates[0] if node.coordinates else None,
                "y": node.coordinates[1] if node.coordinates else None,
                "properties": {
                    "vendor": node.vendor,
                    "model": node.model,
                    "os_version": node.os_version,
                    "management_ip": node.management_ip
                }
            }
            nodes.append(node_data)

        links = []
        for link in topology.links:
            link_data = {
                "source": link.source_device,
                "target": link.destination_device,
                "type": link.link_type,
                "bandwidth": link.bandwidth,
                "status": link.status,
                "protocol": link.protocol,
                "properties": {
                    "source_interface": link.source_interface,
                    "destination_interface": link.destination_interface
                }
            }
            links.append(link_data)

        return {
            "topology_id": topology.topology_id,
            "discovery_time": topology.discovery_time.isoformat(),
            "metadata": topology.metadata,
            "graph": {
                "nodes": nodes,
                "links": links
            },
            "statistics": {
                "total_nodes": len(nodes),
                "total_links": len(links),
                "node_types": list(set(n["group"] for n in nodes)),
                "link_types": list(set(l["type"] for l in links))
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/site-analysis")
async def get_site_analysis(topology_id: Optional[str] = None):
    """Analyze topology by sites/locations"""
    try:
        topology = topology_service.get_topology(topology_id)

        if not topology:
            raise HTTPException(
                status_code=404,
                detail=f"Topology {topology_id or 'latest'} not found"
            )

        # Group nodes by site
        site_analysis = {}
        for node in topology.nodes:
            site = node.site or "unknown"
            if site not in site_analysis:
                site_analysis[site] = {
                    "device_count": 0,
                    "device_types": {},
                    "nodes": []
                }

            site_analysis[site]["device_count"] += 1
            device_type = node.device_type
            site_analysis[site]["device_types"][device_type] = site_analysis[site]["device_types"].get(device_type, 0) + 1
            site_analysis[site]["nodes"].append({
                "device_id": node.device_id,
                "hostname": node.hostname,
                "device_type": node.device_type,
                "role": node.role
            })

        # Analyze inter-site connections
        inter_site_links = []
        for link in topology.links:
            source_node = next((n for n in topology.nodes if n.device_id == link.source_device), None)
            dest_node = next((n for n in topology.nodes if n.device_id == link.destination_device), None)

            if source_node and dest_node and source_node.site != dest_node:
                inter_site_links.append({
                    "source_site": source_node.site,
                    "destination_site": dest_node.site,
                    "link_type": link.link_type,
                    "bandwidth": link.bandwidth
                })

        return {
            "topology_id": topology.topology_id,
            "site_analysis": site_analysis,
            "inter_site_connections": inter_site_links,
            "total_sites": len(site_analysis),
            "isolated_sites": [
                site for site, data in site_analysis.items()
                if not any(link["source_site"] == site or link["destination_site"] == site for link in inter_site_links)
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get site analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topology_id}/device-details/{device_id}")
async def get_device_details(topology_id: Optional[str] = None, device_id: str = ""):
    """Get detailed information about a specific device"""
    try:
        topology = topology_service.get_topology(topology_id)

        if not topology:
            raise HTTPException(
                status_code=404,
                detail=f"Topology {topology_id or 'latest'} not found"
            )

        # Find device
        device = next((n for n in topology.nodes if n.device_id == device_id), None)
        if not device:
            raise HTTPException(
                status_code=404,
                detail=f"Device {device_id} not found in topology"
            )

        # Find device connections
        connections = []
        for link in topology.links:
            if link.source_device == device_id:
                connections.append({
                    "remote_device": link.destination_device,
                    "remote_interface": link.destination_interface,
                    "local_interface": link.source_interface,
                    "link_type": link.link_type,
                    "bandwidth": link.bandwidth,
                    "status": link.status,
                    "direction": "outbound"
                })
            elif link.destination_device == device_id:
                connections.append({
                    "remote_device": link.source_device,
                    "remote_interface": link.source_interface,
                    "local_interface": link.destination_interface,
                    "link_type": link.link_type,
                    "bandwidth": link.bandwidth,
                    "status": link.status,
                    "direction": "inbound"
                })

        return {
            "device": {
                "device_id": device.device_id,
                "hostname": device.hostname,
                "device_type": device.device_type,
                "vendor": device.vendor,
                "model": device.model,
                "os_version": device.os_version,
                "management_ip": device.management_ip,
                "site": device.site,
                "role": device.role,
                "coordinates": list(device.coordinates) if device.coordinates else None
            },
            "connections": connections,
            "connection_count": len(connections),
            "topology_id": topology.topology_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get device details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function to get topology service (for dependency injection)
def get_topology_service() -> TopologyService:
    """Dependency injection for topology service"""
    return topology_service