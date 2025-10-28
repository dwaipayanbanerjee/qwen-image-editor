# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

AI-powered image editing application using Qwen-Image-Edit (20B parameter model) running **locally on Mac with Apple Silicon (MPS)**. Full-stack deployment on your local Mac machine with backend and frontend both running on localhost.

## Quick Start (Mac Local Deployment)

**Prerequisites:**
- Mac with Apple Silicon (M1/M2/M3/M4)
- 64GB+ unified memory recommended (model cache is ~57.7GB)
- ~70GB free disk space (model + cache)
- Python 3.9+ and Node.js 18+ installed

**First-Time Setup:**

```bash
# Navigate to project
cd ~/coding_workshop/computer_utilities/qwen-image-editor

# Run unified setup script (one time only)
./setup.sh
```

The setup script automatically:
- ✅ Checks system prerequisites (Python, Node.js, memory, disk space)
- ✅ Creates data directories in `~/qwen-image-editor/`
- ✅ Sets up backend Python virtual environment
- ✅ Installs all Python dependencies (~5-10 min)
- ✅ Sets up frontend npm dependencies (~2-5 min)
- ✅ Creates configuration files (.env)
- ✅ Verifies PyTorch MPS support on Apple Silicon

**Start the Application (Every Time):**

```bash
# After setup completes, start with:
./start
```

**What the ./start script does:**
1. ✅ Finds and kills any existing backend/frontend processes
2. ✅ Validates environment (checks venv, node_modules)
3. ✅ Auto-installs frontend deps if missing
4. ✅ Starts backend (port 8000) and frontend (port 3000)
5. ✅ Shows all logs in one terminal with color-coded prefixes
6. ✅ Handles Ctrl+C gracefully (kills all processes cleanly)

**What you get:**
- All backend and frontend logs in one terminal
- Color-coded output: [BACKEND] in blue, [FRONTEND] in green
- Automatic cleanup of old instances (no port conflicts)
- Easy debugging - see everything happening in real-time
- Clean shutdown with Ctrl+C stops both services
- No zombie processes left behind

## Architecture

### Local Mac Deployment Model

**Full-Stack on Mac:**
- Both services run on the same local Mac machine
- Backend: Port 8000 (localhost only)
- Frontend: Port 3000 (localhost only)
- Frontend connects to backend via `http://localhost:8000`
- Simple setup, no cross-origin issues
- Start with: `./start` (single command)

**System Requirements:**
- Mac with Apple Silicon (M1, M2, M3, or M4)
- 64GB+ unified memory recommended
- Model requires ~57.7GB disk space (downloads on first run, ~10-30 min)
- All data stored in `~/qwen-image-editor/` (persistent across restarts)

**Technology Stack:**
- Backend: FastAPI + PyTorch with MPS (Metal Performance Shaders)
- Frontend: React + Vite + Tailwind CSS
- Model: Qwen-Image-Edit (20B parameters, BF16 precision)

### Key Design Patterns

**MPS Device Detection:**
- Automatic device selection: MPS > CUDA > CPU
- MPS (Metal Performance Shaders) for Apple Silicon
- BF16 precision on MPS for optimal performance
- CPU fallback for non-Apple Silicon Macs

**Direct Job Processing:**
- Jobs processed immediately as background tasks when submitted
- Background task system allows non-blocking API responses
- Single MPS instance shared across all requests

**Lazy Model Loading:**
- Model loaded on first edit request only (`main.py:63-76`)
- Stored in global `image_editor` variable to reuse across requests
- Reduces startup time and memory footprint when idle

**Job Persistence:**
- In-memory state in `JobManager.jobs` dict
- Disk persistence at `~/qwen-image-editor/jobs/{job_id}/metadata.json`
- Survives server restarts and page refreshes
- Frontend stores current job in localStorage for resume capability

**Real-time Progress:**
- WebSocket at `/ws/{job_id}` for live updates
- JobManager broadcasts to all connected clients via `_broadcast_progress()`
- Progress callbacks from image_editor flow through job_manager to WebSockets

**Multi-Image Support:**
- Can process 1-2 images per job
- Two images combined side-by-side before editing (`image_editor.py:225-256`)
- Resizes to same height while maintaining aspect ratios

### Code Architecture

**Backend Structure:**
- `main.py` - FastAPI app, routes, WebSocket, background task processing
- `image_editor.py` - Qwen model wrapper, inference logic, **MPS device detection**
- `job_manager.py` - Job lifecycle, state management, WebSocket registry
- `models.py` - Pydantic schemas for validation
- `cleanup.py` - CLI utility for maintenance

**Frontend Structure:**
- `App.jsx` - Main orchestrator, state management, workflow control
- `components/ImageUpload.jsx` - Image upload and preview
- `components/EditConfig.jsx` - Configuration form
- `components/ProgressTracker.jsx` - Real-time progress display with WebSocket
- `utils/api.js` - Axios HTTP client and WebSocket connection logic

**Data Flow:**
1. User uploads images → Frontend validates → POST `/api/edit`
2. Backend saves to `~/qwen-image-editor/jobs/{job_id}/` → Returns job_id → Starts processing
3. Frontend connects WebSocket → `/ws/{job_id}`
4. Background task processes job → Broadcasts progress via WebSocket
5. Complete → Frontend downloads → Backend auto-cleans job files

### Storage Layout

```
~/qwen-image-editor/                     # Project root (local Mac)
├── huggingface_cache/                   # Model cache (~57.7GB)
│   └── models--Qwen--Qwen-Image-Edit/
├── jobs/{job_id}/                       # Job storage (~2-5MB each)
│   ├── input_1.jpg
│   ├── input_2.jpg (optional)
│   ├── output.jpg
│   └── metadata.json
└── (workspace is in ~/coding_workshop/computer_utilities/)
    ├── backend/
    │   ├── venv/                        # Python virtual environment
    │   ├── main.py, image_editor.py, etc.
    │   └── .env                         # Backend configuration
    └── frontend/
        ├── node_modules/                # Node.js dependencies
        ├── src/
        └── .env                         # Frontend configuration
```

## Configuration

**Backend `.env`:**
```bash
HF_HOME=~/qwen-image-editor/huggingface_cache
TRANSFORMERS_CACHE=~/qwen-image-editor/huggingface_cache
HF_DATASETS_CACHE=~/qwen-image-editor/huggingface_cache
JOBS_DIR=~/qwen-image-editor/jobs
HOST=0.0.0.0
PORT=8000
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

**Frontend `.env`:**
```bash
VITE_API_URL=http://localhost:8000
```

Note: All paths use `~` which expands to your home directory on Mac.

## Model Details

- **Model:** Qwen-Image-Edit (20B parameters)
- **Precision:** BF16 on MPS/CUDA, FP32 on CPU (~57.7GB disk cache)
- **Processing Time:** ~20s (20 steps), ~45s (50 steps), ~90s (100 steps) on M2/M3 Mac
- **First Run:** Downloads model (~57.7GB, 10-30 min), cached afterward
- **Capabilities:** Semantic editing, appearance changes, text editing (English/Chinese)
- **Device Priority:** MPS (Apple Silicon) > CUDA (NVIDIA) > CPU

## API Endpoints

- `GET /` - Health check (shows device: mps/cuda/cpu)
- `POST /api/edit` - Create job (multipart: image1, image2?, config JSON)
- `GET /api/jobs/{job_id}/status` - Get job status
- `GET /api/jobs/{job_id}/download` - Download result (triggers auto-cleanup)
- `DELETE /api/jobs/{job_id}` - Cancel/delete job
- `POST /api/cleanup?hours=1` - Manual cleanup
- `WS /ws/{job_id}` - Real-time progress WebSocket

## Development Notes

**Adding New Model Parameters:**
1. Update `models.py:EditConfig` with new field
2. Update `image_editor.py:edit_image()` to use parameter
3. Update `frontend/src/components/EditConfig.jsx` with UI input

**Testing Locally:**
- Backend requires Mac with Apple Silicon (MPS support)
- Model will use MPS if available, CPU otherwise
- First run downloads ~57.7GB model (one-time, 10-30 min)

**Job Cleanup:**
- Automatic after download (via `background_tasks`)
- Manual via `cleanup.py` CLI or `/api/cleanup` endpoint
- Jobs persist in `~/qwen-image-editor/jobs/` until explicitly cleaned

**WebSocket Connection:**
- Connects to `ws://localhost:8000/ws/{job_id}`
- Handles reconnection and dead connection cleanup
- Broadcasts progress from worker threads via `asyncio.run_coroutine_threadsafe()`

## Cancellation and Shutdown Behavior

**Important Notes:**
- **During inference**: The diffusers pipeline runs synchronously and cannot be interrupted mid-step
- **When you press Ctrl+C**: The backend will:
  1. Request cancellation for all active jobs
  2. Cancel asyncio tasks immediately
  3. Wait up to 5 seconds for inference threads to complete
  4. Force shutdown after timeout (GPU memory cleared on best-effort basis)
  5. Kill any remaining zombie processes on next start

**Best Practice:**
- Allow inference to complete naturally when possible
- If you must interrupt, wait a few seconds for graceful shutdown
- The `./start` script automatically cleans up old instances on startup

**Resource Cleanup:**
- GPU memory is cleared automatically after each inference
- On Ctrl+C, the backend attempts to clear MPS cache
- If shutdown is forced, resources are freed when the process terminates
- No zombie processes are left behind (verified on next startup)

## Troubleshooting

**Model not loading:**
- Check available memory: System Settings → General → About → Memory
- Ensure 64GB+ unified memory available
- Verify `~/qwen-image-editor/huggingface_cache` directory exists
- Check MPS availability: `python -c "import torch; print(torch.backends.mps.is_available())"`

**Port 8000 not accessible:**
- Check server listening on `0.0.0.0:8000` with `netstat -an | grep 8000`
- Verify firewall allows localhost connections
- Try accessing `http://localhost:8000/` in browser

**Frontend can't connect:**
- Verify `VITE_API_URL=http://localhost:8000` in `frontend/.env`
- Test backend health endpoint directly: `curl http://localhost:8000/`
- Check both services are running: `ps aux | grep -E "(uvicorn|vite)"`

**Out of memory:**
- Restart Mac to clear memory
- Close other memory-intensive apps
- Ensure you have 64GB+ unified memory
- Model requires ~40GB in memory during inference

**Slow processing:**
- Normal: 30-60s for 50 steps on M2/M3
- Check Activity Monitor → GPU tab for Metal usage
- First run is slower due to model download

**MPS not available:**
- Verify you're on Apple Silicon Mac (not Intel)
- Check macOS version (requires macOS 12.3+)
- Ensure PyTorch version supports MPS (2.0+)
- Fallback to CPU if MPS unavailable (slower but works)

## Common Commands

```bash
# Start both services
./start

# Backend only
cd backend
./start.sh

# Frontend only
cd frontend
npm run dev

# Cleanup old jobs
cd backend
source venv/bin/activate
python cleanup.py --status           # Show disk usage
python cleanup.py --list             # List all jobs
python cleanup.py --hours 1          # Clean jobs older than 1 hour
python cleanup.py --all              # Clean all jobs

# Check MPS availability
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"

# Monitor processes
ps aux | grep -E "(uvicorn|vite)"

# Check disk space
df -h ~
du -sh ~/qwen-image-editor
```

## Performance Notes

**Mac Performance (Apple Silicon):**
- M1/M2/M3 with 64GB: ~42 seconds for 50 steps (tested on M3 Ultra)
- Model uses BF16 precision on MPS
- ~60GB memory occupied during inference
- Faster with Lightning LoRA (future enhancement)

**Memory Management:**
- MPS cache cleared after each inference
- Garbage collection forced after processing
- Jobs auto-deleted after download
- Model stays loaded in memory for faster subsequent edits
