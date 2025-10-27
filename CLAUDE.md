# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

AI-powered image editing application using Qwen-Image-Edit (20B parameter model). Flexible deployment: Run full-stack on RunPod, or split architecture with backend on RunPod and frontend locally.

## Common Commands

### Quick Start (Development Mode)

**Simple single-terminal setup for debugging:**

```bash
# SSH into RunPod
ssh root@<SERVER_IP> -p <SSH_PORT> -i ~/.ssh/id_ed25519

# First-time setup only
cd /workspace/qwen-image-editor
cd backend && ./setup.sh && cd ..
cd frontend && npm install && cd ..

# Start both services with visible output
./start-dev.sh

# All logs appear in one terminal with color-coded prefixes
# Press Ctrl+C to stop all services
```

**What you get:**
- All backend and frontend logs in one terminal
- Color-coded output: [BACKEND] in blue, [FRONTEND] in green
- Easy debugging - see everything happening in real-time
- Clean shutdown with Ctrl+C stops both services

### Backend (RunPod Server)

```bash
# SSH into RunPod (replace with your server details)
ssh root@<SERVER_IP> -p <SSH_PORT> -i ~/.ssh/id_ed25519

# Navigate to backend
cd /workspace/qwen-image-editor/backend

# First-time setup (creates venv, installs deps, downloads model)
./setup.sh

# Start backend server (port 8000)
./start.sh

# Run in background with screen
screen -S qwen
./start.sh
# Detach: Ctrl+A, then D
# Reattach: screen -r qwen

# Manage tmux sessions (when using start-all-tmux.sh)
tmux attach -t qwen-image-editor  # Attach to session
# Switch windows: Ctrl+B, then 0 (backend) or 1 (frontend)
# Detach: Ctrl+B, then D
tmux kill-session -t qwen-image-editor  # Stop all services

# Monitor GPU
nvidia-smi
watch -n 1 nvidia-smi

# Cleanup old jobs
source venv/bin/activate
python cleanup.py --status           # Show disk usage
python cleanup.py --list             # List all jobs
python cleanup.py --hours 1          # Clean jobs older than 1 hour
python cleanup.py --job <job_id>     # Clean specific job
python cleanup.py --all              # Clean all jobs
```

### Frontend (Local Development)

```bash
# Navigate to frontend (adjust path to your local repo)
cd /path/to/qwen-image-editor/frontend

# Install dependencies (first time only)
npm install

# Start dev server (port 3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Full-Stack Deployment (RunPod) - Recommended

**Method 1: Using Git (Recommended)**

```bash
# 1. Push latest changes to GitHub (on local machine)
git push origin main

# 2. SSH into RunPod
ssh root@<SERVER_IP> -p <SSH_PORT> -i ~/.ssh/id_ed25519

# 3. First-time setup: Clone repository
cd /workspace
git clone https://github.com/<YOUR_USERNAME>/qwen-image-editor.git
cd qwen-image-editor

# 4. Or update existing: Pull latest changes
cd /workspace/qwen-image-editor
git pull origin main

# 5. Initial setup (first time only)
cd backend
./setup.sh  # Sets up venv, installs deps, downloads model (~10-30 min)
cd ../frontend
npm install  # Install frontend dependencies

# 6. Start both services
cd /workspace/qwen-image-editor
./start-all-tmux.sh

# 7. Access services (expose ports 8000 and 3000 in RunPod HTTP Services)
# Frontend: https://<pod-id>-3000.proxy.runpod.net
# Backend:  https://<pod-id>-8000.proxy.runpod.net
```

**Method 2: Using SCP (Alternative)**

```bash
# For quick file transfers without git (adjust SERVER_IP and SSH_PORT)
scp -P <SSH_PORT> -i ~/.ssh/id_ed25519 -r backend frontend start-all-tmux.sh root@<SERVER_IP>:/workspace/qwen-image-editor/
```

### Split Deployment (Backend on RunPod, Frontend Local)

**Method 1: Using Git (Recommended)**

```bash
# On RunPod: Clone/pull repository
ssh root@<SERVER_IP> -p <SSH_PORT> -i ~/.ssh/id_ed25519
cd /workspace
git clone https://github.com/<YOUR_USERNAME>/qwen-image-editor.git
cd qwen-image-editor/backend
./setup.sh  # First time only
./start.sh

# On local machine: Run frontend
cd /path/to/qwen-image-editor/frontend
# Update .env with: VITE_API_URL=https://<pod-id>-8000.proxy.runpod.net
npm run dev
```

**Method 2: Using SCP (Alternative)**

```bash
# Deploy only backend (adjust SERVER_IP and SSH_PORT)
scp -P <SSH_PORT> -i ~/.ssh/id_ed25519 -r backend/* root@<SERVER_IP>:/workspace/qwen-image-editor/backend/
```

## Architecture

### Deployment Model

**Two deployment options:**

**Option 1: Full-Stack on RunPod (Recommended)**
- Both services run on the same RunPod server
- Backend: Port 8000 (internal/external via proxy)
- Frontend: Port 3000 (internal/external via proxy)
- Frontend connects to backend via `http://localhost:8000`
- Simpler setup, no cross-origin issues
- Start with: `./start-all-tmux.sh`

**Option 2: Split Deployment**
- Backend on RunPod A40 GPU, frontend on local machine
- Backend: `0.0.0.0:8000` → `https://<pod-id>-8000.proxy.runpod.net`
- Frontend: `http://localhost:3000` (local dev server)
- Frontend connects to backend via HTTPS/WSS
- Useful for frontend development

**Backend Requirements:**
- FastAPI server on A40 GPU (48GB VRAM)
- Model requires ~40GB VRAM (BF16), downloads on first run (~10-30 min)
- All data stored in `/workspace` (persistent across pod restarts)

**Frontend Stack:**
- React + Vite + Tailwind CSS
- Configure backend URL in `frontend/.env`

### Key Design Patterns

**Direct Job Processing:**
- Jobs processed immediately as background tasks when submitted
- Background task system allows non-blocking API responses
- Single GPU instance shared across all requests

**Lazy Model Loading:**
- Model loaded on first edit request only (`main.py:63-76`)
- Stored in global `image_editor` variable to reuse across requests
- Reduces startup time and memory footprint when idle

**Job Persistence:**
- In-memory state in `JobManager.jobs` dict
- Disk persistence at `/workspace/jobs/{job_id}/metadata.json`
- Survives server restarts and page refreshes
- Frontend stores current job in localStorage for resume capability

**Real-time Progress:**
- WebSocket at `/ws/{job_id}` for live updates
- JobManager broadcasts to all connected clients via `_broadcast_progress()`
- Progress callbacks from image_editor flow through job_manager to WebSockets

**Multi-Image Support:**
- Can process 1-2 images per job
- Two images combined side-by-side before editing (`image_editor.py:122-153`)
- Resizes to same height while maintaining aspect ratios

### Code Architecture

**Backend Structure:**
- `main.py` - FastAPI app, routes, WebSocket, background task processing
- `image_editor.py` - Qwen model wrapper, inference logic
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
2. Backend saves to `/workspace/jobs/{job_id}/` → Returns job_id → Starts processing
3. Frontend connects WebSocket → `/ws/{job_id}`
4. Background task processes job → Broadcasts progress via WebSocket
5. Complete → Frontend downloads → Backend auto-cleans job files

### Storage Layout

```
/workspace/                              # RunPod persistent volume
├── huggingface_cache/                   # Model cache (~40GB)
│   └── models--Qwen--Qwen-Image-Edit/
├── jobs/{job_id}/                       # Job storage (~2-5MB each)
│   ├── input_1.jpg
│   ├── input_2.jpg (optional)
│   ├── output.jpg
│   └── metadata.json
└── qwen-image-editor/backend/
    ├── venv/                            # Python virtual environment
    ├── main.py, image_editor.py, etc.
    └── .env                             # Configuration
```

## Configuration

**Backend `.env` (RunPod):**
```bash
HF_HOME=/workspace/huggingface_cache
TRANSFORMERS_CACHE=/workspace/huggingface_cache
HF_DATASETS_CACHE=/workspace/huggingface_cache
JOBS_DIR=/workspace/jobs
HOST=0.0.0.0
PORT=8000
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

**Frontend `.env` (Full-stack deployment):**
```bash
VITE_API_URL=http://localhost:8000
```

**Frontend `.env` (Split deployment):**
```bash
VITE_API_URL=https://<pod-id>-8000.proxy.runpod.net
```

Note: `/workspace` is critical - everything else is deleted on RunPod pod restart.

## Model Details

- **Model:** Qwen-Image-Edit (20B parameters)
- **Precision:** BF16 (~40GB VRAM)
- **Processing Time:** ~20s (20 steps), ~45s (50 steps), ~90s (100 steps)
- **First Run:** Downloads model (~40GB, 10-30 min), cached afterward
- **Capabilities:** Semantic editing, appearance changes, text editing (English/Chinese)

## API Endpoints

- `GET /` - Health check
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
- Backend requires 40GB+ VRAM GPU (A40/A6000/A100)
- Can develop frontend against deployed RunPod backend

**Job Cleanup:**
- Automatic after download (via `background_tasks`)
- Manual via `cleanup.py` CLI or `/api/cleanup` endpoint
- Jobs persist in `/workspace` until explicitly cleaned

**WebSocket Connection:**
- Auto-converts `https://` → `wss://` in frontend
- Handles reconnection and dead connection cleanup
- Broadcasts progress from worker threads via `asyncio.run_coroutine_threadsafe()`

## Troubleshooting

**Model not loading:** Check GPU VRAM (`nvidia-smi`), ensure A40 with 48GB, verify `/workspace/huggingface_cache` exists

**Port 8000 not accessible:** Verify RunPod HTTP Services shows port 8000 as "Ready", check server listening on `0.0.0.0:8000` with `netstat -tlnp | grep 8000`

**Frontend can't connect:** Verify `VITE_API_URL` in `frontend/.env`, test backend health endpoint directly in browser

**Out of memory:** Restart server to clear GPU cache, check no other GPU processes with `nvidia-smi`

**Slow processing:** Normal 30-60s for 50 steps, check GPU utilization is 90-100% during inference
