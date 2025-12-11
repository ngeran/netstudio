"""
Inventory YAML Editor Component
Create and edit device inventory YAML files
"""

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static, TextArea, Input, Label, Select, Checkbox
from textual.reactive import reactive
from textual.binding import Binding
from typing import Dict, Any, List
import yaml
import os


class InventoryEditor(Container):
    """Inventory YAML file editor"""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+n", "new_device", "New Device"),
        Binding("escape", "back", "Back"),
    ]

    current_file: reactive[str] = reactive("")
    modified: reactive[bool] = reactive(False)

    def __init__(self, inventory_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.current_inventory = {"devices": []}

    def compose(self):
        """Compose the inventory editor UI"""

        yield Static("📋 Inventory Editor", classes="header-title")

        # Top toolbar
        with Horizontal(classes="toolbar"):
            yield Button("💾 Save", id="save_btn", variant="success")
            yield Button("➕ New Device", id="new_device_btn", variant="primary")
            yield Button("📂 Load", id="load_btn", variant="default")
            yield Button("🗑️ Delete Device", id="delete_btn", variant="error")
            yield Button("🔄 Reload", id="reload_btn", variant="default")
            yield Static("", id="file_status", classes="file-status")

        # Main content area - split view
        with Horizontal(classes="split-view"):
            # Left: Device form
            with Vertical(classes="device-form-panel"):
                yield Static("Device Details", classes="section-title")

                yield Label("Device Name:")
                yield Input(placeholder="core-router-1", id="device_name")

                yield Label("IP Address:")
                yield Input(placeholder="192.168.1.1", id="ip_address")

                yield Label("Username:")
                yield Input(placeholder="admin", id="username")

                yield Label("Password:")
                yield Input(placeholder="password", password=True, id="password")

                yield Label("Device Type:")
                yield Select(
                    options=[
                        ("Router", "router"),
                        ("Switch", "switch"),
                        ("Firewall", "firewall"),
                    ],
                    value="router",
                    id="device_type",
                )

                yield Label("Platform:")
                yield Input(placeholder="junos", id="platform")

                yield Label("Vendor:")
                yield Input(placeholder="juniper", id="vendor")

                yield Label("Location:")
                yield Input(placeholder="datacenter1", id="location")

                yield Label("Description:")
                yield Input(placeholder="Core router", id="description")

                with Horizontal(classes="form-actions"):
                    yield Button(
                        "➕ Add to Inventory", id="add_device_btn", variant="primary"
                    )
                    yield Button(
                        "🔄 Clear Form", id="clear_form_btn", variant="default"
                    )

            # Right: YAML preview
            with Vertical(classes="yaml-preview-panel"):
                yield Static("YAML Preview", classes="section-title")

                yield TextArea(
                    "", id="yaml_preview", language="yaml", classes="yaml-editor"
                )

                yield Static("", id="yaml_status", classes="yaml-status")

        # Status bar
        yield Static("", id="status_message", classes="status-message")

    def on_mount(self):
        """Initialize when mounted"""
        self._load_current_inventory()
        self._update_yaml_preview()

    def _load_current_inventory(self):
        """Load the current inventory file"""
        try:
            data_dir = os.path.join(os.getenv("VECTOR_PY_DIR", "."), "data")
            inventory_file = os.path.join(data_dir, "inventory.yml")

            if os.path.exists(inventory_file):
                with open(inventory_file, "r") as f:
                    self.current_inventory = yaml.safe_load(f) or {"devices": []}
                    self.current_file = inventory_file

                    file_status = self.query_one("#file_status")
                    file_status.update(f"📂 {os.path.basename(inventory_file)}")

                self._show_success(
                    f"Loaded {len(self.current_inventory.get('devices', []))} devices"
                )
            else:
                self.current_inventory = {"devices": []}
                self._show_info("No inventory file found. Start adding devices!")

        except Exception as e:
            self._show_error(f"Error loading inventory: {e}")
            self.current_inventory = {"devices": []}

    def _update_yaml_preview(self):
        """Update the YAML preview"""
        try:
            yaml_text = yaml.dump(
                self.current_inventory, default_flow_style=False, sort_keys=False
            )
            self.query_one("#yaml_preview").text = yaml_text

            device_count = len(self.current_inventory.get("devices", []))
            self.query_one("#yaml_status").update(
                f"✅ {device_count} device{'s' if device_count != 1 else ''} in inventory"
            )
        except Exception as e:
            self._show_error(f"Error generating YAML: {e}")

    def _get_form_data(self) -> Dict[str, Any]:
        """Get data from the form"""
        return {
            "name": self.query_one("#device_name").value,
            "ip_address": self.query_one("#ip_address").value,
            "username": self.query_one("#username").value,
            "password": self.query_one("#password").value,
            "device_type": self.query_one("#device_type").value,
            "platform": self.query_one("#platform").value,
            "vendor": self.query_one("#vendor").value,
            "location": self.query_one("#location").value,
            "description": self.query_one("#description").value,
        }

    def _clear_form(self):
        """Clear the form fields"""
        self.query_one("#device_name").value = ""
        self.query_one("#ip_address").value = ""
        self.query_one("#username").value = ""
        self.query_one("#password").value = ""
        self.query_one("#platform").value = ""
        self.query_one("#vendor").value = ""
        self.query_one("#location").value = ""
        self.query_one("#description").value = ""

    def _add_device(self):
        """Add device from form to inventory"""
        device = self._get_form_data()

        # Validate required fields
        if not device["name"] or not device["ip_address"]:
            self._show_error("Device name and IP address are required!")
            return

        # Check for duplicate
        existing_ips = [
            d.get("ip_address") for d in self.current_inventory.get("devices", [])
        ]
        if device["ip_address"] in existing_ips:
            self._show_error(f"Device with IP {device['ip_address']} already exists!")
            return

        # Add to inventory
        if "devices" not in self.current_inventory:
            self.current_inventory["devices"] = []

        self.current_inventory["devices"].append(device)
        self.modified = True

        # Update preview
        self._update_yaml_preview()
        self._clear_form()

        self._show_success(f"Added device: {device['name']}")

    def _save_inventory(self):
        """Save inventory to file"""
        try:
            data_dir = os.path.join(os.getenv("VECTOR_PY_DIR", "."), "data")
            os.makedirs(data_dir, exist_ok=True)

            inventory_file = os.path.join(data_dir, "inventory.yml")

            with open(inventory_file, "w") as f:
                yaml.dump(
                    self.current_inventory, f, default_flow_style=False, sort_keys=False
                )

            self.modified = False
            self.current_file = inventory_file

            file_status = self.query_one("#file_status")
            file_status.update(f"📂 {os.path.basename(inventory_file)} ✅")

            self._show_success(f"Saved inventory to {os.path.basename(inventory_file)}")

        except Exception as e:
            self._show_error(f"Error saving inventory: {e}")

    def _show_success(self, message: str):
        """Show success message"""
        status = self.query_one("#status_message")
        status.update(f"✅ {message}")
        status.add_class("status-online")

    def _show_error(self, message: str):
        """Show error message"""
        status = self.query_one("#status_message")
        status.update(f"❌ {message}")
        status.add_class("status-error")

    def _show_info(self, message: str):
        """Show info message"""
        status = self.query_one("#status_message")
        status.update(f"ℹ️ {message}")
        status.add_class("label-info")

    def on_button_pressed(self, event):
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "save_btn":
            self.action_save()
        elif button_id == "new_device_btn":
            self.action_new_device()
        elif button_id == "load_btn":
            self._load_current_inventory()
            self._update_yaml_preview()
        elif button_id == "reload_btn":
            self._load_current_inventory()
            self._update_yaml_preview()
        elif button_id == "add_device_btn":
            self._add_device()
        elif button_id == "clear_form_btn":
            self._clear_form()
        elif button_id == "delete_btn":
            self.app.notify(
                "Delete feature: Select device from list first", severity="warning"
            )

    def action_save(self):
        """Save action"""
        self._save_inventory()

    def action_new_device(self):
        """New device action"""
        self._clear_form()
        self._show_info("Fill in the form to add a new device")

    def action_back(self):
        """Go back"""
        if self.modified:
            self.app.notify(
                "You have unsaved changes! Press Ctrl+S to save", severity="warning"
            )
        self.app.pop_screen()
