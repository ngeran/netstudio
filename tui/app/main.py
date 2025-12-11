"""
Network Automation TUI - Main Application

A modern Terminal User Interface for Juniper network device management.
Built with Textual for network engineers who prefer terminal environments.
"""

import sys
import os
import asyncio
from pathlib import Path
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, ListView, ListItem, Label
from textual.binding import Binding
from textual.reactive import reactive
from textual.events import Mount

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tui.services.inventory_service import InventoryService
from tui.models.device import Device
from tui.services.api_client import APIService


class NetworkAutomationApp(App):
    """Main TUI application for network automation"""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        text-align: center;
        text-style: bold;
        background: $primary;
    }

    .menu-container {
        margin: 1;
    }

    .menu-item {
        padding: 1;
        border: solid $primary;
        margin: 1 0;
    }

    .menu-item:hover {
        background: $primary;
        color: $text;
    }

    .status-bar {
        dock: bottom;
        height: 3;
        background: $panel;
        color: $text;
    }

    .version-info {
        text-align: right;
        padding: 0 1;
    }

    .device-count {
        padding: 0 1;
    }
    """

    TITLE = "Network Automation TUI"
    SUB_TITLE = "Juniper Device Management"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "devices", "Devices"),
        Binding("t", "templates", "Templates"),
        Binding("c", "config", "Config"),
        Binding("h", "help", "Help"),
    ]

    inventory_service: reactive[InventoryService] = reactive(InventoryService())
    device_count: reactive[int] = reactive(0)
    api_service: reactive[APIService] = reactive(APIService())

    def on_mount(self) -> None:
        """Initialize the application when mounted"""
        self.title = f"{self.TITLE} - Phase 2"
        self.sub_title = self.SUB_TITLE

        # Load inventory
        try:
            devices = self.inventory_service.load_devices()
            self.device_count = len(devices)
            self.notify(f"Loaded {self.device_count} devices from inventory", severity="information")
        except Exception as e:
            self.notify(f"Failed to load inventory: {e}", severity="error")
            self.device_count = 0

        # Start API service
        asyncio.create_task(self._start_api_service())

    async def _start_api_service(self):
        """Start the API service in background"""
        try:
            success = await self.api_service.start()
            if success:
                self.notify("Connected to API backend", severity="information")
            else:
                self.notify("Failed to connect to API backend", severity="warning")
        except Exception as e:
            self.notify(f"Error starting API service: {e}", severity="error")

    def compose(self) -> ComposeResult:
        """Create the main application layout"""
        yield Header()

        with Container(classes="menu-container"):
            yield Static("Main Menu", classes="menu-item")

            menu_items = [
                ("📱 Device Management", "devices", self.show_device_management),
                ("📝 Template Editor", "templates", self.show_template_editor),
                ("⚙️ Configuration Deploy", "config", self.show_configuration_deploy),
                ("🔍 Device Discovery", "discovery", self.show_device_discovery),
                ("📊 System Status", "status", self.show_system_status),
                ("❓ Help & Documentation", "help", self.show_help),
            ]

            for label, button_id, callback in menu_items:
                yield Button(label, id=button_id, classes="menu-item")

        yield Footer()

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()

    def action_devices(self) -> None:
        """Navigate to device management"""
        self.show_device_management()

    def action_templates(self) -> None:
        """Navigate to templates"""
        self.show_template_editor()

    def action_config(self) -> None:
        """Navigate to configuration"""
        self.show_configuration_deploy()

    def action_help(self) -> None:
        """Show help information"""
        self.show_help()

    def show_device_management(self) -> None:
        """Navigate to device management screen"""
        self.push_screen(DeviceManagementScreen(self.inventory_service, self.api_service))

    def show_template_editor(self) -> None:
        """Navigate to template editor screen"""
        self.push_screen(TemplateEditorScreen())

    def show_configuration_deploy(self) -> None:
        """Navigate to configuration deployment screen"""
        self.push_screen(ConfigurationDeployScreen(self.inventory_service, self.api_service))

    def show_device_discovery(self) -> None:
        """Navigate to device discovery screen"""
        self.push_screen(DeviceDiscoveryScreen())

    def show_system_status(self) -> None:
        """Navigate to system status screen"""
        self.push_screen(SystemStatusScreen())

    def show_help(self) -> None:
        """Navigate to help screen"""
        self.push_screen(HelpScreen())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events"""
        button_id = event.button.id

        navigation_map = {
            "devices": self.show_device_management,
            "templates": self.show_template_editor,
            "config": self.show_configuration_deploy,
            "discovery": self.show_device_discovery,
            "status": self.show_system_status,
            "help": self.show_help,
        }

        if button_id in navigation_map:
            navigation_map[button_id]()


# Import components and services
from tui.components.device_browser import DeviceBrowser
from tui.components.interface_template_editor import InterfaceTemplateEditor
from tui.components.enhanced_device_browser import EnhancedDeviceBrowser
from tui.components.config_deployment import ConfigDeployment


class DeviceManagementScreen(Screen):
    """Device management screen"""

    def __init__(self, inventory_service: InventoryService, api_service: APIService):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service

    def compose(self) -> ComposeResult:
        yield Header("Device Management")
        with Container(classes="main-container"):
            yield Static("Browse and manage network devices with real-time operations")
            yield EnhancedDeviceBrowser(self.inventory_service, self.api_service)
        yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


class TemplateEditorScreen(Screen):
    """Template editor screen"""

    def compose(self) -> ComposeResult:
        yield Header("Template Editor")
        with Container(classes="main-container"):
            yield InterfaceTemplateEditor()
        yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


class ConfigurationDeployScreen(Screen):
    """Configuration deployment screen"""

    def __init__(self, inventory_service: InventoryService, api_service: APIService):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service

    def compose(self) -> ComposeResult:
        yield Header("Configuration Deployment")
        with Container(classes="main-container"):
            yield ConfigDeployment(self.inventory_service, self.api_service)
        yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


class DeviceDiscoveryScreen(Screen):
    """Device discovery screen"""

    def compose(self) -> ComposeResult:
        yield Header("Device Discovery")
        yield Static("Discover and add new devices")
        yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


class SystemStatusScreen(Screen):
    """System status screen"""

    def compose(self) -> ComposeResult:
        yield Header("System Status")
        yield Static("View system and application status")
        yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


class HelpScreen(Screen):
    """Help and documentation screen"""

    def compose(self) -> ComposeResult:
        yield Header("Help & Documentation")

        with Container():
            yield Static("Network Automation TUI - Phase 2", classes="help-title")
            yield Static("")
            yield Static("Keyboard Shortcuts:")
            yield Static("  q - Quit application")
            yield Static("  d - Device Management")
            yield Static("  t - Template Editor")
            yield Static("  c - Configuration Deploy")
            yield("  s - API Status")
            yield Static("  h - Help")
            yield Static("")
            yield Static("Navigation:")
            yield Static("  - Use arrow keys or tab to navigate")
            yield Static("  - Press Enter to select")
            yield Static("  - Press Escape to go back")
            yield Static("")
            yield Static("Features in Phase 1:")
            yield Static("  ✓ Device inventory management")
            yield Static("  ✓ Template editing interface")
            yield Static("  ✓ Configuration preview")
            yield Static("  ✓ Basic connectivity testing")
            yield Static("")
            yield Static("New in Phase 2:")
            yield Static("  ✨ Real-time API backend")
            yield Static("  ✨ Multi-device parallel operations")
            yield Static("  ✨ WebSocket progress tracking")
            yield Static("  ✨ Enhanced device browser")
            yield Static("  ✨ Configuration deployment with rollback")
            yield Static("  ✨ PyEZ integration (mock available)")
            yield Static("")
            yield Static("API Status:")
            yield Static("  🟢 Connected - Full functionality")
            yield Static("  🟡 Disconnected - Limited functionality")

        yield Button("Back", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


if __name__ == "__main__":
    app = NetworkAutomationApp()
    app.run()