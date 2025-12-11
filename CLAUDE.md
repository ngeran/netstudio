# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Net-launcher is a Python-based network automation framework for managing Juniper networking devices (SRX firewalls, EX switches, routers). It provides interactive CLI-driven tools for device management including code upgrades, configuration backup/restore, BGP management, interface configuration, state capture, and route monitoring.

## Environment Setup

**Required Environment Variable:**
```bash
export VECTOR_PY_DIR=/path/to/net-launcher
```

This variable is used throughout the codebase to locate configuration files in the `data/` directory.

**Dependencies:**
- Python 3.x
- Key libraries: `jnpr.junos` (PyEZ), `jinja2`, `pyyaml`, `tabulate`, `deepdiff`

## Running the Application

**Main entry point (recommended):**
```bash
python launcher.py
```

This provides an interactive menu system with all available actions, execution mode selection, and device input options.

**Alternative entry points:**
```bash
# Legacy entry point (calls network_automation.py directly)
python main.py

# Direct script execution
python scripts/code_upgrade.py
python scripts/config_toolbox.py
python scripts/bgp_toolbox.py
python scripts/state_capture.py
```

## Architecture

### Core Components

**Entry Point & Orchestration:**
- `main.py` - Delegates to `scripts/network_automation.py:main()`
- `scripts/network_automation.py` - Main orchestrator with action mapping and menu system
- `scripts/launcher.py` - Alternative launcher with device selection workflow

**Action Layer:**
- `scripts/actions.py` - Action wrappers and orchestrators (ping, interfaces, route_monitor)
- `scripts/diagnostic_actions.py` - Diagnostic actions (ping tests)
- `scripts/interface_actions.py` - Interface configuration with Jinja2 templates
- `scripts/route_monitor.py` - Route monitoring implementation
- `scripts/code_upgrade.py` - Interactive code upgrade workflow for Junos devices
- `scripts/bgp_toolbox.py` - BGP configuration and management
- `scripts/config_toolbox.py` - Configuration backup/restore operations
- `scripts/state_capture.py` - Pre/post state capture with diff analysis using DeepDiff

**Connection Layer:**
- `scripts/connect_to_hosts.py` - Centralizes device connection/disconnection using jnpr.junos.Device
- Returns list of Device objects, handles ConnectError gracefully

**Utilities:**
- `scripts/utils.py` - YAML loading/saving, device reachability checks, device IP input helpers
- `scripts/junos_actions.py` - Junos-specific RPC actions

### Configuration Files (data/)

- `action_map.yml` - Maps action names to display names for the menu system
- `hosts_data.yml` - Device inventory with credentials (username/password), IPs, device metadata
- `upgrade_data.yml` - Vendor/product/release matrix for code upgrades
- `upgrade_hosts.yml` or `upgrade_inventory.yml` - Device lists for upgrade operations
- `actions.yml` - Action definitions with display names
- `devices.yaml` - Simple device IP list

### Data Flow

1. User launches `launcher.py` which presents interactive action menu
2. User selects action (ping, interfaces, route_monitor, state_capture, code_upgrade, etc.)
3. User selects execution mode (Execute Locally or Push to GitHub)
4. **Device Selection:** User chooses device input method:
   - Option 1: Load from inventory file (`hosts_data.yml`)
   - Option 2: Enter manually (prompts for IPs, username, password)
5. Action orchestrator calls `get_hosts()` which prompts for device selection
6. Action orchestrator calls `connect_to_hosts()` to establish jnpr.junos.Device connections
7. Action-specific module executes operations on connected devices
8. Results are logged to `network_automation.log` and/or saved to `reports/` or `state/` directories
9. Connections are closed via `disconnect_from_hosts()`

## Key Patterns

**Connection Management:**
All scripts use a consistent pattern:
```python
from scripts.connect_to_hosts import connect_to_hosts, disconnect_from_hosts

connections = connect_to_hosts(host_ip, username, password)
# ... perform operations ...
disconnect_from_hosts(connections)
```

**Interactive Menu System:**
Menu functions use retry logic (max 5 attempts) with extensive logging and error handling for invalid inputs, EOFError, and KeyboardInterrupt.

**Logging:**
All modules use Python's `logging` module configured to write to `network_automation.log` with format: `%(asctime)s - %(levelname)s - %(message)s`

**Configuration Templating:**
Uses Jinja2 templates (in `templates/`) with YAML data for generating device configurations.

**State Management:**
- `state/` - Stores pre/post state captures for comparison
- `reports/` - Stores generated reports (ping, route monitoring)
- `backups/` - Stores configuration backups

## Code Upgrade Workflow

The upgrade process (`code_upgrade.py`) is interactive and follows these steps:
1. Select vendor → product → release from `upgrade_data.yml`
2. Select device IPs from `upgrade_hosts.yml` or manual entry
3. For each device:
   - Connect and verify image exists on device
   - Check current version vs. target version
   - Install software with validation (`jnpr.junos.utils.sw.SW`)
   - Reboot device
   - Probe device until reachable (with extended timeout for EX4600)
   - Verify new version is running
4. Display summary of successful/failed upgrades

## Important Notes

- Credentials are stored in plaintext in `hosts_data.yml` (username/password fields)
- Default credentials fallback: `username=admin`, `password=password`
- Device reachability checked via subprocess ping before connection attempts
- EX4600 devices have special handling with longer probe timeouts
- The codebase uses both `host_ip` and `ip_address` keys inconsistently across YAML files
