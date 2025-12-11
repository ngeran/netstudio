"""
Comprehensive Dashboard Component for NetStudio TUI
Provides overview of devices, recent activity, quick actions, and system stats
"""

from textual.containers import Container, Horizontal, Vertical, Grid
from textual.widgets import Static, Button, DataTable, Label, ProgressBar
from textual.reactive import reactive
from datetime import datetime
from typing import List, Dict, Any
import os


class StatCard(Container):
    """A card displaying a statistic"""

    def __init__(self, title: str, value: str, icon: str = "📊", classes: str = ""):
        super().__init__(classes=f"stat-card {classes}")
        self.title = title
        self.value = value
        self.icon = icon

    def compose(self):
        yield Static(f"{self.icon} {self.title}", classes="stat-title")
        yield Static(self.value, classes="stat-value")


class QuickAction(Button):
    """Quick action button"""

    def __init__(
        self, label: str, action_id: str, icon: str = "⚡", variant: str = "default"
    ):
        super().__init__(f"{icon} {label}", id=action_id, variant=variant)


class Dashboard(Container):
    """Comprehensive dashboard home screen"""

    # Reactive properties
    total_devices: reactive[int] = reactive(0)
    online_devices: reactive[int] = reactive(0)
    offline_devices: reactive[int] = reactive(0)
    routers: reactive[int] = reactive(0)
    switches: reactive[int] = reactive(0)
    firewalls: reactive[int] = reactive(0)

    def __init__(self, inventory_service, api_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service

    def compose(self):
        """Compose the dashboard UI"""

        # Welcome header
        yield Static("🌃 Network Automation Dashboard", classes="dashboard-title")
        yield Static(
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            classes="dashboard-subtitle",
        )

        # Stats cards row
        with Horizontal(classes="stats-row"):
            yield StatCard("Total Devices", "0", "🖥️", "card-primary")
            yield StatCard("Online", "0", "🟢", "card-success")
            yield StatCard("Offline", "0", "🔴", "card-error")
            yield StatCard("Routers", "0", "🌐", "card-info")
            yield StatCard("Switches", "0", "🔀", "card-info")
            yield StatCard("Firewalls", "0", "🔥", "card-warning")

        # Main content grid
        with Grid(classes="dashboard-grid"):
            # Left column - Quick Actions
            with Vertical(classes="dashboard-panel quick-actions-panel"):
                yield Static("⚡ Quick Actions", classes="panel-title")

                with Vertical(classes="quick-actions-grid"):
                    yield QuickAction(
                        "Device Browser", "action_devices", "📱", "primary"
                    )
                    yield QuickAction(
                        "Create Template", "action_create_template", "📝", "success"
                    )
                    yield QuickAction(
                        "Edit Inventory", "action_edit_inventory", "📋", "default"
                    )
                    yield QuickAction("Deploy Config", "action_deploy", "🚀", "primary")
                    yield QuickAction(
                        "Backup Configs", "action_backup", "💾", "default"
                    )
                    yield QuickAction(
                        "Run Diagnostics", "action_diagnostics", "🔍", "default"
                    )
                    yield QuickAction("View Logs", "action_logs", "📄", "default")
                    yield QuickAction("API Status", "action_api", "🔌", "default")

            # Middle column - Recent Activity
            with Vertical(classes="dashboard-panel recent-activity-panel"):
                yield Static("📊 Recent Activity", classes="panel-title")

                yield DataTable(
                    id="recent_activity_table",
                    zebra_stripes=True,
                    classes="activity-table",
                )

            # Right column - System Status
            with Vertical(classes="dashboard-panel system-status-panel"):
                yield Static("⚙️ System Status", classes="panel-title")

                # API Connection Status
                with Horizontal(classes="status-row"):
                    yield Label("API Server:")
                    yield Static("Checking...", id="api_status_indicator")

                # Inventory Status
                with Horizontal(classes="status-row"):
                    yield Label("Inventory:")
                    yield Static("", id="inventory_status")

                # Templates Status
                with Horizontal(classes="status-row"):
                    yield Label("Templates:")
                    yield Static("", id="templates_status")

                # Disk Space
                with Horizontal(classes="status-row"):
                    yield Label("Disk Space:")
                    yield Static("", id="disk_status")

                yield Static("", classes="spacer")

                # Quick Stats
                yield Static("📈 Quick Stats", classes="subsection-title")
                yield Static("", id="quick_stats")

        # Bottom status bar
        with Horizontal(classes="dashboard-footer"):
            yield Static(
                "Press F1 for help | Tab to navigate | Enter to select",
                classes="footer-help",
            )
            yield Static("", id="system_time", classes="footer-time")

    def on_mount(self):
        """Initialize dashboard when mounted"""
        self._setup_activity_table()
        self._load_statistics()
        self._check_system_status()
        self._populate_recent_activity()
        self._update_time()

    def _setup_activity_table(self):
        """Setup the recent activity table"""
        table = self.query_one("#recent_activity_table")
        table.add_columns("Time", "Action", "Status")

    def _load_statistics(self):
        """Load device statistics"""
        try:
            devices = self.inventory_service.load_devices()
            self.total_devices = len(devices)

            # Count device types
            self.routers = len([d for d in devices if d.device_type == "router"])
            self.switches = len([d for d in devices if d.device_type == "switch"])
            self.firewalls = len([d for d in devices if d.device_type == "firewall"])

            # Update stat cards
            self._update_stat_cards()

        except Exception as e:
            self._show_error(f"Error loading statistics: {e}")

    def _update_stat_cards(self):
        """Update the statistics cards with current values"""
        # This would be done by updating the StatCard widgets
        # For now, we'll update them when they're created
        pass

    def _check_system_status(self):
        """Check and display system status"""
        # API Status
        try:
            if self.api_service.client.is_connected():
                api_status = self.query_one("#api_status_indicator")
                api_status.update("🟢 Connected")
                api_status.add_class("status-online")
            else:
                api_status = self.query_one("#api_status_indicator")
                api_status.update("🔴 Disconnected")
                api_status.add_class("status-error")
        except Exception:
            pass

        # Inventory Status
        try:
            data_dir = os.path.join(os.getenv("VECTOR_PY_DIR", "."), "data")
            inventory_file = os.path.join(data_dir, "inventory.yml")

            if os.path.exists(inventory_file):
                size = os.path.getsize(inventory_file)
                inv_status = self.query_one("#inventory_status")
                inv_status.update(f"✅ Loaded ({size} bytes)")
                inv_status.add_class("status-online")
            else:
                inv_status = self.query_one("#inventory_status")
                inv_status.update("⚠️ Not found")
                inv_status.add_class("status-warning")
        except Exception as e:
            inv_status = self.query_one("#inventory_status")
            inv_status.update(f"❌ Error")
            inv_status.add_class("status-error")

        # Templates Status
        try:
            templates_dir = os.path.join(os.getenv("VECTOR_PY_DIR", "."), "templates")
            if os.path.exists(templates_dir):
                template_count = len(
                    [f for f in os.listdir(templates_dir) if f.endswith(".j2")]
                )
                temp_status = self.query_one("#templates_status")
                temp_status.update(f"✅ {template_count} templates")
                temp_status.add_class("status-online")
            else:
                temp_status = self.query_one("#templates_status")
                temp_status.update("⚠️ Directory not found")
                temp_status.add_class("status-warning")
        except Exception:
            temp_status = self.query_one("#templates_status")
            temp_status.update("❌ Error")
            temp_status.add_class("status-error")

        # Disk Status
        try:
            import shutil

            stat = shutil.disk_usage("/")
            used_percent = (stat.used / stat.total) * 100
            disk_status = self.query_one("#disk_status")

            if used_percent > 90:
                disk_status.update(f"⚠️ {used_percent:.1f}% used")
                disk_status.add_class("status-error")
            elif used_percent > 75:
                disk_status.update(f"⚠️ {used_percent:.1f}% used")
                disk_status.add_class("status-warning")
            else:
                disk_status.update(f"✅ {used_percent:.1f}% used")
                disk_status.add_class("status-online")
        except Exception:
            pass

        # Quick Stats
        try:
            stats_text = f"""
Devices: {self.total_devices}
Routers: {self.routers}
Switches: {self.switches}
Firewalls: {self.firewalls}
            """.strip()

            self.query_one("#quick_stats").update(stats_text)
        except Exception:
            pass

    def _populate_recent_activity(self):
        """Populate recent activity table with sample data"""
        table = self.query_one("#recent_activity_table")

        # Sample recent activities (in production, read from log file)
        activities = [
            (datetime.now().strftime("%H:%M:%S"), "TUI Started", "✅ Success"),
            (datetime.now().strftime("%H:%M:%S"), "Inventory Loaded", "✅ Success"),
            (datetime.now().strftime("%H:%M:%S"), "Dashboard Opened", "✅ Success"),
        ]

        for time, action, status in activities:
            table.add_row(time, action, status)

    def _update_time(self):
        """Update system time display"""
        try:
            time_widget = self.query_one("#system_time")
            time_widget.update(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Update every second
            self.set_timer(1.0, self._update_time)
        except Exception:
            pass

    def _show_error(self, message: str):
        """Show error message"""
        # Could use a notification or status bar
        pass

    def on_button_pressed(self, event):
        """Handle quick action button presses"""
        button_id = event.button.id

        if button_id == "action_devices":
            self.app.action_devices()
        elif button_id == "action_create_template":
            self.app.action_create_template()
        elif button_id == "action_edit_inventory":
            self.app.action_edit_inventory()
        elif button_id == "action_deploy":
            self.app.action_config()
        elif button_id == "action_backup":
            self.app.action_backup()
        elif button_id == "action_diagnostics":
            self.app.notify("Diagnostics feature coming soon!", severity="information")
        elif button_id == "action_logs":
            self.app.notify("Logs viewer coming soon!", severity="information")
        elif button_id == "action_api":
            self.app.notify("API status feature coming soon!", severity="information")
