"""
Network Monitoring Service

Provides real-time device monitoring, telemetry collection, and alerting.
Integrates with WebSocket for live updates to TUI.
"""

import asyncio
import logging
import json
import sqlite3
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from collections import defaultdict, deque

try:
    from jnpr.junos import Device
    from jnpr.junos.op.phyport import PhyPortTable
    from jnpr.junos.op.bgppeer import BgpPeerTable
    from jnpr.junos.op_routes import RouteTable
    from jnpr.junos.rpcmonitor import RpcMonitor
    PYEZ_MONITORING_AVAILABLE = True
except ImportError:
    PYEZ_MONITORING_AVAILABLE = False
    logging.warning("PyEZ monitoring features not available, using mock implementation")

logger = logging.getLogger(__name__)


@dataclass
class InterfaceMetric:
    """Interface monitoring metrics"""
    device_id: str
    interface_name: str
    status: str
    admin_status: str
    speed: int
    mtu: int
    rx_packets: int
    tx_packets: int
    rx_bytes: int
    tx_bytes: int
    rx_errors: int
    tx_errors: int
    rx_drops: int
    tx_drops: int
    timestamp: datetime
    utilization_rx: float = 0.0
    utilization_tx: float = 0.0


@dataclass
class BgpMetric:
    """BGP monitoring metrics"""
    device_id: str
    peer_address: str
    peer_as: int
    state: str
    uptime: int
    received_routes: int
    advertised_routes: int
    input_messages: int
    output_messages: int
    timestamp: datetime


@dataclass
class SystemMetric:
    """System monitoring metrics"""
    device_id: str
    cpu_load_1min: float
    cpu_load_5min: float
    cpu_load_15min: float
    memory_usage: int
    memory_total: int
    memory_percent: float
    temperature: Optional[float]
    uptime_seconds: int
    timestamp: datetime


@dataclass
class Alert:
    """Monitoring alert"""
    alert_id: str
    device_id: str
    metric_type: str
    severity: str  # 'critical', 'warning', 'info'
    title: str
    message: str
    threshold_value: Optional[float]
    current_value: Optional[float]
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class MonitoringService:
    """Network monitoring service with real-time capabilities"""

    def __init__(self, db_path: str = "phase3/data/monitoring.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_interval = 60  # seconds
        self.monitored_devices: Dict[str, Dict[str, Any]] = {}

        # Callbacks for real-time updates
        self.websocket_callbacks: List[Callable] = []

        # Alert thresholds
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'interface_error_rate_warning': 0.01,  # 1%
            'interface_error_rate_critical': 0.05,  # 5%
            'bgp_state_down': 'critical',
            'temperature_warning': 70.0,
            'temperature_critical': 85.0
        }

        # Metric history for trend analysis (store last 100 data points per device/metric)
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

        # Background monitoring thread
        self.monitoring_thread: Optional[threading.Thread] = None

        if not PYEZ_MONITORING_AVAILABLE:
            logger.warning("Running monitoring service in mock mode")

    def _init_database(self):
        """Initialize SQLite database for storing metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Interface metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interface_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                interface_name TEXT NOT NULL,
                status TEXT NOT NULL,
                admin_status TEXT NOT NULL,
                speed INTEGER,
                mtu INTEGER,
                rx_packets INTEGER,
                tx_packets INTEGER,
                rx_bytes INTEGER,
                tx_bytes INTEGER,
                rx_errors INTEGER,
                tx_errors INTEGER,
                rx_drops INTEGER,
                tx_drops INTEGER,
                utilization_rx REAL,
                utilization_tx REAL,
                timestamp DATETIME NOT NULL,
                UNIQUE(device_id, interface_name, timestamp)
            )
        ''')

        # BGP metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bgp_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                peer_address TEXT NOT NULL,
                peer_as INTEGER,
                state TEXT NOT NULL,
                uptime INTEGER,
                received_routes INTEGER,
                advertised_routes INTEGER,
                input_messages INTEGER,
                output_messages INTEGER,
                timestamp DATETIME NOT NULL,
                UNIQUE(device_id, peer_address, timestamp)
            )
        ''')

        # System metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                cpu_load_1min REAL,
                cpu_load_5min REAL,
                cpu_load_15min REAL,
                memory_usage INTEGER,
                memory_total INTEGER,
                memory_percent REAL,
                temperature REAL,
                uptime_seconds INTEGER,
                timestamp DATETIME NOT NULL,
                UNIQUE(device_id, timestamp)
            )
        ''')

        # Alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                device_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                threshold_value REAL,
                current_value REAL,
                timestamp DATETIME NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_by TEXT,
                acknowledged_at DATETIME
            )
        ''')

        conn.commit()
        conn.close()

    def register_websocket_callback(self, callback: Callable):
        """Register callback for WebSocket updates"""
        self.websocket_callbacks.append(callback)

    async def _notify_websockets(self, message: Dict[str, Any]):
        """Notify all registered WebSocket callbacks"""
        for callback in self.websocket_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"WebSocket callback error: {e}")

    def add_device(self, device_info: Dict[str, Any]):
        """Add device to monitoring"""
        device_id = device_info['host_ip']
        self.monitored_devices[device_id] = device_info
        logger.info(f"Added device {device_id} to monitoring")

    def remove_device(self, device_id: str):
        """Remove device from monitoring"""
        if device_id in self.monitored_devices:
            del self.monitored_devices[device_id]
            logger.info(f"Removed device {device_id} from monitoring")

    def start_monitoring(self, interval: int = 60):
        """Start background monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return

        self.monitoring_interval = interval
        self.monitoring_active = True

        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()

        logger.info(f"Started monitoring with {interval}s interval")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Stopped monitoring")

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                asyncio.run(self._collect_metrics())
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            # Sleep until next collection
            for _ in range(self.monitoring_interval):
                if not self.monitoring_active:
                    break
                threading.Event().wait(1)

    async def _collect_metrics(self):
        """Collect metrics from all monitored devices"""
        for device_id, device_info in self.monitored_devices.items():
            try:
                # Collect all metric types
                interface_metrics = await self._collect_interface_metrics(device_info)
                bgp_metrics = await self._collect_bgp_metrics(device_info)
                system_metrics = await self._collect_system_metrics(device_info)

                # Store metrics and check alerts
                await self._store_interface_metrics(interface_metrics)
                await self._store_bgp_metrics(bgp_metrics)
                await self._store_system_metrics(system_metrics)

                await self._check_alerts(device_id, interface_metrics, bgp_metrics, system_metrics)

                # Send real-time update
                await self._notify_websockets({
                    'type': 'metrics_update',
                    'device_id': device_id,
                    'timestamp': datetime.now().isoformat(),
                    'interface_count': len(interface_metrics),
                    'bgp_peers': len(bgp_metrics),
                    'system_health': system_metrics[0].memory_percent if system_metrics else 0
                })

            except Exception as e:
                logger.error(f"Failed to collect metrics from {device_id}: {e}")

                # Send error notification
                await self._notify_websockets({
                    'type': 'collection_error',
                    'device_id': device_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })

    async def _collect_interface_metrics(self, device_info: Dict[str, Any]) -> List[InterfaceMetric]:
        """Collect interface metrics from device"""
        if PYEZ_MONITORING_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()

                # Use PyEZ op tables
                phy_ports = PhyPortTable(device)
                phy_ports.get()

                metrics = []
                for port in phy_ports:
                    metric = InterfaceMetric(
                        device_id=device_info['host_ip'],
                        interface_name=port.name,
                        status=port.oper_status,
                        admin_status=port.admin_status,
                        speed=int(port.speed) if port.speed else 0,
                        mtu=int(port.mtu) if port.mtu else 0,
                        rx_packets=int(port.rx_packets) if port.rx_packets else 0,
                        tx_packets=int(port.tx_packets) if port.tx_packets else 0,
                        rx_bytes=int(port.rx_bytes) if port.rx_bytes else 0,
                        tx_bytes=int(port.tx_bytes) if port.tx_bytes else 0,
                        rx_errors=int(port.rx_errors) if port.rx_errors else 0,
                        tx_errors=int(port.tx_errors) if port.tx_errors else 0,
                        rx_drops=int(port.rx_drops) if port.rx_drops else 0,
                        tx_drops=int(port.tx_drops) if port.tx_drops else 0,
                        timestamp=datetime.now()
                    )
                    metrics.append(metric)

                device.close()
                return metrics

            except Exception as e:
                logger.error(f"Failed to collect interface metrics: {e}")

        # Mock implementation
        import random
        interfaces = ['ge-0/0/0', 'ge-0/0/1', 'ge-0/0/2', 'xe-0/1/0', 'lo0']
        metrics = []

        for iface in interfaces:
            status = 'up' if random.random() > 0.05 else 'down'  # 95% uptime
            if iface == 'lo0':
                status = 'up'  # Loopback always up

            rx_bytes = random.randint(1000000, 10000000)
            tx_bytes = random.randint(1000000, 10000000)
            rx_errors = random.randint(0, 10)
            tx_errors = random.randint(0, 10)

            metric = InterfaceMetric(
                device_id=device_info['host_ip'],
                interface_name=iface,
                status=status,
                admin_status='up',
                speed=1000000000 if iface.startswith('ge') else 10000000000,
                mtu=1514,
                rx_packets=rx_bytes // 1500,
                tx_packets=tx_bytes // 1500,
                rx_bytes=rx_bytes,
                tx_bytes=tx_bytes,
                rx_errors=rx_errors,
                tx_errors=tx_errors,
                rx_drops=random.randint(0, 5),
                tx_drops=random.randint(0, 5),
                timestamp=datetime.now(),
                utilization_rx=random.uniform(0.1, 0.8),
                utilization_tx=random.uniform(0.1, 0.8)
            )
            metrics.append(metric)

        return metrics

    async def _collect_bgp_metrics(self, device_info: Dict[str, Any]) -> List[BgpMetric]:
        """Collect BGP metrics from device"""
        if PYEZ_MONITORING_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()

                bgp_peers = BgpPeerTable(device)
                bgp_peers.get()

                metrics = []
                for peer in bgp_peers:
                    metric = BgpMetric(
                        device_id=device_info['host_ip'],
                        peer_address=peer.peer_address,
                        peer_as=int(peer.peer_as),
                        state=peer.peer_state,
                        uptime=int(peer.established) if peer.established else 0,
                        received_routes=int(peer.received_routes) if peer.received_routes else 0,
                        advertised_routes=int(peer.advertised_routes) if peer.advertised_routes else 0,
                        input_messages=int(peer.input_messages) if peer.input_messages else 0,
                        output_messages=int(peer.output_messages) if peer.output_messages else 0,
                        timestamp=datetime.now()
                    )
                    metrics.append(metric)

                device.close()
                return metrics

            except Exception as e:
                logger.error(f"Failed to collect BGP metrics: {e}")

        # Mock implementation
        import random
        peers = [
            ('192.168.1.1', 65001),
            ('10.0.0.1', 65002),
            ('172.16.1.1', 65003),
            ('192.168.2.1', 65001)
        ]
        metrics = []

        for peer_ip, peer_as in peers:
            state = 'Established' if random.random() > 0.1 else 'Active'  # 90% uptime
            metric = BgpMetric(
                device_id=device_info['host_ip'],
                peer_address=peer_ip,
                peer_as=peer_as,
                state=state,
                uptime=random.randint(3600, 86400 * 30) if state == 'Established' else 0,
                received_routes=random.randint(100, 10000),
                advertised_routes=random.randint(50, 5000),
                input_messages=random.randint(1000, 50000),
                output_messages=random.randint(1000, 50000),
                timestamp=datetime.now()
            )
            metrics.append(metric)

        return metrics

    async def _collect_system_metrics(self, device_info: Dict[str, Any]) -> List[SystemMetric]:
        """Collect system metrics from device"""
        if PYEZ_MONITORING_AVAILABLE:
            try:
                device = Device(
                    host=device_info['host_ip'],
                    user=device_info['username'],
                    password=device_info['password'],
                    gather_facts=False
                )

                device.open()

                # Get system information via RPC
                rpc_results = device.rpc.get_system_information()
                load_avg = rpc_results.findtext('.//load-average')
                if load_avg:
                    loads = load_avg.split(',')
                    cpu_load_1min = float(loads[0])
                    cpu_load_5min = float(loads[1])
                    cpu_load_15min = float(loads[2])
                else:
                    cpu_load_1min = cpu_load_5min = cpu_load_15min = 0.0

                # Get memory information
                mem_rpc = device.rpc.get_system_memory_information()
                mem_total = 0
                mem_used = 0

                for mem_line in mem_rpc.findall('.//system-memory-total'):
                    mem_total += int(mem_line.text.replace('%', '').strip())

                for mem_line in mem_rpc.findall('.//system-memory-used'):
                    mem_used += int(mem_line.text.replace('%', '').strip())

                memory_percent = (mem_used / mem_total * 100) if mem_total > 0 else 0

                # Get uptime
                uptime_info = device.rpc.get_system_uptime_information()
                uptime_seconds = 0
                uptime_text = uptime_info.findtext('.//system-booted-time/time-length')
                if uptime_text:
                    uptime_seconds = self._parse_uptime(uptime_text)

                metric = SystemMetric(
                    device_id=device_info['host_ip'],
                    cpu_load_1min=cpu_load_1min,
                    cpu_load_5min=cpu_load_5min,
                    cpu_load_15min=cpu_load_15min,
                    memory_usage=mem_used,
                    memory_total=mem_total,
                    memory_percent=memory_percent,
                    temperature=None,  # Would need platform-specific RPC
                    uptime_seconds=uptime_seconds,
                    timestamp=datetime.now()
                )

                device.close()
                return [metric]

            except Exception as e:
                logger.error(f"Failed to collect system metrics: {e}")

        # Mock implementation
        import random
        metric = SystemMetric(
            device_id=device_info['host_ip'],
            cpu_load_1min=random.uniform(0.1, 2.0),
            cpu_load_5min=random.uniform(0.1, 1.8),
            cpu_load_15min=random.uniform(0.1, 1.5),
            memory_usage=random.randint(2048, 8192),
            memory_total=16384,
            memory_percent=random.uniform(15.0, 60.0),
            temperature=random.uniform(35.0, 55.0),
            uptime_seconds=random.randint(86400, 86400 * 365),
            timestamp=datetime.now()
        )

        return [metric]

    def _parse_uptime(self, uptime_text: str) -> int:
        """Parse uptime text string to seconds"""
        try:
            uptime_text = uptime_text.lower().strip()
            total_seconds = 0

            # Parse weeks, days, hours, minutes, seconds
            if 'week' in uptime_text:
                weeks = int(uptime_text.split('week')[0].strip())
                total_seconds += weeks * 7 * 24 * 3600
                uptime_text = uptime_text.split('week')[1]

            if 'day' in uptime_text:
                days = int(uptime_text.split('day')[0].strip())
                total_seconds += days * 24 * 3600
                uptime_text = uptime_text.split('day')[1]

            if 'hour' in uptime_text:
                hours = int(uptime_text.split('hour')[0].strip())
                total_seconds += hours * 3600
                uptime_text = uptime_text.split('hour')[1]

            if 'min' in uptime_text:
                minutes = int(uptime_text.split('min')[0].strip())
                total_seconds += minutes * 60
                uptime_text = uptime_text.split('min')[1]

            if 'sec' in uptime_text:
                seconds = int(uptime_text.split('sec')[0].strip())
                total_seconds += seconds

            return total_seconds

        except Exception:
            return 86400  # Default to 1 day

    async def _store_interface_metrics(self, metrics: List[InterfaceMetric]):
        """Store interface metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for metric in metrics:
            cursor.execute('''
                INSERT OR REPLACE INTO interface_metrics
                (device_id, interface_name, status, admin_status, speed, mtu,
                 rx_packets, tx_packets, rx_bytes, tx_bytes, rx_errors, tx_errors,
                 rx_drops, tx_drops, utilization_rx, utilization_tx, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.device_id, metric.interface_name, metric.status, metric.admin_status,
                metric.speed, metric.mtu, metric.rx_packets, metric.tx_packets,
                metric.rx_bytes, metric.tx_bytes, metric.rx_errors, metric.tx_errors,
                metric.rx_drops, metric.tx_drops, metric.utilization_rx,
                metric.utilization_tx, metric.timestamp.isoformat()
            ))

        conn.commit()
        conn.close()

    async def _store_bgp_metrics(self, metrics: List[BgpMetric]):
        """Store BGP metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for metric in metrics:
            cursor.execute('''
                INSERT OR REPLACE INTO bgp_metrics
                (device_id, peer_address, peer_as, state, uptime,
                 received_routes, advertised_routes, input_messages, output_messages, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.device_id, metric.peer_address, metric.peer_as, metric.state,
                metric.uptime, metric.received_routes, metric.advertised_routes,
                metric.input_messages, metric.output_messages, metric.timestamp.isoformat()
            ))

        conn.commit()
        conn.close()

    async def _store_system_metrics(self, metrics: List[SystemMetric]):
        """Store system metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for metric in metrics:
            cursor.execute('''
                INSERT OR REPLACE INTO system_metrics
                (device_id, cpu_load_1min, cpu_load_5min, cpu_load_15min,
                 memory_usage, memory_total, memory_percent, temperature,
                 uptime_seconds, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.device_id, metric.cpu_load_1min, metric.cpu_load_5min,
                metric.cpu_load_15min, metric.memory_usage, metric.memory_total,
                metric.memory_percent, metric.temperature, metric.uptime_seconds,
                metric.timestamp.isoformat()
            ))

        conn.commit()
        conn.close()

    async def _check_alerts(self,
                           device_id: str,
                           interface_metrics: List[InterfaceMetric],
                           bgp_metrics: List[BgpMetric],
                           system_metrics: List[SystemMetric]):
        """Check metrics against thresholds and generate alerts"""
        alerts = []

        # Check system metrics
        if system_metrics:
            sys_metric = system_metrics[0]

            # CPU alerts
            if sys_metric.cpu_load_1min > self.thresholds['cpu_critical']:
                alerts.append(self._create_alert(
                    device_id, 'system', 'critical', 'High CPU Usage',
                    f"CPU load is {sys_metric.cpu_load_1min:.1f}",
                    self.thresholds['cpu_critical'], sys_metric.cpu_load_1min
                ))
            elif sys_metric.cpu_load_1min > self.thresholds['cpu_warning']:
                alerts.append(self._create_alert(
                    device_id, 'system', 'warning', 'Elevated CPU Usage',
                    f"CPU load is {sys_metric.cpu_load_1min:.1f}",
                    self.thresholds['cpu_warning'], sys_metric.cpu_load_1min
                ))

            # Memory alerts
            if sys_metric.memory_percent > self.thresholds['memory_critical']:
                alerts.append(self._create_alert(
                    device_id, 'system', 'critical', 'High Memory Usage',
                    f"Memory usage is {sys_metric.memory_percent:.1f}%",
                    self.thresholds['memory_critical'], sys_metric.memory_percent
                ))
            elif sys_metric.memory_percent > self.thresholds['memory_warning']:
                alerts.append(self._create_alert(
                    device_id, 'system', 'warning', 'Elevated Memory Usage',
                    f"Memory usage is {sys_metric.memory_percent:.1f}%",
                    self.thresholds['memory_warning'], sys_metric.memory_percent
                ))

            # Temperature alerts
            if sys_metric.temperature and sys_metric.temperature > self.thresholds['temperature_critical']:
                alerts.append(self._create_alert(
                    device_id, 'system', 'critical', 'High Temperature',
                    f"Temperature is {sys_metric.temperature:.1f}°C",
                    self.thresholds['temperature_critical'], sys_metric.temperature
                ))

        # Check interface metrics
        for intf_metric in interface_metrics:
            if intf_metric.status == 'down':
                alerts.append(self._create_alert(
                    device_id, 'interface', 'critical', 'Interface Down',
                    f"Interface {intf_metric.interface_name} is down",
                    None, None
                ))

            # Error rate alerts
            total_packets = intf_metric.rx_packets + intf_metric.tx_packets
            total_errors = intf_metric.rx_errors + intf_metric.tx_errors

            if total_packets > 0:
                error_rate = total_errors / total_packets
                if error_rate > self.thresholds['interface_error_rate_critical']:
                    alerts.append(self._create_alert(
                        device_id, 'interface', 'critical', 'High Interface Error Rate',
                        f"Interface {intf_metric.interface_name} error rate is {error_rate:.2%}",
                        self.thresholds['interface_error_rate_critical'], error_rate
                    ))
                elif error_rate > self.thresholds['interface_error_rate_warning']:
                    alerts.append(self._create_alert(
                        device_id, 'interface', 'warning', 'Elevated Interface Error Rate',
                        f"Interface {intf_metric.interface_name} error rate is {error_rate:.2%}",
                        self.thresholds['interface_error_rate_warning'], error_rate
                    ))

        # Check BGP metrics
        for bgp_metric in bgp_metrics:
            if bgp_metric.state != 'Established':
                alerts.append(self._create_alert(
                    device_id, 'bgp', 'critical', 'BGP Session Down',
                    f"BGP session with {bgp_metric.peer_address} (AS{bgp_metric.peer_as}) is {bgp_metric.state}",
                    None, None
                ))

        # Store and notify about new alerts
        for alert in alerts:
            await self._store_alert(alert)
            await self._notify_websockets({
                'type': 'alert',
                'alert': asdict(alert),
                'timestamp': datetime.now().isoformat()
            })

    def _create_alert(self,
                     device_id: str,
                     metric_type: str,
                     severity: str,
                     title: str,
                     message: str,
                     threshold_value: Optional[float],
                     current_value: Optional[float]) -> Alert:
        """Create an alert instance"""
        alert_id = f"alert_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{metric_type}"

        return Alert(
            alert_id=alert_id,
            device_id=device_id,
            metric_type=metric_type,
            severity=severity,
            title=title,
            message=message,
            threshold_value=threshold_value,
            current_value=current_value,
            timestamp=datetime.now()
        )

    async def _store_alert(self, alert: Alert):
        """Store alert in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR IGNORE INTO alerts
            (alert_id, device_id, metric_type, severity, title, message,
             threshold_value, current_value, timestamp, acknowledged,
             acknowledged_by, acknowledged_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.alert_id, alert.device_id, alert.metric_type, alert.severity,
            alert.title, alert.message, alert.threshold_value, alert.current_value,
            alert.timestamp.isoformat(), alert.acknowledged,
            alert.acknowledged_by, alert.acknowledged_at.isoformat() if alert.acknowledged_at else None
        ))

        conn.commit()
        conn.close()

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE alerts
            SET acknowledged = TRUE, acknowledged_by = ?, acknowledged_at = ?
            WHERE alert_id = ?
        ''', (acknowledged_by, datetime.now().isoformat(), alert_id))

        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()

        if rows_affected > 0:
            await self._notify_websockets({
                'type': 'alert_acknowledged',
                'alert_id': alert_id,
                'acknowledged_by': acknowledged_by,
                'timestamp': datetime.now().isoformat()
            })
            return True

        return False

    def get_current_metrics(self, device_id: str) -> Dict[str, Any]:
        """Get current metrics for a device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get latest system metrics
        cursor.execute('''
            SELECT * FROM system_metrics
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (device_id,))
        system_row = cursor.fetchone()

        # Get latest interface metrics
        cursor.execute('''
            SELECT * FROM interface_metrics
            WHERE device_id = ?
            ORDER BY timestamp DESC
        ''', (device_id,))
        interface_rows = cursor.fetchall()

        # Get latest BGP metrics
        cursor.execute('''
            SELECT * FROM bgp_metrics
            WHERE device_id = ?
            ORDER BY timestamp DESC
        ''', (device_id,))
        bgp_rows = cursor.fetchall()

        conn.close()

        return {
            'system': system_row,
            'interfaces': interface_rows,
            'bgp': bgp_rows
        }

    def get_active_alerts(self, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active (unacknowledged) alerts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if device_id:
            cursor.execute('''
                SELECT * FROM alerts
                WHERE device_id = ? AND acknowledged = FALSE
                ORDER BY timestamp DESC
            ''', (device_id,))
        else:
            cursor.execute('''
                SELECT * FROM alerts
                WHERE acknowledged = FALSE
                ORDER BY timestamp DESC
            ''')

        alerts = []
        for row in cursor.fetchall():
            alert = {
                'id': row[0],
                'alert_id': row[1],
                'device_id': row[2],
                'metric_type': row[3],
                'severity': row[4],
                'title': row[5],
                'message': row[6],
                'threshold_value': row[7],
                'current_value': row[8],
                'timestamp': row[9],
                'acknowledged': bool(row[10]),
                'acknowledged_by': row[11],
                'acknowledged_at': row[12]
            }
            alerts.append(alert)

        conn.close()
        return alerts

    def get_historical_metrics(self,
                              device_id: str,
                              metric_type: str,
                              start_time: datetime,
                              end_time: datetime) -> List[Dict[str, Any]]:
        """Get historical metrics for a device"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if metric_type == 'system':
            cursor.execute('''
                SELECT * FROM system_metrics
                WHERE device_id = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            ''', (device_id, start_time.isoformat(), end_time.isoformat()))

        elif metric_type == 'interface':
            cursor.execute('''
                SELECT * FROM interface_metrics
                WHERE device_id = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            ''', (device_id, start_time.isoformat(), end_time.isoformat()))

        elif metric_type == 'bgp':
            cursor.execute('''
                SELECT * FROM bgp_metrics
                WHERE device_id = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            ''', (device_id, start_time.isoformat(), end_time.isoformat()))

        metrics = []
        for row in cursor.fetchall():
            metrics.append(dict(zip([description[0] for description in cursor.description], row)))

        conn.close()
        return metrics

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """Update monitoring thresholds"""
        self.thresholds.update(new_thresholds)
        logger.info(f"Updated monitoring thresholds: {new_thresholds}")

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring service status"""
        return {
            'active': self.monitoring_active,
            'interval': self.monitoring_interval,
            'monitored_devices': list(self.monitored_devices.keys()),
            'device_count': len(self.monitored_devices),
            'thresholds': self.thresholds,
            'thread_alive': self.monitoring_thread.is_alive() if self.monitoring_thread else False
        }