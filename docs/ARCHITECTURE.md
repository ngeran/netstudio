# Network Automation Management UI - Architecture

## System Overview

This document outlines the architecture for a web-based UI wrapper around the existing Juniper PyEZ network automation scripts.

## Architecture Diagram (Text-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Browser                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  React App (Port 3000)                                    │  │
│  │  - TailwindCSS/shadcn UI Components                       │  │
│  │  - Zustand State Management                               │  │
│  │  - WebSocket Client for Real-time Updates                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (Port 8000)                 │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  REST API       │  │  WebSocket   │  │  Task Queue      │   │
│  │  Endpoints      │  │  Handler     │  │  Manager         │   │
│  │  - Scripts CRUD │  │  - Real-time │  │  - Async Exec    │   │
│  │  - Execute      │  │    Logs      │  │  - Status Track  │   │
│  │  - Results      │  │  - Progress  │  │                  │   │
│  └─────────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Redis Protocol
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Redis (Port 6379)                             │
│  - Task Queue (Celery/RQ)                                        │
│  - WebSocket Pub/Sub for real-time updates                      │
│  - Session Storage                                               │
│  - Execution Results Cache                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Worker Processes                              │
│  - Execute Python scripts (launcher.py, scripts/*)               │
│  - Juniper PyEZ operations                                       │
│  - Stream logs to Redis                                          │
│  - Update execution status                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SSH/NETCONF
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Network Devices                               │
│  - Juniper Routers/Switches/Firewalls                           │
│  - EX4600, SRX, etc.                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack Analysis

### Frontend: React + TailwindCSS + Zustand

**Strengths:**
- React: Industry standard, large ecosystem, excellent for dynamic UIs
- TailwindCSS: Utility-first CSS, rapid development, small bundle size
- shadcn/ui: High-quality accessible components, fully customizable
- Zustand: Lightweight state management (3KB), simpler than Redux

**Potential Issues:**
- **Breaking Point**: Large file uploads (scripts/configs) may timeout
  - *Solution*: Implement chunked uploads with progress tracking
- **Compatibility**: Browser WebSocket support
  - *Solution*: Fallback to HTTP polling for older browsers

**Why This Stack for Network Automation:**
- Real-time log streaming essential for debugging network operations
- Complex forms for device configuration need reactive state management
- Network engineers need clean, intuitive UI without web dev knowledge

### Backend: FastAPI

**Strengths:**
- Native async/await support (critical for network I/O)
- Automatic OpenAPI documentation
- Type hints improve code reliability
- WebSocket support built-in
- Fast performance (comparable to Node.js)

**Potential Issues:**
- **Breaking Point**: Long-running network operations block workers
  - *Solution*: Use Celery/RQ workers for script execution
- **Compatibility**: Python version must match existing scripts (3.x)
  - *Solution*: Use same Python environment as existing scripts

**Why FastAPI for Network Automation:**
- Python-native: Wraps existing PyEZ scripts without rewriting
- Async I/O: Handles multiple device connections efficiently
- Type safety: Catches errors before hitting network devices
- WebSocket: Streams real-time logs from device operations

### Message Broker: Redis

**Strengths:**
- Fast in-memory operations
- Pub/Sub for WebSocket broadcasting
- Can queue tasks (with Celery/RQ)
- Simple setup, low resource usage

**Potential Issues:**
- **Breaking Point**: Memory limits with large execution logs
  - *Solution*: Stream logs directly, don't store entire history
  - *Solution*: Implement log rotation and TTL
- **Breaking Point**: Single point of failure
  - *Solution*: Redis persistence (RDB snapshots)
  - *Solution*: For production, consider Redis Sentinel/Cluster

**Why Redis for Network Automation:**
- Ephemeral data: Most logs/results don't need permanent storage
- Speed: Network operations need fast task queuing
- Pub/Sub: Multiple users can monitor same device operations

## Integration Patterns

### Pattern 1: Script Execution Flow

```
User Clicks "Execute"
  → Frontend: POST /api/scripts/{id}/execute
  → Backend: Create task in Redis queue
  → Backend: Return task_id immediately
  → Worker: Pick up task, execute Python script
  → Worker: Stream logs to Redis Pub/Sub
  → Backend WebSocket: Broadcast logs to frontend
  → Worker: Save results to Redis
  → Backend: Notify completion via WebSocket
  → Frontend: Display results
```

### Pattern 2: Real-time Log Streaming

```
Frontend establishes WebSocket connection
  → Backend: Subscribe to Redis channel: "logs:{task_id}"
  → Worker: Publishes log lines to Redis
  → Backend: Receives from Redis, forwards to WebSocket
  → Frontend: Appends to log display
```

### Pattern 3: File Upload (New Scripts)

```
User uploads Python script
  → Frontend: POST /api/scripts/upload (multipart/form-data)
  → Backend: Validate file (syntax check, imports)
  → Backend: Extract metadata (docstring, parameters)
  → Backend: Save to scripts/ directory
  → Backend: Update script registry
  → Frontend: Refresh script library
```

## Security Considerations

### Authentication & Authorization
- Implement JWT-based authentication
- Role-based access: viewer, operator, admin
- Audit log for all script executions

### Script Validation
- Syntax validation before saving
- Whitelist allowed imports (jnpr.junos, scripts.*)
- Prevent arbitrary code execution

### Device Credentials
- Never store passwords in browser
- Use encrypted storage for credentials
- Support credential injection at runtime

### Network Isolation
- Backend should run in same network segment as devices
- Frontend can be public-facing with proper auth
- Use SSH key authentication where possible

## Scalability Considerations

### Horizontal Scaling
- **Frontend**: Serve via CDN, multiple nginx instances
- **Backend**: Multiple FastAPI workers behind load balancer
- **Workers**: Scale worker processes based on load
- **Redis**: Redis Cluster for high availability

### Performance Optimizations
- Cache script metadata (avoid repeated file reads)
- Paginate script library (don't load all at once)
- Compress WebSocket messages
- Use Redis TTL to auto-expire old logs

## Data Flow

### Script Metadata Storage
```
scripts/
├── code_upgrade.py
├── config_toolbox.py
└── ...

Redis:
  script:code_upgrade → {
    "name": "Code Upgrade",
    "description": "...",
    "parameters": [...],
    "last_modified": "..."
  }
```

### Execution State
```
Redis:
  task:{task_id} → {
    "script": "code_upgrade",
    "status": "running",
    "started_at": "...",
    "progress": 45,
    "user": "admin"
  }

  logs:{task_id} → [Stream of log lines]

  result:{task_id} → {
    "exit_code": 0,
    "output": "...",
    "completed_at": "..."
  }
```

## Disaster Recovery

### Backup Strategy
- **Scripts**: Git repository (already version controlled)
- **Configurations**: data/*.yml files in Git
- **Execution History**: Optional PostgreSQL for long-term storage
- **Redis**: RDB snapshots every 5 minutes

### Failure Scenarios

**Backend Crash:**
- Workers continue running (isolated processes)
- On restart, backend reconnects to Redis
- Orphaned tasks detected and marked as failed

**Redis Crash:**
- Running tasks continue, but logs lost
- On restart, workers re-register tasks
- Consider Redis persistence (AOF mode)

**Worker Crash:**
- Task marked as failed after timeout
- User can retry execution
- Implement task heartbeat mechanism

## Development vs Production

### Development Setup
- Single process for Backend + Worker
- Redis in Docker
- Frontend dev server (hot reload)
- SQLite for optional data persistence

### Production Setup
- 4+ Backend workers (Gunicorn/Uvicorn)
- 4+ Celery workers
- Redis with persistence enabled
- Frontend built and served via Nginx
- PostgreSQL for audit logs
- Monitoring (Prometheus + Grafana)

## Next Steps

1. Set up development environment (see DEPLOYMENT.md)
2. Implement MVP with single script execution
3. Add WebSocket log streaming
4. Build script library management
5. Implement authentication
6. Add device inventory management
7. Performance testing and optimizatio
