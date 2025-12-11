"""
Inventory service for managing device inventory
"""

import yaml
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import subprocess
import platform

from tui.models.device import Device

logger = logging.getLogger(__name__)


class InventoryService:
    """Service for managing device inventory"""

    def __init__(self, inventory_path: Optional[str] = None):
        """Initialize inventory service"""
        if inventory_path is None:
            # Default to project root data directory
            project_root = Path(__file__).parent.parent.parent
            inventory_path = project_root / "data" / "inventory.yml"

        self.inventory_path = Path(inventory_path)
        self.devices: List[Device] = []
        self.last_loaded: Optional[datetime] = None

    def load_devices(self) -> List[Device]:
        """Load devices from inventory file"""
        try:
            if not self.inventory_path.exists():
                logger.error(f"Inventory file not found: {self.inventory_path}")
                return []

            with open(self.inventory_path, 'r') as f:
                inventory_data = yaml.safe_load(f)

            self.devices = []

            if 'inventory' in inventory_data:
                for location_data in inventory_data['inventory']:
                    location = location_data.get('location', 'Unknown')

                    # Process routers
                    if 'routers' in location_data:
                        for router_data in location_data['routers']:
                            device = Device.from_inventory_dict(router_data, location)
                            device.device_type = 'router'
                            self.devices.append(device)

                    # Process switches
                    if 'switches' in location_data:
                        for switch_data in location_data['switches']:
                            device = Device.from_inventory_dict(switch_data, location)
                            device.device_type = 'switch'
                            self.devices.append(device)

            self.last_loaded = datetime.now()
            logger.info(f"Loaded {len(self.devices)} devices from inventory")
            return self.devices

        except Exception as e:
            logger.error(f"Failed to load inventory: {e}")
            return []

    def get_all_devices(self) -> List[Device]:
        """Get all devices"""
        if not self.devices:
            self.load_devices()
        return self.devices

    def get_devices_by_type(self, device_type: str) -> List[Device]:
        """Get devices filtered by type"""
        return [d for d in self.get_all_devices() if d.device_type == device_type]

    def get_devices_by_location(self, location: str) -> List[Device]:
        """Get devices filtered by location"""
        return [d for d in self.get_all_devices() if d.location == location]

    def get_device_by_ip(self, ip_address: str) -> Optional[Device]:
        """Get device by IP address"""
        for device in self.get_all_devices():
            if device.ip_address == ip_address:
                return device
        return None

    def get_device_by_name(self, host_name: str) -> Optional[Device]:
        """Get device by hostname"""
        for device in self.get_all_devices():
            if device.host_name == host_name:
                return device
        return None

    def test_device_connectivity(self, device: Device) -> bool:
        """Test connectivity to a device using ping"""
        try:
            # Use different ping commands based on OS
            if platform.system().lower() == 'windows':
                cmd = ['ping', '-n', '1', '-w', '2000', device.ip_address]
            else:
                cmd = ['ping', '-c', '1', '-W', '2', device.ip_address]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            is_reachable = result.returncode == 0
            device.update_status('reachable' if is_reachable else 'unreachable')

            return is_reachable

        except subprocess.TimeoutExpired:
            device.update_status('unreachable')
            return False
        except Exception as e:
            logger.error(f"Error testing connectivity to {device.ip_address}: {e}")
            device.update_status('error')
            return False

    def test_all_devices(self) -> Dict[str, bool]:
        """Test connectivity to all devices"""
        results = {}
        devices = self.get_all_devices()

        for device in devices:
            results[device.ip_address] = self.test_device_connectivity(device)

        return results

    def get_device_count_by_type(self) -> Dict[str, int]:
        """Get device counts by type"""
        devices = self.get_all_devices()
        counts = {}

        for device in devices:
            counts[device.device_type] = counts.get(device.device_type, 0) + 1

        return counts

    def get_device_count_by_location(self) -> Dict[str, int]:
        """Get device counts by location"""
        devices = self.get_all_devices()
        counts = {}

        for device in devices:
            location = device.location or 'Unknown'
            counts[location] = counts.get(location, 0) + 1

        return counts

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about the inventory"""
        devices = self.get_all_devices()

        # Test connectivity if needed
        reachable_count = sum(1 for d in devices if d.is_reachable())

        return {
            'total_devices': len(devices),
            'reachable_devices': reachable_count,
            'unreachable_devices': len(devices) - reachable_count,
            'by_type': self.get_device_count_by_type(),
            'by_location': self.get_device_count_by_location(),
            'last_loaded': self.last_loaded.isoformat() if self.last_loaded else None
        }

    def save_device(self, device: Device) -> bool:
        """Save a device to inventory (placeholder for future implementation)"""
        # This would update the inventory file
        # For now, just add to in-memory list
        if device not in self.devices:
            self.devices.append(device)
            return True
        return False

    def refresh_inventory(self) -> List[Device]:
        """Refresh the inventory from file"""
        self.devices = []
        return self.load_devices()