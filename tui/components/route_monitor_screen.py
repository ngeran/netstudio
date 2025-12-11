"""
Route Monitor Screen

Real-time monitoring of routing table changes on network devices.
Shows added/removed routes with auto-refresh capability.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Button, Static, DataTable, Select, Label
from textual.reactive import reactive
from textual import work

# Import legacy route monitor functions
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.route_monitor import get_all_route_tables, compare_routes
from scripts.connect_to_hosts import connect_to_hosts, disconnect_from_hosts

logger = logging.getLogger(__name__)


class RouteMonitorScreen(Screen):
    """Route monitoring screen with real-time updates"""

    # Monitoring state
    is_monitoring: reactive[bool] = reactive(False)
    selected_device: reactive[Optional[str]] = reactive(None)
    poll_interval: reactive[int] = reactive(60)  # seconds

    # Route data
    current_routes: reactive[Dict] = reactive({})
    previous_routes: reactive[Dict] = reactive({})
    change_log: reactive[List[Dict]] = reactive([])

    # Report directory
    reports_dir = Path("reports")

    def __init__(self, inventory_service, api_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service
        self.reports_dir.mkdir(exist_ok=True)

        # Load available devices
        try:
            self.available_devices = self.inventory_service.load_devices()
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            self.available_devices = []

        # Active connection
        self.device_connection = None
        self.monitoring_task = None

    def compose(self):
        """Compose the route monitor screen layout"""
        yield Header("📊 Route Monitor")

        with Container(classes="monitor-container"):
            # Control panel
            with Horizontal(classes="monitor-controls"):
                with Vertical(classes="control-section"):
                    yield Label("Device:")
                    device_options = [
                        (f"{d.host_name} ({d.ip_address})", d.ip_address)
                        for d in self.available_devices
                    ]
                    yield Select(
                        options=device_options
                        if device_options
                        else [("No devices", "none")],
                        id="device_select",
                        allow_blank=False,
                    )

                with Vertical(classes="control-section"):
                    yield Label("Poll Interval:")
                    yield Select(
                        options=[
                            ("30 seconds", "30"),
                            ("1 minute", "60"),
                            ("2 minutes", "120"),
                            ("5 minutes", "300"),
                        ],
                        value="60",
                        id="interval_select",
                    )

                with Vertical(classes="control-section"):
                    yield Label("Actions:")
                    with Horizontal():
                        yield Button("▶️ Start", id="btn_start", variant="success")
                        yield Button(
                            "⏸️ Stop", id="btn_stop", variant="default", disabled=True
                        )
                        yield Button(
                            "📸 Snapshot", id="btn_snapshot", variant="default"
                        )

            # Status bar
            yield Static(
                "Ready to monitor", id="monitor_status", classes="monitor-status"
            )

            # Main content area - split view
            with Horizontal(classes="monitor-content"):
                # Left: Current routing table
                with Vertical(classes="routes-panel"):
                    yield Static("📋 Current Routing Table", classes="panel-title")
                    yield DataTable(id="routes_table", classes="routes-table")

                # Right: Change log
                with Vertical(classes="changes-panel"):
                    yield Static("🔄 Change Log", classes="panel-title")
                    yield VerticalScroll(id="change_log", classes="change-log")

        yield Button("🔙 Back", id="btn_back")
        yield Footer()

    def on_mount(self):
        """Initialize when screen is mounted"""
        self._setup_routes_table()
        self._update_change_log()

    def _setup_routes_table(self):
        """Setup the routing table"""
        table = self.query_one("#routes_table", DataTable)
        table.clear(columns=True)
        table.add_column("Prefix", width=20)
        table.add_column("Next Hop", width=20)
        table.add_column("Protocol", width=12)
        table.add_column("AS Path", width=20)

    def _update_routes_table(self):
        """Update the routing table display"""
        table = self.query_one("#routes_table", DataTable)
        table.clear()

        if not self.current_routes:
            return

        # Show inet.0 table by default (most common)
        routes = self.current_routes.get("inet.0", [])

        for route in routes[:100]:  # Limit to 100 routes for performance
            table.add_row(
                route.get("prefix", "-"),
                route.get("next_hop", "-"),
                route.get("protocol", "-"),
                route.get("as_path", "-"),
            )

    def _update_change_log(self):
        """Update the change log display"""
        log_container = self.query_one("#change_log", VerticalScroll)
        log_container.remove_children()

        if not self.change_log:
            log_container.mount(Static("[dim]No changes detected yet[/]"))
            return

        # Show last 50 changes
        for change in self.change_log[-50:]:
            timestamp = change.get("timestamp", "")
            change_type = change.get("type", "")  # "added" or "removed"
            route = change.get("route", {})

            if change_type == "added":
                icon = "+"
                color = "green"
            else:
                icon = "-"
                color = "red"

            text = f"[{color}]{icon}[/] [{timestamp}] {route.get('prefix')} via {route.get('next_hop')} ({route.get('protocol')})"
            log_container.mount(Static(text))

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn_back":
            await self._stop_monitoring()
            self.app.pop_screen()

        elif button_id == "btn_start":
            await self._start_monitoring()

        elif button_id == "btn_stop":
            await self._stop_monitoring()

        elif button_id == "btn_snapshot":
            await self._save_snapshot()

    def on_select_changed(self, event: Select.Changed):
        """Handle select changes"""
        if event.select.id == "device_select":
            self.selected_device = event.value
        elif event.select.id == "interval_select":
            self.poll_interval = int(event.value)

    @work(exclusive=True)
    async def _start_monitoring(self):
        """Start monitoring routing tables"""
        if not self.selected_device or self.selected_device == "none":
            self.notify("Please select a device first", severity="warning")
            return

        if self.is_monitoring:
            self.notify("Monitoring already running", severity="warning")
            return

        # Update UI
        status_widget = self.query_one("#monitor_status", Static)
        status_widget.update("🔄 Connecting to device...")

        try:
            # Get device credentials
            device = next(
                (
                    d
                    for d in self.available_devices
                    if d.ip_address == self.selected_device
                ),
                None,
            )

            if not device:
                raise ValueError("Selected device not found")

            username = device.username if device.username else "admin"
            password = device.password if device.password else "password"

            # Connect to device
            connections = await asyncio.to_thread(
                connect_to_hosts, [self.selected_device], username, password
            )

            if not connections:
                raise Exception("Failed to connect to device")

            self.device_connection = connections[0]

            # Update UI state
            self.is_monitoring = True
            self._update_button_states()

            status_widget.update(
                f"✅ Monitoring {self.selected_device} (interval: {self.poll_interval}s)"
            )
            self.notify(
                f"Started monitoring {self.selected_device}", severity="success"
            )

            # Start monitoring loop
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        except Exception as e:
            status_widget.update(f"❌ Failed to start monitoring: {str(e)}")
            self.notify(f"Failed to start: {str(e)}", severity="error")
            logger.error(f"Monitoring start error: {e}", exc_info=True)

    async def _stop_monitoring(self):
        """Stop monitoring"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False

        # Cancel monitoring task
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None

        # Disconnect from device
        if self.device_connection:
            try:
                await asyncio.to_thread(disconnect_from_hosts, [self.device_connection])
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            self.device_connection = None

        # Update UI
        self._update_button_states()
        status_widget = self.query_one("#monitor_status", Static)
        status_widget.update("⏹️ Monitoring stopped")
        self.notify("Monitoring stopped", severity="information")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self.is_monitoring:
                # Fetch current routes
                routes = await asyncio.to_thread(
                    get_all_route_tables, self.device_connection
                )

                if routes:
                    # Compare with previous
                    if self.previous_routes:
                        await self._detect_changes(routes)

                    # Update current state
                    self.current_routes = routes
                    self.previous_routes = routes.copy()

                    # Update display
                    self._update_routes_table()

                    # Update status
                    status_widget = self.query_one("#monitor_status", Static)
                    status_widget.update(
                        f"✅ Monitoring {self.selected_device} | "
                        f"Last update: {datetime.now().strftime('%H:%M:%S')} | "
                        f"Routes: {len(routes.get('inet.0', []))}"
                    )

                # Wait for next poll
                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Monitoring loop error: {e}", exc_info=True)
            self.notify(f"Monitoring error: {str(e)}", severity="error")
            await self._stop_monitoring()

    async def _detect_changes(self, current_routes: Dict):
        """Detect and log route changes"""
        for table_name, routes in current_routes.items():
            prev_routes = self.previous_routes.get(table_name, [])
            added, removed = compare_routes(prev_routes, routes)

            timestamp = datetime.now().strftime("%H:%M:%S")

            # Log added routes
            for route in added:
                self.change_log.append(
                    {
                        "timestamp": timestamp,
                        "type": "added",
                        "table": table_name,
                        "route": route,
                    }
                )

            # Log removed routes
            for route in removed:
                self.change_log.append(
                    {
                        "timestamp": timestamp,
                        "type": "removed",
                        "table": table_name,
                        "route": route,
                    }
                )

            # Update change log display
            if added or removed:
                self._update_change_log()

                # Save to report file
                await self._save_changes_to_file(table_name, added, removed)

    async def _save_changes_to_file(self, table_name: str, added: List, removed: List):
        """Save changes to report file"""
        try:
            report_file = self.reports_dir / f"route_changes_{self.selected_device}.txt"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(report_file, "a") as f:
                f.write(f"\n[{timestamp}] Table: {table_name}\n")

                if added:
                    f.write("  Added routes:\n")
                    for r in added:
                        f.write(
                            f"    + {r['prefix']:20} {r['next_hop']:20} "
                            f"{r['protocol']:10} {r['as_path']}\n"
                        )

                if removed:
                    f.write("  Removed routes:\n")
                    for r in removed:
                        f.write(
                            f"    - {r['prefix']:20} {r['next_hop']:20} "
                            f"{r['protocol']:10} {r['as_path']}\n"
                        )

                if not (added or removed):
                    f.write("  No changes detected.\n")

            logger.info(f"Changes saved to {report_file}")

        except Exception as e:
            logger.error(f"Failed to save changes to file: {e}")

    async def _save_snapshot(self):
        """Save current routing table snapshot"""
        if not self.current_routes:
            self.notify("No routing data to save", severity="warning")
            return

        try:
            snapshot_file = (
                self.reports_dir
                / f"route_snapshot_{self.selected_device}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )

            with open(snapshot_file, "w") as f:
                f.write(f"Route Snapshot: {self.selected_device}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")

                for table_name, routes in self.current_routes.items():
                    f.write(f"\nTable: {table_name} ({len(routes)} routes)\n")
                    f.write("-" * 80 + "\n")

                    for route in routes:
                        f.write(
                            f"{route['prefix']:20} {route['next_hop']:20} "
                            f"{route['protocol']:10} {route['as_path']}\n"
                        )

            self.notify(f"Snapshot saved: {snapshot_file.name}", severity="success")
            logger.info(f"Snapshot saved to {snapshot_file}")

        except Exception as e:
            self.notify(f"Failed to save snapshot: {str(e)}", severity="error")
            logger.error(f"Snapshot save error: {e}", exc_info=True)

    def _update_button_states(self):
        """Update button enabled/disabled states"""
        try:
            btn_start = self.query_one("#btn_start", Button)
            btn_stop = self.query_one("#btn_stop", Button)
            device_select = self.query_one("#device_select", Select)
            interval_select = self.query_one("#interval_select", Select)

            btn_start.disabled = self.is_monitoring
            btn_stop.disabled = not self.is_monitoring
            device_select.disabled = self.is_monitoring
            interval_select.disabled = self.is_monitoring

        except Exception as e:
            logger.error(f"Error updating button states: {e}")
