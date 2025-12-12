"""
Horizontal Menu Bar Component
Top navigation bar with quick access to all features
"""

from textual.containers import Horizontal
from textual.widgets import Button, Static
from textual.reactive import reactive


class MenuBar(Horizontal):
    """Horizontal menu bar for top navigation"""

    active_menu: reactive[str] = reactive("dashboard")

    def __init__(self):
        super().__init__(classes="menu-bar")

    def compose(self):
        """Compose the menu bar"""

        # Logo/Title
        yield Static("🌃 NetStudio", classes="menu-logo")

        # Menu items
        yield Button(
            "🏠 Dashboard",
            id="menu_dashboard",
            variant="primary",
            classes="menu-button",
        )
        yield Button(
            "📱 Devices", id="menu_devices", variant="default", classes="menu-button"
        )
        yield Button(
            "📝 Templates",
            id="menu_templates",
            variant="default",
            classes="menu-button",
        )
        yield Button(
            "📋 Inventory",
            id="menu_inventory",
            variant="default",
            classes="menu-button",
        )
        yield Button(
            "💾 Backup", id="menu_backup", variant="default", classes="menu-button"
        )
        yield Button(
            "📸 State", id="menu_state", variant="default", classes="menu-button"
        )
        yield Button(
            "📊 Routes", id="menu_routes", variant="default", classes="menu-button"
        )
        yield Button("🔀 BGP", id="menu_bgp", variant="default", classes="menu-button")
        yield Button(
            "⬆️ Upgrade", id="menu_upgrade", variant="default", classes="menu-button"
        )
        yield Button(
            "⚙️ Config", id="menu_config", variant="default", classes="menu-button"
        )
        yield Button(
            "❓ Help", id="menu_help", variant="default", classes="menu-button"
        )
        yield Button(
            "🎨 Theme", id="menu_theme", variant="default", classes="menu-button"
        )

        # Right side - Status indicators
        yield Static("", id="connection_status", classes="menu-status")
        yield Static("", id="device_count", classes="menu-status")

    def on_mount(self):
        """Initialize when mounted"""
        self._update_connection_status()
        self._update_device_count()

    def _update_connection_status(self):
        """Update API connection status"""
        try:
            status_widget = self.query_one("#connection_status")
            # Check if API is connected (would need actual API service reference)
            status_widget.update("🟢 API")
            status_widget.add_class("status-online")
        except Exception:
            pass

    def _update_device_count(self):
        """Update device count"""
        try:
            count_widget = self.query_one("#device_count")
            # Would get actual count from inventory service
            count_widget.update("📊 Devices: --")
        except Exception:
            pass

    def on_button_pressed(self, event):
        """Handle menu button presses"""
        button_id = event.button.id

        # Update active state
        self._set_active_menu(button_id)

        # Trigger navigation
        if button_id == "menu_dashboard":
            self.app.action_dashboard()
        elif button_id == "menu_devices":
            self.app.action_devices()
        elif button_id == "menu_templates":
            self.app.action_templates()
        elif button_id == "menu_inventory":
            self.app.action_inventory()
        elif button_id == "menu_backup":
            self.app.action_backup()
        elif button_id == "menu_state":
            self.app.action_state_capture()
        elif button_id == "menu_routes":
            self.app.action_route_monitor()
        elif button_id == "menu_bgp":
            self.app.action_bgp_toolbox()
        elif button_id == "menu_upgrade":
            self.app.action_code_upgrade()
        elif button_id == "menu_config":
            self.app.action_config()
        elif button_id == "menu_help":
            self.app.action_help()
        elif button_id == "menu_theme":
            self.app.action_theme_selector()

    def _set_active_menu(self, menu_id: str):
        """Set the active menu item"""
        # Remove active class from all buttons
        for button in self.query(".menu-button"):
            button.variant = "default"

        # Set active button
        try:
            active_button = self.query_one(f"#{menu_id}")
            active_button.variant = "primary"
        except Exception:
            pass
