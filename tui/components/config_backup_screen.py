"""
Config Backup Screen - User-Friendly Configuration Backup and Restore
Designed for network engineers with no coding experience
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static, DataTable, Select, Label, Input, TextArea
from textual.reactive import reactive
from textual.screen import ModalScreen

# Import legacy functions
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class HostCredentialsModal(ModalScreen):
    """Modal screen for host entry and credentials input"""

    def __init__(self, inventory_files=None):
        super().__init__()
        self.hosts = []
        self.username = ""
        self.password = ""
        self.inventory_files = inventory_files or []

    def compose(self) -> ComposeResult:
        with Container(id="modal_container"):
            yield Static("🖥️ Device Configuration", classes="section-title")
            yield Static("Configure device hosts and credentials for backup operations", classes="subtitle")

            # Host input method
            yield Static("📝 Host Input Method:", classes="section-title")
            yield Select(
                options=[
                    ("Manual Entry", "manual"),
                    ("From Inventory File", "inventory")
                ],
                id="host_input_method",
                value="manual",
                allow_blank=False
            )

            # Manual host entry
            with Vertical(id="manual_host_section"):
                yield Static("Enter device information (one per line):", id="manual_instruction")
                yield Static("Format: hostname:ip_address")
                yield TextArea(
                    placeholder="router1:192.168.1.1\nswitch1:192.168.1.2\nrouter2:192.168.1.3",
                    id="manual_hosts_input",
                    language="text"
                )

            # Inventory file selection
            with Vertical(id="inventory_file_section", classes="hidden"):
                yield Static("Select inventory file:")
                if self.inventory_files:
                    yield Select(
                        options=self.inventory_files,
                        id="inventory_file_select",
                        value=self.inventory_files[0][1] if self.inventory_files else "none",
                        allow_blank=False
                    )
                else:
                    yield Select(
                        options=[("-- No inventory files found --", "none")],
                        id="inventory_file_select",
                        value="none",
                        allow_blank=False
                    )

            # Credentials
            yield Static("🔐 Device Credentials:", classes="section-title")
            yield Label("Username:")
            yield Input(
                placeholder="admin",
                id="username_input"
            )
            yield Label("Password:")
            yield Input(
                placeholder="Enter password",
                password=True,
                id="password_input"
            )

            # Buttons
            with Horizontal():
                yield Button("✅ Confirm", id="btn_confirm", variant="success")
                yield Button("❌ Cancel", id="btn_cancel", variant="error")

    def on_select_changed(self, event: Select.Changed):
        """Handle host input method change"""
        manual_section = self.query_one("#manual_host_section", Vertical)
        inventory_section = self.query_one("#inventory_file_section", Vertical)

        if event.value == "manual":
            manual_section.remove_class("hidden")
            inventory_section.add_class("hidden")
        else:
            manual_section.add_class("hidden")
            inventory_section.remove_class("hidden")

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_confirm":
            method_select = self.query_one("#host_input_method", Select)

            if method_select.value == "manual":
                hosts_input = self.query_one("#manual_hosts_input", TextArea)
                hosts_text = hosts_input.text.strip()
                if not hosts_text:
                    self.notify("Please enter at least one device", severity="warning")
                    return

                # Parse lines of hostname:ip format
                self.hosts = []
                for line in hosts_text.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Parse hostname:ip or just IP
                        if ":" in line:
                            parts = line.split(":", 1)
                            hostname = parts[0].strip()
                            ip = parts[1].strip()
                            # Store as tuple for later processing
                            self.hosts.append({"hostname": hostname, "ip": ip})
                        else:
                            # Just IP address - generate hostname
                            ip = line.strip()
                            hostname = f"device-{len(self.hosts) + 1}"
                            self.hosts.append({"hostname": hostname, "ip": ip})
            else:
                file_select = self.query_one("#inventory_file_select", Select)
                if file_select.value == "none":
                    self.notify("Please select an inventory file", severity="warning")
                    return
                self.hosts = self._extract_hosts_from_inventory(file_select.value)

            username_input = self.query_one("#username_input", Input)
            password_input = self.query_one("#password_input", Input)

            if not username_input.value.strip():
                self.notify("Please enter a username", severity="warning")
                return

            if not password_input.value:
                self.notify("Please enter a password", severity="warning")
                return

            self.username = username_input.value.strip()
            self.password = password_input.value

            self.dismiss({"hosts": self.hosts, "username": self.username, "password": self.password})

        elif event.button.id == "btn_cancel":
            self.dismiss(None)

    def _extract_hosts_from_inventory(self, inventory_path):
        """Extract host information from inventory file"""
        try:
            import yaml
            with open(inventory_path, "r") as f:
                data = yaml.safe_load(f)

            hosts = []

            # Handle inventory files format from SimpleInventoryManager
            if isinstance(data, dict) and "devices" in data:
                for device in data["devices"]:
                    if isinstance(device, dict):
                        # Try different IP field names
                        ip = device.get("ip_address") or device.get("ip") or device.get("host_ip")
                        hostname = device.get("hostname") or device.get("host_name") or device.get("name") or f"device-{len(hosts) + 1}"
                        if ip:
                            hosts.append({"hostname": hostname, "ip": ip})
            else:
                # Legacy format handling
                if isinstance(data, dict):
                    # Check for hosts_data.yml format
                    for location in data.get("inventory", []):
                        for router in location.get("routers", []):
                            if router.get("ip_address"):
                                hostname = router.get("host_name") or router.get("name") or f"router-{len(hosts) + 1}"
                                hosts.append({"hostname": hostname, "ip": router["ip_address"]})
                        for switch in location.get("switches", []):
                            if switch.get("ip_address"):
                                hostname = switch.get("host_name") or switch.get("name") or f"switch-{len(hosts) + 1}"
                                hosts.append({"hostname": hostname, "ip": switch["ip_address"]})

                    # Check for simple device list format
                    if not hosts and "devices" in data:
                        for device in data["devices"]:
                            if isinstance(device, dict) and device.get("ip"):
                                ip = device.get("ip")
                                hostname = device.get("hostname") or device.get("name") or f"device-{len(hosts) + 1}"
                                hosts.append({"hostname": hostname, "ip": ip})
                            elif isinstance(device, str):
                                hosts.append({"hostname": f"device-{len(hosts) + 1}", "ip": device})

            return hosts
        except Exception as e:
            logger.error(f"Error extracting hosts from inventory: {e}")
            return []


class ConfigBackupScreen(Screen):
    """User-friendly configuration backup and restore screen"""

    selected_devices: reactive[List[str]] = reactive([])
    backup_mode: reactive[str] = reactive("backup")

    def __init__(self, inventory_service, api_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service
        self.device_credentials = {}  # {ip_address: {"username": "", "password": ""}}
        self.all_devices = []  # List of all available devices

    CSS = """
    ConfigBackupScreen {
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

    .template-selector {
        height: auto;
        background: $surface;
        border: tall $panel;
        padding: 1;
        margin: 0 0 1 0;
    }

    .form-area {
        height: 1fr;
        background: $surface;
        border: tall $panel;
        padding: 1;
    }

    .preview-area {
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

    .compact-buttons {
        height: auto;
        padding: 1 0 0 0;
        margin: 0;
    }

    .compact-buttons Button {
        margin: 0 0 0 1;
    }

    #device_table {
        height: 1fr;
    }

    #progress_table {
        height: 1fr;
    }

    #progress_table DataTable {
        width: 1fr;
    }

    #progress_table .datatable--header {
        background: $primary;
        color: $text;
    }

    #progress_table .datatable--odd-row {
        background: $surface;
    }

    #progress_table .datatable--even-row {
        background: $panel;
    }

    /* Modal styles */
    HostCredentialsModal {
        align: center middle;
    }

    #modal_container {
        background: $surface;
        border: thick $primary;
        padding: 2;
    }

    #modal_container Static.section-title {
        text-align: center;
        margin-bottom: 1;
    }

    #modal_container Label {
        margin: 1 0 0 0;
    }

    #modal_container Input {
        width: 100%;
        margin: 0 0 1 0;
    }

    #modal_container Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    #modal_container TextArea {
        width: 100%;
        height: 10;
        margin: 0 0 1 0;
        border: solid $primary;
    }

    .hidden {
        display: none;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()

        # Compact header at the top
        with Horizontal(classes="compact-header"):
            yield Static("💾 Configuration Backup & Restore", classes="section-title")
            yield Static(" | Your Network Safety Net", classes="subtitle")

        # Two-column layout
        with Horizontal(classes="main-layout"):
            # LEFT COLUMN: Device selection
            with Vertical(classes="left-column"):
                # Device selection (Step 1)
                with Vertical(classes="form-area"):
                    yield Static("🖥️ Step 1: Select Devices", classes="section-title")
                    yield Static("Choose devices for backup/restore operations", classes="subtitle")

                    yield DataTable(id="device_table", zebra_stripes=True)

                    yield Static(f"Selected: 0 devices", id="device_count")

                    with Horizontal(classes="compact-buttons"):
                        yield Button("⚙️ Configure Devices", id="btn_configure_devices", variant="primary")
                        yield Button("✅ Select All", id="btn_select_all", variant="success")
                        yield Button("🔄 Clear All", id="btn_clear", variant="default")

                # Action area (Step 3)
                with Vertical(classes="form-area"):
                    yield Static("🚀 Step 3: Execute Operation", classes="section-title")
                    yield Static("Choose and start your operation", classes="subtitle")

                    with Horizontal(classes="compact-buttons"):
                        yield Button("💾 Backup", id="btn_start_backup", variant="success")
                        yield Button("🔄 Restore", id="btn_start_restore", variant="warning")
                        yield Button("🔍 Compare", id="btn_start_compare", variant="primary")

                    yield Static("", id="operation_info")

            # RIGHT COLUMN: File operations and progress
            with Vertical(classes="right-column"):
                # File selector (Step 2, for restore/compare)
                with Vertical(classes="template-selector", id="restore_file_section"):
                    yield Static("📁 Step 2: Select Backup File", classes="section-title")
                    yield Static("Choose backup file (for restore/compare operations)", classes="subtitle")
                    yield Select(
                        options=[("-- No backup files found --", "none")],
                        id="backup_file_select",
                        value="none",
                        allow_blank=False
                    )
                    yield Static("", id="file_info")

                    with Horizontal(classes="compact-buttons"):
                        yield Button("📂 Open Folder", id="btn_open_folder", variant="default")

                # Progress tracking (Step 4)
                with Vertical(classes="preview-area"):
                    yield Static("📈 Step 4: Operation Progress", classes="section-title")
                    yield Static("Real-time progress tracking", classes="subtitle")

                    yield DataTable(id="progress_table", zebra_stripes=True)

                    with Horizontal(classes="compact-buttons"):
                        yield Button("🗑️ Clear History", id="btn_clear_history", variant="error")
                        yield Button("📋 Export Log", id="btn_export_log", variant="default")

        yield Footer()

    def on_mount(self):
        """Initialize when mounted"""
        self._setup_device_table()
        self._setup_progress_table()
        self._refresh_device_selection()
        self._load_backup_files()
        # Set default mode to backup
        self.backup_mode = "backup"
        self._update_ui_for_mode()
        self.notify("Welcome! Configure devices and select operation 🚀", severity="information")

    def _setup_device_table(self):
        """Setup the device selection table"""
        table = self.query_one("#device_table", DataTable)
        table.add_columns("☑", "Hostname", "IP Address", "Device Type", "Credentials")
        table.cursor_type = "row"

    def _setup_progress_table(self):
        """Setup the progress tracking table"""
        table = self.query_one("#progress_table", DataTable)
        table.add_columns("Device", "Status", "Details")
        # Set column widths
        table.zebra_stripes = True

    def _refresh_device_selection(self):
        """Refresh the device selection table"""
        table = self.query_one("#device_table", DataTable)
        table.clear()

        for device in self.all_devices:
            checkbox = "☑" if device["ip_address"] in self.selected_devices else "☐"

            # Check credentials status
            if device["ip_address"] in self.device_credentials:
                credentials_status = "✅ Configured"
            else:
                credentials_status = "❌ Not set"

            table.add_row(
                checkbox,
                device["host_name"],
                device["ip_address"],
                device["device_type"],
                credentials_status,
                key=device["ip_address"]
            )

        # Update count
        count_widget = self.query_one("#device_count", Static)
        count_widget.update(f"📊 Selected: {len(self.selected_devices)} of {len(self.all_devices)} devices")

    def _load_backup_files(self):
        """Load available backup files"""
        try:
            backups_dir = Path(os.getenv("VECTOR_PY_DIR", ".")) / "data" / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)

            backup_files = list(backups_dir.glob("**/*.conf"))
            backup_files.extend(list(backups_dir.glob("**/*.txt")))
            backup_files.extend(list(backups_dir.glob("**/*.cfg")))

            if backup_files:
                options = []
                for file in sorted(backup_files, key=lambda f: f.stat().st_mtime, reverse=True):
                    relative_path = file.relative_to(backups_dir)
                    display_name = f"{relative_path} ({self._format_file_time(file.stat().st_mtime)})"
                    options.append((display_name, str(file)))
            else:
                options = [("-- No backup files found --", "none")]

            select = self.query_one("#backup_file_select", Select)
            select.set_options(options)

        except Exception as e:
            logger.error(f"Error loading backup files: {e}")

    def _format_file_time(self, timestamp):
        """Format file timestamp for display"""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")

    def _update_ui_for_mode(self):
        """Update UI based on selected mode"""
        restore_section = self.query_one("#restore_file_section", Vertical)
        operation_info = self.query_one("#operation_info", Static)

        if self.backup_mode == "backup":
            restore_section.add_class("hidden")
            operation_info.update(
                "💾 **Backup Operation**\n\n"
                "• Save current configuration from selected devices\n"
                "• Files will be saved with timestamps\n"
                "• Safe operation - no changes to devices"
            )
        elif self.backup_mode == "restore":
            restore_section.remove_class("hidden")
            operation_info.update(
                "⚠️ **Restore Operation**\n\n"
                "• Replace device configuration with backup file\n"
                "• **DANGER**: This will change running config!\n"
                "• Ensure backup file is compatible"
            )
        elif self.backup_mode == "compare":
            restore_section.remove_class("hidden")
            operation_info.update(
                "🔍 **Compare Operation**\n\n"
                "• Show differences between configs\n"
                "• Compare running config vs backup file\n"
                "• Safe - no changes to devices"
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        """Handle device row highlight - toggle selection"""
        if event.data_table.id == "device_table":
            self._toggle_device_selection(event.data_table, event.cursor_row, event.row_key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Handle device row selection - toggle selection"""
        if event.data_table.id == "device_table":
            self._toggle_device_selection(event.data_table, event.cursor_row, event.row_key)

    def _toggle_device_selection(self, table: DataTable, cursor_row, row_key):
        """Toggle device selection state"""
        try:
            current_cell = table.get_cell_at((cursor_row, 0))
            new_state = "☑" if current_cell == "☐" else "☐"
            table.update_cell_at((cursor_row, 0), new_state)

            ip_address = str(row_key) if isinstance(row_key, str) else row_key.value

            if new_state == "☑":
                if ip_address not in self.selected_devices:
                    self.selected_devices.append(ip_address)
            else:
                if ip_address in self.selected_devices:
                    self.selected_devices.remove(ip_address)

            # Update count
            count_widget = self.query_one("#device_count", Static)
            count_widget.update(f"📊 Selected: {len(self.selected_devices)} of {len(self.all_devices)} devices")

        except Exception as e:
            logger.error(f"Error toggling device selection: {e}")

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn_refresh_devices":
            self._refresh_devices()
        elif button_id == "btn_configure_devices":
            await self._configure_devices()
        elif button_id == "btn_start_backup":
            self.backup_mode = "backup"
            await self._start_operation()
        elif button_id == "btn_start_restore":
            self.backup_mode = "restore"
            await self._start_operation()
        elif button_id == "btn_start_compare":
            self.backup_mode = "compare"
            await self._start_operation()
        elif button_id == "btn_clear":
            self._clear_selection()
        elif button_id == "btn_select_all":
            self._select_all_devices()
        elif button_id == "btn_open_folder":
            self._open_backups_folder()
        elif button_id == "btn_clear_history":
            self._clear_history()
        elif button_id == "btn_export_log":
            self._export_log()

    def _refresh_devices(self):
        """Refresh device list"""
        self.notify("Device list refreshed", severity="success")
        self._refresh_device_selection()

    async def _configure_devices(self):
        """Configure devices and credentials"""
        try:
            # Load inventory files first
            inventory_files = await self._get_inventory_files()

            # Create modal with inventory files pre-loaded
            modal = HostCredentialsModal(inventory_files=inventory_files)

            # Use push_screen with a callback
            def modal_callback(result):
                if result:
                    # Clear existing devices and credentials
                    self.all_devices = []
                    self.device_credentials = {}

                    # Add new devices
                    for host_data in result["hosts"]:
                        # Handle both dict format (hostname, ip) and string format (just ip)
                        if isinstance(host_data, dict):
                            hostname = host_data.get("hostname", "unknown")
                            ip = host_data.get("ip", host_data.get("ip_address"))
                        else:
                            # Legacy format - just IP string
                            ip = host_data
                            hostname = f"device-{len(self.all_devices) + 1}"

                        device_type = "router"  # Default type

                        # Try to determine device type based on hostname
                        hostname_lower = hostname.lower()
                        if "switch" in hostname_lower or "sw" in hostname_lower:
                            device_type = "switch"
                        elif "firewall" in hostname_lower or "srx" in hostname_lower or "fw" in hostname_lower:
                            device_type = "firewall"

                        self.all_devices.append({
                            "host_name": hostname,
                            "ip_address": ip,
                            "device_type": device_type
                        })

                        # Store credentials for each device
                        self.device_credentials[ip] = {
                            "username": result["username"],
                            "password": result["password"]
                        }

                    self._refresh_device_selection()
                    self.notify(f"Configured {len(self.all_devices)} devices with credentials", severity="success")
                else:
                    self.notify("Device configuration cancelled", severity="information")

            self.app.push_screen(modal, modal_callback)

        except Exception as e:
            logger.error(f"Error configuring devices: {e}")
            self.notify(f"Error configuring devices: {e}", severity="error")

    async def _get_inventory_files(self):
        """Get list of available inventory files"""
        try:
            inventories_dir = Path(os.getenv("VECTOR_PY_DIR", ".")) / "data" / "inventories"
            inventories_dir.mkdir(parents=True, exist_ok=True)

            inventory_files = []

            # Look for YAML files in inventories directory
            for pattern in ["*.yml", "*.yaml"]:
                for file in sorted(inventories_dir.glob(pattern)):
                    inventory_files.append((file.name, str(file)))

            if not inventory_files:
                return [("-- No inventory files found --", "none")]

            return inventory_files

        except Exception as e:
            logger.error(f"Error getting inventory files: {e}")
            return [("-- Error loading files --", "none")]

    def _clear_selection(self):
        """Clear all selections"""
        self.selected_devices = []
        self._refresh_device_selection()
        self.notify("Device selection cleared", severity="information")

    def _select_all_devices(self):
        """Select all available devices"""
        if not self.all_devices:
            self.notify("No devices configured. Please configure devices first.", severity="warning")
            return

        self.selected_devices = [device["ip_address"] for device in self.all_devices]
        self._refresh_device_selection()
        self.notify(f"Selected all {len(self.selected_devices)} devices", severity="success")

    def _clear_history(self):
        """Clear operation history"""
        table = self.query_one("#progress_table", DataTable)
        table.clear()
        self.notify("Operation history cleared", severity="information")

    def _export_log(self):
        """Export operation log to file"""
        self.notify("Log export feature not yet implemented", severity="warning")

    def _open_backups_folder(self):
        """Open backups folder"""
        import subprocess
        import platform

        try:
            backups_dir = Path(os.getenv("VECTOR_PY_DIR", ".")) / "data" / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)

            if platform.system() == "Windows":
                subprocess.run(["explorer", str(backups_dir)], check=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(backups_dir)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(backups_dir)], check=True)

            self.notify(f"Opened backups folder: {backups_dir}", severity="success")
        except Exception as e:
            self.notify(f"Could not open folder: {e}", severity="error")

    async def _start_operation(self):
        """Start the selected operation"""
        if not self.all_devices:
            self.notify("No devices configured. Please configure devices first.", severity="warning")
            return

        if not self.selected_devices:
            self.notify("Please select at least one device", severity="warning")
            return

        # Check credentials for selected devices
        missing_credentials = []
        for device_ip in self.selected_devices:
            if device_ip not in self.device_credentials:
                missing_credentials.append(device_ip)

        if missing_credentials:
            self.notify(f"Missing credentials for: {', '.join(missing_credentials)}. Please configure devices first.", severity="warning")
            return

        if self.backup_mode in ["restore", "compare"]:
            file_select = self.query_one("#backup_file_select", Select)
            if file_select.value == "none":
                self.notify("Please select a backup file", severity="warning")
                return

        # Start actual operation
        table = self.query_one("#progress_table", DataTable)
        table.clear()

        if self.backup_mode == "backup":
            await self._perform_backup_operation(table)
        elif self.backup_mode == "restore":
            await self._perform_restore_operation(table)
        elif self.backup_mode == "compare":
            await self._perform_compare_operation(table)

        self.notify(f"{self.backup_mode.title()} operation completed!", severity="success")

    async def _perform_backup_operation(self, table):
        """Perform the actual backup operation"""
        try:
            from scripts.connect_to_hosts import connect_to_hosts
            from lxml import etree
            import json

            # Clear table first
            table.clear()
            logger.info("Starting backup operation - progress table cleared")
            self.notify("Starting backup operation...", severity="information")

            # Check if WebSocket is available
            websocket_connected = False
            if hasattr(self, 'api_service') and self.api_service:
                websocket_connected = self.api_service.client.is_websocket_connected()
                logger.info(f"WebSocket status: {'Connected' if websocket_connected else 'Not connected'}")

            backups_dir = Path(os.getenv("VECTOR_PY_DIR", ".")) / "data" / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Backup directory: {backups_dir}")

            logger.info(f"Starting backup for {len(self.selected_devices)} devices: {self.selected_devices}")

            for device_ip in self.selected_devices:
                # Add initial row for this device
                table.add_row(device_ip, "⏳", "Starting backup...")
                row_index = len(table.rows) - 1
                logger.info(f"Added row for device {device_ip} at index {row_index}")

                try:
                    credentials = self.device_credentials[device_ip]

                    # Update status with refresh
                    def update_progress(status, details, icon="⏳"):
                        table.update_cell_at((row_index, 0), device_ip)
                        table.update_cell_at((row_index, 1), icon)
                        table.update_cell_at((row_index, 2), details)
                        # Try to force UI refresh with multiple methods
                        try:
                            table.bell()  # Notify TUI of changes
                            self.bell()    # Also notify screen
                            self.app.bell()  # Also notify app

                            # Try to manually trigger a redraw
                            table._invalidate_layout()
                            table._refresh_layout()

                            # Log for debugging
                            logger.info(f"Progress update for {device_ip}: [{icon}] {details}")
                            logger.info(f"Table rows count: {len(table.rows)}")

                            # Verify the update was applied
                            try:
                                cell0 = table.get_cell_at((row_index, 0))
                                cell1 = table.get_cell_at((row_index, 1))
                                cell2 = table.get_cell_at((row_index, 2))
                                logger.info(f"✓ Row {row_index} content verified: {cell0}, {cell1}, {cell2}")
                            except Exception as e:
                                logger.error(f"Could not verify row content: {e}")
                        except Exception as e:
                            logger.error(f"Error in update_progress: {e}")

                    update_progress("", f"Connecting to {device_ip}...")
                    await asyncio.sleep(0.2)  # Small delay to ensure UI updates

                    # Connect to device
                    connections = connect_to_hosts(device_ip, credentials["username"], credentials["password"])
                    if not connections:
                        update_progress("", "Connection failed", "❌")
                        continue

                    dev = connections[0]

                    # Update status
                    update_progress("", f"Successfully connected to {device_ip}", "✅")
                    await asyncio.sleep(0.3)  # Let user see the success

                    # Generate timestamp for all backup files
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # XML backup
                    update_progress("", "Backing up XML configuration...")
                    await asyncio.sleep(0.3)

                    config_xml = dev.rpc.get_config()
                    backup_file_xml = backups_dir / f"{device_ip}_config_{timestamp}.xml"
                    with open(backup_file_xml, "w") as f:
                        f.write(etree.tostring(config_xml, pretty_print=True).decode())

                    update_progress("", f"✅ XML saved: {backup_file_xml.name}")
                    await asyncio.sleep(0.3)

                    # Set format backup
                    update_progress("", "Backing up set commands...")
                    await asyncio.sleep(0.3)

                    config_set = dev.rpc.get_config(options={"format": "set"})
                    backup_file_set = backups_dir / f"{device_ip}_config_{timestamp}.set"
                    with open(backup_file_set, "w") as f:
                        # Legacy approach - check if it's a dict first
                        if isinstance(config_set, dict):
                            f.write(config_set.get("output", ""))
                        else:
                            # Check for text attribute
                            if hasattr(config_set, 'text') and config_set.text is not None:
                                f.write(config_set.text)
                            else:
                                # Try to get the text content differently
                                f.write(str(config_set))

                    update_progress("", f"✅ SET saved: {backup_file_set.name}")
                    await asyncio.sleep(0.3)

                    # JSON backup
                    update_progress("", "Backing up JSON configuration...")
                    await asyncio.sleep(0.3)

                    config_json = dev.rpc.get_config(options={"format": "json"})
                    backup_file_json = backups_dir / f"{device_ip}_config_{timestamp}.json"
                    with open(backup_file_json, "w") as f:
                        if isinstance(config_json, dict):
                            f.write(json.dumps(config_json, indent=4))
                        else:
                            # Check for text attribute
                            if hasattr(config_json, 'text') and config_json.text is not None:
                                f.write(config_json.text)
                            else:
                                f.write(str(config_json))

                    # Final success with shortened path for display
                    short_path = str(backups_dir)
                    if len(short_path) > 50:
                        short_path = "..." + short_path[-47:]

                    update_progress("", f"✅ Backup complete! Files in: {short_path}", "✅")
                    logger.info(f"Backup successful: {backup_file_xml}, {backup_file_set}, {backup_file_json}")

                    # Show notification with summary
                    self.notify(
                        f"✅ Backup completed for {device_ip}\n\n"
                        f"Files saved:\n"
                        f"• {backup_file_xml.name}\n"
                        f"• {backup_file_set.name}\n"
                        f"• {backup_file_json.name}\n\n"
                        f"Location: {backups_dir}",
                        severity="success"
                    )

                    # Close connection
                    dev.close()

                except Exception as e:
                    logger.error(f"Failed to backup {device_ip}: {e}")
                    update_progress("", f"❌ Error: {str(e)}", "❌")
                    self.notify(f"Failed to backup {device_ip}: {str(e)}", severity="error")
                    try:
                        dev.close()
                    except:
                        pass

        except Exception as e:
            logger.error(f"Backup operation error: {e}")
            self.notify(f"Backup operation failed: {e}", severity="error")

    async def _perform_restore_operation(self, table):
        """Perform restore operation"""
        try:
            from scripts.connect_to_hosts import connect_to_hosts
            from jnpr.junos.utils.config import Config

            # Get selected backup file
            file_select = self.query_one("#backup_file_select", Select)
            if file_select.value == "none":
                self.notify("Please select a backup file to restore", severity="warning")
                return

            backup_file_path = file_select.value

            # Clear table first
            table.clear()

            for device_ip in self.selected_devices:
                # Add initial row for this device
                table.add_row(device_ip, "⏳", "Starting restore...")
                row_index = len(table.rows) - 1

                dev = None
                try:
                    credentials = self.device_credentials[device_ip]

                    # Update status
                    table.update_cell_at((row_index, 1), "⏳")
                    table.update_cell_at((row_index, 2), "Connecting to device...")

                    # Connect to device
                    connections = connect_to_hosts(device_ip, credentials["username"], credentials["password"])
                    if not connections:
                        table.update_cell_at((row_index, 1), "❌")
                        table.update_cell_at((row_index, 2), "Connection failed")
                        continue

                    dev = connections[0]

                    # Update status
                    table.update_cell_at((row_index, 1), "⏳")
                    table.update_cell_at((row_index, 2), "Preparing restore...")

                    # Check if backup file exists
                    if not Path(backup_file_path).exists():
                        table.update_cell_at((row_index, 1), "❌")
                        table.update_cell_at((row_index, 2), "Backup file not found")
                        continue

                    # Read backup file
                    with open(backup_file_path, 'r') as f:
                        config_data = f.read()

                    # Update status
                    table.update_cell_at((row_index, 1), "⚠️")
                    table.update_cell_at((row_index, 2), "WARNING: About to restore configuration!")

                    # Log the restore operation
                    logger.warning(f"Restoring configuration to {device_ip} from {backup_file_path}")

                    # For safety, we'll just prepare the restore (following legacy pattern)
                    # In production, uncomment the actual restore commands:
                    try:
                        cu = Config(dev)

                        # Determine format based on file extension
                        if backup_file_path.endswith('.set'):
                            table.update_cell_at((row_index, 1), "⚠️")
                            table.update_cell_at((row_index, 2), "Loading set format configuration...")
                            # cu.load(config_data, format="set", overwrite=True)
                        elif backup_file_path.endswith('.xml'):
                            table.update_cell_at((row_index, 1), "⚠️")
                            table.update_cell_at((row_index, 2), "Loading XML format configuration...")
                            # cu.load(config_data, format="xml", overwrite=True)
                        else:
                            table.update_cell_at((row_index, 1), "⚠️")
                            table.update_cell_at((row_index, 2), "Loading text format configuration...")
                            # cu.load(config_data, format="text", overwrite=True)

                        # Uncomment in production:
                        # cu.commit()
                        # table.update_cell_at((row_index, 1), "✅")
                        # table.update_cell_at((row_index, 2), "Configuration restored successfully!")

                        # For safety, just show prepared
                        table.update_cell_at((row_index, 1), "⚠️")
                        table.update_cell_at((row_index, 2), "Restore prepared (manual confirmation needed)")

                    except Exception as restore_e:
                        logger.error(f"Restore preparation error: {restore_e}")
                        table.update_cell_at((row_index, 1), "❌")
                        table.update_cell_at((row_index, 2), f"Restore prep failed: {str(restore_e)[:50]}...")

                    self.notify(f"Restore prepared for {device_ip}. Configuration length: {len(config_data)} chars", severity="warning")

                except Exception as e:
                    logger.error(f"Failed to restore {device_ip}: {e}")
                    table.update_cell_at((row_index, 1), "❌")
                    table.update_cell_at((row_index, 2), f"Error: {str(e)[:50]}...")
                finally:
                    if dev:
                        try:
                            dev.close()
                        except:
                            pass

            # Inform user about safety
            self.notify(
                "⚠️ Restore operation prepared!\n\n"
                "For safety, actual restore is not performed automatically.\n"
                "Please verify the backup file before applying configuration changes.",
                severity="warning"
            )

        except Exception as e:
            logger.error(f"Restore operation error: {e}")
            self.notify(f"Restore operation error: {e}", severity="error")

    async def _perform_compare_operation(self, table):
        """Perform compare operation (placeholder)"""
        self.notify("Compare operation not yet implemented", severity="warning")