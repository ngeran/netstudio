"""
Device browser component for TUI
"""

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Input, Button, Static, Select, LoadingIndicator
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from typing import List, Optional
import asyncio

from tui.models.device import Device
from tui.services.inventory_service import InventoryService


class DeviceSelected(Message):
    """Message sent when a device is selected"""
    def __init__(self, device: Device) -> None:
        self.device = device
        super().__init__()


class DeviceBrowser(Container):
    """Device inventory browser component"""

    devices: reactive[List[Device]] = reactive([])
    filtered_devices: reactive[List[Device]] = reactive([])
    selected_device: reactive[Optional[Device]] = reactive(None)
    loading: reactive[bool] = reactive(False)

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("t", "test_connectivity", "Test All"),
        Binding("s", "search_focus", "Search"),
    ]

    def compose(self):
        """Compose the device browser UI"""
        yield Horizontal(
            Input(placeholder="Search devices...", id="search_input"),
            Select(
                options=[("All", "all"), ("Routers", "router"), ("Switches", "switch")],
                value="all",
                id="type_filter",
                allow_blank=False
            ),
            Select(
                options=[("All Locations", "all")],
                value="all",
                id="location_filter",
                allow_blank=False
            ),
            Button("🔄 Refresh", id="refresh_btn", variant="primary"),
            Button("🔍 Test All", id="test_all_btn"),
            classes="toolbar"
        )

        yield LoadingIndicator(id="loading", classes="hidden")

        yield DataTable(
            id="device_table",
            zebra_stripes=True,
        )

        with Horizontal(classes="status-bar"):
            yield Static("", id="status_text")
            yield Static("", id="count_text")

    def on_mount(self):
        """Initialize component when mounted"""
        self._setup_table()
        self._refresh_devices()

    def _setup_table(self):
        """Set up the data table columns"""
        table = self.query_one("#device_table")
        table.add_columns(
            "Device Name",
            "IP Address",
            "Type",
            "Platform",
            "Location",
            "Status",
            "Last Check"
        )

    def _refresh_devices(self):
        """Refresh the device list"""
        self.loading = True
        table = self.query_one("#device_table")
        table.clear()
        self.query_one("#loading").remove_class("hidden")

        # This will be async in real implementation
        import asyncio
        asyncio.create_task(self._load_devices_async())

    async def _load_devices_async(self):
        """Load devices asynchronously"""
        try:
            # Simulate loading time
            await asyncio.sleep(0.5)

            inventory_service = InventoryService()
            devices = inventory_service.load_devices()
            self.devices = devices
            self.filtered_devices = devices

            # Update location filter options
            locations = list(set(d.location or "Unknown" for d in devices))
            location_select = self.query_one("#location_filter")
            location_select.set_options(
                [("All Locations", "all")] + [(loc, loc.lower()) for loc in sorted(locations)]
            )

            # Update device count
            self.query_one("#count_text").update(f"{len(devices)} devices")

            self.loading = False
            self.query_one("#loading").add_class("hidden")

            self._update_table()
            self.query_one("#status_text").update(f"Loaded {len(devices)} devices", style="green")

        except Exception as e:
            self.loading = False
            self.query_one("#loading").add_class("hidden")
            self.query_one("#status_text").update(f"Error loading devices: {e}", style="red")

    def _update_table(self):
        """Update the device table with current filtered devices"""
        table = self.query_one("#device_table")
        table.clear()

        for device in self.filtered_devices:
            status_style = self._get_status_style(device.status)

            table.add_row(
                device.host_name,
                device.ip_address,
                device.device_type.capitalize(),
                device.platform,
                device.location or "Unknown",
                device.status,
                device.last_check.strftime("%H:%M:%S") if device.last_check else "Never",
                key=device.ip_address,
                style=status_style
            )

    def _get_status_style(self, status: str) -> str:
        """Get display style based on device status"""
        status_styles = {
            'reachable': 'green',
            'connected': 'green',
            'unreachable': 'red',
            'disconnected': 'red',
            'error': 'red',
            'unknown': 'yellow'
        }
        return status_styles.get(status.lower(), 'white')

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
                    search_term in device.host_name.lower() or
                    search_term in device.ip_address or
                    search_term in (device.platform or "").lower() or
                    search_term in (device.location or "").lower()
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

        self.query_one("#count_text").update(f"{len(filtered)}/{len(self.devices)} devices")

    def on_data_table_row_selected(self, event):
        """Handle device row selection"""
        if event.row_key and event.row_key.value:
            device_ip = event.row_key.value
            device = next((d for d in self.filtered_devices if d.ip_address == device_ip), None)
            if device:
                self.selected_device = device
                self.post_message(DeviceSelected(device))

    def action_refresh(self):
        """Refresh device list"""
        self._refresh_devices()

    async def action_test_connectivity(self):
        """Test connectivity to all devices"""
        if self.loading:
            return

        self.loading = True
        self.query_one("#test_all_btn").disabled = True
        self.query_one("#status_text").update("Testing connectivity...", style="yellow")

        inventory_service = InventoryService()
        devices = inventory_service.get_all_devices()

        # Test each device
        reachable_count = 0
        for i, device in enumerate(devices):
            self.query_one("#status_text").update(
                f"Testing {device.ip_address} ({i+1}/{len(devices)})..."
            )
            if inventory_service.test_device_connectivity(device):
                reachable_count += 1
            # Update table after each test
            self._update_table()
            await asyncio.sleep(0.1)  # Small delay for UI updates

        self.loading = False
        self.query_one("#test_all_btn").disabled = False
        self.query_one("#status_text").update(
            f"Connectivity test complete: {reachable_count}/{len(devices)} reachable",
            style="green" if reachable_count > 0 else "red"
        )

    def action_search_focus(self):
        """Focus on search input"""
        self.query_one("#search_input").focus()

    def on_button_pressed(self, event):
        """Handle button press events"""
        if event.button.id == "refresh_btn":
            self.action_refresh()
        elif event.button.id == "test_all_btn":
            asyncio.create_task(self.action_test_connectivity())