# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

AI-powered image editing application using Qwen-Image-Edit (20B parameter model). Split architecture: FastAPI backend on RunPod A40 GPU, React frontend running locally.

## Common Commands

### Backend (RunPod Server)

```bash
# SSH into RunPod
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519

# Navigate to backend
cd /workspace/qwen-image-editor/backend

# First-time setup (creates venv, installs deps, downloads model)
./setup.sh

# Start backend server (port 8002)
./start.sh

# Run in background with screen
screen -S qwen
./start.sh
# Detach: Ctrl+A, then D
# Reattach: screen -r qwen

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

### Frontend (Local Mac)

```bash
# Navigate to frontend
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor/frontend

# Install dependencies (first time only)
npm install

# Start dev server (port 3001)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Deploy Backend to RunPod

```bash
# From local Mac, copy backend files to RunPod
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor
scp -P 22101 -i ~/.ssh/id_ed25519 -r backend/* root@69.30.85.14:/workspace/qwen-image-editor/backend/
```

## Architecture

### Deployment Model

**Backend (RunPod):**
- FastAPI server on A40 GPU (48GB VRAM)
- Internal: `0.0.0.0:8002`
- External: `https://<pod-id>-8002.proxy.runpod.net`
- Model requires ~40GB VRAM (BF16), downloads on first run (~10-30 min)
- All data stored in `/workspace` (persistent across pod restarts)

**Frontend (Local Mac):**
- React + Vite + Tailwind CSS
- Runs on `http://localhost:3001`
- Connects to RunPod backend via HTTPS/WSS
- Configure backend URL in `frontend/.env`

### Key Design Patterns

**Sequential Job Processing:**
- Jobs queued using `asyncio.Queue` to prevent GPU OOM
- Worker thread in `main.py:process_generation_queue()` processes one job at a time
- Background task system allows non-blocking API responses

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
- `main.py` - FastAPI app, routes, WebSocket, queue worker
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
2. Backend saves to `/workspace/jobs/{job_id}/` → Returns job_id → Queues job
3. Frontend connects WebSocket → `/ws/{job_id}`
4. Worker processes job → Broadcasts progress via WebSocket
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
PORT=8002
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

**Frontend `.env` (Local):**
```bash
VITE_API_URL=https://2ww93nrkflzjy2-644110bf-8002.proxy.runpod.net
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

**Port 8002 not accessible:** Verify RunPod HTTP Services shows port 8002 as "Ready", check server listening on `0.0.0.0:8002` with `netstat -tlnp | grep 8002`

**Frontend can't connect:** Verify `VITE_API_URL` in `frontend/.env`, test backend health endpoint directly in browser

**Out of memory:** Restart server to clear GPU cache, check no other GPU processes with `nvidia-smi`

**Slow processing:** Normal 30-60s for 50 steps, check GPU utilization is 90-100% during inference
