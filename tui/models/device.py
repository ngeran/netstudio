"""
Device model for representing network devices in the TUI
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class Device:
    """Represents a network device"""

    # Core device information
    host_name: str
    ip_address: str
    vendor: str = "JUNIPER"
    platform: str = "UNKNOWN"

    # Connection information
    username: Optional[str] = None
    password: Optional[str] = None

    # Location/organization information
    location: Optional[str] = None
    device_type: str = "router"  # router, switch, firewall

    # Status information
    status: str = "unknown"  # unknown, reachable, unreachable, error
    last_check: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    # Additional metadata
    model: Optional[str] = None
    os_version: Optional[str] = None
    serial_number: Optional[str] = None
    uptime: Optional[str] = None

    # Connection details
    is_connected: bool = False
    connection_time: Optional[datetime] = None

    @classmethod
    def from_inventory_dict(cls, data: Dict[str, Any], location: str = "Unknown") -> 'Device':
        """Create Device instance from inventory dictionary"""
        return cls(
            host_name=data.get('host_name', 'Unknown'),
            ip_address=data.get('ip_address', ''),
            vendor=data.get('vendor', 'JUNIPER'),
            platform=data.get('platform', 'UNKNOWN'),
            username=data.get('username'),
            password=data.get('password'),
            location=location,
            device_type='switch' if 'EX' in data.get('platform', '') else 'router'
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Device to dictionary"""
        return {
            'host_name': self.host_name,
            'ip_address': self.ip_address,
            'vendor': self.vendor,
            'platform': self.platform,
            'username': self.username,
            'password': self.password,
            'location': self.location,
            'device_type': self.device_type,
            'status': self.status,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'model': self.model,
            'os_version': self.os_version,
            'serial_number': self.serial_number,
            'uptime': self.uptime,
            'is_connected': self.is_connected,
            'connection_time': self.connection_time.isoformat() if self.connection_time else None
        }

    def get_display_name(self) -> str:
        """Get device display name"""
        if self.host_name and self.host_name != 'Unknown':
            return f"{self.host_name} ({self.ip_address})"
        return self.ip_address

    def get_status_color(self) -> str:
        """Get status color for display"""
        status_colors = {
            'reachable': 'green',
            'unreachable': 'red',
            'error': 'red',
            'unknown': 'yellow',
            'connected': 'green',
            'disconnected': 'red'
        }
        return status_colors.get(self.status.lower(), 'white')

    def is_reachable(self) -> bool:
        """Check if device is reachable"""
        return self.status.lower() in ['reachable', 'connected']

    def update_status(self, status: str, message: Optional[str] = None):
        """Update device status"""
        self.status = status
        self.last_check = datetime.now()

        if status == 'reachable':
            self.last_seen = datetime.now()

    def mark_connected(self):
        """Mark device as connected"""
        self.is_connected = True
        self.connection_time = datetime.now()
        self.update_status('connected')

    def mark_disconnected(self):
        """Mark device as disconnected"""
        self.is_connected = False
        self.connection_time = None
        self.update_status('disconnected')