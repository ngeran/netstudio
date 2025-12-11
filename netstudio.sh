#!/bin/bash

# Network Automation TUI Management Script
# Usage: ./netstudio.sh [start|stop|restart|status|tui|api|logs]

set -e

# Configuration
VENV_DIR="phase1_env"
API_HOST="0.0.0.0"
API_PORT="8000"
LOG_FILE="api.log"
PID_FILE="api.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}[*] $1${NC}"
}

print_success() {
    echo -e "${GREEN}[✓] $1${NC}"
}

print_error() {
    echo -e "${RED}[✗] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

# Check if virtual environment exists
check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment $VENV_DIR not found"
        echo "Run: python -m venv $VENV_DIR"
        exit 1
    fi
}

# Check if required directories exist
check_structure() {
    if [ ! -f "api/main.py" ]; then
        print_error "API main.py not found. Are you in the correct directory?"
        exit 1
    fi
}

# Activate virtual environment
activate_env() {
    check_venv
    source "$VENV_DIR/bin/activate"
    print_success "Virtual environment activated"
}

# Check if API server is running
is_api_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Start API server
start_api() {
    if is_api_running; then
        print_warning "API server is already running (PID: $(cat $PID_FILE))"
        return
    fi

    print_status "Starting API server..."
    activate_env
    check_structure

    # Set environment variable
    export VECTOR_PY_DIR=$(pwd)

    # Start in background
    nohup python api/main.py > "$LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"

    # Wait for server to start
    sleep 3

    if is_api_running; then
        print_success "API server started successfully (PID: $pid)"
        print_status "API Documentation: http://localhost:$API_PORT/docs"
        print_status "Health Check: curl http://localhost:$API_PORT/api/health"
    else
        print_error "Failed to start API server"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Stop API server
stop_api() {
    if ! is_api_running; then
        print_warning "API server is not running"
        return
    fi

    local pid=$(cat "$PID_FILE")
    print_status "Stopping API server (PID: $pid)..."

    kill "$pid" 2>/dev/null || true

    # Wait for graceful shutdown
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done

    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
        print_warning "Force killing API server..."
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    print_success "API server stopped"
}

# Restart API server
restart_api() {
    stop_api
    sleep 2
    start_api
}

# Show API server status
show_status() {
    echo -e "${BLUE}=== Network Automation TUI Status ===${NC}"

    if is_api_running; then
        local pid=$(cat "$PID_FILE")
        print_success "API Server: RUNNING (PID: $pid)"

        # Show health check if available
        if command -v curl >/dev/null 2>&1; then
            local health=$(curl -s http://localhost:$API_PORT/api/health 2>/dev/null | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
            print_status "Health Check: $health"

            local version=$(curl -s http://localhost:$API_PORT/ 2>/dev/null | jq -r '.version // "unknown"' 2>/dev/null || echo "unknown")
            print_status "Version: $version"
        fi
    else
        print_error "API Server: STOPPED"
    fi

    echo
    print_status "Log File: $LOG_FILE"
    print_status "PID File: $PID_FILE"
    print_status "Virtual Environment: $VENV_DIR"

    if [ -f "$LOG_FILE" ]; then
        local log_size=$(du -h "$LOG_FILE" | cut -f1)
        print_status "Log Size: $log_size"
    fi
}

# Launch TUI interface
launch_tui() {
    activate_env
    check_structure

    # Set environment variable
    export VECTOR_PY_DIR=$(pwd)

    print_status "Launching TUI interface..."
    python launcher.py
}

# Show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_status "Showing last 50 lines of $LOG_FILE:"
        tail -50 "$LOG_FILE"
    else
        print_warning "Log file $LOG_FILE not found"
    fi
}

# Follow logs
follow_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_status "Following $LOG_FILE (Ctrl+C to stop)..."
        tail -f "$LOG_FILE"
    else
        print_warning "Log file $LOG_FILE not found"
    fi
}

# Test API endpoints
test_api() {
    if ! is_api_running; then
        print_error "API server is not running"
        return
    fi

    print_status "Testing API endpoints..."

    # Test health endpoint
    echo -e "${BLUE}Testing health endpoint...${NC}"
    curl -s http://localhost:$API_PORT/api/health | jq . 2>/dev/null || curl -s http://localhost:$API_PORT/api/health
    echo

    # Test root endpoint
    echo -e "${BLUE}Testing root endpoint...${NC}"
    curl -s http://localhost:$API_PORT/ | jq . 2>/dev/null || curl -s http://localhost:$API_PORT/
    echo

    # Test Phase 3 services
    echo -e "${BLUE}Testing Phase 3 services...${NC}"
    curl -s http://localhost:$API_PORT/api/validation/status | jq .service 2>/dev/null || echo "Validation service: unknown"
    curl -s http://localhost:$API_PORT/api/monitoring/status | jq .active 2>/dev/null || echo "Monitoring service: unknown"
    curl -s http://localhost:$API_PORT/api/reports/definitions | jq length 2>/dev/null || echo "Reports service: unknown"
    echo

    print_success "API test completed"
}

# Install dependencies
install_deps() {
    print_status "Installing dependencies..."

    if [ ! -d "$VENV_DIR" ]; then
        print_status "Creating virtual environment..."
        python -m venv "$VENV_DIR"
    fi

    activate_env

    # Install basic requirements
    pip install --upgrade pip
    pip install fastapi uvicorn jinja2 pydantic requests

    # Install Phase 3 requirements
    pip install networkx psutil aiohttp

    print_success "Dependencies installed"
}

# Show help
show_help() {
    echo -e "${BLUE}Network Automation TUI Management Script${NC}"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  start     Start API server"
    echo "  stop      Stop API server"
    echo "  restart   Restart API server"
    echo "  status    Show service status"
    echo "  tui       Launch TUI interface"
    echo "  api       Show API info and test endpoints"
    echo "  logs      Show recent logs"
    echo "  follow    Follow logs in real-time"
    echo "  install   Install dependencies"
    echo "  help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 start          # Start API server"
    echo "  $0 tui            # Launch TUI"
    echo "  $0 status         # Check status"
    echo "  $0 logs           # View logs"
    echo "  $0 stop           # Stop services"
    echo
    echo "Access Points:"
    echo "  API Documentation: http://localhost:$API_PORT/docs"
    echo "  Health Check:     http://localhost:$API_PORT/api/health"
    echo "  ReDoc:            http://localhost:$API_PORT/redoc"
}

# Main script logic
case "${1:-help}" in
    start)
        start_api
        ;;
    stop)
        stop_api
        ;;
    restart)
        restart_api
        ;;
    status)
        show_status
        ;;
    tui)
        launch_tui
        ;;
    api)
        test_api
        ;;
    logs)
        show_logs
        ;;
    follow)
        follow_logs
        ;;
    install)
        install_deps
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac