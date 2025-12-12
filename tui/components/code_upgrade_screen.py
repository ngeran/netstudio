"""
Code Upgrade Screen

Wizard-style interface for upgrading Junos software on network devices.
Full implementation with vendor/product/release selection and upgrade execution.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Button, Static, DataTable, Select, Label
from textual.reactive import reactive
from textual import work

# Import legacy code upgrade functions
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils import load_yaml_file
from scripts.connect_to_hosts import connect_to_hosts, disconnect_from_hosts
from scripts.code_upgrade import (
    check_image_exists,
    check_current_version,
    probe_device,
    verify_version,
)
from jnpr.junos.utils.sw import SW
from jnpr.junos.exception import ConnectError, RpcError

logger = logging.getLogger(__name__)


class CodeUpgradeScreen(Screen):
    """Code Upgrade wizard screen"""

    # Wizard state
    current_step: reactive[int] = reactive(1)
    total_steps: reactive[int] = reactive(5)

    # Selected data
    selected_vendor: reactive[Optional[str]] = reactive(None)
    selected_product_type: reactive[Optional[str]] = reactive(
        None
    )  # switches, firewalls, routers
    selected_product: reactive[Optional[str]] = reactive(None)
    selected_release: reactive[Optional[Dict]] = reactive(None)
    selected_devices: reactive[List[str]] = reactive([])

    # Upgrade progress
    upgrade_status: reactive[List[Dict]] = reactive([])
    is_upgrading: reactive[bool] = reactive(False)

    def __init__(self, inventory_service, api_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service

        # Load upgrade data
        try:
            upgrade_data_file = project_root / "data" / "upgrade_data.yml"
            self.upgrade_data = load_yaml_file(str(upgrade_data_file))
            self.vendors = self.upgrade_data.get("products", [])
        except Exception as e:
            logger.error(f"Failed to load upgrade_data.yml: {e}")
            self.upgrade_data = {}
            self.vendors = []

        # Load available devices
        try:
            self.available_devices = self.inventory_service.load_devices()
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            self.available_devices = []

    def compose(self):
        """Compose the upgrade screen layout"""
        yield Header("⬆️ Code Upgrade Wizard")

        with Container(classes="upgrade-wizard-container"):
            # Step indicator
            yield Static("", id="step_indicator", classes="step-indicator")

            # Main content area (changes based on step)
            with VerticalScroll(id="content_area", classes="content-area"):
                yield Static("Loading...", id="step_content")

            # Navigation buttons
            with Horizontal(classes="wizard-navigation"):
                yield Button("❮ Previous", id="btn_previous", variant="default")
                yield Button("Next ❯", id="btn_next", variant="primary")
                yield Button(
                    "⬆️ Start Upgrade",
                    id="btn_upgrade",
                    variant="success",
                    classes="hidden",
                )
                yield Button("🔙 Back", id="btn_back", variant="default")

            # Status/Progress area
            yield Static(
                "Ready to begin upgrade process",
                id="wizard_status",
                classes="wizard-status",
            )

        yield Footer()

    def on_mount(self):
        """Initialize when screen is mounted"""
        self._update_step_indicator()
        self._render_step()

    def _update_step_indicator(self):
        """Update the step indicator display"""
        steps = [
            "1. Select Version",
            "2. Select Devices",
            "3. Verify Images",
            "4. Review & Confirm",
            "5. Upgrade Progress",
        ]

        indicator_html = []
        for i, step in enumerate(steps, 1):
            if i == self.current_step:
                indicator_html.append(f"[bold cyan]▶ {step}[/]")
            elif i < self.current_step:
                indicator_html.append(f"[green]✓ {step}[/]")
            else:
                indicator_html.append(f"[dim]  {step}[/]")

        step_indicator = self.query_one("#step_indicator", Static)
        step_indicator.update("\n".join(indicator_html))

    def _render_step(self):
        """Render content for current step"""
        content_area = self.query_one("#content_area", VerticalScroll)
        content_area.remove_children()

        if self.current_step == 1:
            self._render_step1_version_selection(content_area)
        elif self.current_step == 2:
            self._render_step2_device_selection(content_area)
        elif self.current_step == 3:
            self._render_step3_verify_images(content_area)
        elif self.current_step == 4:
            self._render_step4_review_confirm(content_area)
        elif self.current_step == 5:
            self._render_step5_upgrade_progress(content_area)

        # Update button visibility
        self._update_buttons()

    def _render_step1_version_selection(self, container):
        """Render Step 1: Version selection"""
        container.mount(
            Static(
                "[bold cyan]Step 1: Select Software Version[/]\n", classes="step-title"
            )
        )
        container.mount(Static("Select the Junos software version to install:\n"))

        # Build flat list of all available upgrades
        upgrade_options = []
        for vendor in self.vendors:
            vendor_name = vendor["vendor-name"]
            for product_type_key in ["switches", "firewalls", "routers"]:
                if product_type_key in vendor:
                    product_type_display = product_type_key.title()
                    for product in vendor[product_type_key]:
                        product_name = product["product"]
                        for idx, release in enumerate(product.get("releases", [])):
                            release_name = release["release"]
                            display_name = f"{vendor_name} - {product_type_display} - {product_name} - {release_name}"
                            # Value format: vendor|type|product|idx
                            value = (
                                f"{vendor_name}|{product_type_key}|{product_name}|{idx}"
                            )
                            upgrade_options.append((display_name, value))

        container.mount(Label("\nSelect Upgrade Version:"))
        upgrade_select = Select(
            options=upgrade_options
            if upgrade_options
            else [("No upgrades available", "none")],
            id="upgrade_select",
            allow_blank=False,
        )
        container.mount(upgrade_select)

        # Show current selection summary
        if self.selected_release:
            container.mount(Static(f"\n[bold green]✅ Selected Version:[/]"))
            container.mount(Static(f"  Vendor: {self.selected_vendor}"))
            container.mount(
                Static(f"  Product Type: {self.selected_product_type.title()}")
            )
            container.mount(Static(f"  Product: {self.selected_product}"))
            container.mount(
                Static(f"  Release: {self.selected_release.get('release')}")
            )
            container.mount(Static(f"  Image: {self.selected_release.get('os')}"))
            container.mount(
                Static(f"\n[green]Click 'Next' to proceed to device selection.[/]")
            )
        else:
            container.mount(
                Static(f"\n[dim]Select a version from the dropdown above.[/]")
            )

    def _render_step2_device_selection(self, container):
        """Render Step 2: Device selection"""
        container.mount(
            Static(
                "[bold cyan]Step 2: Select Target Devices[/]\n", classes="step-title"
            )
        )
        container.mount(Static("Select which devices to upgrade:\n"))
        container.mount(
            Static(
                "[yellow]Use arrow keys to navigate, press ENTER to toggle selection[/]\n"
            )
        )

        # Device selection table
        table = DataTable(
            id="device_selection_table",
            classes="device-select-table",
            cursor_type="row",
        )
        table.add_column("Select", width=8)
        table.add_column("Device Name", width=20)
        table.add_column("IP Address", width=20)
        table.add_column("Type", width=12)

        for device in self.available_devices:
            checkbox = "☑" if device.ip_address in self.selected_devices else "☐"
            table.add_row(
                checkbox,
                device.host_name,
                device.ip_address,
                device.device_type,
                key=device.ip_address,
            )

        container.mount(table)
        container.mount(
            Static(
                f"\n[cyan]Selected: {len(self.selected_devices)} device(s)[/]",
                id="device_selection_count",
            )
        )
        container.mount(
            Static("\n[dim]Devices will be upgraded one at a time for safety.[/]")
        )

    def _render_step3_verify_images(self, container):
        """Render Step 3: Image verification"""
        container.mount(
            Static("[bold cyan]Step 3: Verify Images[/]\n", classes="step-title")
        )

        if not self.selected_release:
            container.mount(Static("[yellow]Please select a release in Step 1[/]"))
            return

        image_name = self.selected_release.get("os", "Unknown")

        container.mount(
            Static(f"""Checking if upgrade images exist on target devices...

[bold yellow]Target Image:[/] {image_name}
[bold yellow]Expected Location:[/] /var/tmp/{image_name}

[dim]Tip: Images must be pre-copied to /var/tmp/ on each device before upgrade.[/]
[dim]     You can use SCP/FTP to transfer the image file to the devices.[/]

[green]Click "Next" to proceed to review - image verification will occur during upgrade.[/]
""")
        )

    def _render_step4_review_confirm(self, container):
        """Render Step 4: Review and confirm"""
        container.mount(
            Static("[bold cyan]Step 4: Review & Confirm[/]\n", classes="step-title")
        )

        if not self.selected_release or not self.selected_devices:
            container.mount(Static("[yellow]Please complete previous steps[/]"))
            return

        device_list = "\n".join([f"  • {ip}" for ip in self.selected_devices])

        container.mount(
            Static(f"""Please review the upgrade plan:

[bold]Software Version:[/]
  Vendor: {self.selected_vendor}
  Product: {self.selected_product}
  Release: {self.selected_release.get("release", "Unknown")}
  Image: {self.selected_release.get("os", "Unknown")}

[bold]Target Devices:[/] ({len(self.selected_devices)})
{device_list}

[bold]Upgrade Process (per device):[/]
  1. Connect and verify image exists on device
  2. Check current version (warn if downgrade)
  3. Install software with validation (no-copy, no-validate flags)
  4. Reboot device
  5. Wait for device to come back online (~15 minutes)
  6. Verify new version is running
  7. Move to next device

[yellow]⚠️  Warning: Devices will reboot during this process![/]
[yellow]⚠️  Ensure you have console access in case of issues.[/]
[yellow]⚠️  This process may take 15-30 minutes per device.[/]

[bold green]Click "Start Upgrade" when ready to proceed.[/]
""")
        )

    def _render_step5_upgrade_progress(self, container):
        """Render Step 5: Upgrade progress"""
        container.mount(
            Static("[bold cyan]Step 5: Upgrade Progress[/]\n", classes="step-title")
        )

        if not self.upgrade_status:
            container.mount(Static("[cyan]Preparing to start upgrade...[/]"))
            return

        for status in self.upgrade_status:
            hostname = status.get("hostname", "Unknown")
            current_step = status.get("current_step", "")

            if status.get("in_progress"):
                container.mount(Static(f"[yellow]🔄 {hostname}[/] - {current_step}"))
            elif status.get("success"):
                new_version = status.get("new_version", "Unknown")
                container.mount(
                    Static(
                        f"[green]✅ {hostname}[/] - Upgraded to {new_version} successfully"
                    )
                )
            elif status.get("error"):
                container.mount(
                    Static(f"[red]❌ {hostname}[/] - {status.get('error', 'Failed')}")
                )
            else:
                container.mount(Static(f"[dim]⏳ {hostname}[/] - Waiting..."))

    def _update_buttons(self):
        """Update button visibility and state based on current step"""
        try:
            btn_previous = self.query_one("#btn_previous", Button)
            btn_next = self.query_one("#btn_next", Button)
            btn_upgrade = self.query_one("#btn_upgrade", Button)

            # Previous button
            btn_previous.disabled = self.current_step == 1 or self.is_upgrading

            # Next button
            if self.current_step < 4:
                btn_next.remove_class("hidden")
                btn_next.disabled = not self._can_proceed_to_next_step()
            else:
                btn_next.add_class("hidden")

            # Upgrade button
            if self.current_step == 4:
                btn_upgrade.remove_class("hidden")
                btn_upgrade.disabled = (
                    not self.selected_release
                    or not self.selected_devices
                    or self.is_upgrading
                )
            else:
                btn_upgrade.add_class("hidden")

        except Exception as e:
            logger.error(f"Error updating buttons: {e}")

    def _can_proceed_to_next_step(self) -> bool:
        """Check if user can proceed to next step"""
        if self.current_step == 1:
            return self.selected_release is not None
        elif self.current_step == 2:
            return len(self.selected_devices) > 0
        elif self.current_step == 3:
            return True  # Image verification is automatic
        return False

    def on_select_changed(self, event: Select.Changed):
        """Handle select changes - parse the upgrade selection"""
        if event.select.id == "upgrade_select":
            # Parse the selection value: "vendor|type|product|release_idx"
            try:
                if event.value and event.value != "none":
                    parts = event.value.split("|")
                    if len(parts) == 4:
                        vendor, ptype, product, rel_idx = parts
                        self.selected_vendor = vendor
                        self.selected_product_type = ptype
                        self.selected_product = product

                        # Get release from index
                        vendor_data = next(
                            (v for v in self.vendors if v["vendor-name"] == vendor),
                            None,
                        )
                        if vendor_data and ptype in vendor_data:
                            products = vendor_data[ptype]
                            product_data = next(
                                (p for p in products if p["product"] == product), None
                            )
                            if product_data:
                                releases = product_data.get("releases", [])
                                idx = int(rel_idx)
                                if 0 <= idx < len(releases):
                                    self.selected_release = releases[idx]
                                    self.notify(
                                        f"Selected: {product} - {self.selected_release.get('release')}",
                                        severity="success",
                                    )
                        self._update_buttons()
            except Exception as e:
                logger.error(f"Error parsing upgrade selection: {e}")
                self.notify(f"Error selecting version: {str(e)}", severity="error")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        """Handle device row highlight - toggle selection"""
        if event.data_table.id == "device_selection_table":
            self._toggle_device_selection(
                event.data_table, event.cursor_row, event.row_key
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Handle device row Enter press - toggle selection"""
        if event.data_table.id == "device_selection_table":
            self._toggle_device_selection(
                event.data_table, event.cursor_row, event.row_key
            )

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

            # Update count display
            try:
                count_widget = self.query_one("#device_selection_count", Static)
                count_widget.update(
                    f"\n[cyan]Selected: {len(self.selected_devices)} device(s)[/]"
                )
            except Exception:
                pass

            self._update_buttons()

        except Exception as e:
            logger.error(f"Error toggling selection: {e}", exc_info=True)

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn_back":
            self.app.pop_screen()

        elif button_id == "btn_previous":
            if self.current_step > 1 and not self.is_upgrading:
                self.current_step -= 1
                self._update_step_indicator()
                self._render_step()

        elif button_id == "btn_next":
            if self.current_step < 4 and self._can_proceed_to_next_step():
                self.current_step += 1
                self._update_step_indicator()
                self._render_step()

        elif button_id == "btn_upgrade":
            self._start_upgrade()

    @work(exclusive=True)
    async def _start_upgrade(self):
        """Start the upgrade process"""
        if not self.selected_release or not self.selected_devices:
            self.notify(
                "Please complete all steps before starting upgrade", severity="warning"
            )
            return

        self.is_upgrading = True
        self.current_step = 5
        self._update_step_indicator()
        self._update_buttons()

        status_widget = self.query_one("#wizard_status", Static)
        status_widget.update("🔄 Starting upgrade process...")

        try:
            # Get credentials from first device
            first_device = next(
                (
                    d
                    for d in self.available_devices
                    if d.ip_address in self.selected_devices
                ),
                None,
            )

            if not first_device:
                raise ValueError("Selected devices not found in inventory")

            username = first_device.username if first_device.username else "admin"
            password = first_device.password if first_device.password else "password"

            # Initialize upgrade status
            self.upgrade_status = [
                {
                    "hostname": ip,
                    "success": False,
                    "error": None,
                    "in_progress": False,
                    "current_step": "",
                }
                for ip in self.selected_devices
            ]

            self._render_step()

            # Run upgrade in background thread
            await asyncio.to_thread(
                self._run_upgrade,
                self.selected_devices,
                username,
                password,
                self.selected_release,
            )

            # Final status
            successful = sum(1 for s in self.upgrade_status if s.get("success"))
            failed = sum(1 for s in self.upgrade_status if s.get("error"))

            status_widget.update(
                f"✅ Upgrade completed: {successful} successful, {failed} failed"
            )
            self.notify(
                f"Upgrade completed: {successful} successful, {failed} failed",
                severity="success" if failed == 0 else "warning",
            )

        except Exception as e:
            status_widget.update(f"❌ Upgrade failed: {str(e)}")
            self.notify(f"Upgrade failed: {str(e)}", severity="error")
            logger.error(f"Upgrade error: {e}", exc_info=True)

        finally:
            self.is_upgrading = False
            self._update_buttons()

    def _run_upgrade(
        self, device_ips: List[str], username: str, password: str, release: Dict
    ):
        """Run upgrade operation (blocking, runs in thread)"""
        logger.info(f"Starting upgrade for devices: {device_ips}")
        logger.info(f"Target version: {release.get('release')}")

        target_version = release.get("release")
        image_path = f"/var/tmp/{release.get('os')}"

        for idx, hostname in enumerate(device_ips):
            try:
                # Update status
                self.upgrade_status[idx]["in_progress"] = True
                self.upgrade_status[idx]["current_step"] = "Connecting..."
                self.app.call_from_thread(self._render_step)

                # Connect
                connections = connect_to_hosts([hostname], username, password)
                if not connections:
                    raise ConnectError(f"Failed to connect to {hostname}")

                dev = connections[0]

                # Check image exists
                self.upgrade_status[idx]["current_step"] = "Checking image..."
                self.app.call_from_thread(self._render_step)

                if not check_image_exists(dev, image_path, hostname):
                    raise Exception(f"Image not found: {image_path}")

                # Check current version
                self.upgrade_status[idx]["current_step"] = "Checking current version..."
                self.app.call_from_thread(self._render_step)

                if not check_current_version(dev, hostname, target_version):
                    logger.info(
                        f"Skipping {hostname} - already on target version or user cancelled"
                    )
                    disconnect_from_hosts(connections)
                    self.upgrade_status[idx]["in_progress"] = False
                    self.upgrade_status[idx]["error"] = (
                        "Skipped (already on version or cancelled)"
                    )
                    self.app.call_from_thread(self._render_step)
                    continue

                # Install software
                self.upgrade_status[idx]["current_step"] = "Installing software..."
                self.app.call_from_thread(self._render_step)

                sw = SW(dev)
                ok = sw.install(
                    package=image_path, progress=True, validate=True, no_copy=True
                )

                if not ok:
                    raise Exception("Software installation failed")

                # Reboot
                self.upgrade_status[idx]["current_step"] = "Rebooting device..."
                self.app.call_from_thread(self._render_step)

                sw.reboot()
                disconnect_from_hosts(connections)

                # Wait for device
                self.upgrade_status[idx]["current_step"] = (
                    "Waiting for device to come back online..."
                )
                self.app.call_from_thread(self._render_step)

                # Determine max_wait based on device type
                max_wait = 1800  # 30 minutes default
                if "EX4600" in release.get("os", ""):
                    max_wait = 2400  # 40 minutes for EX4600

                if not probe_device(hostname, username, password, max_wait=max_wait):
                    raise Exception("Device did not come back online")

                # Verify version
                self.upgrade_status[idx]["current_step"] = "Verifying new version..."
                self.app.call_from_thread(self._render_step)

                success, new_version, error = verify_version(
                    hostname, username, password, target_version
                )

                if success:
                    self.upgrade_status[idx]["success"] = True
                    self.upgrade_status[idx]["new_version"] = new_version
                    logger.info(f"Successfully upgraded {hostname} to {new_version}")
                else:
                    raise Exception(error or "Version verification failed")

            except Exception as e:
                logger.error(f"Upgrade failed for {hostname}: {e}")
                self.upgrade_status[idx]["error"] = str(e)

            finally:
                self.upgrade_status[idx]["in_progress"] = False
                self.app.call_from_thread(self._render_step)

        logger.info("Upgrade process completed for all devices")
