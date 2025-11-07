# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

AI-powered image editing and generation application with two distinct workflows:

**IMAGE EDITING MODELS** (preserve input dimensions):
1. **Qwen-Image-Edit-2509-GGUF** - Local quantized (free, 1-2 images, output matches input size)
2. **Qwen-Image-Edit** - Cloud simple edits ($0.01, 1 image, output matches input size)
3. **Qwen-Image-Edit-Plus** - Cloud advanced ($0.02, 1-3 images, output matches input size)

**IMAGE GENERATION MODELS** (text-to-image, aspect ratio control):
4. **Hunyuan Image 3** - Tencent 80B model ($0.02, text-only, configurable aspect ratio)
5. **Qwen-Image** - Text-to-image ($0.015, text-only, configurable aspect ratio)

**HYBRID MODEL** (edit or generate):
6. **Seedream-4** - ByteDance cloud ($0.03/image, 0-10 inputs, 1-15 outputs, flexible)

Full-stack deployment on your local Mac machine with backend and frontend both running on localhost.

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
- Models:
  - Qwen-Image-Edit-2509-GGUF (Quantized: Q2_K/Q4_K_M/Q5_K_S/Q8_0, local)
  - Hunyuan Image 3 (80B parameters, cloud via Replicate)
  - Seedream-4 (Cloud API via Replicate)
  - Qwen Cloud Variants (via Replicate API)

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
├── huggingface_cache/                   # Model cache
│   ├── models--Qwen--Qwen-Image-Edit/ (~57.7GB)
│   └── models--QuantStack--Qwen-Image-Edit-2509-GGUF/ (~7-22GB depending on quantization)
├── jobs/{job_id}/                       # Job storage
│   ├── input_1.jpg ... input_N.jpg      # Input images (1-10)
│   ├── output_0.jpg ... output_N.jpg    # Output images (1-15)
│   └── metadata.json                    # Job metadata with output_images array
└── (workspace is in ~/coding_workshop/computer_utilities/)
    ├── backend/
    │   ├── .venv/                       # Python virtual environment
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

## Key Workflow Distinction

### IMAGE EDITING Workflow
**Philosophy:** Preserve input image dimensions exactly. No resizing, no aspect ratio changes.

**Models:** qwen_gguf, qwen_image_edit, qwen_image_edit_plus
- User uploads image(s) → Model edits content → Output matches input dimensions
- Example: 1200×800 input → 1200×800 output (exact same size)
- Use case: "Change person's hair color", "Remove object", "Style transfer"

### IMAGE GENERATION Workflow
**Philosophy:** Create new images from text. User controls aspect ratio and composition.

**Models:** hunyuan, qwen_image
- User enters text prompt → Model generates from scratch → Output uses chosen aspect ratio
- Example: Prompt "sunset over mountains" → User selects 16:9 → 1664×928 output
- Use case: "Create image of...", "Generate artwork of..."

### HYBRID Workflow
**Model:** seedream
- With images: Flexible editing (can preserve or transform dimensions via aspect_ratio)
- Without images: Pure generation with aspect ratio control

---

## Model Details

### Qwen-Image-Edit-2509-GGUF (Local EDIT Model)
- **Type:** Image Editing (preserves input dimensions)
- **Parameters:** 20B (quantized)
- **Quantization Levels:**
  - Q2_K: ~7GB VRAM, fastest, lowest quality
  - Q4_K_M: ~14GB VRAM, good quality
  - Q5_K_S: ~17GB VRAM, **recommended**, best balance
  - Q8_0: ~22GB VRAM, highest quantized quality
- **Processing Time:** ~32s (50 steps) - 20-30% faster than standard
- **First Run:** Downloads 7-22GB depending on quantization
- **Input Images:** 1-2 (combines side-by-side)
- **Output Dimensions:** Matches combined input size (no resizing)
- **Requirements:** `gguf>=0.10.0` package

### Qwen-Image-Edit (Cloud EDIT Model)
- **Type:** Image Editing (preserves input dimensions)
- **Provider:** Qwen via Replicate
- **Cost:** $0.01 per prediction
- **Processing Time:** ~10-20s
- **Input Images:** 1 (simple single-image edits)
- **Output Dimensions:** Matches input image exactly
- **Use Case:** Simple edits like color changes, object removal, basic modifications
- **Requirements:** REPLICATE_API_TOKEN in .env

### Qwen-Image-Edit-Plus (Cloud EDIT Model)
- **Type:** Advanced Image Editing (preserves input dimensions)
- **Provider:** Qwen via Replicate
- **Cost:** $0.02 per prediction
- **Processing Time:** ~15-30s
- **Input Images:** 1-3 (optimal performance with 1-3)
- **Output Dimensions:** Matches first input image dimensions
- **Input Constraints:** 384px - 3,072px per dimension (Alibaba Cloud spec)
- **Optimal Input:** ~1M total pixels (e.g., 1000×1000) per ComfyUI best practice
- **Use Case:** Pose transfer, style transfer, multi-person composition, product placement
- **Features:** Combines multiple images, preserves identity, advanced multi-image edits
- **Requirements:** REPLICATE_API_TOKEN in .env

### Hunyuan Image 3 (Cloud GENERATION Model)
- **Type:** Text-to-Image Generation (aspect ratio control)
- **Provider:** Tencent via Replicate
- **Cost:** $0.02 per prediction
- **Processing Time:** ~30-45s
- **Parameters:** 80B total (13B active per token, MoE architecture)
- **Input:** Text prompt only (no images)
- **Output Dimensions:** User-controlled via aspect_ratio (1:1, 4:3, 16:9, etc.)
- **Features:** Aspect ratio control, seed for reproducibility, fast mode
- **Requirements:** REPLICATE_API_TOKEN in .env

### Qwen-Image (Cloud GENERATION Model)
- **Type:** Text-to-Image Generation (aspect ratio control)
- **Provider:** Qwen via Replicate
- **Cost:** $0.015 per prediction
- **Processing Time:** ~20-40s
- **Input:** Text prompt only (no images)
- **Output Dimensions:** User-controlled via aspect_ratio
- **Features:** Text-to-image generation, prompt enhancement option
- **Requirements:** REPLICATE_API_TOKEN in .env

### Seedream-4 (HYBRID Cloud Model)
- **Type:** Hybrid - Can edit OR generate (flexible dimensions)
- **Provider:** ByteDance via Replicate
- **Cost:** $0.03 per output image
- **Processing Time:** ~30-60s
- **Input Images:** 0-10 (optional - can work without images)
- **Output Images:** 1-15 (configurable via max_images)
- **Output Dimensions:** User-controlled via aspect_ratio and size parameters
- **Aspect Ratio Options:** 1:1, 4:3, 16:9, 9:16, match_input_image (when images provided)
- **Use Case:** Flexible - can edit existing images or generate from scratch
- **Features:** Prompt enhancement, sequential multi-image generation, auto-retry on errors
- **Requirements:** REPLICATE_API_TOKEN in .env

## API Endpoints

- `GET /` - Health check (shows device and available models)
- `POST /api/edit` - Create job (multipart: image1-imageN, config JSON)
- `GET /api/jobs/{job_id}/status` - Get job status
- `GET /api/jobs/{job_id}/images` - List all output images with metadata
- `GET /api/jobs/{job_id}/images/{index}` - Download specific output image
- `DELETE /api/jobs/{job_id}` - Cancel/delete job
- `POST /api/cleanup?hours=1` - Manual cleanup
- `WS /ws/{job_id}` - Real-time progress WebSocket

## Development Notes

**Critical Design Principle: EDIT vs GENERATION**
- **EDIT models** (qwen_gguf, qwen_image_edit, qwen_image_edit_plus): MUST preserve input dimensions
  - Never resize input images before processing
  - Always use `aspect_ratio: "match_input_image"` in API calls
  - Output should match input dimensions exactly
  - Do NOT expose aspect ratio controls to users for these models

- **GENERATION models** (hunyuan, qwen_image): Aspect ratio is user-controlled
  - No input images required
  - User selects desired output aspect ratio
  - Expose aspect ratio controls in UI

- **HYBRID models** (seedream): User chooses behavior
  - With images: Can use "match_input_image" or custom aspect ratio
  - Without images: User-controlled aspect ratio

**Adding New Model Parameters:**
1. Update `models.py:EditConfig` with new field
2. Update appropriate handler in `main.py` or `replicate_client.py`
3. Update `frontend/src/components/EditConfig.jsx` with UI input (only for relevant models)

**Testing Locally:**
- Backend requires Mac with Apple Silicon (MPS support)
- Model will use MPS if available, CPU otherwise
- First run downloads ~57.7GB model (one-time, 10-30 min)

**Job Cleanup:**
- Manual via `cleanup.py` CLI or `/api/cleanup` endpoint
- User deletes jobs via DELETE button in UI
- Jobs persist in `~/qwen-image-editor/jobs/` until explicitly deleted

**New Features:**
- **Multi-Image Output:** Seedream can generate 1-15 images per job
- **Output Gallery:** All images displayed with individual download buttons
- **Prompt History:** Last 20 prompts saved in localStorage, dropdown for quick reuse
- **GGUF Support:** Quantized models for faster inference and lower VRAM
- **Auto-Retry:** Replicate API errors automatically retry up to 3 times

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
