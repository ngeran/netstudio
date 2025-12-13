"""
Simple Inventory Manager - User-Friendly Device Management
Redesigned to match Smart Template Manager layout for no-scroll experience
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Button, DataTable, Static, Input, Select, Label
from textual.reactive import reactive
from textual import work
from typing import Optional
import os
import yaml
from pathlib import Path
from .save_as_dialog import SaveAsDialog


class SimpleInventoryManager(Screen):
    """User-friendly inventory management for network devices"""

    CSS = """
    SimpleInventoryManager {
        background: $background;
    }

    .main-layout {
        height: 1fr;
        layout: grid;
        grid-size: 2 1;
        grid-columns: 1fr 1fr;
        padding: 1;
    }

    .left-column {
        height: 1fr;
        padding: 0 1 0 0;
    }

    .right-column {
        height: 1fr;
        padding: 0 0 0 1;
    }

    .compact-header {
        height: auto;
        background: $surface;
        border: heavy $primary;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    .file-selector {
        height: auto;
        background: $surface;
        border: tall $panel;
        padding: 1;
        margin: 0 0 1 0;
    }

    .table-area {
        height: 2fr;
        background: $surface;
        border: tall $panel;
        padding: 1;
    }

    .form-area {
        height: 1fr;
        background: $surface;
        border: tall $panel;
        padding: 1;
    }

    .section-title {
        text-style: bold;
        color: $primary;
        padding: 0 0 0 0;
        margin: 0;
    }

    .subtitle {
        color: $text-muted;
        padding: 0;
        margin: 0;
    }

    .form-row {
        height: auto;
        padding: 0;
        margin: 0 0 0 0;
    }

    .form-row Label {
        width: 18;
        color: $text;
        padding: 0 1 0 0;
    }

    .form-row Input {
        width: 1fr;
    }

    .form-row Select {
        width: 1fr;
        min-width: 20;
        background: $surface;
        border: tall $primary;
    }

    .compact-buttons {
        height: auto;
        padding: 1 0 0 0;
        margin: 0;
    }

    .compact-buttons Button {
        margin: 0 0 0 1;
    }

    .file-controls {
        height: auto;
        padding: 0;
        margin: 0;
    }

    .file-controls Button {
        margin: 0 0 0 1;
    }

    .selector-row {
        height: auto;
    }

    .selector-row Label {
        width: 12;
        padding: 0 1 0 0;
    }

    .selector-row Select {
        width: 1fr;
    }

    .selector-row Button {
        margin: 0 0 0 1;
    }

    .file-display {
        color: $text-muted;
        padding: 0;
        margin: 0 0 1 0;
    }

    .action-bar {
        height: auto;
        background: $surface;
        border: tall $panel;
        padding: 1;
        margin: 0 0 1 0;
    }

    .action-bar Button {
        margin: 0 1 0 0;
    }

    #device_table {
        height: 1fr;
    }
    """

    selected_device_ip: reactive[Optional[str]] = reactive(None)
    devices: reactive[list] = reactive([])
    current_file: reactive[Optional[str]] = reactive(None)

    def __init__(self, inventory_service, api_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service
        self.inventories_dir = Path(os.getenv("VECTOR_PY_DIR", ".")) / "data" / "inventories"
        self.inventories_dir.mkdir(parents=True, exist_ok=True)

    def compose(self) -> ComposeResult:
        yield Header()

        # Compact header at the top
        with Horizontal(classes="compact-header"):
            yield Static("📋 Inventory Manager", classes="section-title")
            yield Static(" | Manage Network Devices", classes="subtitle")

        # Two-column layout like Smart Template Manager
        with Horizontal(classes="main-layout"):
            # LEFT COLUMN: File selector + Device table
            with Vertical(classes="left-column"):
                # File selector (compact)
                with Vertical(classes="file-selector"):
                    yield Static("Step 1: Select Inventory File", classes="section-title")

                    with Horizontal(classes="selector-row"):
                        yield Label("File:")
                        yield Select(
                            options=[("-- New Inventory --", "NEW")],
                            id="select_inventory_file",
                            value="NEW",
                            allow_blank=False
                        )
                        yield Button("📂 Load", id="btn_load_file", variant="primary")

                    yield Static("", id="current_file_display", classes="file-display")

                    with Horizontal(classes="file-controls"):
                        yield Button("💾 Save", id="btn_save_current", variant="success")
                        yield Button("💾 Save As...", id="btn_save_as", variant="default")

                # Device table (takes most of the space)
                with Vertical(classes="table-area"):
                    yield Static("Step 2: Select Device", classes="section-title")
                    yield DataTable(id="device_table", zebra_stripes=True)

                # Action buttons (compact)
                with Horizontal(classes="action-bar"):
                    yield Button("➕ New", id="btn_new", variant="primary")
                    yield Button("✏️ Edit", id="btn_edit", variant="default")
                    yield Button("🗑️ Delete", id="btn_delete", variant="error")
                    yield Button("📊 Facts", id="btn_facts", variant="default")
                    yield Button("📡 Ping", id="btn_ping", variant="default")

            # RIGHT COLUMN: Device form
            with Vertical(classes="right-column"):
                with Vertical(classes="form-area"):
                    yield Static("Step 3: Device Details", classes="section-title")
                    yield Static("Fill in device information (* = required)", classes="subtitle")

                    with Horizontal(classes="form-row"):
                        yield Label("* Hostname:")
                        yield Input(placeholder="router1", id="input_hostname")

                    with Horizontal(classes="form-row"):
                        yield Label("* IP Address:")
                        yield Input(placeholder="192.168.1.1", id="input_ip")

                    with Horizontal(classes="form-row"):
                        yield Label("Device Type:")
                        yield Select(
                            options=[
                                ("Router", "router"),
                                ("Switch", "switch"),
                                ("Firewall", "firewall"),
                            ],
                            id="select_type",
                            value="router",
                            allow_blank=False
                        )

                    with Horizontal(classes="form-row"):
                        yield Label("Platform:")
                        yield Input(placeholder="junos", id="input_platform", value="junos")

                    with Horizontal(classes="form-row"):
                        yield Label("Location:")
                        yield Input(placeholder="Data Center A", id="input_location")

                    with Horizontal(classes="form-row"):
                        yield Label("Username:")
                        yield Input(placeholder="admin", id="input_username", value="admin")

                    with Horizontal(classes="form-row"):
                        yield Label("Password:")
                        yield Input(placeholder="password", id="input_password", password=True, value="password")

                # Form action buttons
                with Horizontal(classes="compact-buttons"):
                    yield Button("✅ Add/Update", id="btn_add_update", variant="success")
                    yield Button("🔄 Clear", id="btn_clear", variant="default")

        yield Footer()

    def on_mount(self):
        """Initialize when mounted"""
        self._setup_table()
        self._load_available_files()
        self.notify("Welcome! Select a file or start new inventory 🚀", severity="information")

    def _setup_table(self):
        """Setup the device table"""
        table = self.query_one("#device_table", DataTable)
        table.add_columns(
            "☑",
            "Hostname",
            "IP Address",
            "Type",
            "Platform",
            "Location",
            "Status"
        )
        table.cursor_type = "row"

    def _load_available_files(self):
        """Load list of available inventory files"""
        try:
            # Get all YAML files in inventories directory
            yaml_files = list(self.inventories_dir.glob("*.yml")) + list(self.inventories_dir.glob("*.yaml"))

            options = [("-- New Inventory --", "NEW")]
            for file in sorted(yaml_files):
                options.append((file.name, str(file)))

            select = self.query_one("#select_inventory_file", Select)
            select.set_options(options)

        except Exception as e:
            self.notify(f"Error loading file list: {e}", severity="error")

    def _load_inventory_from_file(self, file_path: str):
        """Load devices from a specific YAML file"""
        try:
            # Verify file exists
            if not Path(file_path).exists():
                self.notify(f"File not found: {file_path}", severity="error")
                return

            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            # Check if data is valid
            if not data:
                self.notify(f"File is empty or invalid YAML: {Path(file_path).name}", severity="error")
                return

            if 'devices' not in data:
                self.notify(f"File does not contain 'devices' key: {Path(file_path).name}", severity="error")
                return

            # Convert to Device objects
            from tui.models.device import Device
            devices = []
            for device_data in data.get('devices', []):
                device = Device(
                    host_name=device_data.get('hostname', ''),
                    ip_address=device_data.get('ip_address', ''),
                    device_type=device_data.get('device_type', 'router'),
                    platform=device_data.get('platform', 'junos'),
                    username=device_data.get('username', 'admin'),
                    password=device_data.get('password', 'password')
                )
                device.location = device_data.get('location', 'Unknown')
                devices.append(device)

            self.devices = devices
            self.current_file = file_path
            self._refresh_table()

            file_name = Path(file_path).name
            self.query_one("#current_file_display", Static).update(f"📄 {file_name}")
            self.notify(f"Loaded {len(devices)} devices from {file_name}", severity="success")

        except FileNotFoundError:
            self.notify(f"File not found: {Path(file_path).name}", severity="error")
            self.devices = []
        except yaml.YAMLError as e:
            self.notify(f"Invalid YAML format: {e}", severity="error")
            self.devices = []
        except Exception as e:
            self.notify(f"Error loading file: {e}", severity="error")
            self.devices = []

    def _refresh_table(self):
        """Refresh the device table"""
        table = self.query_one("#device_table", DataTable)
        table.clear()

        for device in self.devices:
            is_selected = device.ip_address == self.selected_device_ip
            select_mark = "☑" if is_selected else "☐"

            table.add_row(
                select_mark,
                device.host_name or "Unknown",
                device.ip_address,
                device.device_type.capitalize() if hasattr(device, 'device_type') else "Router",
                device.platform or "junos",
                getattr(device, 'location', 'Unknown'),
                "⚪ Unknown",
                key=device.ip_address
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Handle row selection"""
        table = self.query_one("#device_table", DataTable)
        row_key = event.row_key

        # Toggle selection
        if self.selected_device_ip == row_key.value:
            self.selected_device_ip = None
        else:
            self.selected_device_ip = row_key.value
            self._populate_form_with_device(row_key.value)

        self._refresh_table()

    def _populate_form_with_device(self, ip_address: str):
        """Populate form with selected device data"""
        device = next((d for d in self.devices if d.ip_address == ip_address), None)
        if not device:
            return

        self.query_one("#input_hostname", Input).value = device.host_name or ""
        self.query_one("#input_ip", Input).value = device.ip_address or ""
        self.query_one("#input_platform", Input).value = device.platform or "junos"
        self.query_one("#input_location", Input).value = getattr(device, 'location', '')
        self.query_one("#input_username", Input).value = getattr(device, 'username', 'admin')
        self.query_one("#input_password", Input).value = getattr(device, 'password', 'password')

        if hasattr(device, 'device_type'):
            self.query_one("#select_type", Select).value = device.device_type

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button clicks"""
        button_id = event.button.id

        if button_id == "btn_load_file":
            self._load_selected_file()

        elif button_id == "btn_save_as":
            self._save_inventory_as()

        elif button_id == "btn_new":
            self._clear_form()
            self.selected_device_ip = None
            self._refresh_table()
            self.notify("Ready to add new device", severity="information")

        elif button_id == "btn_edit":
            if not self.selected_device_ip:
                self.notify("Please select a device first", severity="warning")
            else:
                self.notify("Edit the form and click 'Add/Update Device'", severity="information")

        elif button_id == "btn_delete":
            if not self.selected_device_ip:
                self.notify("Please select a device to delete", severity="warning")
            else:
                self._delete_device()

        elif button_id == "btn_save_current":
            self._save_inventory()

        elif button_id == "btn_facts":
            if not self.selected_device_ip:
                self.notify("Please select a device first", severity="warning")
            else:
                self._get_facts()

        elif button_id == "btn_ping":
            if not self.selected_device_ip:
                self.notify("Please select a device first", severity="warning")
            else:
                self._ping_test()

        elif button_id == "btn_add_update":
            self._add_or_update_device()

        elif button_id == "btn_clear":
            self._clear_form()

    def _clear_form(self):
        """Clear all form fields"""
        self.query_one("#input_hostname", Input).value = ""
        self.query_one("#input_ip", Input).value = ""
        self.query_one("#input_platform", Input).value = "junos"
        self.query_one("#input_location", Input).value = ""
        self.query_one("#input_username", Input).value = "admin"
        self.query_one("#input_password", Input).value = "password"
        self.query_one("#select_type", Select).value = "router"

    def _add_or_update_device(self):
        """Add new device or update existing"""
        hostname = self.query_one("#input_hostname", Input).value.strip()
        ip = self.query_one("#input_ip", Input).value.strip()
        device_type = self.query_one("#select_type", Select).value
        platform = self.query_one("#input_platform", Input).value.strip()
        location = self.query_one("#input_location", Input).value.strip()
        username = self.query_one("#input_username", Input).value.strip()
        password = self.query_one("#input_password", Input).value.strip()

        # Validation
        if not hostname:
            self.notify("Hostname is required", severity="error")
            return
        if not ip:
            self.notify("IP Address is required", severity="error")
            return

        # Create device object (simple dict for now)
        from tui.models.device import Device
        device = Device(
            host_name=hostname,
            ip_address=ip,
            device_type=device_type,
            platform=platform,
            username=username,
            password=password
        )
        device.location = location

        # Check if updating existing
        existing = next((i for i, d in enumerate(self.devices) if d.ip_address == ip), None)

        if existing is not None:
            self.devices[existing] = device
            self.notify(f"Updated device: {hostname}", severity="success")
        else:
            self.devices.append(device)
            self.notify(f"Added device: {hostname}", severity="success")

        self._refresh_table()
        self._clear_form()

    def _delete_device(self):
        """Delete selected device"""
        if not self.selected_device_ip:
            return

        device = next((d for d in self.devices if d.ip_address == self.selected_device_ip), None)
        if device:
            self.devices.remove(device)
            self.notify(f"Deleted device: {device.host_name}", severity="success")
            self.selected_device_ip = None
            self._refresh_table()
            self._clear_form()

    def _load_selected_file(self):
        """Load the selected inventory file"""
        select = self.query_one("#select_inventory_file", Select)
        file_value = select.value

        # Handle Select.BLANK or None
        if file_value is Select.BLANK or file_value is None:
            self.notify("Please select a file from the dropdown", severity="warning")
            return

        if file_value == "NEW":
            # Start fresh
            self.devices = []
            self.current_file = None
            self._refresh_table()
            self.query_one("#current_file_display", Static).update("📄 New Inventory")
            self.notify("Started new inventory - add devices below", severity="information")
        else:
            # Load existing file
            self._load_inventory_from_file(file_value)

    def _save_inventory(self):
        """Save inventory to current file or prompt for new file"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self._save_inventory_as()

    def _save_inventory_as(self):
        """Save inventory with a custom filename using a dialog"""
        # Create default filename based on current file or timestamp
        default_name = ""
        if self.current_file:
            # Use current filename without extension as default
            default_name = Path(self.current_file).stem
        else:
            # Generate timestamp-based default
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"inventory_{timestamp}"

        # Create and show the Save As dialog
        dialog = SaveAsDialog(
            current_filename=default_name,
            inventories_dir=self.inventories_dir
        )

        # Handle the result when the dialog is closed
        def handle_save_result(result):
            if result:  # User didn't cancel
                file_path = self.inventories_dir / result
                self._save_to_file(str(file_path))
                self._load_available_files()  # Refresh file list

                # Update the file selector to show the new file
                select = self.query_one("#select_inventory_file", Select)
                select.value = str(file_path)

        # Set up a callback to handle the result
        self.app.push_screen(dialog, handle_save_result)

    def _save_to_file(self, file_path: str):
        """Save inventory to specific file"""
        try:
            # Convert devices to dict format
            devices_data = []
            for device in self.devices:
                device_dict = {
                    'hostname': device.host_name,
                    'ip_address': device.ip_address,
                    'device_type': device.device_type if hasattr(device, 'device_type') else 'router',
                    'platform': device.platform or 'junos',
                    'location': getattr(device, 'location', 'Unknown'),
                    'username': getattr(device, 'username', 'admin'),
                    'password': getattr(device, 'password', 'password'),
                }
                devices_data.append(device_dict)

            # Save to YAML
            with open(file_path, 'w') as f:
                yaml.dump({'devices': devices_data}, f, default_flow_style=False, sort_keys=False)

            self.current_file = file_path
            file_name = Path(file_path).name
            self.query_one("#current_file_display", Static).update(f"📄 {file_name}")
            self.notify(f"✅ Saved {len(devices_data)} devices to {file_name}", severity="success")

        except Exception as e:
            self.notify(f"❌ Error saving inventory: {e}", severity="error")

    @work(exclusive=True)
    async def _get_facts(self):
        """Get device facts for selected device"""
        if not self.selected_device_ip:
            return

        device = next((d for d in self.devices if d.ip_address == self.selected_device_ip), None)
        if not device:
            return

        self.notify(f"Getting facts from {device.host_name}...", severity="information")

        try:
            # Mock implementation - replace with actual PyEZ call
            import asyncio
            await asyncio.sleep(1)

            self.notify(
                f"Facts retrieved from {device.host_name}:\n"
                f"  Model: MX204\n"
                f"  Version: 21.4R1\n"
                f"  Serial: ABC123456",
                severity="information"
            )
        except Exception as e:
            self.notify(f"Error getting facts: {e}", severity="error")

    @work(exclusive=True)
    async def _ping_test(self):
        """Ping test selected device"""
        if not self.selected_device_ip:
            return

        device = next((d for d in self.devices if d.ip_address == self.selected_device_ip), None)
        if not device:
            return

        self.notify(f"Pinging {device.host_name} ({device.ip_address})...", severity="information")

        try:
            import subprocess
            result = subprocess.run(
                ['ping', '-c', '3', device.ip_address],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.notify(f"✅ {device.host_name} is reachable!", severity="success")
            else:
                self.notify(f"❌ {device.host_name} is NOT reachable", severity="error")

        except Exception as e:
            self.notify(f"Error pinging device: {e}", severity="error")