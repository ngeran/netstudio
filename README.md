# Network Automation TUI

A comprehensive Terminal User Interface (TUI) for Juniper network automation with advanced validation, monitoring, topology discovery, and reporting capabilities.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment
- Juniper devices (for full functionality)

### Installation & Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd netstudio

# 2. Create and activate virtual environment
python -m venv network_tui_env
source network_tui_env/bin/activate  # On Windows: network_tui_env\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variable
export VECTOR_PY_DIR=/path/to/netstudio

# 5. Add to PATH
export PATH=$PATH:/path/to/netstudio
```

## 🎮 Usage Modes

### 1. TUI Interface (Recommended)

```bash
# Launch the interactive TUI
python launcher.py
```

**TUI Features:**
- Device inventory management
- Template-based configuration generation
- Real-time deployment with progress tracking
- Multi-device parallel operations
- Validation and monitoring integration

### 2. API Server Mode

```bash
# Start the FastAPI backend server
python api/main.py

# Or with specific host/port
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**API Features:**
- RESTful API for all operations
- WebSocket for real-time updates
- Phase 3 advanced services (validation, monitoring, topology, reporting)
- Interactive API docs at `http://localhost:8000/docs`

### 3. Legacy CLI Mode

```bash
# Use the original CLI interface
python main.py
```

## 🛠️ Service Management

### Starting Services

```bash
# Start with TUI
python launcher.py

# Start API server only
python api/main.py &

# Start in background with nohup
nohup python api/main.py > api.log 2>&1 &
```

### Stopping Services

```bash
# Find and stop API server
lsof -ti:8000 | xargs kill -9

# Or find process by name
pkill -f "python.*api/main.py"

# Stop TUI (press Ctrl+C in terminal)
```

### Checking Service Status

```bash
# Check if API server is running
curl -s http://localhost:8000/api/health | jq .

# Check process status
ps aux | grep "python.*api/main.py"

# Check port usage
lsof -i:8000
```

## 📱 Web Interface & API

### Access Points

**API Documentation**: http://localhost:8000/docs
**ReDoc Documentation**: http://localhost:8000/redoc
**Health Check**: http://localhost:8000/api/health

### Key API Endpoints

#### Phase 2 (Core Operations)
```bash
# Device management
GET /api/devices
GET /api/devices/{device_ip}
POST /api/devices/connect

# Configuration management
POST /api/config/deploy
POST /api/config/rollback
POST /api/devices/facts

# Task management
GET /api/tasks
GET /api/tasks/{task_id}
POST /api/tasks/{task_id}/cancel
```

#### Phase 3 (Advanced Features)
```bash
# JSNAPy Validation
GET /api/validation/test-cases
POST /api/validation/suite
GET /api/validation/{suite_id}/report

# Real-time Monitoring
POST /api/monitoring/start
GET /api/monitoring/status
WebSocket: /api/monitoring/ws

# Network Topology
POST /api/topology/discover
GET /api/topology/{topology_id}
GET /api/topology/{topology_id}/export/{format}

# Reporting & Analytics
GET /api/reports/definitions
POST /api/reports/generate
GET /api/reports/dashboard
```

### Using the API

```bash
# Get device inventory
curl -X GET "http://localhost:8000/api/devices" \
  -H "accept: application/json"

# Deploy configuration
curl -X POST "http://localhost:8000/api/config/deploy" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "device_ips": ["172.27.200.200"],
    "config": "set system hostname test-device",
    "message": "API deployment test"
  }'

# Start monitoring
curl -X POST "http://localhost:8000/api/monitoring/start" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "interval": 60,
    "thresholds": {"cpu_warning": 75.0}
  }'
```

## 🔧 Configuration

### Device Inventory Setup

Edit configuration files in the `data/` directory:

```bash
# Edit device inventory
nano data/hosts_data.yml

# Example hosts_data.yml format:
hosts:
  - host_name: core-router-1
    ip_address: 172.27.200.200
    username: admin
    password: your_password
    device_type: router
    vendor: juniper
    location: datacenter1
```

### Environment Variables

```bash
# Required
export VECTOR_PY_DIR=/path/to/netstudio

# Optional
export LOG_LEVEL=INFO
export API_HOST=0.0.0.0
export API_PORT=8000
export DEBUG=true
```

### Monitoring Configuration

```yaml
# data/monitoring.yml
monitoring:
  interval: 60  # seconds
  thresholds:
    cpu_warning: 70.0
    cpu_critical: 90.0
    memory_warning: 80.0
    memory_critical: 95.0
    interface_error_rate_warning: 0.01
    bgp_state_down: critical
```

## 🎯 Phase 3 Advanced Features

### JSNAPy Validation

```bash
# List available test cases
curl http://localhost:8000/api/validation/test-cases

# Create validation suite
curl -X POST http://localhost:8000/api/validation/suite \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Interface Validation",
    "description": "Validate interface configurations",
    "test_cases": ["interface_validation"],
    "devices": [{
      "host_ip": "172.27.200.200",
      "username": "admin",
      "password": "password"
    }]
  }'
```

### Real-time Monitoring

```bash
# Register devices for monitoring
curl -X POST http://localhost:8000/api/monitoring/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_info": {
      "host_ip": "172.27.200.200",
      "username": "admin",
      "password": "password"
    }
  }'

# Start monitoring
curl -X POST http://localhost:8000/api/monitoring/start

# Get monitoring dashboard
curl http://localhost:8000/api/monitoring/dashboard/summary
```

### Network Topology Discovery

```bash
# Start topology discovery
curl -X POST http://localhost:8000/api/topology/discover \
  -H "Content-Type: application/json" \
  -d '{
    "seed_devices": [{
      "host_ip": "172.27.200.200",
      "username": "admin",
      "password": "password"
    }],
    "discovery_method": "auto"
  }'

# Get visualization data
curl http://localhost:8000/api/topology/latest/visualization-data
```

### Reporting and Analytics

```bash
# Generate a report
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "daily_deployment_summary",
    "format": "json"
  }'

# Get reports dashboard
curl http://localhost:8000/api/reports/dashboard
```

## 🐛 Troubleshooting

### Common Issues

**1. Port 8000 already in use**
```bash
# Find process using port
lsof -i:8000

# Kill process
kill -9 <PID>

# Or use different port
python -m uvicorn api.main:app --port 8001
```

**2. Import errors**
```bash
# Ensure virtual environment is activated
source network_tui_env/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

**3. Device connection issues**
```bash
# Test device connectivity
ping 172.27.200.200

# Check device credentials in hosts_data.yml
cat data/hosts_data.yml

# Test PyEZ connection manually
python -c "
from jnpr.junos import Device
dev = Device(host='172.27.200.200', user='admin', password='password')
dev.open()
print('Connected successfully')
dev.close()
"
```

**4. Mock mode warnings**
```bash
# These are normal if JSNAPy/PyEZ not installed
# All services work with mock implementations
# To install full dependencies:
pip install jnpr.junos jnpr.jsnapy
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true

# Start with verbose logging
python api/main.py --log-level debug

# Check logs
tail -f api.log
tail -f network_automation.log
```

### Performance Monitoring

```bash
# Monitor API server performance
curl -s http://localhost:8000/api/health | jq .

# Monitor memory usage
ps aux | grep python

# Check response times
time curl -s http://localhost:8000/api/devices
```

## 🔄 Development Workflow

### Making Changes

```bash
# 1. Make code changes
vim api/main.py

# 2. Restart API server (auto-reload enabled)
# Server will restart automatically

# 3. Test changes
curl http://localhost:8000/api/health

# 4. Run tests
python test_phase2_evaluation.py
python test_phase3_evaluation.py
```

### Adding New Features

1. **New Service**: Add to `phase3/services/`
2. **API Endpoints**: Add to `phase3/api/endpoints/`
3. **TUI Components**: Add to `tui/components/`
4. **Tests**: Create test file and update evaluation

## 📊 Monitoring & Logs

### Log Files

```bash
# API logs
tail -f api.log

# Network automation logs
tail -f network_automation.log

# Phase 3 service logs
tail -f phase3/data/monitoring.log
```

### Performance Metrics

```bash
# Check API health
curl -s http://localhost:8000/api/health | jq '.statistics'

# Monitoring service status
curl -s http://localhost:8000/api/monitoring/status | jq .

# Report generation status
curl -s http://localhost:8000/api/reports/dashboard | jq '.summary'
```

## 🔒 Security Considerations

### Production Deployment

```bash
# Use environment variables for credentials
export JUNIPER_PASSWORD=$(cat /secure/passwords/juniper.txt)

# Enable HTTPS
pip install uvicorn[standard]
uvicorn api.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=key.pem --ssl-certfile=cert.pem

# Use reverse proxy (nginx/apache)
# Limit API access to internal networks
# Implement authentication/authorization
```

## 📝 Support & Documentation

### Getting Help

```bash
# Check API documentation
curl http://localhost:8000/docs

# Check available endpoints
curl http://localhost:8000/ | jq .endpoints

# Run health check
curl http://localhost:8000/api/health
```

### File Structure Reference

```
netstudio/
├── api/                    # FastAPI backend
│   ├── main.py            # Main API application
│   └── services/          # Core services
├── phase3/                # Phase 3 advanced features
│   ├── services/          # Validation, monitoring, etc.
│   └── api/endpoints/     # Phase 3 API endpoints
├── tui/                   # Terminal User Interface
│   ├── app/               # Main TUI application
│   └── components/        # TUI widgets
├── data/                  # Configuration files
├── docs/                  # Documentation
└── scripts/               # Legacy CLI scripts
```

### Contact & Support

- **Issues**: Create GitHub issue
- **Documentation**: Check `docs/` directory
- **API Reference**: http://localhost:8000/docs
- **Logs**: Check application logs for error details