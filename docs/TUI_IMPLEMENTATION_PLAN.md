# Network Automation TUI - Comprehensive Implementation Plan

## Project Overview

Transform the existing CLI-based network automation framework into a modern Terminal User Interface (TUI) with optional web components, leveraging Juniper PyEZ and JSNAPy for simplified device management.

## Architecture Vision

```
┌─────────────────────────────────────────────────────────────┐
│                    Network Engineer                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Terminal (TUI) - Primary Interface        │    │
│  │  - Textual-based interactive menus                  │    │
│  │  - Form-based template editors                      │    │
│  │  - Real-time progress display                       │    │
│  │  - Multi-device operations                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                      │                                      │
│   (Optional) Web Access │                                    │
│                      ↓                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            FastAPI Backend (Port 8000)              │    │
│  │  - WebSocket for real-time updates                  │    │
│  │  - REST API for file operations                     │    │
│  │  - PyEZ/JSNAPy integration layer                   │    │
│  │  - Template rendering service                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                      │                                      │
│                      ↓                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Juniper PyEZ + JSNAPy                     │    │
│  │  - Device connections & auth                        │    │
│  │  - Configuration management                         │    │
│  │  - Operational state monitoring                    │    │
│  │  - Validation & testing                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                      │                                      │
│                      ↓                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               Network Devices                        │    │
│  │         SRX, EX, QFX, MX Series Junos               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Phase-Based Implementation Plan

### Phase 1: Foundation & TUI Core (Week 1-2)

**Objectives:**
- Set up Textual TUI framework
- Create basic application structure
- Implement device inventory management
- Build template editing interface

**Tasks:**

#### 1.1 Environment Setup
- [ ] Install Textual and dependencies
- [ ] Set up virtual environment
- [ ] Configure logging for TUI
- [ ] Test basic TUI capabilities

#### 1.2 Core TUI Application
- [ ] Create main application class (`tui/app.py`)
- [ ] Implement navigation system
- [ ] Add keyboard shortcuts
- [ ] Create reusable TUI components

#### 1.3 Device Inventory Management
- [ ] Integrate with existing `inventory.yml`
- [ ] Create device browser interface
- [ ] Implement device grouping and filtering
- [ ] Add device connection testing

#### 1.4 Template Editor
- [ ] Build form-based template editor
- [ ] Create interface configuration builder
- [ ] Add routing protocol templates
- [ ] Implement validation rules

#### 1.5 Configuration Generation
- [ ] Integrate with existing Jinja2 templates
- [ ] Add real-time config preview
- [ ] Implement syntax validation
- [ ] Add config diff visualization

**Deliverables:**
- Working TUI application with device inventory
- Visual template editor for interfaces
- Configuration preview and validation
- Basic device connectivity testing

---

### Phase 2: PyEZ Integration & Real-Time Updates (Week 3-4)

**Objectives:**
- Integrate PyEZ for device operations
- Implement real-time progress updates
- Add configuration deployment
- Build validation workflows

**Tasks:**

#### 2.1 PyEZ Integration Layer
- [ ] Create PyEZ connection manager
- [ ] Implement credential management
- [ ] Add connection pooling
- [ ] Create device operation wrappers

#### 2.2 Configuration Deployment
- [ ] Implement config deployment workflow
- [ ] Add configuration comparison
- [ ] Create rollback functionality
- [ ] Implement staged deployments

#### 2.3 JSNAPy Integration
- [ ] Integrate JSNAPy for pre/post validation
- [ ] Create test case builder
- [ ] Add validation report viewer
- [ ] Implement automated testing workflows

#### 2.4 Real-Time Updates with FastAPI
- [ ] Set up FastAPI server
- [ ] Implement WebSocket for progress updates
- [ ] Create task queue system
- [ ] Add execution monitoring

#### 2.5 Multi-Device Operations
- [ ] Implement parallel device operations
- [ ] Add progress tracking per device
- [ ] Create operation summary reports
- [ ] Implement failure recovery

**Deliverables:**
- Full PyEZ integration with device operations
- JSNAPy validation workflows
- Real-time progress monitoring
- Multi-device deployment capabilities

---

### Phase 3: Advanced Features & Web Integration (Week 5-6)

**Objectives:**
- Add advanced monitoring capabilities
- Implement web API for external access
- Create reporting system
- Add automation workflows

**Tasks:**

#### 3.1 Advanced Monitoring
- [ ] Create interface monitoring dashboard
- [ ] Implement BGP neighbor monitoring
- [ ] Add system health monitoring
- [ ] Create alerting system

#### 3.2 Web API Development
- [ ] Implement FastAPI REST endpoints
- [ ] Add WebSocket for external clients
- [ ] Create authentication system
- [ ] Add API documentation

#### 3.3 Reporting System
- [ ] Create automated report generation
- [ ] Implement report templates
- [ ] Add scheduled reporting
- [ ] Create report distribution

#### 3.4 Automation Workflows
- [ ] Create workflow builder
- [ ] Add scheduled automation
- [ ] Implement conditional logic
- [ ] Create workflow templates

#### 3.5 File Management
- [ ] Add file upload/download capabilities
- [ ] Implement version control
- [ ] Create backup/restore system
- [ ] Add configuration history

**Deliverables:**
- Comprehensive monitoring dashboard
- Full REST API with WebSocket support
- Automated reporting system
- Workflow automation engine

---

### Phase 4: Production Readiness (Week 7-8)

**Objectives:**
- Add security features
- Implement backup/restore
- Create deployment automation
- Add user management

**Tasks:**

#### 4.1 Security Implementation
- [ ] Add user authentication
- [ ] Implement role-based access control
- [ ] Add audit logging
- [ ] Create security policies

#### 4.2 Backup & Recovery
- [ ] Implement automated backups
- [ ] Create disaster recovery procedures
- [ ] Add configuration restore
- [ ] Test recovery procedures

#### 4.3 Deployment Automation
- [ ] Create deployment scripts
- [ ] Add Docker support
- [ ] Implement configuration management
- [ ] Create monitoring setup

#### 4.4 Documentation & Training
- [ ] Create user documentation
- [ ] Add admin guide
- [ ] Create video tutorials
- [ ] Develop training materials

**Deliverables:**
- Production-ready system
- Complete documentation
- Training materials
- Deployment automation

---

## Detailed Implementation Steps

### Phase 1 Implementation Details

#### Step 1: Environment Setup
```bash
# Create TUI environment
python3 -m venv tui_env
source tui_env/bin/activate

# Install dependencies
pip install textual rich pyyaml jinja2 jnpr.junos
pip install fastapi uvicorn websockets
pip install jsnapy tqdm

# Create directory structure
mkdir -p tui/{app,components,services,models}
mkdir -p api/{routers,services,models}
mkdir -p templates/{forms,configs}
mkdir -p logs/{tui,api}
mkdir -p config/{backups,exports}
```

#### Step 2: Core TUI Application
```python
# tui/app/main.py
from textual.app import App
from textual.screen import Screen
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, ListView

class NetworkAutomationApp(App):
    """Main TUI application for network automation"""

    CSS = """
    Screen {
        background: $background;
    }
    Header {
        text-align: center;
        text-style: bold;
    }
    .menu-item {
        padding: 1;
    }
    """

    def on_mount(self):
        self.push_screen(MainMenuScreen())

    def action_quit(self):
        self.exit()

class MainMenuScreen(Screen):
    """Main menu screen"""

    def compose(self):
        yield Header("Network Automation TUI")
        yield Container(
            ListView(
                ("Device Management", self.show_device_menu),
                ("Template Editor", self.show_template_editor),
                ("Configuration Deploy", self.show_deployment),
                ("Monitoring", self.show_monitoring),
                ("Reports", self.show_reports),
            ),
            classes="menu-container"
        )
        yield Footer()

if __name__ == "__main__":
    app = NetworkAutomationApp()
    app.run()
```

#### Step 3: Device Inventory Interface
```python
# tui/components/device_browser.py
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Input, Button, Static
from textual.reactive import reactive
import yaml

class DeviceBrowser(Container):
    """Device inventory browser component"""

    devices = reactive([])

    def compose(self):
        yield Horizontal(
            Input(placeholder="Search devices...", id="search"),
            Button("Connect Test", id="test_conn"),
            classes="toolbar"
        )
        yield DataTable(id="device_table")
        yield Static("Select devices to manage", classes="help-text")

    def on_mount(self):
        table = self.query_one("#device_table")
        table.add_columns("Device", "IP", "Model", "Status", "Last Check")
        self.load_devices()

    def load_devices(self):
        """Load devices from inventory.yml"""
        try:
            with open('../data/inventory.yml', 'r') as f:
                inventory = yaml.safe_load(f)

            table = self.query_one("#device_table")
            table.clear()

            for device in inventory.get('devices', []):
                table.add_row(
                    device.get('name', 'Unknown'),
                    device.get('ip', 'N/A'),
                    device.get('model', 'N/A'),
                    "Unknown",
                    "Never"
                )

        except Exception as e:
            self.log.error(f"Failed to load devices: {e}")
```

#### Step 4: Template Editor Interface
```python
# tui/components/template_editor.py
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Select, Input, Button, Static, TextArea
from textual.validation import Function
import jinja2

class InterfaceTemplateEditor(Container):
    """Visual template editor for interface configurations"""

    def compose(self):
        yield Static("Interface Configuration Builder")

        with Vertical(classes="form-section"):
            yield Input(
                placeholder="ge-0/0/0",
                validators=[Function(self.validate_interface)],
                id="interface_name"
            )
            yield Input(placeholder="Link description", id="description")
            yield Select(
                options=[("Enabled", "enable"), ("Disabled", "disable")],
                value="enable",
                id="status"
            )

        with Vertical(classes="form-section"):
            yield Static("IP Configuration")
            yield Input(placeholder="192.168.1.1/24", id="ip_address")
            yield Select(
                options=[("None", "none"), ("OSPF", "ospf"), ("BGP", "bgp")],
                value="none",
                id="routing_protocol"
            )

        with Horizontal(classes="button-bar"):
            yield Button("Generate Config", id="generate", variant="primary")
            yield Button("Test on Device", id="test")
            yield Button("Save Template", id="save")

        yield TextArea("", id="config_preview", read_only=True)

    def validate_interface(self, value):
        """Validate interface name format"""
        import re
        pattern = r'^(ge|xe|et|lo)-[0-9]+/[0-9]+/[0-9]+$'
        return bool(re.match(pattern, value)) or "Invalid interface format"

    def on_button_pressed(self, event):
        if event.button.id == "generate":
            self.generate_config()

    def generate_config(self):
        """Generate Junos configuration from form data"""
        interface = self.query_one("#interface_name").value
        description = self.query_one("#description").value
        status = self.query_one("#status").value
        ip = self.query_one("#ip_address").value
        routing = self.query_one("#routing_protocol").value

        template = """
interfaces {
    {{ interface_name }} {
        description "{{ description }}";
        {% if ip %}
        unit 0 {
            family inet {
                address {{ ip }};
            }
        }
        {% endif %}
    }
}
        """

        config = jinja2.Template(template).render(
            interface_name=interface,
            description=description,
            ip=ip
        )

        self.query_one("#config_preview").text = config.strip()
```

### PyEZ and JSNAPy Integration Analysis

#### Current PyEZ Usage Review
Let me examine how PyEZ is currently used in the codebase to identify simplification opportunities:

1. **Connection Management**: Already centralized in `connect_to_hosts.py`
2. **Device Operations**: Basic RPC calls implemented
3. **Configuration Management**: File-based approach

#### PyEZ Enhancement Opportunities

```python
# Enhanced PyEZ integration using built-in capabilities
class EnhancedDeviceManager:
    """Simplified device management using PyEZ native features"""

    def __init__(self):
        from jnpr.junos import Device
        from jnpr.junos.utils.config import Config
        from jnpr.junos.op.ethport import EthPortTable
        from jnpr.junos.op.route import RouteTable
        from jnpr.junos.op.bgp import BGPNeighborTable

        self.Device = Device
        self.Config = Config
        self.EthPortTable = EthPortTable
        self.RouteTable = RouteTable
        self.BGPNeighborTable = BGPNeighborTable

    def get_interface_summary(self, device):
        """Use PyEZ op tables instead of raw RPC"""
        ports = self.EthPortTable(device)
        ports.get()
        return ports.items()

    def get_routes(self, device, table="inet.0"):
        """Use PyEZ route table operations"""
        routes = self.RouteTable(device, table=table)
        routes.get()
        return routes.items()

    def get_bgp_summary(self, device):
        """Use PyEZ BGP neighbor table"""
        bgp = self.BGPNeighborTable(device)
        bgp.get()
        return bgp.items()
```

#### JSNAPy Integration for Validation

```python
# JSNAPy integration for automated testing
class JSNAPyValidator:
    """Integrate JSNAPy for pre/post configuration validation"""

    def __init__(self):
        from jnpr.jsnapy import SnapAdmin
        self.snap_admin = SnapAdmin()

    def create_pre_snapshot(self, device, test_file):
        """Create pre-change snapshot"""
        return self.snap_admin.snap(
            device,
            snap_name="pre_change",
            test_file=test_file
        )

    def create_post_snapshot(self, device, test_file):
        """Create post-change snapshot"""
        return self.snap_admin.snap(
            device,
            snap_name="post_change",
            test_file=test_file
        )

    def compare_snapshots(self, device, test_file):
        """Compare pre/post snapshots"""
        return self.snap_admin.check(
            device,
            check_from="pre_change",
            check_to="post_change",
            test_file=test_file
        )
```

#### Simplified Architecture with PyEZ/JSNAPy

```
TUI Application
├── PyEZ Device Manager (simplified)
│   ├── Native PyEZ Tables (no raw RPC)
│   ├── Built-in Config Utilities
│   ├── Automatic Connection Pooling
│   └── Error Handling
├── JSNAPy Validation Layer
│   ├── Pre/Post Snapshots
│   ├── Automated Test Cases
│   ├── Diff Analysis
│   └── Pass/Fail Reporting
└── FastAPI WebSocket
    ├── Real-time Progress
    ├── Status Updates
    ├── Log Streaming
    └── Task Management
```

### FastAPI + WebSocket Implementation

```python
# api/main.py - FastAPI with WebSocket support
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import asyncio
import json

app = FastAPI(title="Network Automation API")

# CORS for TUI access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For TUI, adjust for production
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
            await manager.send_message(f"Received: {data}", client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# API endpoints for TUI
@app.post("/api/devices/connect")
async def connect_devices(device_list: list):
    """Connect to multiple devices with real-time updates"""
    task_id = f"connect_{len(device_list)}_devices"

    # Start background task
    asyncio.create_task(connect_devices_background(device_list, task_id))

    return {"task_id": task_id, "status": "started"}

async def connect_devices_background(devices, task_id):
    """Background task with WebSocket updates"""
    for i, device in enumerate(devices):
        # Simulate device connection
        await asyncio.sleep(1)  # Connection time

        # Send progress update
        await manager.broadcast(json.dumps({
            "task_id": task_id,
            "progress": (i + 1) / len(devices) * 100,
            "device": device,
            "status": "connected"
        }))

    await manager.broadcast(json.dumps({
        "task_id": task_id,
        "status": "completed"
    }))
```

### Deployment Instructions

#### Development Deployment
```bash
# 1. Clone repository
git clone <repository_url>
cd netstudio

# 2. Set up TUI environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Install additional TUI dependencies
pip install textual rich pyyaml jnpr.junos jsnapy

# 4. Start TUI application
python tui/app/main.py

# 5. Start FastAPI server (in separate terminal)
source venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production Deployment
```bash
# 1. Create deployment directory
sudo mkdir -p /opt/netstudio
sudo cp -r . /opt/netstudio/
cd /opt/netstudio

# 2. Set up system user
sudo useradd -r -s /bin/false netstudio
sudo chown -R netstudio:netstudio /opt/netstudio

# 3. Create systemd service for FastAPI
sudo tee /etc/systemd/system/netstudio-api.service > /dev/null <<EOF
[Unit]
Description=Network Automation API
After=network.target

[Service]
Type=exec
User=netstudio
Group=netstudio
WorkingDirectory=/opt/netstudio
Environment=PATH=/opt/netstudio/venv/bin
ExecStart=/opt/netstudio/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 4. Create systemd service for TUI (optional)
sudo tee /etc/systemd/system/netstudio-tui.service > /dev/null <<EOF
[Unit]
Description=Network Automation TUI
After=network.target

[Service]
Type=simple
User=netstudio
Group=netstudio
WorkingDirectory=/opt/netstudio
Environment=PATH=/opt/netstudio/venv/bin
ExecStart=/opt/netstudio/venv/bin/python tui/app/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 5. Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable netstudio-api
sudo systemctl start netstudio-api

# 6. Verify deployment
curl http://localhost:8000/docs
```

#### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Start API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  netstudio-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - VECTOR_PY_DIR=/app
    restart: unless-stopped

  netstudio-tui:
    build: .
    command: python tui/app/main.py
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - /dev/tty:/dev/tty
    environment:
      - TERM=xterm-256color
    restart: unless-stopped
```

---

## Next Steps

With this comprehensive plan, we can proceed with:

1. **Phase 1**: Build the core TUI with device inventory and template editing
2. **Phase 2**: Integrate PyEZ/JSNAPy for real device operations
3. **Phase 3**: Add FastAPI + WebSocket for real-time updates

The architecture leverages Juniper's native capabilities (PyEZ/JSNAPy) to simplify our implementation while providing a modern, user-friendly interface for network engineers.

**Key Benefits of This Approach:**
- **Simplified stack**: TUI + FastAPI + PyEZ/JSNAPy
- **Leverages existing tools**: Uses Juniper's official libraries
- **Familiar environment**: Network engineers stay in terminal
- **Real-time capabilities**: WebSocket for live updates
- **Progressive enhancement**: Start simple, add features as needed

Ready to begin Phase 1 implementation?