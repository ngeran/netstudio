
"""
Smart Template Manager - User-Friendly Template Editor
Designed for network engineers with no coding experience
"""
 
from textual.app import ComposeResult
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Static, Input, Select,
    Label, Checkbox, TextArea
)
from textual.reactive import reactive
from textual import work
from typing import Optional, Dict, List
import os
import yaml
import jinja2
from pathlib import Path
import re
 
 
class SmartTemplateManager(Screen):
    """Smart template manager with dynamic form generation"""
 
    CSS = """
    SmartTemplateManager {
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
 
    .mandatory-label {
        color: $error;
        text-style: bold;
    }
 
    .optional-label {
        color: $text-muted;
    }
 
    .compact-buttons {
        height: auto;
        padding: 1 0 0 0;
        margin: 0;
    }
 
    .compact-buttons Button {
        margin: 0 0 0 1;
    }
 
    .help-icon {
        color: $warning;
        padding: 0;
    }
 
    .template-desc {
        color: $text-muted;
        padding: 0;
        margin: 0 0 1 0;
    }
 
    #config_preview {
        height: 1fr;
        background: $panel;
        color: $text;
    }
 
    Select {
        width: 1fr;
        background: $surface;
        border: tall $primary;
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
    """
 
    selected_template: reactive[Optional[str]] = reactive(None)
    template_vars: reactive[Dict] = reactive({})
    generated_config: reactive[str] = reactive("")
 
    def __init__(self):
        super().__init__()
        self.templates_dir = Path(os.getenv("VECTOR_PY_DIR", ".")) / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
 
        # Template metadata (in real scenario, parse from templates)
        self.template_info = {
            "interface_template.j2": {
                "name": "🔌 Interface Configuration",
                "description": "Configure physical or logical interfaces with IP addresses and VLANs",
                "icon": "🔌",
                "fields": [
                    {"name": "interfaces", "label": "Interface Name", "type": "text", "mandatory": True,
                     "placeholder": "ge-0/0/0", "help": "Physical interface name (e.g., ge-0/0/0, xe-0/0/1)"},
                    {"name": "description", "label": "Description", "type": "text", "mandatory": False,
                     "placeholder": "Link to Core Router", "help": "Friendly description of the interface"},
                    {"name": "ip_address", "label": "IP Address", "type": "text", "mandatory": False,
                     "placeholder": "192.168.1.1/24", "help": "IP address with CIDR notation"},
                    {"name": "vlan_id", "label": "VLAN ID", "type": "text", "mandatory": False,
                     "placeholder": "100", "help": "VLAN ID (if using VLANs)"},
                    {"name": "unit", "label": "Unit ID", "type": "text", "mandatory": False,
                     "placeholder": "0", "help": "Logical unit number"},
                ]
            },
            "bgp_template.j2": {
                "name": "🌐 BGP Configuration",
                "description": "Configure BGP neighbors and routing policies",
                "icon": "🌐",
                "fields": [
                    {"name": "as_number", "label": "AS Number", "type": "text", "mandatory": True,
                     "placeholder": "65000", "help": "Your autonomous system number"},
                    {"name": "router_id", "label": "Router ID", "type": "text", "mandatory": True,
                     "placeholder": "10.0.0.1", "help": "BGP router identifier"},
                    {"name": "neighbor_ip", "label": "Neighbor IP", "type": "text", "mandatory": True,
                     "placeholder": "10.0.0.2", "help": "BGP neighbor IP address"},
                    {"name": "neighbor_as", "label": "Neighbor AS", "type": "text", "mandatory": True,
                     "placeholder": "65001", "help": "Neighbor's AS number"},
                    {"name": "description", "label": "Description", "type": "text", "mandatory": False,
                     "placeholder": "Peer to ISP", "help": "Peering description"},
                ]
            },
            "ospf_template.j2": {
                "name": "🗺️ OSPF Configuration",
                "description": "Configure OSPF routing protocol with areas and interfaces",
                "icon": "🗺️",
                "fields": [
                    {"name": "router_id", "label": "Router ID", "type": "text", "mandatory": True,
                     "placeholder": "10.0.0.1", "help": "OSPF router identifier"},
                    {"name": "area", "label": "OSPF Area", "type": "text", "mandatory": True,
                     "placeholder": "0.0.0.0", "help": "OSPF area (e.g., 0.0.0.0 for backbone)"},
                    {"name": "interface", "label": "Interface", "type": "text", "mandatory": True,
                     "placeholder": "ge-0/0/0.0", "help": "Interface participating in OSPF"},
                    {"name": "metric", "label": "Metric", "type": "text", "mandatory": False,
                     "placeholder": "10", "help": "OSPF interface cost"},
                    {"name": "priority", "label": "Priority", "type": "text", "mandatory": False,
                     "placeholder": "128", "help": "Router priority for DR election"},
                ]
            },
            "vlan_template.j2": {
                "name": "🏷️ VLAN Configuration",
                "description": "Configure VLANs and VLAN interfaces",
                "icon": "🏷️",
                "fields": [
                    {"name": "vlan_id", "label": "VLAN ID", "type": "text", "mandatory": True,
                     "placeholder": "100", "help": "VLAN identifier (1-4094)"},
                    {"name": "vlan_name", "label": "VLAN Name", "type": "text", "mandatory": True,
                     "placeholder": "DATA_VLAN", "help": "Descriptive VLAN name"},
                    {"name": "description", "label": "Description", "type": "text", "mandatory": False,
                     "placeholder": "Data Network", "help": "VLAN description"},
                    {"name": "ip_address", "label": "Gateway IP", "type": "text", "mandatory": False,
                     "placeholder": "192.168.100.1/24", "help": "Gateway IP for this VLAN"},
                ]
            },
            "firewall_filter_template.j2": {
                "name": "🛡️ Firewall Filter",
                "description": "Create firewall filter rules for traffic control",
                "icon": "🛡️",
                "fields": [
                    {"name": "filter_name", "label": "Filter Name", "type": "text", "mandatory": True,
                     "placeholder": "PROTECT_RE", "help": "Name of the firewall filter"},
                    {"name": "term_name", "label": "Term Name", "type": "text", "mandatory": True,
                     "placeholder": "ALLOW_SSH", "help": "Name of the filter term"},
                    {"name": "protocol", "label": "Protocol", "type": "select", "mandatory": False,
                     "options": ["tcp", "udp", "icmp", "any"], "help": "IP protocol to match"},
                    {"name": "port", "label": "Destination Port", "type": "text", "mandatory": False,
                     "placeholder": "22", "help": "Destination port number"},
                    {"name": "action", "label": "Action", "type": "select", "mandatory": True,
                     "options": ["accept", "discard", "reject"], "help": "Action to take on match"},
                ]
            },
            "static_route_template.j2": {
                "name": "🛤️ Static Routes",
                "description": "Configure static routing entries",
                "icon": "🛤️",
                "fields": [
                    {"name": "destination", "label": "Destination", "type": "text", "mandatory": True,
                     "placeholder": "10.10.0.0/16", "help": "Destination network"},
                    {"name": "next_hop", "label": "Next Hop", "type": "text", "mandatory": True,
                     "placeholder": "192.168.1.1", "help": "Next hop IP address"},
                    {"name": "preference", "label": "Preference", "type": "text", "mandatory": False,
                     "placeholder": "5", "help": "Route preference (lower is better)"},
                    {"name": "description", "label": "Description", "type": "text", "mandatory": False,
                     "placeholder": "Route to Branch Office", "help": "Route description"},
                ]
            }
        }
 
    def compose(self) -> ComposeResult:
        yield Header()
 
        # Compact header at the top
        with Horizontal(classes="compact-header"):
            yield Static("📝 Smart Template Manager", classes="section-title")
            yield Static(" | No Coding Required!", classes="subtitle")
 
        # Two-column layout
        with Horizontal(classes="main-layout"):
            # LEFT COLUMN: Template selector + Form
            with Vertical(classes="left-column"):
                # Template Selector (compact)
                with Vertical(classes="template-selector"):
                    yield Static("Step 1: Select Template", classes="section-title")
 
                    with Horizontal(classes="selector-row"):
                        yield Label("Template:")
                        yield Select(
                            options=[("-- Select a Template --", "NONE")] + self._get_template_options(),
                            id="select_template",
                            value="NONE",
                            allow_blank=False
                        )
                        yield Button("📂 Load", id="btn_load_template", variant="primary")
 
                    yield Static("", id="template_description", classes="template-desc")
 
                # Dynamic Form Area (scrollable but compact)
                with VerticalScroll(classes="form-area", id="dynamic_form"):
                    yield Static("Step 2: Fill Details", classes="section-title")
                    yield Static("Select template to see form", classes="subtitle", id="form_placeholder")
 
                # Action Buttons (compact)
                with Horizontal(classes="compact-buttons"):
                    yield Button("⚡ Generate", id="btn_generate", variant="primary")
                    yield Button("🔍 Test", id="btn_test", variant="default")
                    yield Button("💾 Save", id="btn_save", variant="success")
                    yield Button("🔄 Reset", id="btn_reset", variant="default")
 
            # RIGHT COLUMN: Configuration Preview
            with Vertical(classes="right-column"):
                with Vertical(classes="preview-area"):
                    yield Static("Step 3: Generated Config", classes="section-title")
                    yield TextArea(
                        "# Select template → Fill form → Generate\n\n"
                        "# Your Junos config appears here!\n\n"
                        "# Ready to copy and deploy",
                        id="config_preview",
                        read_only=True
                    )
 
        yield Footer()
 
    def on_mount(self):
        """Initialize when mounted"""
        self.notify("Welcome! Select a template to get started 🚀", severity="information")
 
    def _get_template_options(self):
        """Get list of available templates"""
        options = []
        for template_file, info in self.template_info.items():
            # Don't include icon - it's already in the name
            display_name = info['name']
            options.append((display_name, template_file))
        return options
 
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button clicks"""
        button_id = event.button.id
 
        if button_id == "btn_load_template":
            self._load_selected_template()
 
        elif button_id == "btn_reset":
            self._reset_form()
 
        elif button_id == "btn_test":
            self._test_syntax()
 
        elif button_id == "btn_save":
            self._save_generated_config()
 
        elif button_id == "btn_generate":
            self._generate_config()
 
    def _load_selected_template(self):
        """Load the selected template and build dynamic form"""
        select = self.query_one("#select_template", Select)
        template_file = select.value
 
        if template_file == "NONE":
            self.notify("Please select a template from the dropdown", severity="warning")
            return
 
        self.selected_template = template_file
 
        # Update description
        if template_file in self.template_info:
            info = self.template_info[template_file]
            desc_widget = self.query_one("#template_description", Static)
            desc_widget.update(f"✨ {info['description']}")
 
            # Build dynamic form
            self._build_dynamic_form(info)
 
            self.notify(f"Loaded template: {info['name']}", severity="success")
        else:
            self.notify(f"Template not found: {template_file}", severity="error")
 
    def _build_dynamic_form(self, template_info: Dict):
        """Build a dynamic form based on template fields"""
        form_container = self.query_one("#dynamic_form", VerticalScroll)
 
        # Clear existing form
        form_container.remove_children()
 
        # Build list of widgets to mount
        widgets_to_mount = []
 
        # Add compact title
        widgets_to_mount.append(Static("Step 2: Fill Details (* = required)", classes="section-title"))
 
        # Create form fields dynamically (more compact, no separate help text)
        for field in template_info["fields"]:
            field_name = field["name"]
            field_label = field["label"]
            field_type = field["type"]
            mandatory = field.get("mandatory", False)
            placeholder = field.get("placeholder", "")
            help_text = field.get("help", "")
 
            # Create label with mandatory indicator and help icon
            if mandatory:
                label_text = f"* {field_label}"
                label_class = "mandatory-label"
            else:
                label_text = f"{field_label}"
                label_class = "optional-label"
 
            # Add help text to placeholder for space efficiency
            if help_text and placeholder:
                enhanced_placeholder = f"{placeholder} - {help_text}"
            else:
                enhanced_placeholder = placeholder or help_text
 
            # Create form row container
            row = Horizontal(classes="form-row")
 
            if field_type == "text":
                # Compose the row inline before mounting
                widgets_to_mount.append(row)
                row.compose_add_child(Label(label_text, classes=label_class))
                row.compose_add_child(Input(
                    placeholder=enhanced_placeholder,
                    id=f"field_{field_name}"
                ))
 
            elif field_type == "select":
                options = [(opt.capitalize(), opt) for opt in field.get("options", [])]
                widgets_to_mount.append(row)
                row.compose_add_child(Label(label_text, classes=label_class))
                row.compose_add_child(Select(
                    options=[("-- Select --", "")] + options,
                    id=f"field_{field_name}",
                    value=""
                ))
 
            elif field_type == "checkbox":
                widgets_to_mount.append(row)
                row.compose_add_child(Label(label_text, classes=label_class))
                row.compose_add_child(Checkbox(
                    help_text,
                    id=f"field_{field_name}",
                    value=False
                ))
 
        # Mount all widgets at once
        form_container.mount(*widgets_to_mount)
 
        self.notify("Form loaded! Fill in required fields (*)", severity="information")
 
    def _reset_form(self):
        """Reset the form to defaults"""
        if not self.selected_template:
            self.notify("No template loaded", severity="warning")
            return
 
        # Reload the template to reset form
        if self.selected_template in self.template_info:
            info = self.template_info[self.selected_template]
            self._build_dynamic_form(info)
            self.notify("Form reset to defaults", severity="information")
 
    def _generate_config(self):
        """Generate configuration from form data"""
        if not self.selected_template:
            self.notify("Please load a template first", severity="warning")
            return
 
        try:
            # Collect form data
            template_info = self.template_info[self.selected_template]
            form_data = {}
 
            missing_required = []
 
            for field in template_info["fields"]:
                field_name = field["name"]
                mandatory = field.get("mandatory", False)
 
                # Get value from form
                try:
                    widget = self.query_one(f"#field_{field_name}")
                    if hasattr(widget, 'value'):
                        value = widget.value
                    else:
                        value = ""
 
                    if mandatory and not value:
                        missing_required.append(field["label"])
 
                    form_data[field_name] = value
                except:
                    form_data[field_name] = ""
 
            # Check for required fields
            if missing_required:
                self.notify(f"⚠️ Required fields missing: {', '.join(missing_required)}", severity="error")
                return
 
            # Generate config (simplified - in real scenario, use actual Jinja2 templates)
            config = self._generate_config_from_template(self.selected_template, form_data)
 
            # Update preview
            preview = self.query_one("#config_preview", TextArea)
            preview.text = config
 
            self.generated_config = config
            self.notify("✅ Configuration generated successfully!", severity="success")
 
        except Exception as e:
            self.notify(f"Error generating config: {e}", severity="error")
 
    def _generate_config_from_template(self, template_file: str, data: Dict) -> str:
        """Generate config from template file and data"""
        # This is a simplified version - real implementation would load actual .j2 files
 
        if template_file == "interface_template.j2":
            config = f"""interfaces {{
    {data.get('interfaces', 'ge-0/0/0')} {{"""
 
            if data.get('description'):
                config += f"""
        description "{data['description']}";"""
 
            if data.get('unit'):
                config += f"""
        unit {data['unit']} {{"""
            else:
                config += """
        unit 0 {"""
 
            if data.get('ip_address'):
                config += f"""
            family inet {{
                address {data['ip_address']};
            }}"""
 
            if data.get('vlan_id'):
                config += f"""
            vlan-id {data['vlan_id']};"""
 
            config += """
        }
    }
}"""
            return config
 
        elif template_file == "bgp_template.j2":
            config = f"""protocols {{
    bgp {{
        group PEERS {{
            type external;
            peer-as {data.get('neighbor_as', '65001')};
            neighbor {data.get('neighbor_ip', '10.0.0.2')} {{"""
 
            if data.get('description'):
                config += f"""
                description "{data['description']}";"""
 
            config += f"""
            }}
        }}
        local-as {data.get('as_number', '65000')};
    }}
}}
routing-options {{
    router-id {data.get('router_id', '10.0.0.1')};
}}"""
            return config
 
        elif template_file == "ospf_template.j2":
            config = f"""protocols {{
    ospf {{
        area {data.get('area', '0.0.0.0')} {{
            interface {data.get('interface', 'ge-0/0/0.0')} {{"""
 
            if data.get('metric'):
                config += f"""
                metric {data['metric']};"""
 
            if data.get('priority'):
                config += f"""
                priority {data['priority']};"""
 
            config += """
            }
        }
    }
}
routing-options {
    router-id """ + data.get('router_id', '10.0.0.1') + """;
}"""
            return config
 
        elif template_file == "vlan_template.j2":
            config = f"""vlans {{
    {data.get('vlan_name', 'VLAN')} {{
        vlan-id {data.get('vlan_id', '100')};"""
 
            if data.get('description'):
                config += f"""
        description "{data['description']}";"""
 
            if data.get('ip_address'):
                config += f"""
        l3-interface irb.{data['vlan_id']};"""
 
            config += """
    }
}"""
 
            if data.get('ip_address'):
                config += f"""
interfaces {{
    irb {{
        unit {data['vlan_id']} {{
            family inet {{
                address {data['ip_address']};
            }}
        }}
    }}
}}"""
 
            return config
 
        elif template_file == "firewall_filter_template.j2":
            config = f"""firewall {{
    filter {data.get('filter_name', 'FILTER')} {{
        term {data.get('term_name', 'TERM')} {{
            from {{"""
 
            if data.get('protocol'):
                config += f"""
                protocol {data['protocol']};"""
 
            if data.get('port'):
                config += f"""
                destination-port {data['port']};"""
 
            config += f"""
            }}
            then {data.get('action', 'accept')};
        }}
    }}
}}"""
            return config
 
        elif template_file == "static_route_template.j2":
            config = f"""routing-options {{
    static {{
        route {data.get('destination', '0.0.0.0/0')} {{
            next-hop {data.get('next_hop', '192.168.1.1')};"""
 
            if data.get('preference'):
                config += f"""
            preference {data['preference']};"""
 
            if data.get('description'):
                config += f"""
            /* {data['description']} */"""
 
            config += """
        }
    }
}"""
            return config
 
        return "# Template not yet implemented"
 
    def _test_syntax(self):
        """Test configuration syntax"""
        if not self.generated_config:
            self.notify("Generate config first before testing", severity="warning")
            return
 
        config = self.generated_config
        errors = []
 
        # Basic syntax checks
        open_braces = config.count('{')
        close_braces = config.count('}')
 
        if open_braces != close_braces:
            errors.append(f"Unmatched braces (open: {open_braces}, close: {close_braces})")
 
        # Check for lines missing semicolons
        lines = config.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if (line and
                not line.startswith('#') and
                not line.startswith('/*') and
                not line.startswith('}') and
                not line.endswith(';') and
                not line.endswith('{') and
                not line.endswith('*/')):
                errors.append(f"Line {i}: Possible missing semicolon")
 
        if errors:
            self.notify(f"⚠️ Syntax issues: {'; '.join(errors[:3])}", severity="warning")
        else:
            self.notify("✅ Configuration syntax looks good!", severity="success")
 
    def _save_generated_config(self):
        """Save generated configuration to file"""
        if not self.generated_config:
            self.notify("No configuration to save. Generate config first!", severity="warning")
            return
 
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
 
            # Create output directory
            output_dir = Path(os.getenv("VECTOR_PY_DIR", ".")) / "data" / "generated_configs"
            output_dir.mkdir(parents=True, exist_ok=True)
 
            # Save config
            filename = f"config_{self.selected_template.replace('.j2', '')}_{timestamp}.conf"
            filepath = output_dir / filename
 
            with open(filepath, 'w') as f:
                f.write(self.generated_config)
 
            self.notify(f"💾 Saved to: {filepath.name}", severity="success")
 
        except Exception as e:
            self.notify(f"Error saving file: {e}", severity="error")
