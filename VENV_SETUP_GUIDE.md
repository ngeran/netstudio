# Virtual Environment Setup Guide for NetStudio

This guide will walk you through setting up and running NetStudio in a Python virtual environment.

## Prerequisites

- Python 3.8 or higher installed
- macOS/Linux or Windows with terminal access
- Git (if cloning the repository)

## Step-by-Step Setup

### 1. Navigate to the Project Directory

```bash
cd /Users/UPGH/github/Vanguard/netstudio
```

### 2. Create a Virtual Environment

```bash
# Create a virtual environment named 'venv'
python3 -m venv venv

# Alternative: Create with a specific Python version
python3.11 -m venv venv
```

This creates a `venv` directory containing:
- `bin/` (or `Scripts/` on Windows) - executables and activation scripts
- `lib/` - installed Python packages
- `pyvenv.cfg` - configuration file

### 3. Activate the Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**On Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Success Indicator:** Your terminal prompt will change to show `(venv)` at the beginning:
```
(venv) username@hostname:~/github/Vanguard/netstudio$
```

### 4. Upgrade pip (Recommended)

```bash
pip install --upgrade pip
```

### 5. Install Dependencies

**Option A: Install all dependencies (including development tools)**
```bash
pip install -r requirements.txt
```

**Option B: Install core dependencies only (faster, smaller)**
```bash
# Core dependencies
pip install junos-eznc ncclient PyYAML Jinja2 deepdiff tabulate
pip install fastapi uvicorn[standard] pydantic python-multipart websockets
pip install textual rich networkx lxml psutil requests
```

**Option C: Install with optional dependencies**
```bash
# Install everything including JSNAPy and reporting tools
pip install -r requirements.txt
pip install jsnapy reportlab matplotlib
```

### 6. Set Environment Variables

```bash
# Set the project directory (required)
export VECTOR_PY_DIR=/Users/UPGH/github/Vanguard/netstudio

# Optional: Add project to PATH
export PATH=$PATH:/Users/UPGH/github/Vanguard/netstudio

# Optional: Set logging level
export LOG_LEVEL=INFO
```

**Make it permanent** by adding to your shell profile:

**For bash (~/.bashrc or ~/.bash_profile):**
```bash
echo 'export VECTOR_PY_DIR=/Users/UPGH/github/Vanguard/netstudio' >> ~/.bashrc
echo 'export PATH=$PATH:/Users/UPGH/github/Vanguard/netstudio' >> ~/.bashrc
source ~/.bashrc
```

**For zsh (~/.zshrc):**
```bash
echo 'export VECTOR_PY_DIR=/Users/UPGH/github/Vanguard/netstudio' >> ~/.zshrc
echo 'export PATH=$PATH:/Users/UPGH/github/Vanguard/netstudio' >> ~/.zshrc
source ~/.zshrc
```

### 7. Verify Installation

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Verify key packages
pip show junos-eznc fastapi textual
```

### 8. Run the Application

**Option 1: TUI Interface (Recommended)**
```bash
python launcher.py
```

**Option 2: API Server**
```bash
python api/main.py

# Or with uvicorn directly
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option 3: Legacy CLI**
```bash
python main.py
```

**Option 4: Specific Scripts**
```bash
python scripts/code_upgrade.py
python scripts/config_toolbox.py
python scripts/bgp_toolbox.py
```

## Daily Usage

### Starting a Session

```bash
# 1. Navigate to project
cd /Users/UPGH/github/Vanguard/netstudio

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run application
python launcher.py
```

### Ending a Session

```bash
# Deactivate the virtual environment
deactivate
```

Your prompt will return to normal:
```
username@hostname:~/github/Vanguard/netstudio$
```

## Troubleshooting

### Issue 1: "python3: command not found"

**Solution:** Install Python 3:
- macOS: `brew install python3`
- Ubuntu/Debian: `sudo apt-get install python3 python3-venv`
- Windows: Download from [python.org](https://www.python.org/downloads/)

### Issue 2: Virtual environment won't activate

**Solution:**
```bash
# Make sure you're in the project directory
cd /Users/UPGH/github/Vanguard/netstudio

# Try creating a fresh virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

### Issue 3: Permission denied on activation script

**Solution:**
```bash
chmod +x venv/bin/activate
source venv/bin/activate
```

### Issue 4: Module not found errors

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Check if modules are installed
pip list | grep junos
pip list | grep fastapi
```

### Issue 5: ImportError: No module named 'jnpr.junos'

**Solution:**
```bash
# Install junos-eznc specifically
pip install junos-eznc

# If that fails, try upgrading pip first
pip install --upgrade pip
pip install junos-eznc
```

### Issue 6: SSL/TLS certificate errors

**Solution:**
```bash
# Upgrade certifi
pip install --upgrade certifi

# Or install with --trusted-host
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Issue 7: "VECTOR_PY_DIR not set" error

**Solution:**
```bash
# Set temporarily for current session
export VECTOR_PY_DIR=/Users/UPGH/github/Vanguard/netstudio

# Or run with inline environment variable
VECTOR_PY_DIR=/Users/UPGH/github/Vanguard/netstudio python launcher.py
```

## Advanced: Multiple Virtual Environments

You can create different environments for different purposes:

```bash
# Development environment (with all tools)
python3 -m venv venv-dev
source venv-dev/bin/activate
pip install -r requirements.txt

# Production environment (minimal dependencies)
python3 -m venv venv-prod
source venv-prod/bin/activate
pip install junos-eznc fastapi uvicorn PyYAML Jinja2 deepdiff tabulate
```

## Checking Which Virtual Environment is Active

```bash
# Show Python interpreter path
which python

# Should show something like:
# /Users/UPGH/github/Vanguard/netstudio/venv/bin/python

# Show pip location
which pip

# Show installed packages location
pip show fastapi | grep Location
```

## Updating Dependencies

```bash
# Update all packages
pip list --outdated
pip install --upgrade <package-name>

# Or update everything (be careful!)
pip list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 pip install -U

# Regenerate requirements.txt
pip freeze > requirements.txt
```

## Deactivating and Removing Virtual Environment

```bash
# Deactivate
deactivate

# Remove virtual environment
rm -rf venv

# Create fresh environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Quick Reference Commands

| Action | Command |
|--------|---------|
| **Create venv** | `python3 -m venv venv` |
| **Activate (macOS/Linux)** | `source venv/bin/activate` |
| **Activate (Windows)** | `venv\Scripts\activate` |
| **Deactivate** | `deactivate` |
| **Install deps** | `pip install -r requirements.txt` |
| **Run TUI** | `python launcher.py` |
| **Run API** | `python api/main.py` |
| **Check packages** | `pip list` |
| **Remove venv** | `rm -rf venv` |

## Integration with IDEs

### VS Code

1. Open project folder in VS Code
2. Press `Cmd+Shift+P` (or `Ctrl+Shift+P` on Windows)
3. Type "Python: Select Interpreter"
4. Choose the interpreter from `venv/bin/python`

VS Code will automatically activate the venv when opening terminals.

### PyCharm

1. Open project in PyCharm
2. Go to **Settings/Preferences** → **Project** → **Python Interpreter**
3. Click gear icon → **Add**
4. Select **Existing environment**
5. Browse to `/Users/UPGH/github/Vanguard/netstudio/venv/bin/python`
6. Click **OK**

## Best Practices

1. **Always activate venv** before working on the project
2. **Use pip freeze** to document exact dependency versions
3. **Don't commit venv/** to Git (already in .gitignore)
4. **Create requirements.txt** for reproducible environments
5. **Test in fresh venv** before deploying to production
6. **Use separate venvs** for different projects to avoid conflicts

## Need Help?

If you encounter issues:

1. Check that Python 3.8+ is installed: `python3 --version`
2. Ensure virtual environment is activated: `which python`
3. Verify dependencies are installed: `pip list`
4. Check environment variable: `echo $VECTOR_PY_DIR`
5. Review application logs: `tail -f network_automation.log`

For more information, see:
- [README.md](README.md) - Project documentation
- [QUICK_START.md](QUICK_START.md) - Quick start guide
- [Python venv documentation](https://docs.python.org/3/library/venv.html)
