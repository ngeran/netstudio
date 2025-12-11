"""
Interface Template Editor Component for TUI

A form-based template editor that allows network engineers to create
Juniper interface configurations without writing Jinja2 or YAML.
"""

from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Input, Select, Button, Static, TextArea, Checkbox,
    LoadingIndicator, Label, Switch
)
from textual.reactive import reactive
from textual.validation import Function, Regex, Length
from textual.message import Message
from textual.binding import Binding
import jinja2
import re
from typing import Dict, Any, Optional, List


class ConfigGenerated(Message):
    """Message sent when configuration is generated"""
    def __init__(self, config: str) -> None:
        self.config = config
        super().__init__()


class InterfaceTemplateEditor(Container):
    """Form-based interface template editor"""

    CSS = """
    InterfaceTemplateEditor {
        height: 100%;
    }

    .header-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin: 1 0;
    }

    .form-column {
        width: 1fr;
        padding: 0 1;
        border: solid $surface;
        margin: 0 1;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin: 1 0 0 0;
        padding: 0 0 1 0;
        border-bottom: solid $surface;
    }

    .button-bar {
        margin: 1 0;
        padding: 1 0;
        border-top: solid $surface;
        justify-content: center;
    }

    .config-preview {
        height: 40%;
        margin: 1 0;
        padding: 1;
        border: solid $surface;
        background: $surface;
    }

    #ospf_options {
        margin-left: 2;
        display: block;
    }

    #bgp_options {
        margin-left: 2;
        display: block;
    }

    #config_preview {
        height: 100%;
        background: $panel;
        color: $text;
    }
    """

    BINDINGS = [
        Binding("g", "generate", "Generate Config"),
        Binding("t", "test", "Test Syntax"),
        Binding("s", "save", "Save Template"),
        Binding("l", "load", "Load Template"),
        Binding("r", "reset", "Reset Form"),
    ]

    # Form state
    interface_name: reactive[str] = reactive("")
    description: reactive[str] = reactive("")
    ip_address: reactive[str] = reactive("")
    ip_enabled: reactive[bool] = reactive(True)
    unit_id: reactive[str] = reactive("0")
    interface_enabled: reactive[bool] = reactive(True)

    # Advanced settings
    mtu: reactive[str] = reactive("1500")
    bandwidth: reactive[str] = reactive("")
    encapsulation: reactive[str] = reactive("")

    # Protocol settings
    ospf_enabled: reactive[bool] = reactive(False)
    ospf_area: reactive[str] = reactive("")
    ospf_cost: reactive[str] = reactive("")

    bgp_enabled: reactive[bool] = reactive(False)
    bgp_as: reactive[str] = reactive("")

    # Monitoring
    enable_monitoring: reactive[bool] = reactive(False)

    # Generated config
    generated_config: reactive[str] = reactive("")

    def compose(self):
        """Compose the template editor UI"""
        yield Static("Interface Configuration Builder", classes="header-title")

        # Main form layout
        with Horizontal():
            # Left column - Basic settings
            with Vertical(classes="form-column"):
                yield Static("Basic Settings", classes="section-title")

                yield Label("Interface Name:")
                yield Input(
                    placeholder="ge-0/0/0",
                    id="interface_name",
                    validators=[
                        Function(self._validate_interface_name, "Invalid interface format")
                    ]
                )

                yield Label("Description:")
                yield Input(
                    placeholder="Link description",
                    id="description"
                )

                yield Label("Unit ID:")
                yield Input(
                    value="0",
                    id="unit_id",
                    validators=[
                        Regex(r"^\d+$", "Unit ID must be a number")
                    ]
                )

                yield Label("Status:")
                yield Switch(value=True, id="interface_enabled")

            # Middle column - IP Configuration
            with Vertical(classes="form-column"):
                yield Static("IP Configuration", classes="section-title")

                yield Checkbox(
                    "Enable IP Configuration",
                    value=True,
                    id="ip_enabled"
                )

                yield Label("IP Address:")
                yield Input(
                    placeholder="192.168.1.1/24",
                    id="ip_address",
                    validators=[
                        Function(self._validate_ip_address, "Invalid IP format")
                    ]
                )

                yield Static("Advanced Settings", classes="section-title")

                yield Label("MTU:")
                yield Input(
                    value="1500",
                    id="mtu",
                    validators=[
                        Regex(r"^\d+$", "MTU must be a number")
                    ]
                )

                yield Label("Bandwidth:")
                yield Input(
                    placeholder="1G",
                    id="bandwidth"
                )

                yield Label("Encapsulation:")
                yield Select(
                    options=[
                        ("None", ""),
                        ("VLAN", "vlan-ccc"),
                        ("PPP", "ppp-ccc"),
                        ("Frame Relay", "frame-relay-ccc")
                    ],
                    value="",
                    id="encapsulation"
                )

            # Right column - Routing Protocols
            with Vertical(classes="form-column"):
                yield Static("Routing Protocols", classes="section-title")

                # OSPF Section
                yield Checkbox("Enable OSPF", id="ospf_enabled")

                with Container(id="ospf_options"):
                    yield Label("OSPF Area:")
                    yield Input(
                        placeholder="0.0.0.0",
                        id="ospf_area",
                        validators=[
                            Function(self._validate_ospf_area, "Invalid OSPF area format")
                        ]
                    )

                    yield Label("OSPF Cost:")
                    yield Input(
                        placeholder="10",
                        id="ospf_cost",
                        validators=[
                            Regex(r"^\d+$", "OSPF cost must be a number")
                        ]
                    )

                # BGP Section
                yield Checkbox("Enable BGP", id="bgp_enabled")

                with Container(id="bgp_options"):
                    yield Label("BGP AS Number:")
                    yield Input(
                        placeholder="65000",
                        id="bgp_as",
                        validators=[
                            Regex(r"^\d+$", "BGP AS must be a number")
                        ]
                    )

                # Monitoring
                yield Static("Monitoring", classes="section-title")
                yield Checkbox(
                    "Enable Interface Monitoring",
                    id="enable_monitoring"
                )

        # Action buttons
        with Horizontal(classes="button-bar"):
            yield Button("🔄 Reset", id="reset", variant="default")
            yield Button("🔍 Test Syntax", id="test_syntax", variant="secondary")
            yield Button("💾 Save Template", id="save", variant="secondary")
            yield Button("⚡ Generate Config", id="generate", variant="primary")

        # Configuration preview
        with Vertical(classes="config-preview"):
            yield Static("Generated Configuration", classes="section-title")
            yield TextArea(
                "",
                id="config_preview",
                read_only=True,
                language="junos"
            )

    def on_mount(self):
        """Initialize component when mounted"""
        self._update_form_visibility()

    def _validate_interface_name(self, value: str) -> bool:
        """Validate Juniper interface name format"""
        pattern = r'^(ge|xe|et|lo|irb|ae|st)-[0-9]+/[0-9]+(/[0-9]+)?$'
        return re.match(pattern, value) is not None

    def _validate_ip_address(self, value: str) -> bool:
        """Validate IP address with CIDR"""
        pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(?:[0-9]|[1-2][0-9]|3[0-2])$'
        return value == "" or re.match(pattern, value) is not None

    def _validate_ospf_area(self, value: str) -> bool:
        """Validate OSPF area format"""
        pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^[0-9]+$'
        return value == "" or re.match(pattern, value) is not None

    def on_input_changed(self, event):
        """Handle input changes"""
        input_id = event.input.id
        value = event.input.value

        # Update reactive properties
        if hasattr(self, input_id):
            setattr(self, input_id, value)

        # Auto-generate preview if key fields changed
        if input_id in ["interface_name", "ip_address", "description"]:
            self.action_generate()

    def on_checkbox_changed(self, event):
        """Handle checkbox changes"""
        checkbox_id = event.checkbox.id
        value = event.checkbox.value

        # Update reactive properties
        if hasattr(self, checkbox_id):
            setattr(self, checkbox_id, value)

        # Update form visibility based on checkboxes
        self._update_form_visibility()

        # Auto-generate preview
        self.action_generate()

    def on_select_changed(self, event):
        """Handle select changes"""
        select_id = event.select.id
        value = event.select.value

        # Update reactive properties
        if hasattr(self, select_id):
            setattr(self, select_id, value)

        # Auto-generate preview
        self.action_generate()

    def _update_form_visibility(self):
        """Update form field visibility based on checkboxes"""
        # OSPF options
        ospf_container = self.query_one("#ospf_options")
        ospf_container.set_display(bool(self.ospf_enabled))

        # BGP options
        bgp_container = self.query_one("#bgp_options")
        bgp_container.set_display(bool(self.bgp_enabled))

    def action_generate(self):
        """Generate Junos configuration"""
        try:
            config = self._generate_junos_config()
            self.generated_config = config

            # Update preview
            preview = self.query_one("#config_preview")
            preview.text = config

            self.post_message(ConfigGenerated(config))

        except Exception as e:
            self.notify(f"Error generating config: {e}", severity="error")

    def _generate_junos_config(self) -> str:
        """Generate Junos configuration from form data"""
        # Get actual values from form widgets instead of reactive properties
        interface_name = self.query_one("#interface_name").value
        description = self.query_one("#description").value
        unit_id = self.query_one("#unit_id").value
        interface_enabled = self.query_one("#interface_enabled").value
        ip_enabled = self.query_one("#ip_enabled").value
        ip_address = self.query_one("#ip_address").value
        mtu = self.query_one("#mtu").value
        bandwidth = self.query_one("#bandwidth").value
        encapsulation = self.query_one("#encapsulation").value
        ospf_enabled = self.query_one("#ospf_enabled").value
        ospf_area = self.query_one("#ospf_area").value
        ospf_cost = self.query_one("#ospf_cost").value or "10"
        bgp_enabled = self.query_one("#bgp_enabled").value
        bgp_as = self.query_one("#bgp_as").value
        enable_monitoring = self.query_one("#enable_monitoring").value

        template_vars = {
            'interface_name': interface_name,
            'description': description,
            'unit_id': unit_id,
            'interface_enabled': interface_enabled,
            'ip_enabled': ip_enabled,
            'ip_address': ip_address,
            'mtu': mtu,
            'bandwidth': bandwidth,
            'encapsulation': encapsulation,
            'ospf_enabled': ospf_enabled,
            'ospf_area': ospf_area,
            'ospf_cost': ospf_cost,
            'bgp_enabled': bgp_enabled,
            'bgp_as': bgp_as,
            'enable_monitoring': enable_monitoring
        }

        template = """
interfaces {
    {{ interface_name }} {
        {% if description %}
        description "{{ description }}";
        {% endif %}
        {% if mtu and mtu != '1500' %}
        mtu {{ mtu }};
        {% endif %}
        {% if bandwidth %}
        bandwidth {{ bandwidth }};
        {% endif %}
        {% if encapsulation %}
        encapsulation {{ encapsulation }};
        {% endif %}
        {% if interface_enabled %}
        unit {{ unit_id }} {
            {% if ip_enabled and ip_address %}
            family inet {
                address {{ ip_address }};
                {% if ospf_enabled %}
                {% if ospf_area %}
                ospf {
                    area {{ ospf_area }};
                    {% if ospf_cost %}
                    metric {{ ospf_cost }};
                    {% endif %}
                }
                {% endif %}
                {% endif %}
            }
            {% endif %}
        }
        {% else %}
        disable;
        {% endif %}
    }
}

{% if enable_monitoring and interface_name and ip_address %}
# Interface monitoring configuration
snmp {
    interface {{ interface_name }};
}
{% endif %}
        """

        jinja_template = jinja2.Template(template, trim_blocks=True, lstrip_blocks=True)
        return jinja_template.render(**template_vars).strip()

    def action_test_syntax(self):
        """Test generated configuration syntax"""
        if not self.generated_config:
            self.action_generate()

        # Basic syntax validation
        config = self.generated_config

        # Check for common syntax errors
        errors = []

        # Check for unmatched braces
        brace_count = config.count('{') - config.count('}')
        if brace_count != 0:
            errors.append(f"Unmatched braces: {brace_count}")

        # Check for missing semicolons
        lines = config.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if (line and
                not line.startswith('#') and
                not line.startswith('}') and
                not line.endswith(';') and
                not line.endswith('{')):
                errors.append(f"Line {i}: Missing semicolon")

        if errors:
            self.notify(f"Syntax errors found: {'; '.join(errors)}", severity="error")
        else:
            self.notify("Configuration syntax appears valid", severity="information")

    def action_reset(self):
        """Reset form to defaults"""
        self.interface_name = ""
        self.description = ""
        self.ip_address = ""
        self.ip_enabled = True
        self.interface_enabled = True
        self.unit_id = "0"
        self.mtu = "1500"
        self.bandwidth = ""
        self.encapsulation = ""
        self.ospf_enabled = False
        self.ospf_area = ""
        self.ospf_cost = ""
        self.bgp_enabled = False
        self.bgp_as = ""
        self.enable_monitoring = False

        # Update form fields
        self.query_one("#interface_name").value = ""
        self.query_one("#description").value = ""
        self.query_one("#ip_address").value = ""
        self.query_one("#unit_id").value = "0"
        self.query_one("#mtu").value = "1500"
        self.query_one("#bandwidth").value = ""
        self.query_one("#encapsulation").value = ""
        self.query_one("#ospf_area").value = ""
        self.query_one("#ospf_cost").value = ""
        self.query_one("#bgp_as").value = ""
        self.query_one("#config_preview").text = ""

        self.query_one("#ip_enabled").value = True
        self.query_one("#interface_enabled").value = True
        self.query_one("#ospf_enabled").value = False
        self.query_one("#bgp_enabled").value = False
        self.query_one("#enable_monitoring").value = False

        self._update_form_visibility()

        self.notify("Form reset to defaults", severity="information")

    def on_button_pressed(self, event):
        """Handle button press events"""
        button_id = event.button.id

        if button_id == "generate":
            self.action_generate()
        elif button_id == "test_syntax":
            self.action_test_syntax()
        elif button_id == "reset":
            self.action_reset()
        elif button_id == "save":
            self.notify("Save template feature coming in Phase 2", severity="information")