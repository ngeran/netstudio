# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NetStudio** is a comprehensive network automation framework for managing Juniper networking devices (SRX firewalls, EX switches, routers). It provides three distinct interfaces:

1. **Terminal User Interface (TUI)** - Modern, interactive terminal UI built with Textual framework
2. **FastAPI REST Backend** - Async REST and WebSocket API for programmatic access
3. **Legacy CLI** - Original script-based command-line interface

The project supports device management including code upgrades, configuration backup/restore, BGP management, interface configuration, state capture, route monitoring, and advanced Phase 3 features (validation, monitoring, topology discovery, reporting).

## Environment Setup

**Required Environment Variable:**
```bash
export VECTOR_PY_DIR=/path/to/netstudio
```

This variable is used throughout the codebase to locate configuration files in the `data/` directory.

**Dependencies:**
- Python 3.8+
- Install with: `pip install -r requirements.txt`
- Key libraries: `jnpr.junos` (PyEZ), `fastapi`, `textual`, `jinja2`, `pyyaml`, `deepdiff`, `psutil`

## Running the Application

### Primary Interfaces

**1. TUI Interface (Recommended):**
```bash
python tui/app/main.py
```
Modern terminal interface with themes, real-time updates, and keyboard navigation.

**2. FastAPI Backend:**
```bash
python api/main.py
# Or with uvicorn for development:
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
REST API at http://localhost:8000, interactive docs at http://localhost:8000/docs

**3. Legacy CLI:**
```bash
python launcher.py
```
Interactive menu system with all available automation actions.

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_basic_functionality.py

# Run with verbose output
pytest -v

# Run specific test markers
pytest -m slow  # For tests marked as slow
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking (optional)
mypy .
```

## Architecture Overview

The project follows a multi-layered architecture with clear separation of concerns:

### 1. Frontend Interfaces

**TUI (tui/):**
- `tui/app/main.py` - Main TUI application using Textual framework
- `tui/components/` - Reusable UI components and widgets
- `tui/services/` - Service layer for TUI operations
- `tui/models/` - Data models used by the TUI

**API (api/):**
- `api/main.py` - FastAPI application with WebSocket support
- `api/services/` - Core business logic services
- `api/endpoints/` - REST API route definitions

### 2. Service Layer

**Core Services:**
- `api/services/device_manager.py` - Device connection and management
- `api/services/task_manager.py` - Async task execution and tracking
- `tui/services/inventory_service.py` - Device inventory management
- `tui/services/api_client.py` - TUI to API communication

### 3. Automation Scripts (scripts/)

**Device Operations:**
- `connect_to_hosts.py` - Centralized connection management
- `code_upgrade.py` - Interactive Junos upgrade workflow
- `state_capture.py` - Pre/post state capture with diff analysis

**Configuration Management:**
- `config_toolbox.py` - Backup, restore, and deployment
- `interface_actions.py` - Interface configuration with Jinja2 templates
- `bgp_toolbox.py` - BGP configuration and monitoring

**Monitoring & Diagnostics:**
- `route_monitor.py` - Real-time route monitoring
- `diagnostic_actions.py` - Ping tests and diagnostics
- `junos_actions.py` - Junos-specific RPC actions

### 4. Phase 3 Advanced Features (phase3/)

**Services (planned/in development):**
- `phase3/services/jsnapy_service.py` - Configuration validation
- `phase3/services/monitoring_service.py` - Real-time monitoring
- `phase3/services/topology_service.py` - Network topology discovery
- `phase3/services/reporting_service.py` - Analytics and reporting

### 5. Data Layer (data/)

**Configuration Files:**
- `hosts_data.yml` - Device inventory with credentials
- `actions.yml` - Action definitions for automation
- `action_map.yml` - UI/action mappings
- `upgrade_data.yml` - Software upgrade matrices

**Storage Directories:**
- `backups/` - Configuration backups
- `inventories/` - Multiple inventory support
- `templates/` - Jinja2 configuration templates
- `state/` - State captures for comparison

## Key Patterns and Conventions

### Connection Management
```python
from scripts.connect_to_hosts import connect_to_hosts, disconnect_from_hosts

# Consistent pattern across all scripts
connections = connect_to_hosts(host_ip, username, password)
# ... perform operations ...
disconnect_from_hosts(connections)
```

### Async Operations
FastAPI backend uses async/await throughout:
```python
@app.post("/api/devices/{device_ip}/config")
async def deploy_config(device_ip: str, config: ConfigModel):
    async with device_manager.connect(device_ip) as device:
        result = await device.deploy_config(config.config)
    return result
```

### WebSocket Integration
Real-time updates via WebSocket for:
- Task progress tracking
- Monitoring data streams
- Live configuration deployment status

### Error Handling
- Comprehensive logging to `network_automation.log`
- Graceful fallbacks for missing dependencies (mock modes)
- Retry mechanisms for transient failures
- Consistent exception handling across layers

## Development Workflow

### Adding New Features

1. **TUI Components**: Add to `tui/components/`
2. **API Endpoints**: Add to appropriate `api/` module
3. **Automation Scripts**: Add to `scripts/`
4. **Phase 3 Features**: Add to `phase3/services/` or `phase3/api/endpoints/`
5. **Tests**: Add to `tests/` directory

### Project Structure Reference
```
netstudio/
├── api/                    # FastAPI backend
│   ├── main.py            # Main API application
│   └── services/          # Core services
├── tui/                   # Terminal User Interface
│   ├── app/               # Main TUI application
│   ├── components/        # UI widgets
│   └── services/          # TUI services
├── phase3/                # Advanced features
│   ├── services/          # Validation, monitoring, etc.
│   └── api/endpoints/     # Phase 3 API endpoints
├── scripts/               # Core automation scripts
├── data/                  # Configuration files
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## Important Notes

- **Security**: Credentials stored in plaintext in `hosts_data.yml` (consider environment variables for production)
- **Mock Mode**: Services work with mock implementations when PyEZ/JSNAPy not installed
- **Theming**: TUI supports multiple themes (tokyo-night, nord, gruvbox)
- **Real-time Features**: WebSocket support for live updates in both TUI and API
- **Phase 3**: Advanced features are modular - can be enabled/disabled based on requirements
