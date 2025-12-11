"""
Enhanced Device Browser with API Integration

Advanced device browser that connects to the FastAPI backend
for real device operations and WebSocket updates.
"""

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    DataTable,
    Input,
    Button,
    Static,
    Select,
    LoadingIndicator,
    ProgressBar,
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from textual.screen import Screen
from typing import List, Optional, Dict, Any
import asyncio
import json

from tui.models.device import Device
from tui.services.inventory_service import InventoryService
from tui.services.api_client import APIService


class DeviceSelected(Message):
    """Message sent when a device is selected"""

    def __init__(self, device: Device) -> None:
        self.device = device
        super().__init__()


class TaskStarted(Message):
    """Message sent when a task is started"""

    def __init__(self, task_id: str, task_name: str) -> None:
        self.task_id = task_id
        self.task_name = task_name
        super().__init__()


class EnhancedDeviceBrowser(Container):
    """Enhanced device browser with API integration"""

    devices: reactive[List[Device]] = reactive([])
    filtered_devices: reactive[List[Device]] = reactive([])
    selected_device: reactive[Optional[Device]] = reactive(None)
    selected_devices: reactive[List[Device]] = reactive([])
    loading: reactive[bool] = reactive(False)
    api_connected: reactive[bool] = reactive(False)
    current_task: reactive[Dict[str, Any]] = reactive({})

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("c", "connect_selected", "Connect"),
        Binding("f", "get_facts", "Get Facts"),
        Binding("d", "deploy_config", "Deploy"),
        Binding("p", "ping_test", "Ping Test"),
        Binding("t", "toggle_selection", "Toggle Selection"),
        Binding("a", "select_all", "Select All"),
        Binding("s", "status", "API Status"),
    ]

    def __init__(self, inventory_service: InventoryService, api_service: APIService):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service
        self.task_updates = {}

    def compose(self):
        """Compose the enhanced device browser UI"""
        # Status bar
        yield Horizontal(
            Static("API:", classes="status-label"),
            Static("Disconnected", id="api_status", classes="status-value"),
            Static("Selected:", classes="status-label"),
            Static("0 devices", id="selection_count", classes="status-value"),
            Button("🔌 Connect API", id="connect_api", variant="primary"),
            classes="status-bar",
        )

        # Toolbar
        yield Horizontal(
            Input(placeholder="Search devices...", id="search_input"),
            Select(
                options=[("All", "all"), ("Routers", "router"), ("Switches", "switch")],
                value="all",
                id="type_filter",
                allow_blank=False,
            ),
            Select(
                options=[("All Locations", "all")],
                value="all",
                id="location_filter",
                allow_blank=False,
            ),
            Button("🔄 Refresh", id="refresh_btn"),
            Button("🔍 Test All", id="test_all_btn"),
            Button("📊 Get Facts", id="get_facts_btn"),
            classes="toolbar",
        )

        # Device table
        yield DataTable(
            id="device_table",
            zebra_stripes=True,
        )

        # Loading indicator
        yield LoadingIndicator(id="loading", classes="hidden")

        # Action buttons for selected devices
        yield Horizontal(
            Button("🔌 Connect Selected", id="connect_selected_btn"),
            Button("⚙️ Deploy Config", id="deploy_config_btn"),
            Button("🔙 Rollback", id="rollback_btn"),
            Button("📊 Get Facts", id="get_facts_selected_btn"),
            Button("🌐 Ping Test", id="ping_test_btn"),
            classes="action-bar",
        )

        # Progress bar for operations
        yield ProgressBar(
            id="operation_progress",
            show_eta=True,
            show_percentage=True,
            classes="hidden",
        )

        # Status message
        yield Static("", id="status_message", classes="status-message")

    def on_mount(self):
        """Initialize component when mounted"""
        self._setup_table()
        self._refresh_devices()
        self._check_api_status()

        # Register API message handlers
        self.api_service.client.register_handler(
            "task_update", self._handle_task_update
        )
        self.api_service.client.register_handler(
            "log_message", self._handle_log_message
        )

    def _setup_table(self):
        """Set up the data table columns"""
        table = self.query_one("#device_table")
        table.add_columns(
            "☐",  # Selection checkbox
            "Device Name",
            "IP Address",
            "Type",
            "Platform",
            "Location",
            "Status",
            "API Connected",
            "Last Check",
        )

    async def _check_api_status(self):
        """Check API connection status"""
        if self.api_service.client.is_connected():
            self.api_connected = True
            status = self.query_one("#api_status")
            status.update("✅ Connected")
            status.add_class("status-online")
            self.query_one("#connect_api").display = False
        else:
            self.api_connected = False
            status = self.query_one("#api_status")
            status.update("❌ Disconnected")
            status.add_class("status-error")
            self.query_one("#connect_api").display = True

    def _refresh_devices(self):
        """Refresh the device list"""
        self.loading = True
        table = self.query_one("#device_table")
        table.clear()

        # Show loading indicator
        try:
            loading = self.query_one("#loading")
            loading.remove_class("hidden")
        except Exception:
            pass  # Loading indicator might not exist yet

        # This will be async in real implementation
        asyncio.create_task(self._load_devices_async())

    async def _load_devices_async(self):
        """Load devices asynchronously"""
        try:
            # Simulate loading time
            await asyncio.sleep(0.5)

            devices = self.inventory_service.load_devices()
            self.devices = devices
            self.filtered_devices = devices

            # Update location filter options
            locations = list(set(d.location or "Unknown" for d in devices))
            location_select = self.query_one("#location_filter")
            location_select.set_options(
                [("All Locations", "all")]
                + [(loc, loc.lower()) for loc in sorted(locations)]
            )

            self._update_table()
            self._update_selection_count()

        except Exception as e:
            self._show_error(f"Error loading devices: {e}")
        finally:
            self.loading = False
            try:
                loading = self.query_one("#loading")
                loading.add_class("hidden")
            except Exception:
                pass  # Loading indicator might not exist

    def _update_table(self):
        """Update the device table with current filtered devices"""
        table = self.query_one("#device_table")
        table.clear()

        for device in self.filtered_devices:
            is_selected = device in self.selected_devices
            api_status = "🟢" if device.is_connected else "🔴"
            status_style = self._get_status_style(device.status)

            table.add_row(
                "☑" if is_selected else "☐",
                device.host_name,
                device.ip_address,
                device.device_type.capitalize(),
                device.platform,
                device.location or "Unknown",
                device.status,
                api_status,
                device.last_check.strftime("%H:%M:%S")
                if device.last_check
                else "Never",
                key=device.ip_address,
                style=status_style,
            )

    def _get_status_style(self, status: str) -> str:
        """Get display style based on device status"""
        status_styles = {
            "reachable": "green",
            "connected": "green",
            "unreachable": "red",
            "disconnected": "red",
            "error": "red",
            "unknown": "yellow",
        }
        return status_styles.get(status.lower(), "white")

    def on_input_changed(self, event):
        """Handle search input changes"""
        if event.input.id == "search_input":
            self._apply_filters()

    def on_select_changed(self, event):
        """Handle filter select changes"""
        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters to device list"""
        search_term = self.query_one("#search_input").value.lower()
        type_filter = self.query_one("#type_filter").value
        location_filter = self.query_one("#location_filter").value

        filtered = []

        for device in self.devices:
            # Search filter
            if search_term:
                search_match = (
                    search_term in device.host_name.lower()
                    or search_term in device.ip_address
                    or search_term in (device.platform or "").lower()
                    or search_term in (device.location or "").lower()
                )
                if not search_match:
                    continue

            # Type filter
            if type_filter != "all" and device.device_type != type_filter:
                continue

            # Location filter
            if location_filter != "all":
                device_location = (device.location or "").lower()
                if device_location != location_filter:
                    continue

            filtered.append(device)

        self.filtered_devices = filtered
        self._update_table()

    def on_data_table_row_selected(self, event):
        """Handle device row selection"""
        if event.row_key and event.row_key.value:
            device_ip = event.row_key.value
            device = next(
                (d for d in self.filtered_devices if d.ip_address == device_ip), None
            )
            if device:
                self.selected_device = device
                self.post_message(DeviceSelected(device))

    def action_toggle_selection(self):
        """Toggle selection of current device"""
        if self.selected_device:
            if self.selected_device in self.selected_devices:
                self.selected_devices.remove(self.selected_device)
            else:
                self.selected_devices.append(self.selected_device)
            self._update_table()
            self._update_selection_count()

    def action_select_all(self):
        """Select/deselect all devices"""
        if len(self.selected_devices) == len(self.filtered_devices):
            # Deselect all
            self.selected_devices = []
        else:
            # Select all
            self.selected_devices = self.filtered_devices.copy()
        self._update_table()
        self._update_selection_count()

    def action_refresh(self):
        """Refresh device list"""
        self._refresh_devices()

    def action_connect_selected(self):
        """Connect to selected devices"""
        if not self.selected_devices:
            self._show_error("No devices selected")
            return

        device_ips = [d.ip_address for d in self.selected_devices]
        self._start_api_task("connect_devices", device_ips)

    def action_get_facts(self):
        """Get facts from selected devices"""
        if not self.selected_devices:
            self._show_error("No devices selected")
            return

        device_ips = [d.ip_address for d in self.selected_devices]
        self._start_api_task("get_device_facts", device_ips)

    async def action_deploy_config(self):
        """Deploy configuration to selected devices"""
        if not self.selected_devices:
            self._show_error("No devices selected")
            return

        # For now, use a simple test config
        config = """
interfaces {
    ge-0/0/0 {
        description "Deployed from TUI";
        unit 0 {
            family inet {
                description "Test deployment";
            }
        }
    }
        """.strip()

        device_ips = [d.ip_address for d in self.selected_devices]
        self._start_api_task("deploy_config", device_ips, config=config)

    def action_ping_test(self):
        """Run ping test from selected devices"""
        if not self.selected_devices:
            self._show_error("No devices selected")
            return

        device_ips = [d.ip_address for d in self.selected_devices]
        self._start_api_task("ping_test", device_ips)

    async def _start_api_task(self, operation: str, device_ips: List[str], **kwargs):
        """Start an API task"""
        if not self.api_service.client.is_connected():
            self._show_error("API not connected")
            return

        try:
            task_id = None

            if operation == "connect_devices":
                task_id = await self.api_service.client.connect_devices(device_ips)
                task_name = f"Connect to {len(device_ips)} devices"
            elif operation == "get_device_facts":
                task_id = await self.api_service.client.get_device_facts(device_ips)
                task_name = f"Get facts from {len(device_ips)} devices"
            elif operation == "deploy_config":
                config = kwargs.get("config", "")
                task_id = await self.api_service.client.deploy_config(
                    device_ips, config
                )
                task_name = f"Deploy config to {len(device_ips)} devices"
            elif operation == "ping_test":
                task_id = await self.api_service.client.ping_test(device_ips)
                task_name = f"Ping test from {len(device_ips)} devices"

            if task_id:
                self.current_task = {"task_id": task_id, "operation": operation}
                self.query_one("#operation_progress").remove_class("hidden")
                self.query_one("#status_message").update(f"Task started: {task_name}")
                self.post_message(TaskStarted(task_id, task_name))
            else:
                self._show_error("Failed to start task")

        except Exception as e:
            self._show_error(f"Error starting task: {e}")

    async def _handle_task_update(self, data: Dict[str, Any]):
        """Handle task update from WebSocket"""
        task_data = data.get("task", {})
        task_id = task_data.get("task_id")

        if task_id and self.current_task.get("task_id") == task_id:
            # Update progress bar
            progress = task_data.get("progress", 0)
            progress_bar = self.query_one("#operation_progress")
            progress_bar.advance = progress

            # Update status message
            message = task_data.get("message", "")
            self.query_one("#status_message").update(message)

            # Check if task is complete
            status = task_data.get("status", "")
            if status in ["success", "failed", "cancelled"]:
                progress_bar.add_class("hidden")
                if status == "success":
                    self._show_success("Task completed successfully")
                elif status == "failed":
                    error = task_data.get("error", "Unknown error")
                    self._show_error(f"Task failed: {error}")

    async def _handle_log_message(self, data: Dict[str, Any]):
        """Handle log message from WebSocket"""
        level = data.get("level", "info")
        message = data.get("message", "")
        task_id = data.get("task_id", "")

        if task_id and self.current_task.get("task_id") == task_id:
            # Update status with log message
            self.query_one("#status_message").update(f"[{level.upper()}] {message}")

    def _update_selection_count(self):
        """Update the selection count display"""
        count = len(self.selected_devices)
        self.query_one("#selection_count").update(
            f"{count} device{'s' if count != 1 else ''}"
        )

    def _show_error(self, message: str):
        """Show error message"""
        status = self.query_one("#status_message")
        status.update(f"❌ {message}")
        status.remove_class("status-online")
        status.add_class("status-error")

    def _show_success(self, message: str):
        """Show success message"""
        status = self.query_one("#status_message")
        status.update(f"✅ {message}")
        status.remove_class("status-error")
        status.add_class("status-online")

    def on_button_pressed(self, event):
        """Handle button press events"""
        button_id = event.button.id

        if button_id == "refresh_btn":
            self.action_refresh()
        elif button_id == "connect_api":
            asyncio.create_task(self._connect_api())
        elif button_id == "test_all_btn":
            # Test connectivity to all devices
            asyncio.create_task(self._test_all_devices())
        elif button_id == "get_facts_btn":
            if self.selected_device:
                asyncio.create_task(self._get_device_facts())
        elif button_id == "connect_selected_btn":
            asyncio.create_task(self.action_connect_selected())
        elif button_id == "deploy_config_btn":
            asyncio.create_task(self.action_deploy_config())
        elif button_id == "rollback_btn":
            asyncio.create_task(self._rollback_config())
        elif button_id == "get_facts_selected_btn":
            asyncio.create_task(self.action_get_facts())
        elif button_id == "ping_test_btn":
            asyncio.create_task(self.action_ping_test())

    async def _connect_api(self):
        """Connect to API server"""
        try:
            success = await self.api_service.start()
            if success:
                await self._check_api_status()
                self._show_success("Connected to API server")
            else:
                self._show_error("Failed to connect to API server")
        except Exception as e:
            self._show_error(f"Error connecting to API: {e}")

    async def _test_all_devices(self):
        """Test connectivity to all devices"""
        results = self.inventory_service.test_all_devices()
        reachable = sum(1 for r in results.values() if r)
        total = len(results)
        self._show_success(f"Connectivity test: {reachable}/{total} reachable")

    async def _get_device_facts(self):
        """Get facts from single selected device"""
        if not self.selected_device:
            self._show_error("No device selected")
            return

        try:
            facts = await self.api_service.client.get_device_facts(
                [self.selected_device.ip_address]
            )
            if facts:
                self._show_success("Facts retrieved successfully")
            else:
                self._show_error("Failed to get facts")
        except Exception as e:
            self._show_error(f"Error getting facts: {e}")

    async def _rollback_config(self):
        """Rollback configuration on selected devices"""
        if not self.selected_devices:
            self._show_error("No devices selected")
            return

        device_ips = [d.ip_address for d in self.selected_devices]
        task_id = await self.api_service.client.rollback_config(device_ips)

        if task_id:
            self.current_task = {"task_id": task_id, "operation": "rollback"}
            self.query_one("#operation_progress").remove_class("hidden")
            self.query_one("#status_message").update("Rollback started")
        else:
            self._show_error("Failed to start rollback")

    def action_status(self):
        """Show API status"""
        if self.api_service.client.is_connected():
            self._show_success("API Connected")
        else:
            self._show_error("API Disconnected")

