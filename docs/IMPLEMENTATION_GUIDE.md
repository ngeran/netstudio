# Implementation Guide - MVP Development Phases

This guide outlines building a Minimum Viable Product (MVP) in phases, with each phase delivering working functionality.

## Phase Roadmap

```
Phase 1: Hello World (1 day)
  └─→ Basic API + Frontend connection

Phase 2: Script Library (2 days)
  └─→ View existing scripts

Phase 3: Script Execution (3 days)
  └─→ Execute scripts, basic logs

Phase 4: Real-time Logs (2 days)
  └─→ WebSocket streaming

Phase 5: Script Management (2 days)
  └─→ Upload, edit, delete scripts

Phase 6: Production Ready (3 days)
  └─→ Auth, error handling, deployment
```

**Total MVP Timeline: 13 days**

---

## Phase 1: Hello World (Foundation)

**Goal**: Verify frontend can call backend API.

### Backend: Minimal FastAPI Server

```python
# ui/backend/app/main.py
"""
Minimal FastAPI server to test setup.

FastAPI automatically generates:
- OpenAPI docs at http://localhost:8000/docs
- ReDoc at http://localhost:8000/redoc
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Create FastAPI instance
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version
)

# Enable CORS so frontend (localhost:3000) can call backend (localhost:8000)
# CORS = Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],  # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Allow all headers
)


@app.get("/")
async def root():
    """
    Health check endpoint.
    Returns JSON: {"message": "Network Automation API is running"}
    """
    return {
        "message": "Network Automation API is running",
        "version": settings.api_version
    }


@app.get("/api/health")
async def health_check():
    """
    Detailed health check with Redis connection test.
    """
    import redis
    try:
        # Try to connect to Redis
        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
        r.ping()  # Raises exception if Redis is down
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "redis": redis_status,
        "scripts_dir": settings.scripts_dir
    }
```

**Run Backend:**
```bash
cd /Users/UPGH/github/net-launcher/ui/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Test:**
```bash
# Should return JSON
curl http://localhost:8000/

# Check health
curl http://localhost:8000/api/health

# View auto-generated API docs
open http://localhost:8000/docs
```

---

### Frontend: Call Backend API

```javascript
// ui/frontend/src/App.jsx
import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [apiStatus, setApiStatus] = useState('Checking...')
  const [apiHealth, setApiHealth] = useState(null)

  // Fetch API status when component loads
  useEffect(() => {
    // Call backend API
    fetch('http://localhost:8000/')
      .then(res => res.json())
      .then(data => {
        setApiStatus(data.message)
      })
      .catch(err => {
        setApiStatus('Error: Cannot connect to backend')
      })

    // Check detailed health
    fetch('http://localhost:8000/api/health')
      .then(res => res.json())
      .then(data => setApiHealth(data))
      .catch(err => console.error(err))
  }, [])  // Empty array = run once on mount

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          Network Automation Management
        </h1>

        <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-2">API Status</h2>
          <p className="text-gray-600 dark:text-gray-300">{apiStatus}</p>

          {apiHealth && (
            <div className="mt-4 space-y-2">
              <p>✅ Status: {apiHealth.status}</p>
              <p>🔗 Redis: {apiHealth.redis}</p>
              <p>📁 Scripts: {apiHealth.scripts_dir}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
```

**Run Frontend:**
```bash
cd /Users/UPGH/github/net-launcher/ui/frontend
npm run dev
```

**Test:**
Open http://localhost:3000 - should see API status.

---

## Phase 2: Script Library

**Goal**: Display list of existing scripts from `scripts/` directory.

### Backend: Script Scanner Service

```python
# ui/backend/app/services/script_scanner.py
"""
Service to scan the scripts/ directory and extract metadata.

This reads Python files and extracts:
- Docstrings (for description)
- Function definitions (for parameters)
- File metadata (last modified time)
"""
import os
import ast
import inspect
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from app.models.script import ScriptMetadata, ScriptParameter
from app.config import settings


class ScriptScanner:
    """
    Scans scripts directory and extracts metadata from Python files.
    """

    def __init__(self):
        self.scripts_dir = Path(settings.scripts_dir)

    def scan_all_scripts(self) -> List[ScriptMetadata]:
        """
        Scan all .py files in scripts directory.
        Returns list of ScriptMetadata objects.
        """
        scripts = []

        # Find all .py files
        for py_file in self.scripts_dir.glob("*.py"):
            # Skip __init__.py and private files
            if py_file.name.startswith("_"):
                continue

            try:
                metadata = self._extract_metadata(py_file)
                if metadata:
                    scripts.append(metadata)
            except Exception as e:
                print(f"Error scanning {py_file.name}: {e}")

        return scripts

    def _extract_metadata(self, file_path: Path) -> Optional[ScriptMetadata]:
        """
        Extract metadata from a single Python file.
        """
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse Python AST (Abstract Syntax Tree)
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Invalid Python file, skip it
            return None

        # Extract module docstring
        description = ast.get_docstring(tree)

        # Find main function (usually matches filename or is called "main")
        main_func = self._find_main_function(tree, file_path.stem)

        # Get file stats
        stats = file_path.stat()
        last_modified = datetime.fromtimestamp(stats.st_mtime)

        # Determine category from filename/docstring
        category = self._categorize_script(file_path.stem, description)

        return ScriptMetadata(
            id=file_path.stem,  # e.g., "code_upgrade"
            name=self._humanize_name(file_path.stem),  # "Code Upgrade"
            description=description or "No description available",
            category=category,
            parameters=[],  # TODO: Extract from function signature
            file_path=str(file_path),
            last_modified=last_modified
        )

    def _find_main_function(self, tree, filename: str):
        """
        Find the main entry point function.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Look for main(), code_upgrade(), etc.
                if node.name in ['main', filename, f'{filename}_main']:
                    return node
        return None

    def _humanize_name(self, snake_case: str) -> str:
        """
        Convert snake_case to Title Case.
        Example: "code_upgrade" -> "Code Upgrade"
        """
        return " ".join(word.capitalize() for word in snake_case.split("_"))

    def _categorize_script(self, name: str, description: str) -> str:
        """
        Guess category from filename and description.
        """
        name_lower = name.lower()
        desc_lower = (description or "").lower()

        if "upgrade" in name_lower or "upgrade" in desc_lower:
            return "upgrade"
        elif "config" in name_lower or "backup" in desc_lower:
            return "configuration"
        elif "bgp" in name_lower or "route" in name_lower:
            return "routing"
        elif "ping" in name_lower or "diagnostic" in desc_lower:
            return "diagnostic"
        elif "state" in name_lower or "capture" in desc_lower:
            return "monitoring"
        else:
            return "general"


# Create singleton instance
script_scanner = ScriptScanner()
```

### Backend: REST Endpoint

```python
# ui/backend/app/routers/scripts.py
"""
API endpoints for script management.
"""
from fastapi import APIRouter, HTTPException
from typing import List
from app.models.script import ScriptMetadata
from app.services.script_scanner import script_scanner

# Create router (like a mini-app for /api/scripts endpoints)
router = APIRouter(
    prefix="/api/scripts",
    tags=["scripts"]  # Groups endpoints in API docs
)


@router.get("/", response_model=List[ScriptMetadata])
async def list_scripts():
    """
    Get list of all available scripts.

    Returns:
        List of script metadata objects

    Example response:
    [
      {
        "id": "code_upgrade",
        "name": "Code Upgrade",
        "description": "Upgrade Juniper device software",
        "category": "upgrade",
        "parameters": [],
        "file_path": "/Users/UPGH/github/net-launcher/scripts/code_upgrade.py",
        "last_modified": "2025-12-09T10:30:00"
      }
    ]
    """
    try:
        scripts = script_scanner.scan_all_scripts()
        return scripts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{script_id}", response_model=ScriptMetadata)
async def get_script(script_id: str):
    """
    Get detailed information about a specific script.

    Args:
        script_id: Script identifier (e.g., "code_upgrade")

    Returns:
        Script metadata

    Raises:
        404 if script not found
    """
    scripts = script_scanner.scan_all_scripts()

    # Find script by ID
    script = next((s for s in scripts if s.id == script_id), None)

    if not script:
        raise HTTPException(
            status_code=404,
            detail=f"Script '{script_id}' not found"
        )

    return script
```

**Update main.py to include router:**

```python
# ui/backend/app/main.py (add after app creation)
from app.routers import scripts

# Include scripts router
app.include_router(scripts.router)
```

### Frontend: Script Library Component

```javascript
// ui/frontend/src/components/ScriptLibrary.jsx
import { useState, useEffect } from 'react'

function ScriptCard({ script }) {
  // Format date for display
  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return '1 day ago'
    if (diffDays < 7) return `${diffDays} days ago'
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return date.toLocaleDateString()
  }

  // Icon based on category
  const categoryIcon = {
    upgrade: '📦',
    configuration: '⚙️',
    routing: '🔍',
    diagnostic: '🔌',
    monitoring: '📊',
    general: '📝'
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow hover:shadow-lg transition-shadow p-6 border border-gray-200 dark:border-slate-700">
      <div className="flex items-start justify-between mb-3">
        <div className="text-3xl">{categoryIcon[script.category] || '📝'}</div>
        <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
          {script.category}
        </span>
      </div>

      <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
        {script.name}
      </h3>

      <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 line-clamp-2">
        {script.description}
      </p>

      <div className="flex items-center text-xs text-gray-500 dark:text-gray-400 mb-4">
        <span>Modified: {formatDate(script.last_modified)}</span>
      </div>

      <div className="flex gap-2">
        <button className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
          Execute
        </button>
        <button className="px-4 py-2 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-slate-700 text-gray-700 dark:text-gray-300 rounded-md text-sm font-medium transition-colors">
          Edit
        </button>
      </div>
    </div>
  )
}

export default function ScriptLibrary() {
  const [scripts, setScripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')

  // Fetch scripts from API
  useEffect(() => {
    fetch('http://localhost:8000/api/scripts/')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch scripts')
        return res.json()
      })
      .then(data => {
        setScripts(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  // Filter scripts
  const filteredScripts = scripts.filter(script => {
    const matchesSearch = script.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         script.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = categoryFilter === 'all' || script.category === categoryFilter
    return matchesSearch && matchesCategory
  })

  if (loading) {
    return <div className="text-center py-12">Loading scripts...</div>
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600 dark:text-red-400">
        Error: {error}
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Script Library
        </h1>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium">
          + New Script
        </button>
      </div>

      {/* Search and Filter */}
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="🔍 Search scripts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
        />

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
        >
          <option value="all">All Categories</option>
          <option value="upgrade">Upgrade</option>
          <option value="configuration">Configuration</option>
          <option value="routing">Routing</option>
          <option value="diagnostic">Diagnostic</option>
          <option value="monitoring">Monitoring</option>
        </select>
      </div>

      {/* Scripts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredScripts.map(script => (
          <ScriptCard key={script.id} script={script} />
        ))}
      </div>

      {filteredScripts.length === 0 && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No scripts found
        </div>
      )}
    </div>
  )
}
```

**Test Phase 2:**
1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Open http://localhost:3000
4. Should see grid of scripts from `scripts/` directory

---

## Next Phases (Abbreviated)

**Phase 3: Script Execution**
- Add POST `/api/scripts/{id}/execute` endpoint
- Use Celery to run scripts asynchronously
- Return task_id immediately
- Add execution modal to frontend

**Phase 4: Real-time Logs**
- Add WebSocket endpoint
- Stream logs from Celery worker to Redis Pub/Sub
- Frontend subscribes to WebSocket
- Display logs in real-time

**Phase 5: Script Management**
- Add file upload endpoint
- Add script editor with syntax highlighting
- Add delete/rename endpoints

**Phase 6: Production Ready**
- Add JWT authentication
- Add user management
- Add comprehensive error handling
- Docker Compose for deployment
- Nginx reverse proxy
- PM2 for process management

---

## Testing Strategy

### Unit Tests (Backend)
```bash
# Install pytest
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

### E2E Tests (Frontend)
```bash
# Install Playwright
npm install -D @playwright/test

# Run tests
npx playwright test
```

### Integration Tests
Test full flow: Frontend → API → Redis → Worker → Device

---

## Production Deployment Checklist

- [ ] Environment variables (no hardcoded secrets)
- [ ] HTTPS with SSL certificate
- [ ] Redis persistence enabled
- [ ] Database backups
- [ ] Log rotation
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Rate limiting
- [ ] Input sanitization
- [ ] CSRF protection
- [ ] API versioning
- [ ] Documentation

---

This guide provides a roadmap from zero to production-ready network automation UI. Each phase builds on the previous, ensuring you always have working software.
