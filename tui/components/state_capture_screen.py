"""
State Capture Screen

Wizard-style interface for capturing device state before/after changes
and comparing the differences using DeepDiff.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Button, Static, DataTable, Input, Label
from textual.widgets.data_table import RowKey
from textual.reactive import reactive
from textual import work

# Import legacy state capture functions
import sys

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.state_capture import capture_device_state, compare_states
import yaml
from deepdiff import DeepDiff

logger = logging.getLogger(__name__)


class StateCaptureScreen(Screen):
    """State Capture wizard screen"""

    # State directories
    state_dir = Path("state")

    # Wizard state
    current_step: reactive[int] = reactive(1)
    change_number: reactive[str] = reactive("")
    selected_devices: reactive[List[str]] = reactive([])

    # Capture status
    pre_state_captured: reactive[bool] = reactive(False)
    post_state_captured: reactive[bool] = reactive(False)
    is_capturing: reactive[bool] = reactive(False)

    # File paths
    pre_check_file: reactive[Optional[str]] = reactive(None)
    post_check_file: reactive[Optional[str]] = reactive(None)

    def __init__(self, inventory_service, api_service):
        super().__init__()
        self.inventory_service = inventory_service
        self.api_service = api_service
        self.state_dir.mkdir(exist_ok=True)

        # Load available devices
        try:
            self.available_devices = self.inventory_service.load_devices()
        except Exception as e:
            logger.error(f"Failed to load devices: {e}")
            self.available_devices = []

    def compose(self):
        """Compose the state capture screen layout"""
        yield Header("📸 Device State Capture")

        with Container(classes="state-wizard-container"):
            # Step indicator
            yield Static("", id="step_indicator", classes="step-indicator")

            # Main content area
            with VerticalScroll(id="content_area", classes="content-area"):
                yield Static("Loading...", id="step_content")

            # Navigation buttons
            with Horizontal(classes="wizard-navigation"):
                yield Button("❮ Previous", id="btn_previous", variant="default")
                yield Button("Next ❯", id="btn_next", variant="primary")
                yield Button(
                    "📸 Capture Pre-State",
                    id="btn_pre_capture",
                    variant="success",
                    classes="hidden",
                )
                yield Button(
                    "📸 Capture Post-State",
                    id="btn_post_capture",
                    variant="success",
                    classes="hidden",
                )
                yield Button(
                    "🔍 Compare States",
                    id="btn_compare",
                    variant="primary",
                    classes="hidden",
                )
                yield Button("🔙 Back", id="btn_back", variant="default")

            # Status area
            yield Static(
                "Ready to begin state capture",
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
            "1. Setup",
            "2. Select Devices",
            "3. Pre-Check",
            "4. Post-Check",
            "5. Compare",
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

        # Clear existing widgets
        content_area.remove_children()

        if self.current_step == 1:
            self._render_step1_setup(content_area)
        elif self.current_step == 2:
            self._render_step2_device_selection(content_area)
        elif self.current_step == 3:
            self._render_step3_pre_check(content_area)
        elif self.current_step == 4:
            self._render_step4_post_check(content_area)
        elif self.current_step == 5:
            self._render_step5_compare(content_area)

        self._update_buttons()

    def _render_step1_setup(self, container):
        """Render Step 1: Setup and change number"""
        container.mount(Static("[bold cyan]Step 1: Setup[/]\n", classes="step-title"))
        container.mount(
            Static("Enter a change/ticket number to track this state capture:\n")
        )

        container.mount(Label("Change Number:"))
        change_input = Input(
            value=self.change_number or "",
            placeholder="e.g., CHG001234 or 2024-12-11-maintenance",
            id="change_number_input",
        )
        container.mount(change_input)

        container.mount(Static("\n[yellow]What is State Capture?[/]"))
        container.mount(
            Static("""State capture records the current state of network devices before and after making changes.
It captures:
  • BGP sessions and peers
  • OSPF neighbors and interfaces
  • Routing tables
  • Interface status
  • LLDP neighbors
  • System alarms and core dumps

After capturing pre and post states, you can compare them to see
exactly what changed, helping with:
  • Change validation
  • Troubleshooting
  • Audit trails
  • Rollback decisions
""")
        )

    def _render_step2_device_selection(self, container):
        """Render Step 2: Device selection"""
        container.mount(
            Static("[bold cyan]Step 2: Select Devices[/]\n", classes="step-title")
        )
        container.mount(Static("Select devices to capture state from:\n"))
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
                id="selection_count",
            )
        )

    def _render_step3_pre_check(self, container):
        """Render Step 3: Pre-check capture"""
        container.mount(
            Static(
                "[bold cyan]Step 3: Pre-Change State Capture[/]\n", classes="step-title"
            )
        )

        if not self.pre_state_captured:
            container.mount(
                Static(f"""Capture the current state of selected devices BEFORE making any changes.

[bold]Change Number:[/] {self.change_number}
[bold]Selected Devices:[/] {len(self.selected_devices)}
{chr(10).join([f"  • {ip}" for ip in self.selected_devices])}

[yellow]Click "Capture Pre-State" to begin.[/]

[dim]This will collect BGP, OSPF, routing, interface, LLDP, and system data.[/]
[dim]Files will be saved to: state/pre_check_{self.change_number}.yaml[/]
""")
            )
        else:
            container.mount(
                Static(f"""[green]✅ Pre-change state captured successfully![/]

[bold]File:[/] {self.pre_check_file}
[bold]Devices:[/] {len(self.selected_devices)}
[bold]Captured:[/] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

[cyan]You can now make your changes to the network devices.[/]

Click "Next" when ready to capture post-change state.
""")
            )

    def _render_step4_post_check(self, container):
        """Render Step 4: Post-check capture"""
        container.mount(
            Static(
                "[bold cyan]Step 4: Post-Change State Capture[/]\n",
                classes="step-title",
            )
        )

        if not self.post_state_captured:
            container.mount(
                Static(f"""Capture the current state of selected devices AFTER making changes.

[bold]Change Number:[/] {self.change_number}
[bold]Selected Devices:[/] {len(self.selected_devices)}

[yellow]⚠️  Make sure you have completed your changes before proceeding![/]

[yellow]Click "Capture Post-State" to begin.[/]

[dim]This will collect the same data as pre-check for comparison.[/]
[dim]Files will be saved to: state/post_check_{self.change_number}.yaml[/]
""")
            )
        else:
            container.mount(
                Static(f"""[green]✅ Post-change state captured successfully![/]

[bold]File:[/] {self.post_check_file}
[bold]Devices:[/] {len(self.selected_devices)}
[bold]Captured:[/] {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

[cyan]Ready to compare pre and post states![/]

Click "Next" to view the differences.
""")
            )

    def _render_step5_compare(self, container):
        """Render Step 5: Comparison results"""
        container.mount(
            Static("[bold cyan]Step 5: State Comparison[/]\n", classes="step-title")
        )

        if not self.pre_state_captured or not self.post_state_captured:
            container.mount(Static("[yellow]Complete pre and post captures first[/]"))
            return

        container.mount(
            Static(f"""Comparing states for change: {self.change_number}

[bold]Pre-check file:[/] {self.pre_check_file}
[bold]Post-check file:[/] {self.post_check_file}

[yellow]Click "Compare States" to see differences[/]

[dim]Comparison results will show:[/]
[dim]  • Added items (new BGP peers, routes, etc.)[/]
[dim]  • Removed items (lost sessions, down interfaces)[/]
[dim]  • Changed values (state changes, counters)[/]
""")
        )

        # Show comparison results if available
        container.mount(Static("", id="comparison_results"))

    def _update_buttons(self):
        """Update button visibility based on current step"""
        try:
            btn_previous = self.query_one("#btn_previous", Button)
            btn_next = self.query_one("#btn_next", Button)
            btn_pre = self.query_one("#btn_pre_capture", Button)
            btn_post = self.query_one("#btn_post_capture", Button)
            btn_compare = self.query_one("#btn_compare", Button)

            # Hide all action buttons first
            btn_pre.add_class("hidden")
            btn_post.add_class("hidden")
            btn_compare.add_class("hidden")

            # Previous button
            btn_previous.disabled = self.current_step == 1 or self.is_capturing

            # Next button
            btn_next.remove_class("hidden")
            btn_next.disabled = not self._can_proceed_to_next_step()

            # Step-specific action buttons
            if self.current_step == 3 and not self.pre_state_captured:
                btn_pre.remove_class("hidden")
                btn_pre.disabled = self.is_capturing
                btn_next.add_class("hidden")
            elif self.current_step == 4 and not self.post_state_captured:
                btn_post.remove_class("hidden")
                btn_post.disabled = self.is_capturing
                btn_next.add_class("hidden")
            elif self.current_step == 5:
                btn_compare.remove_class("hidden")
                btn_next.add_class("hidden")

        except Exception as e:
            logger.error(f"Error updating buttons: {e}")

    def _can_proceed_to_next_step(self) -> bool:
        """Check if user can proceed to next step"""
        if self.current_step == 1:
            return bool(self.change_number)
        elif self.current_step == 2:
            return len(self.selected_devices) > 0
        elif self.current_step == 3:
            return self.pre_state_captured
        elif self.current_step == 4:
            return self.post_state_captured
        return False

    def on_input_changed(self, event: Input.Changed):
        """Handle input changes"""
        if event.input.id == "change_number_input":
            self.change_number = event.value.strip()
            self._update_buttons()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted):
        """Handle device row click/highlight - toggle selection"""
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
            # Get current checkbox state
            current_cell = table.get_cell_at((cursor_row, 0))
            new_state = "☑" if current_cell == "☐" else "☐"

            # Update cell
            table.update_cell_at((cursor_row, 0), new_state)

            # Extract IP address from row_key (it's the key we used when adding rows)
            ip_address = str(row_key) if isinstance(row_key, str) else row_key.value

            # Update selected devices list
            if new_state == "☑":
                if ip_address not in self.selected_devices:
                    self.selected_devices.append(ip_address)
            else:
                if ip_address in self.selected_devices:
                    self.selected_devices.remove(ip_address)

            # Update count display
            try:
                count_widget = self.query_one("#selection_count", Static)
                count_widget.update(
                    f"\n[cyan]Selected: {len(self.selected_devices)} device(s)[/]"
                )
            except Exception as e:
                logger.error(f"Error updating count: {e}")

            self._update_buttons()

            # Log for debugging
            logger.info(
                f"Device selection toggled: {ip_address} -> {new_state}, total selected: {len(self.selected_devices)}"
            )

        except Exception as e:
            logger.error(f"Error toggling selection: {e}", exc_info=True)

    async def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses"""
        button_id = event.button.id

        if button_id == "btn_back":
            self.app.pop_screen()

        elif button_id == "btn_previous":
            if self.current_step > 1 and not self.is_capturing:
                self.current_step -= 1
                self._update_step_indicator()
                self._render_step()

        elif button_id == "btn_next":
            if self._can_proceed_to_next_step():
                self.current_step += 1
                self._update_step_indicator()
                self._render_step()

        elif button_id == "btn_pre_capture":
            self._capture_pre_state()

        elif button_id == "btn_post_capture":
            self._capture_post_state()

        elif button_id == "btn_compare":
            self._compare_states()

    @work(exclusive=True)
    async def _capture_pre_state(self):
        """Capture pre-change state"""
        if not self.change_number or not self.selected_devices:
            self.notify("Please complete setup first", severity="warning")
            return

        self.is_capturing = True
        self._update_buttons()

        status_widget = self.query_one("#wizard_status", Static)
        status_widget.update("📸 Capturing pre-change state...")

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

            # Capture state in background thread
            self.pre_check_file = await asyncio.to_thread(
                self._run_state_capture,
                "pre_check",
                self.selected_devices,
                username,
                password,
                self.change_number,
            )

            self.pre_state_captured = True
            status_widget.update("✅ Pre-change state captured successfully")
            self.notify(f"Pre-state saved to {self.pre_check_file}", severity="success")
            self._render_step()

        except Exception as e:
            status_widget.update(f"❌ Pre-capture failed: {str(e)}")
            self.notify(f"Pre-capture failed: {str(e)}", severity="error")
            logger.error(f"Pre-capture error: {e}", exc_info=True)

        finally:
            self.is_capturing = False
            self._update_buttons()

    @work(exclusive=True)
    async def _capture_post_state(self):
        """Capture post-change state"""
        self.is_capturing = True
        self._update_buttons()

        status_widget = self.query_one("#wizard_status", Static)
        status_widget.update("📸 Capturing post-change state...")

        try:
            # Get credentials
            first_device = next(
                (
                    d
                    for d in self.available_devices
                    if d.ip_address in self.selected_devices
                ),
                None,
            )

            username = first_device.username if first_device.username else "admin"
            password = first_device.password if first_device.password else "password"

            # Capture state in background thread
            self.post_check_file = await asyncio.to_thread(
                self._run_state_capture,
                "post_check",
                self.selected_devices,
                username,
                password,
                self.change_number,
            )

            self.post_state_captured = True
            status_widget.update("✅ Post-change state captured successfully")
            self.notify(
                f"Post-state saved to {self.post_check_file}", severity="success"
            )
            self._render_step()

        except Exception as e:
            status_widget.update(f"❌ Post-capture failed: {str(e)}")
            self.notify(f"Post-capture failed: {str(e)}", severity="error")
            logger.error(f"Post-capture error: {e}", exc_info=True)

        finally:
            self.is_capturing = False
            self._update_buttons()

    def _run_state_capture(
        self,
        label: str,
        devices: List[str],
        username: str,
        password: str,
        change_number: str,
    ) -> str:
        """Run state capture (blocking, runs in thread)"""
        state_file = self.state_dir / f"{label}_{change_number}.yaml"
        txt_file = self.state_dir / f"{label}_{change_number}.txt"
        all_states = {}

        logger.info(f"Starting {label} capture for {len(devices)} device(s)")

        for device in devices:
            try:
                logger.info(f"Capturing state for {device}")
                state = capture_device_state(device, username, password)
                if state:
                    all_states[device] = state
                    logger.info(f"State captured successfully for {device}")
                else:
                    logger.warning(f"No data collected for {device}")
            except Exception as e:
                logger.error(f"Error capturing state for {device}: {e}")

        if all_states:
            # Save as YAML
            with open(state_file, "w") as f:
                yaml.dump(all_states, f, default_flow_style=False)
            logger.info(f"State saved to {state_file}")

            # Save as TXT for readability
            with open(txt_file, "w") as f:
                for device, state in all_states.items():
                    f.write(f"Device: {device}\n")
                    f.write("=" * 80 + "\n")
                    for section, summary in state.items():
                        f.write(f"\n{section}:\n")
                        f.write(f"{summary}\n")
                    f.write("\n\n")
            logger.info(f"State saved to {txt_file}")

        return str(state_file)

    @work(exclusive=True)
    async def _compare_states(self):
        """Compare pre and post states"""
        if not self.pre_check_file or not self.post_check_file:
            self.notify(
                "Both pre and post states must be captured first", severity="warning"
            )
            return

        status_widget = self.query_one("#wizard_status", Static)
        status_widget.update("🔍 Comparing states...")

        try:
            # Load states
            with open(self.pre_check_file, "r") as f:
                pre_state = yaml.safe_load(f)

            with open(self.post_check_file, "r") as f:
                post_state = yaml.safe_load(f)

            # Compare using DeepDiff
            differences = DeepDiff(pre_state, post_state, ignore_order=True)

            # Display results
            results_widget = self.query_one("#comparison_results", Static)

            if differences:
                diff_text = ["[bold yellow]Differences Found:[/]\n"]

                if "values_changed" in differences:
                    diff_text.append("[bold cyan]Values Changed:[/]")
                    for key, change in list(differences["values_changed"].items())[
                        :10
                    ]:  # Show first 10
                        diff_text.append(f"  • {key}")
                        diff_text.append(f"    Old: {change['old_value']}")
                        diff_text.append(f"    New: {change['new_value']}")

                if "iterable_item_added" in differences:
                    diff_text.append("\n[bold green]Items Added:[/]")
                    for key in list(differences["iterable_item_added"].keys())[:10]:
                        diff_text.append(f"  • {key}")

                if "iterable_item_removed" in differences:
                    diff_text.append("\n[bold red]Items Removed:[/]")
                    for key in list(differences["iterable_item_removed"].keys())[:10]:
                        diff_text.append(f"  • {key}")

                diff_text.append(
                    f"\n[dim]Full diff saved to: state/diff_{self.change_number}.txt[/]"
                )

                results_widget.update("\n".join(diff_text))

                # Save full diff to file
                diff_file = self.state_dir / f"diff_{self.change_number}.txt"
                with open(diff_file, "w") as f:
                    f.write(str(differences))
                logger.info(f"Diff saved to {diff_file}")

            else:
                results_widget.update(
                    "[green]✅ No differences found - states are identical[/]"
                )

            status_widget.update("✅ Comparison completed")
            self.notify("State comparison completed", severity="success")

        except Exception as e:
            status_widget.update(f"❌ Comparison failed: {str(e)}")
            self.notify(f"Comparison failed: {str(e)}", severity="error")
            logger.error(f"Comparison error: {e}", exc_info=True)
