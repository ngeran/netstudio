"""
Enhanced Device Manager with PyEZ Integration

This service provides device management capabilities using Juniper PyEZ
for real network device operations.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import json
import subprocess
import platform

# Try to import PyEZ from system installation
try:
    from jnpr.junos import Device
    from jnpr.junos.utils.config import Config
    from jnpr.junos.exception import ConnectError, ConfigLoadError, CommitError, RpcError
    PYEZ_AVAILABLE = True
except ImportError:
    PYEZ_AVAILABLE = False
    print("Warning: PyEZ not available, using mock implementation")

from tui.models.device import Device

logger = logging.getLogger(__name__)


class EnhancedDeviceManager:
    """Enhanced device manager with PyEZ integration"""

    def __init__(self):
        """Initialize the device manager"""
        self.connections: Dict[str, Device] = {}
        self.connection_pool = asyncio.Semaphore(10)  # Limit concurrent connections

    async def connect_to_device(self, device: Device) -> bool:
        """Connect to a single device using PyEZ"""
        if not PYEZ_AVAILABLE:
            logger.warning("PyEZ not available, using mock connection")
            device.mark_connected()
            return True

        try:
            async with self.connection_pool:
                logger.info(f"Connecting to {device.ip_address}...")

                # Create PyEZ Device object
                dev = Device(
                    host=device.ip_address,
                    user=device.username,
                    password=device.password,
                    port=22,
                    timeout=30
                )

                # Connect to device
                dev.open()
                self.connections[device.ip_address] = dev

                # Update device info
                device.mark_connected()
                device.hostname = dev.hostname
                device.model = getattr(dev, 'facts', {}).get('model', 'Unknown')
                device.os_version = getattr(dev, 'facts', {}).get('version', 'Unknown')
                device.serial_number = getattr(dev, 'facts', {}).get('serial_number', 'Unknown')

                logger.info(f"Successfully connected to {device.ip_address}")
                return True

        except ConnectError as e:
            logger.error(f"Failed to connect to {device.ip_address}: {e}")
            device.status = "connection_failed"
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to {device.ip_address}: {e}")
            device.status = "error"
            return False

    async def connect_to_devices(self, devices: List[Device]) -> Dict[str, bool]:
        """Connect to multiple devices in parallel"""
        if not PYEZ_AVAILABLE:
            logger.warning("PyEZ not available, using mock connections")
            results = {}
            for device in devices:
                device.mark_connected()
                results[device.ip_address] = True
            return results

        # Create connection tasks
        tasks = [self.connect_to_device(device) for device in devices]

        # Wait for all connections to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map results to device IPs
        device_results = {}
        for i, device in enumerate(devices):
            device_results[device.ip_address] = isinstance(results[i], bool) and results[i]

        return device_results

    async def disconnect_from_device(self, device: Device):
        """Disconnect from a single device"""
        if device.ip_address in self.connections:
            try:
                dev = self.connections[device.ip_address]
                dev.close()
                del self.connections[device.ip_address]
                device.mark_disconnected()
                logger.info(f"Disconnected from {device.ip_address}")
            except Exception as e:
                logger.error(f"Error disconnecting from {device.ip_address}: {e}")

    async def disconnect_from_devices(self, devices: List[Device]):
        """Disconnect from multiple devices"""
        tasks = [self.disconnect_from_device(device) for device in devices]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def deploy_configuration(self, device: Device, config: str, message: str = "TUI Configuration") -> Dict[str, Any]:
        """Deploy configuration to a device"""
        result = {
            'device': device.ip_address,
            'success': False,
            'message': '',
            'config_diff': '',
            'timestamp': datetime.now().isoformat()
        }

        if not PYEZ_AVAILABLE:
            logger.warning("PyEZ not available, mocking config deployment")
            result['success'] = True
            result['message'] = 'Configuration deployed successfully (mock)'
            return result

        try:
            if device.ip_address not in self.connections:
                # Connect if not connected
                await self.connect_to_device(device)

            dev = self.connections[device.ip_address]

            with Config(dev, mode='exclusive') as cu:
                # Load configuration
                cu.load(config, format='text')

                # Show diff (commented out for now as it requires exclusive mode)
                # diff = cu.diff()
                # result['config_diff'] = diff

                # Commit configuration
                cu.commit(comment=message)

            result['success'] = True
            result['message'] = f'Configuration deployed successfully to {device.ip_address}'
            logger.info(f"Configuration deployed to {device.ip_address}")

        except ConfigLoadError as e:
            result['message'] = f'Configuration load error: {str(e)}'
            logger.error(f"Config load error on {device.ip_address}: {e}")
        except CommitError as e:
            result['message'] = f'Configuration commit error: {str(e)}'
            logger.error(f"Commit error on {device.ip_address}: {e}")
        except Exception as e:
            result['message'] = f'Unexpected error: {str(e)}'
            logger.error(f"Unexpected error deploying to {device.ip_address}: {e}")

        return result

    async def rollback_configuration(self, device: Device, rollback_id: int = 1) -> Dict[str, Any]:
        """Rollback configuration on a device"""
        result = {
            'device': device.ip_address,
            'success': False,
            'message': '',
            'timestamp': datetime.now().isoformat()
        }

        if not PYEZ_AVAILABLE:
            result['success'] = True
            result['message'] = 'Configuration rolled back successfully (mock)'
            return result

        try:
            if device.ip_address not in self.connections:
                await self.connect_to_device(device)

            dev = self.connections[device.ip_address]

            with Config(dev, mode='exclusive') as cu:
                cu.rollback(rb_id=rollback_id)
                cu.commit(comment=f"TUI Rollback to {rollback_id}")

            result['success'] = True
            result['message'] = f'Configuration rolled back to {rollback_id} on {device.ip_address}'
            logger.info(f"Configuration rolled back on {device.ip_address}")

        except Exception as e:
            result['message'] = f'Rollback error: {str(e)}'
            logger.error(f"Rollback error on {device.ip_address}: {e}")

        return result

    async def get_device_facts(self, device: Device) -> Dict[str, Any]:
        """Get device facts and status"""
        result = {
            'device': device.ip_address,
            'success': False,
            'facts': {},
            'interfaces': [],
            'timestamp': datetime.now().isoformat()
        }

        if not PYEZ_AVAILABLE:
            # Mock device facts
            result['success'] = True
            result['facts'] = {
                'hostname': device.host_name,
                'model': device.platform,
                'version': 'Mock Version',
                'serial': 'Mock Serial'
            }
            result['interfaces'] = [
                {'name': 'ge-0/0/0', 'status': 'up', 'description': 'Mock Interface'}
            ]
            return result

        try:
            if device.ip_address not in self.connections:
                await self.connect_to_device(device)

            dev = self.connections[device.ip_address]

            # Get device facts
            facts = dev.facts
            result['facts'] = {
                'hostname': facts.get('hostname', 'Unknown'),
                'model': facts.get('model', 'Unknown'),
                'version': facts.get('version', 'Unknown'),
                'serial_number': facts.get('serial_number', 'Unknown'),
                'domain': facts.get('domain', 'Unknown'),
                'personality': facts.get('personality', 'Unknown'),
                'switch_style': facts.get('switch_style', 'Unknown'),
            }

            # Get interface information
            try:
                interfaces = dev.rpc.get_interface_information()
                interface_list = []
                for interface in interfaces.findall('physical-interface'):
                    name = interface.find('name').text
                    oper_status = interface.find('oper-status').text
                    admin_status = interface.find('admin-status').text
                    description_elem = interface.find('description')
                    description = description_elem.text if description_elem is not None else ''

                    interface_list.append({
                        'name': name,
                        'oper_status': oper_status,
                        'admin_status': admin_status,
                        'description': description
                    })

                result['interfaces'] = interface_list
                result['success'] = True

            except Exception as e:
                logger.warning(f"Could not get interface info from {device.ip_address}: {e}")
                result['success'] = True  # Still consider success if we got facts

        except Exception as e:
            logger.error(f"Error getting device facts from {device.ip_address}: {e}")
            result['message'] = str(e)

        return result

    async def execute_rpc_command(self, device: Device, rpc_command: str) -> Dict[str, Any]:
        """Execute RPC command on device"""
        result = {
            'device': device.ip_address,
            'success': False,
            'output': '',
            'timestamp': datetime.now().isoformat()
        }

        if not PYEZ_AVAILABLE:
            result['success'] = True
            result['output'] = f'Mock RPC output for: {rpc_command}'
            return result

        try:
            if device.ip_address not in self.connections:
                await self.connect_to_device(device)

            dev = self.connections[device.ip_address]

            # Execute RPC command
            rpc_result = dev.rpc.rpc(rpc_command)
            result['output'] = str(rpc_result)
            result['success'] = True

        except RpcError as e:
            result['message'] = f'RPC error: {str(e)}'
            logger.error(f"RPC error on {device.ip_address}: {e}")
        except Exception as e:
            result['message'] = f'Unexpected error: {str(e)}'
            logger.error(f"Unexpected error executing RPC on {device.ip_address}: {e}")

        return result

    async def ping_from_device(self, device: Device, target: str, count: int = 5) -> Dict[str, Any]:
        """Ping from device to target"""
        result = {
            'device': device.ip_address,
            'target': target,
            'success': False,
            'ping_results': {},
            'timestamp': datetime.now().isoformat()
        }

        if not PYEZ_AVAILABLE:
            result['success'] = True
            result['ping_results'] = {
                'packet_loss': 0,
                'round_trip_avg': 10.5,
                'packets_sent': count,
                'packets_received': count
            }
            return result

        try:
            if device.ip_address not in self.connections:
                await self.connect_to_device(device)

            dev = self.connections[device.ip_address]

            # Execute ping RPC
            ping_rpc = f"""
            <ping>
                <count>{count}</count>
                <wait>1</wait>
                <target>{target}</target>
            </ping>
            """

            ping_result = dev.rpc.rpc(ping_rpc)

            # Parse ping results
            ping_summary = ping_result.find('ping-success')
            if ping_summary is not None:
                result['success'] = True
                result['ping_results'] = {
                    'packet_loss': ping_summary.find('packet-loss').text,
                    'round_trip_avg': ping_summary.find('rtt-average').text,
                    'packets_sent': ping_summary.find('packets-sent').text,
                    'packets_received': ping_summary.find('packets-received').text
                }

        except Exception as e:
            result['message'] = f'Ping error: {str(e)}'
            logger.error(f"Ping error from {device.ip_address} to {target}: {e}")

        return result

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all connections"""
        return {
            'connected_devices': list(self.connections.keys()),
            'total_connections': len(self.connections),
            'pyez_available': PYEZ_AVAILABLE,
            'timestamp': datetime.now().isoformat()
        }

    def cleanup_connections(self):
        """Clean up all connections"""
        for device_ip in list(self.connections.keys()):
            try:
                dev = self.connections[device_ip]
                dev.close()
                logger.info(f"Cleaned up connection to {device_ip}")
            except:
                pass
        self.connections.clear()