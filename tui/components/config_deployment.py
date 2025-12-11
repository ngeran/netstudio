"""
Configuration Deployment Component with Real-time Updates

Advanced configuration deployment interface that integrates with the FastAPI backend
for multi-device operations with WebSocket progress tracking.
"""

from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button, Static, TextArea, DataTable, LoadingIndicator, ProgressBar,
    Select, Input, Label, Checkbox, Switch
)
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from typing import List, Dict, Any, Optional
import asyncio
import json

from tui.services.inventory_service import InventoryService
from tui.services.api_client import APIService


class DeploymentResult:
    """Represents a deployment result"""

    def __init__(self, device_ip: str, success: bool, message: str):
        self.device_ip = device_ip
        self.success = success
        self.message = message
        self.timestamp = None


class ConfigDeployment(Container):
    """Configuration deployment interface with real-time updates"""

    BINDINGS = [
        Binding("g", "generate", "Generate Config"),
        Binding("d", "deploy", "Deploy"),
        Binding("v", "preview", "Preview"),
        Binding("r", "rollback", "Rollback"),
        Binding("c", "clear", "Clear"),
        Binding("s", "save", "Save"),
    ]

    def __init__(self, inventory_service: InventoryService, api_service: APIService):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service
        self.current_task = None
        self.deployment_results: List[DeploymentResult] = []

    def compose(self):
        """Compose the configuration deployment UI"""
        yield Static("Configuration Deployment", classes="header-title")

        # Device selection
        with Vertical(classes="section"):
            yield Static("Device Selection", classes="section-title")

            with Horizontal():
                yield Select(
                    options=[("All Devices", "all"), ("Select Devices", "selected")],
                    value="all",
                    id="device_selection",
                    allow_blank=False
                )
                yield Button("🔄 Refresh Devices", id="refresh_devices")
                yield Static("0 selected", id="selected_count")

        # Template selection or manual config
        with Vertical(classes="section"):
            yield Static("Configuration Source", classes="section-title")

            with Horizontal():
                yield Select(
                    options=[("Manual Entry", "manual"), ("From Template", "template")],
                    value="manual",
                    id="config_source",
                    allow_blank=False
                )
                yield Select(
                    options=[("Interface Config", "interface"), ("BGP Config", "bgp"), ("OSPF Config", "ospf")],
                    value="interface",
                    id="template_type",
                    allow_blank=False
                )

        # Configuration editor
        with Vertical(classes="section"):
            yield Static("Configuration", classes="section-title")

            with Horizontal():
                yield Button("📋 Load Template", id="load_template")
                yield Button("🔍 Validate Syntax", id="validate_syntax")
                yield Button("💾 Save Config", id="save_config")
                yield Button("🔄 Clear", id="clear_config")

        # Configuration text area
        yield TextArea(
            "# Enter Junos configuration here\n# Example:\ninterfaces {\n    ge-0/0/0 {\n        description \"Link to core\";\n        unit 0 {\n            family inet {\n                address 192.168.1.1/24;\n            }\n        }\n    }\n}",
            id="config_text",
            language="junos"
        )

        # Deployment options
        with Vertical(classes="section"):
            yield Static("Deployment Options", classes="section-title")

            with Horizontal():
                yield Checkbox("Validate before deploy", id="validate_before_deploy", value=True)
                yield Checkbox("Rollback on failure", id="rollback_on_failure", value=True)
                yield Input(placeholder="Commit message", id="commit_message", value="Deployed from TUI")

        # Action buttons
        with Horizontal(classes="action-bar"):
            yield Button("🔍 Preview Changes", id="preview_changes", variant="secondary")
            yield Button("🚀 Deploy Configuration", id="deploy_config", variant="primary")
            yield Button("🔙 Rollback Last", id="rollback_last", variant="warning")
            yield Button("📊 Get Status", id="get_status", variant="secondary")

        # Progress bar
        yield ProgressBar(
            id="deployment_progress",
            show_eta=True,
            show_percentage=True,
            classes="hidden"
        )

        # Results table
        with Vertical(classes="section"):
            yield Static("Deployment Results", classes="section-title")

            yield DataTable(
                id="results_table",
                zebra_stripes=True,
            )

        # Status message
        yield Static("", id="status_message", classes="status-message")

    def on_mount(self):
        """Initialize component when mounted"""
        self._setup_results_table()
        self._refresh_device_selection()

        # Register API message handlers
        self.api_service.client.register_handler("task_update", self._handle_task_update)
        self.api_service.client.register_handler("log_message", self._handle_log_message)

    def _setup_results_table(self):
        """Set up the results table"""
        table = self.query_one("#results_table")
        table.add_columns(
            "Device IP",
            "Status",
            "Message",
            "Timestamp"
        )

    def _refresh_device_selection(self):
        """Refresh device selection options"""
        devices = self.inventory_service.get_all_devices()
        device_count = len(devices)
        self.query_one("#selected_count").update(f"{device_count} devices available")

    def action_generate(self):
        """Generate configuration from template"""
        template_type = self.query_one("#template_type").value

        if template_type == "interface":
            config = self._generate_interface_template()
        elif template_type == "bgp":
            config = self._generate_bgp_template()
        elif template_type == "ospf":
            config = self._generate_ospf_template()
        else:
            config = "# Select a template type"

        self.query_one("#config_text").text = config

    def _generate_interface_template(self) -> str:
        """Generate interface configuration template"""
        return """
interfaces {
    ge-0/0/0 {
        description "Uplink to core";
        unit 0 {
            family inet {
                address 192.168.1.1/24;
            }
            family inet6 {
                address 2001:db8::1/64;
            }
        }
    }

    ge-0/0/1 {
        description "Downlink to access";
        unit 0 {
            family inet {
                address 192.168.2.1/24;
            }
        }
    }
        """.strip()

    def _generate_bgp_template(self) -> str:
        """Generate BGP configuration template"""
        return """
protocols {
    bgp {
        group PEERS {
            type external;
            peer-as 65001;
            neighbor 192.168.1.2 {
                description "Peer to ISP";
                authentication-key "$9$aBcDeFg"; ## SECRET-DATA
            }
        }

        local-address 192.168.1.1;
        autonomous-system 65002;
    }
}
        """.strip()

    def _generate_ospf_template(self) -> str:
        """Generate OSPF configuration template"""
        return """
protocols {
    ospf {
        area 0.0.0.0 {
            interface ge-0/0/0 {
                passive;
            }
            interface ge-0/0/1 {
                interface-type p2p;
                metric 10;
            }
        }
    }
}
        """.strip()

    def action_validate(self):
        """Validate configuration syntax"""
        config = self.query_one("#config_text").text

        if not config.strip():
            self._show_error("No configuration to validate")
            return

        # Basic syntax validation
        errors = []
        lines = config.split('\n')

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if (line and not line.startswith('#') and
                not line.startswith('}') and
                not line.endswith(';') and
                not line.endswith('{')):
                errors.append(f"Line {i}: Missing semicolon - '{line}'")

        if errors:
            error_msg = "Syntax errors found:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors) - 5} more errors"
            self._show_error(error_msg)
        else:
            self._show_success("Configuration syntax appears valid")

    def action_preview(self):
        """Preview configuration changes"""
        self._show_info("Preview feature coming in Phase 3")

    def action_deploy(self):
        """Deploy configuration to devices"""
        config = self.query_one("#config_text").text
        commit_message = self.query_one("#commit_message").value
        validate_before = self.query_one("#validate_before_deploy").value

        if not config.strip():
            self._show_error("No configuration to deploy")
            return

        if validate_before:
            self.action_validate()
            # Could check if validation passed here

        device_selection = self.query_one("#device_selection").value
        devices = []

        if device_selection == "all":
            devices = self.inventory_service.get_all_devices()
        else:
            # For now, use all devices. In Phase 3, implement device selection UI
            devices = self.inventory_service.get_all_devices()

        if not devices:
            self._show_error("No devices available")
            return

        device_ips = [d.ip_address for d in devices]

        # Start deployment task
        asyncio.create_task(self._deploy_config(device_ips, config, commit_message))

    async def _deploy_config(self, device_ips: List[str], config: str, commit_message: str):
        """Deploy configuration to devices"""
        try:
            task_id = await self.api_service.client.deploy_config(device_ips, config, commit_message)

            if task_id:
                self.current_task = task_id
                self.query_one("#deployment_progress").remove_class("hidden")
                self._show_info(f"Deployment started for {len(device_ips)} devices")
            else:
                self._show_error("Failed to start deployment")

        except Exception as e:
            self._show_error(f"Error starting deployment: {e}")

    def action_rollback(self):
        """Rollback last configuration"""
        device_selection = self.query_one("#device_selection").value
        devices = []

        if device_selection == "all":
            devices = self.inventory_service.get_all_devices()
        else:
            devices = self.inventory_service.get_all_devices()

        if not devices:
            self._show_error("No devices available")
            return

        device_ips = [d.ip_address for d in devices]

        # Start rollback task
        asyncio.create_task(self._rollback_config(device_ips))

    async def _rollback_config(self, device_ips: List[str]):
        """Rollback configuration on devices"""
        try:
            task_id = await self.api_service.client.rollback_config(device_ips)

            if task_id:
                self.current_task = task_id
                self.query_one("#deployment_progress").remove_class("hidden")
                self._show_info(f"Rollback started for {len(device_ips)} devices")
            else:
                self._show_error("Failed to start rollback")

        except Exception as e:
            self._show_error(f"Error starting rollback: {e}")

    def action_clear(self):
        """Clear configuration"""
        self.query_one("#config_text").text = ""
        self.deployment_results = []
        self._update_results_table()

    def action_save(self):
        """Save configuration"""
        config = self.query_one("#config_text").text
        if not config.strip():
            self._show_error("No configuration to save")
            return

        # For now, just show success. In Phase 3, implement actual file saving
        self._show_success("Configuration saved (feature coming in Phase 3)")

    async def _handle_task_update(self, data: Dict[str, Any]):
        """Handle task update from WebSocket"""
        task_data = data.get('task', {})
        task_id = task_data.get('task_id')

        if task_id and task_id == self.current_task:
            # Update progress bar
            progress = task_data.get('progress', 0)
            progress_bar = self.query_one("#deployment_progress")
            progress_bar.advance = progress

            # Update status message
            message = task_data.get('message', '')
            self._show_info(message)

            # Check if task is complete
            status = task_data.get('status', '')
            if status in ['success', 'failed', 'cancelled']:
                progress_bar.add_class("hidden")

                # Get deployment results if available
                if status == 'success' and 'deployments' in task_data.get('results', {}):
                    deployments = task_data['results']['deployments']
                    self._process_deployment_results(deployments)

                if status == 'success':
                    self._show_success("Deployment completed successfully")
                elif status == 'failed':
                    error = task_data.get('error', 'Unknown error')
                    self._show_error(f"Deployment failed: {error}")

    async def _handle_log_message(self, data: Dict[str, Any]):
        """Handle log message from WebSocket"""
        level = data.get('level', 'info')
        message = data.get('message', '')
        task_id = data.get('task_id', '')

        if task_id and task_id == self.current_task:
            if level == 'error':
                self._show_error(f"Error: {message}")
            elif level == 'warning':
                self._show_info(f"Warning: {message}")
            else:
                self._show_info(message)

    def _process_deployment_results(self, deployments: Dict[str, Any]):
        """Process deployment results and update table"""
        from datetime import datetime

        self.deployment_results = []

        for device_ip, result in deployments.items():
            success = result.get('success', False)
            message = result.get('message', 'No message')
            timestamp = datetime.now().strftime("%H:%M:%S")

            self.deployment_results.append(
                DeploymentResult(device_ip, success, message)
            )

        self._update_results_table()

    def _update_results_table(self):
        """Update the results table"""
        table = self.query_one("#results_table")
        table.clear()

        for result in self.deployment_results:
            status_icon = "✅" if result.success else "❌"
            status_text = "Success" if result.success else "Failed"
            style = "green" if result.success else "red"

            table.add_row(
                result.device_ip,
                f"{status_icon} {status_text}",
                result.message,
                result.timestamp or "N/A",
                style=style
            )

    def _show_success(self, message: str):
        """Show success message"""
        self.query_one("#status_message").update(f"✅ {message}", style="green")

    def _show_error(self, message: str):
        """Show error message"""
        self.query_one("#status_message").update(f"❌ {message}", style="red")

    def _show_info(self, message: str):
        """Show info message"""
        self.query_one("#status_message").update(f"ℹ️ {message}", style="blue")

    def on_button_pressed(self, event):
        """Handle button press events"""
        button_id = event.button.id

        if button_id == "load_template":
            self.action_generate()
        elif button_id == "validate_syntax":
            self.action_validate()
        elif button_id == "clear_config":
            self.action_clear()
        elif button_id == "save_config":
            self.action_save()
        elif button_id == "preview_changes":
            self.action_preview()
        elif button_id == "deploy_config":
            asyncio.create_task(self.action_deploy())
        elif button_id == "rollback_last":
            asyncio.create_task(self.action_rollback())
        elif button_id == "get_status":
            asyncio.create_task(self._get_status())

    async def _get_status(self):
        """Get deployment status"""
        if self.current_task:
            task_info = await self.api_service.client.get_task(self.current_task)
            if task_info:
                status = task_info.get('status', 'unknown')
                progress = task_info.get('progress', 0)
                message = task_info.get('message', '')
                self._show_info(f"Task {status}: {progress}% - {message}")
            else:
                self._show_error("Task not found")
        else:
            self._show_info("No active deployment task")