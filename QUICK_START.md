# Network Automation TUI - Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### 1. Launch the System

```bash
# Make the management script executable
chmod +x netstudio.sh

# Start the API server
./netstudio.sh start

# Launch the TUI interface
./netstudio.sh tui
```

### 2. Access Points

**🌐 Web Interface**: http://localhost:8000/docs
**💻 TUI Interface**: Run `./netstudio.sh tui`
**📊 API Health**: http://localhost:8000/api/health

## 📱 Main Usage Modes

### Mode 1: Interactive TUI (Recommended)
```bash
./netstudio.sh tui
```
✅ Features:
- Device inventory management
- Configuration template editor
- Real-time deployment tracking
- Multi-device operations

### Mode 2: Web API
```bash
./netstudio.sh start
# Open http://localhost:8000/docs
```
✅ Features:
- RESTful API for all operations
- Interactive API documentation
- Phase 3 advanced features

### Mode 3: Management Script
```bash
./netstudio.sh status    # Check status
./netstudio.sh logs      # View logs
./netstudio.sh restart   # Restart services
./netstudio.sh stop      # Stop services
```

## 🎯 Basic Operations

### Add a Device
```bash
# Edit device inventory
nano data/hosts_data.yml

# Add device:
# - host_name: router-1
#   ip_address: 172.27.200.200
#   username: admin
#   password: your_password
```

### Deploy Configuration via TUI
1. Launch `./netstudio.sh tui`
2. Select "Device Browser"
3. Choose devices
4. Go to "Configuration Deployment"
5. Select template and deploy

### Deploy Configuration via API
```bash
curl -X POST http://localhost:8000/api/config/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "device_ips": ["172.27.200.200"],
    "config": "set system hostname new-hostname",
    "message": "API test deployment"
  }'
```

## 🔧 Phase 3 Advanced Features

### 1. Configuration Validation (JSNAPy)
```bash
# List validation test cases
curl http://localhost:8000/api/validation/test-cases

# Run validation suite
curl -X POST http://localhost:8000/api/validation/suite \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Interface Validation",
    "test_cases": ["interface_validation"],
    "devices": [{"host_ip": "172.27.200.200", "username": "admin", "password": "password"}]
  }'
```

### 2. Real-time Monitoring
```bash
# Register device for monitoring
curl -X POST http://localhost:8000/api/monitoring/devices/register \
  -H "Content-Type: application/json" \
  -d '{"device_info": {"host_ip": "172.27.200.200", "username": "admin", "password": "password"}}'

# Start monitoring
curl -X POST http://localhost:8000/api/monitoring/start

# View monitoring dashboard
curl http://localhost:8000/api/monitoring/dashboard/summary
```

### 3. Network Topology Discovery
```bash
# Discover network topology
curl -X POST http://localhost:8000/api/topology/discover \
  -H "Content-Type: application/json" \
  -d '{
    "seed_devices": [{"host_ip": "172.27.200.200", "username": "admin", "password": "password"}],
    "discovery_method": "auto"
  }'

# Get visualization data
curl http://localhost:8000/api/topology/latest/visualization-data
```

### 4. Reporting and Analytics
```bash
# Generate a report
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "daily_deployment_summary",
    "format": "json"
  }'

# View reports dashboard
curl http://localhost:8000/api/reports/dashboard
```

## 🛠️ Essential Commands

```bash
# System Management
./netstudio.sh start     # Start API server
./netstudio.sh stop      # Stop API server
./netstudio.sh restart   # Restart API server
./netstudio.sh status    # Check system status
./netstudio.sh tui       # Launch TUI interface

# Development & Debugging
./netstudio.sh logs      # View logs
./netstudio.sh follow    # Follow logs in real-time
./netstudio.sh api       # Test API endpoints
./netstudio.sh install   # Install dependencies

# Direct Execution
python launcher.py                    # Launch TUI directly
python api/main.py                    # Start API server directly
python -m uvicorn api.main:app --reload  # API with auto-reload
```

## 📊 Common Tasks

### Check System Status
```bash
./netstudio.sh status
curl http://localhost:8000/api/health
```

### View Available Devices
```bash
curl http://localhost:8000/api/devices
```

### Test Device Connection
```bash
curl -X POST http://localhost:8000/api/devices/connect \
  -H "Content-Type: application/json" \
  -d '["172.27.200.200"]'
```

### Get Task Status
```bash
curl http://localhost:8000/api/tasks
```

### View Recent Deployments
```bash
curl -X POST http://localhost:8000/api/devices/facts \
  -H "Content-Type: application/json" \
  -d '["172.27.200.200"]'
```

## 🔍 Troubleshooting

### API Server Not Starting
```bash
# Check if port 8000 is in use
lsof -i:8000

# Kill existing process
pkill -f "python.*api/main.py"

# Restart with clean slate
./netstudio.sh stop
./netstudio.sh start
```

### Device Connection Issues
```bash
# Test network connectivity
ping 172.27.200.200

# Check device credentials in hosts_data.yml
cat data/hosts_data.yml

# View detailed error logs
./netstudio.sh follow
```

### Import Errors
```bash
# Reinstall dependencies
./netstudio.sh install

# Check virtual environment
source phase1_env/bin/activate
pip list | grep fastapi
```

## 📱 Access Points Summary

| Interface | URL | Command |
|-----------|-----|---------|
| **TUI** | Terminal | `./netstudio.sh tui` |
| **API Docs** | http://localhost:8000/docs | `./netstudio.sh start` |
| **ReDoc** | http://localhost:8000/redoc | `./netstudio.sh start` |
| **Health Check** | http://localhost:8000/api/health | `./netstudio.sh api` |
| **Device List** | http://localhost:8000/api/devices | `curl http://localhost:8000/api/devices` |

## 🎯 Quick Workflow

1. **Setup**: `./netstudio.sh install && ./netstudio.sh start`
2. **Configure**: Edit `data/hosts_data.yml` with device details
3. **Test**: `./netstudio.sh api` to verify connectivity
4. **Launch**: `./netstudio.sh tui` for interactive interface
5. **Monitor**: `./netstudio.sh status` to check system health

## 📞 Help & Support

```bash
# Get help
./netstudio.sh help

# View comprehensive documentation
cat README.md

# Check API capabilities
curl http://localhost:8000/ | jq .
```

**🎉 You're ready to start using Network Automation TUI!**