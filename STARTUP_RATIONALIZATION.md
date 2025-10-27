# Startup Script Rationalization

Date: 2024-10-27

## What Changed

### ✅ New Single Entrypoint

**One command to rule them all:**
```bash
./start
```

This is now the **ONLY** way you should start the application.

### 🗑️ Removed Scripts

The following redundant scripts have been removed:
- ~~`start-dev.sh`~~ - Replaced by `./start`
- ~~`start-all-tmux.sh`~~ - Replaced by `./start`
- ~~`start-frontend.sh`~~ - Replaced by `./start`

### ✨ What the New Script Does

The new `start` script (which runs `start-foreground.py`) provides a **complete** startup solution:

#### 1. **Automatic Process Cleanup**
```
[STEP 1] Checking for existing instances...
[CLEANUP] Found existing backend process: PID 1234
[CLEANUP] Found existing frontend process: PID 5678
[CLEANUP] Stopping 2 existing process(es)...
[CLEANUP] All existing processes stopped
```

**What it does:**
- Searches for running backend (uvicorn/python main.py) processes
- Searches for running frontend (npm/vite) processes
- Kills them gracefully (SIGTERM)
- Force kills if needed (SIGKILL after 2 seconds)
- Ensures clean slate before starting

#### 2. **Environment Validation**
```
[STEP 2] Validating environment setup...
[STEP 2] Environment validated successfully
```

**What it checks:**
- Backend directory exists
- Frontend directory exists
- Backend venv is set up (`backend/venv/bin/activate` exists)
- Frontend dependencies installed (`frontend/node_modules` exists)
- Auto-installs frontend deps if missing

#### 3. **Service Startup**
```
[STEP 3] Starting services...
[BACKEND] Starting on port 8000...
[FRONTEND] Starting on port 3000...

======================================================================
✓ Services Started Successfully
======================================================================

  Backend API:   http://localhost:8000
  Frontend UI:   http://localhost:3000

  Press Ctrl+C to stop all services
======================================================================
```

**Features:**
- Color-coded output (BLUE for backend, GREEN for frontend)
- All logs in one terminal
- Easy to see errors from both services
- Clear success banner with access URLs

#### 4. **Graceful Shutdown**
```
^C
======================================================================
[SHUTDOWN] Stopping all services...
[SHUTDOWN] Cleaning up any remaining processes...
[SHUTDOWN] All services stopped cleanly
======================================================================
```

**What happens on Ctrl+C:**
1. Catches the signal
2. Terminates both processes (SIGTERM)
3. Waits 2 seconds for graceful shutdown
4. Force kills if needed (SIGKILL)
5. Scans for any stragglers and kills them
6. Clean exit

---

## Why This is Better

### Old Way (Multiple Scripts)
```bash
# Had to remember which script to use
./start-dev.sh          # Development mode?
./start-all-tmux.sh     # Production mode?
./start-frontend.sh     # Just frontend?

# Manual cleanup if things got stuck
pkill -f uvicorn
pkill -f npm
pkill -f vite

# Hope it worked...
```

**Problems:**
- ❌ Multiple scripts = confusion
- ❌ Processes left running if script crashes
- ❌ Port conflicts from zombie processes
- ❌ No validation before starting
- ❌ Scattered logs across terminals

### New Way (Single Script)
```bash
./start
```

**Benefits:**
- ✅ One script for everything
- ✅ Auto-kills existing instances
- ✅ Validates setup before starting
- ✅ All logs in one place (color-coded)
- ✅ Clean shutdown guaranteed
- ✅ Works identically everywhere (local, RunPod, etc.)

---

## Migration Guide

### If You Were Using `start-dev.sh`

**Before:**
```bash
./start-dev.sh
# Hope no processes running...
# Ctrl+C to stop
```

**After:**
```bash
./start
# Auto-kills old processes
# Ctrl+C to stop (guaranteed cleanup)
```

### If You Were Using `start-all-tmux.sh`

The tmux script was useful for running in background, but had issues:
- Hard to see logs
- Manual cleanup needed
- Didn't validate setup

**Before:**
```bash
./start-all-tmux.sh
tmux attach -t qwen-image-editor
# Ctrl+B, D to detach
# tmux kill-session -t qwen-image-editor to stop
```

**After:**
```bash
# For foreground (recommended):
./start

# If you REALLY need background, use screen:
screen -S qwen
./start
# Ctrl+A, D to detach
# screen -r qwen to reattach
# screen -X -S qwen quit to stop
```

### If You Were Using `start-frontend.sh`

**Before:**
```bash
# Terminal 1: Start backend manually
cd backend
./start.sh

# Terminal 2: Start frontend
./start-frontend.sh
```

**After:**
```bash
# One terminal, everything:
./start
```

---

## Technical Details

### Process Detection

The script finds processes using pattern matching:

```python
# Backend: uvicorn or python main.py in backend directory
ps aux | grep -E '(uvicorn|python.*main\.py)' | grep '<path>/backend'

# Frontend: npm or vite in frontend directory
ps aux | grep -E '(npm|vite)' | grep '<path>/frontend'
```

This ensures it only kills **YOUR** processes, not system-wide instances.

### Cleanup Strategy

```python
1. Send SIGTERM (graceful shutdown)
2. Wait 2 seconds
3. Check if still alive
4. If alive, send SIGKILL (force kill)
5. Scan for stragglers
6. Repeat if needed
```

### Validation Checks

```python
✓ backend/venv/bin/activate exists
✓ frontend/node_modules exists (auto-install if missing)
✓ Directories are valid
```

---

## Files Structure

```
qwen-image-editor/
├── start                      # ← Simple wrapper (USE THIS)
├── start-foreground.py        # ← Main script (called by ./start)
│
├── backend/
│   ├── setup.sh               # ← First-time setup (still needed)
│   └── start.sh               # ← Internal use only
│
└── frontend/
    └── (no startup scripts)
```

**What to run:**
- **First time**: `cd backend && ./setup.sh`
- **Every time**: `./start`

**What NOT to run:**
- ~~`start-dev.sh`~~ (removed)
- ~~`start-all-tmux.sh`~~ (removed)
- ~~`start-frontend.sh`~~ (removed)
- `backend/start.sh` (internal use only, called by `./start`)

---

## Example Session

```bash
$ ./start

======================================================================
  Qwen Image Editor - Single Entrypoint Startup
======================================================================

[STEP 1] Checking for existing instances...
[CLEANUP] Found existing backend process: PID 42789
[CLEANUP] Found existing frontend process: PID 42801
[CLEANUP] Stopping 2 existing process(es)...
[CLEANUP] All existing processes stopped
[STEP 1] Done

[STEP 2] Validating environment setup...
[STEP 2] Environment validated successfully

[STEP 3] Starting services...

[BACKEND] Starting on port 8000...
[BACKEND] INFO: Started server process [43012]
[BACKEND] INFO: Application startup complete.
[BACKEND] INFO: Uvicorn running on http://0.0.0.0:8000

[FRONTEND] Starting on port 3000...
[FRONTEND] VITE v5.4.21  ready in 768 ms
[FRONTEND] ➜  Local:   http://localhost:3000/

======================================================================
✓ Services Started Successfully
======================================================================

  Backend API:   http://localhost:8000
  Frontend UI:   http://localhost:3000

  Press Ctrl+C to stop all services
======================================================================

[BACKEND] INFO: 24.62.181.162:0 - "GET / HTTP/1.1" 200 OK
[FRONTEND] 4:52:10 PM [vite] page reload src/App.jsx

^C
======================================================================
[SHUTDOWN] Stopping all services...
[SHUTDOWN] Cleaning up any remaining processes...
[SHUTDOWN] All services stopped cleanly
======================================================================
```

---

## Troubleshooting

### "Permission denied: ./start"
```bash
chmod +x start
./start
```

### "python3: command not found"
```bash
# Install Python 3
apt-get install python3
```

### "Processes won't die"
The script tries:
1. SIGTERM (graceful)
2. Wait 2 seconds
3. SIGKILL (force)
4. Scan and repeat

If processes **still** won't die, something is very wrong:
```bash
# Nuclear option (use with caution)
pkill -9 -f uvicorn
pkill -9 -f npm
pkill -9 -f vite
```

### "Port 8000 already in use"
Shouldn't happen - the script kills existing processes. But if it does:
```bash
# Check what's using the port
lsof -i :8000
# Kill it manually
kill -9 <PID>
```

---

## Summary

**Before:** 3 scripts, manual cleanup, scattered logs
**After:** 1 script, auto cleanup, unified logs

**Just run:**
```bash
./start
```

That's it! 🎉
