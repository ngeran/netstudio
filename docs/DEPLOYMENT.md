# Network Automation Management UI - Deployment Guide

This guide walks you through setting up the Network Automation Management UI from scratch, with zero coding experience required. Each step includes automated tests to verify success.

## Prerequisites Check

Before starting, verify you have:
- macOS (you're on TU1428)
- Terminal access
- Internet connection

## Phase 1: System Dependencies

### Step 1.1: Install Homebrew (Package Manager)

**What it does:** Homebrew is like an "app store" for developer tools. It helps install software from the command line.

**Why we need it:** We'll use it to install Python, Redis, and Node.js.

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Test:**
```bash
# This should show version 4.x or higher
brew --version
```

**Expected Output:**
```
Homebrew 4.x.x
```

**If test fails:** Close and reopen Terminal, then retry.

---

### Step 1.2: Install Python 3.11

**What it does:** Python is the programming language used for network automation scripts.

**Why we need it:** Your existing scripts (code_upgrade.py, etc.) and the new backend both use Python.

```bash
# Install Python 3.11
brew install python@3.11

# Make it the default Python
echo 'export PATH="/usr/local/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Test:**
```bash
python3 --version
```

**Expected Output:**
```
Python 3.11.x
```

---

### Step 1.3: Install Redis

**What it does:** Redis is an in-memory database that acts as a message broker.

**Why we need it:** Redis queues script execution tasks and enables real-time log streaming to the web UI.

**Network Automation Context:** When you execute a script on 10 devices, Redis manages the task queue so scripts don't overwhelm your computer.

```bash
# Install Redis
brew install redis

# Start Redis as a background service
brew services start redis
```

**Test:**
```bash
# This should return "PONG"
redis-cli ping
```

**Expected Output:**
```
PONG
```

**If test fails:** Check Redis is running:
```bash
brew services list | grep redis
# Should show "started"
```

---

### Step 1.4: Install Node.js and npm

**What it does:** Node.js runs JavaScript outside the browser. npm is its package manager.

**Why we need it:** The frontend (React UI) is built with JavaScript and needs Node.js to run during development.

```bash
# Install Node.js (includes npm)
brew install node
```

**Test:**
```bash
node --version
npm --version
```

**Expected Output:**
```
v20.x.x  (or v18.x.x)
10.x.x   (or 9.x.x)
```

---

## Phase 2: Project Setup

### Step 2.1: Create Project Structure

**What it does:** Organizes code into frontend and backend directories.

**Why this structure:** Separates concerns - frontend handles UI, backend handles script execution.

```bash
# Navigate to your project
cd /Users/UPGH/github/net-launcher

# Create directories
mkdir -p ui/frontend ui/backend

# Show structure
tree -L 2 -d .
```

**Test:**
```bash
# Both directories should exist
ls -la ui/
```

**Expected Output:**
```
drwx------  frontend
drwx------  backend
```

---

### Step 2.2: Set Up Python Virtual Environment

**What it does:** Creates an isolated Python environment for the backend.

**Why we need it:** Prevents conflicts between different projects' Python packages.

**Network Automation Context:** Your backend needs PyEZ, but other projects might need different versions.

```bash
# Create virtual environment
python3 -m venv ui/backend/venv

# Activate it (you'll need to do this every time you work on the backend)
source ui/backend/venv/bin/activate

# Your prompt should now show (venv)
```

**Test:**
```bash
# Should show the venv Python, not system Python
which python
```

**Expected Output:**
```
/Users/UPGH/github/net-launcher/ui/backend/venv/bin/python
```

---

### Step 2.3: Install Backend Dependencies

**What it does:** Installs Python packages needed for the backend API.

**Package Explanations:**
- **fastapi**: Web framework for building the API
- **uvicorn**: Web server that runs FastAPI
- **redis**: Python client for Redis
- **celery**: Task queue for running scripts asynchronously
- **websockets**: Real-time communication with frontend
- **python-multipart**: Handle file uploads
- **pydantic**: Data validation (ensures correct input)

```bash
# Make sure venv is activated
source ui/backend/venv/bin/activate

# Create requirements file
cat > ui/backend/requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
redis==5.0.1
celery==5.3.6
websockets==12.0
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
aiofiles==23.2.1
EOF

# Install packages
pip install -r ui/backend/requirements.txt
```

**Test:**
```bash
# Should show all installed packages
pip list | grep -E "fastapi|uvicorn|redis|celery"
```

**Expected Output:**
```
fastapi                0.109.0
uvicorn                0.27.0
redis                  5.0.1
celery                 5.3.6
```

---

### Step 2.4: Initialize Frontend

**What it does:** Creates a new React application.

**Why Vite:** Vite is a modern build tool that's much faster than the older Create React App.

```bash
cd ui/frontend

# Create React app with Vite
npm create vite@latest . -- --template react

# Install dependencies
npm install

# Install TailwindCSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Install shadcn/ui dependencies
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react
npm install @radix-ui/react-slot

# Install Zustand for state management
npm install zustand

# Install WebSocket client
npm install socket.io-client
```

**Test:**
```bash
# Should show package.json with all dependencies
cat package.json | grep -A 20 "dependencies"
```

**Expected Output:** Should list react, zustand, socket.io-client, etc.

---

### Step 2.5: Configure TailwindCSS

**What it does:** Sets up TailwindCSS for styling.

```bash
cd /Users/UPGH/github/net-launcher/ui/frontend

# Update tailwind.config.js
cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    './pages/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
    './app/**/*.{js,jsx}',
    './src/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
      },
    },
  },
  plugins: [],
}
EOF

# Update src/index.css
cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --border: 214.3 31.8% 91.4%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
  }
}
EOF
```

**Test:**
```bash
cat tailwind.config.js | grep darkMode
```

**Expected Output:**
```
  darkMode: ["class"],
```

---

## Phase 3: Backend Implementation

### Step 3.1: Create Backend Structure

```bash
cd /Users/UPGH/github/net-launcher/ui/backend

# Create directory structure
mkdir -p app/routers app/models app/services app/utils

# Create __init__.py files (makes directories Python packages)
touch app/__init__.py
touch app/routers/__init__.py
touch app/models/__init__.py
touch app/services/__init__.py
touch app/utils/__init__.py
```

**Test:**
```bash
tree app/
```

**Expected Output:**
```
app/
├── __init__.py
├── models
│   └── __init__.py
├── routers
│   └── __init__.py
├── services
│   └── __init__.py
└── utils
    └── __init__.py
```

---

### Step 3.2: Create Configuration File

**What it does:** Centralizes all configuration settings.

**Why we need it:** Makes it easy to change settings without modifying code.

```bash
cat > ui/backend/app/config.py << 'EOF'
"""
Configuration settings for the Network Automation API.

This file stores all configuration in one place, making it easy to change
settings without modifying code. In production, these values should come
from environment variables for security.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings using Pydantic.

    Pydantic automatically validates that values are the correct type
    (e.g., ensures redis_port is an integer, not a string).
    """

    # API Settings
    api_title: str = "Network Automation API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api"

    # CORS Settings (Cross-Origin Resource Sharing)
    # This allows the frontend (localhost:3000) to call the backend (localhost:8000)
    cors_origins: list = ["http://localhost:3000"]

    # Redis Settings
    # Redis is our message broker and cache
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # Celery Settings (Task Queue)
    # Celery uses Redis to queue long-running network automation tasks
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # File Upload Settings
    max_upload_size: int = 10 * 1024 * 1024  # 10MB in bytes
    allowed_script_extensions: list = [".py"]

    # Scripts Directory
    # Points to your existing scripts folder
    scripts_dir: str = "/Users/UPGH/github/net-launcher/scripts"
    data_dir: str = "/Users/UPGH/github/net-launcher/data"

    # Execution Settings
    script_timeout: int = 3600  # 1 hour in seconds
    max_concurrent_tasks: int = 5  # Limit simultaneous script executions

    # WebSocket Settings
    websocket_ping_interval: int = 30  # Keep connection alive
    websocket_ping_timeout: int = 10

    # Security Settings
    secret_key: str = "change-this-in-production-to-random-secure-key"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    class Config:
        # Load from .env file if it exists
        env_file = ".env"


# Create a single instance to use throughout the app
settings = Settings()
EOF
```

**Test:**
```bash
python3 << 'PYTEST'
import sys
sys.path.insert(0, '/Users/UPGH/github/net-launcher/ui/backend')
from app.config import settings
print(f"✓ Scripts directory: {settings.scripts_dir}")
print(f"✓ Redis host: {settings.redis_host}:{settings.redis_port}")
print(f"✓ API prefix: {settings.api_prefix}")
PYTEST
```

**Expected Output:**
```
✓ Scripts directory: /Users/UPGH/github/net-launcher/scripts
✓ Redis host: localhost:6379
✓ API prefix: /api
```

---

### Step 3.3: Create Data Models

**What it does:** Defines the structure of data passed between frontend and backend.

**Why we need it:** Ensures data is valid and documents the API structure.

```bash
cat > ui/backend/app/models/script.py << 'EOF'
"""
Data models for network automation scripts.

These models define the "shape" of data - like a blueprint.
Pydantic validates that data matches the blueprint before processing.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ScriptParameter(BaseModel):
    """
    Represents a parameter that a script accepts.

    Example: code_upgrade.py needs 'vendor', 'product', 'release'
    """
    name: str = Field(..., description="Parameter name (e.g., 'vendor')")
    type: str = Field(..., description="Data type: string, int, bool, list")
    required: bool = Field(True, description="Is this parameter mandatory?")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    description: Optional[str] = Field(None, description="Help text for users")
    choices: Optional[List[str]] = Field(None, description="Valid options (for dropdowns)")


class ScriptMetadata(BaseModel):
    """
    Information about a script file.

    This is what users see in the script library.
    """
    id: str = Field(..., description="Unique identifier (filename without .py)")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="What this script does")
    category: str = Field("general", description="Group: upgrade, config, diagnostic, etc.")
    parameters: List[ScriptParameter] = Field(default_factory=list)
    file_path: str = Field(..., description="Absolute path to .py file")
    last_modified: datetime = Field(..., description="Last edit time")
    author: Optional[str] = Field(None, description="Who wrote this script")


class TaskStatus(str, Enum):
    """
    Possible states for a script execution task.

    State transitions: PENDING → RUNNING → (SUCCESS or FAILED)
    """
    PENDING = "pending"      # Queued, not started yet
    RUNNING = "running"      # Currently executing
    SUCCESS = "success"      # Completed successfully
    FAILED = "failed"        # Error occurred
    CANCELLED = "cancelled"  # User stopped it


class ScriptExecutionRequest(BaseModel):
    """
    Request to execute a script.

    Frontend sends this when user clicks "Execute".
    """
    script_id: str = Field(..., description="Which script to run")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameter values")
    device_selection: str = Field("inventory", description="'inventory' or 'manual'")
    devices: Optional[List[str]] = Field(None, description="For manual: list of IPs")
    credentials: Optional[Dict[str, str]] = Field(None, description="username/password if manual")


class TaskInfo(BaseModel):
    """
    Information about a running or completed task.

    Frontend polls this to show progress.
    """
    task_id: str
    script_id: str
    status: TaskStatus
    progress: int = Field(0, ge=0, le=100, description="Percentage complete")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    user: str = Field("anonymous", description="Who started this task")
    error: Optional[str] = Field(None, description="Error message if failed")


class TaskResult(BaseModel):
    """
    Results after task completes.

    Contains logs, output, and success/failure info.
    """
    task_id: str
    status: TaskStatus
    exit_code: int = Field(0, description="0 = success, non-zero = error")
    output: str = Field("", description="Captured stdout/stderr")
    logs: List[str] = Field(default_factory=list, description="Timestamped log lines")
    result_data: Optional[Dict[str, Any]] = Field(None, description="Structured results")
    execution_time: float = Field(0, description="Seconds elapsed")
EOF
```

**Test:**
```bash
python3 << 'PYTEST'
import sys
sys.path.insert(0, '/Users/UPGH/github/net-launcher/ui/backend')
from app.models.script import ScriptMetadata, TaskStatus, ScriptParameter
from datetime import datetime

# Test creating a script metadata object
script = ScriptMetadata(
    id="code_upgrade",
    name="Code Upgrade",
    description="Upgrade Juniper device software",
    category="upgrade",
    file_path="/path/to/code_upgrade.py",
    last_modified=datetime.now(),
    parameters=[
        ScriptParameter(name="vendor", type="string", required=True)
    ]
)
print(f"✓ Script model: {script.name}")
print(f"✓ Has {len(script.parameters)} parameters")
print(f"✓ Task statuses: {[s.value for s in TaskStatus]}")
PYTEST
```

**Expected Output:**
```
✓ Script model: Code Upgrade
✓ Has 1 parameters
✓ Task statuses: ['pending', 'running', 'success', 'failed', 'cancelled']
```

---

## Summary and Next Steps

You've completed Phase 1-3! Here's what's set up:

✅ **Phase 1**: System dependencies (Python, Redis, Node.js)
✅ **Phase 2**: Project structure (frontend & backend directories)
✅ **Phase 3**: Backend foundation (config, models)

**What You Have:**
- Python 3.11 environment
- Redis message broker running
- Node.js for frontend development
- Backend structure with configuration
- Data models for API

**Next Phases:**
- **Phase 4**: Implement FastAPI routes (REST endpoints)
- **Phase 5**: Implement Celery workers (script execution)
- **Phase 6**: Implement WebSocket (real-time logs)
- **Phase 7**: Build React frontend components
- **Phase 8**: Integration and testing
- **Phase 9**: Production deployment

**To Continue:**
Run these commands to verify everything is working:

```bash
# Test Redis
redis-cli ping

# Test Python environment
source ui/backend/venv/bin/activate
python3 -c "from app.config import settings; print(settings.api_title)"

# Test Node
cd ui/frontend && npm --version
```

All tests should pass before moving to Phase 4.

Would you like me to continue with Phase 4 (FastAPI Routes implementation)?
