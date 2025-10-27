# Qwen Image Editor - Complete Setup & Documentation

**AI-Powered Image Editing using Qwen-Image-Edit (20B Parameters)**

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Details](#architecture-details)
3. [Prerequisites](#prerequisites)
4. [Complete Setup Process](#complete-setup-process)
5. [Configuration Reference](#configuration-reference)
6. [Usage Guide](#usage-guide)
7. [API Documentation](#api-documentation)
8. [Maintenance & Operations](#maintenance--operations)
9. [Troubleshooting](#troubleshooting)
10. [Technical Specifications](#technical-specifications)
11. [Development Notes](#development-notes)

---

## Project Overview

### What is This?

A full-stack AI image editing application that uses the Qwen-Image-Edit model (20B parameters) to edit images based on natural language prompts. The system can work with single images or combine two images before applying edits.

### Key Features

- ✨ **Natural Language Editing**: Describe edits in plain English/Chinese
- 🖼️ **Image Combining**: Merge two images side-by-side before editing
- ⚡ **Fast Processing**: ~30-60 seconds per edit on A40 GPU
- 📊 **Real-time Progress**: WebSocket-based live updates
- 💾 **Persistent Storage**: Survives RunPod pod restarts
- 🎨 **Advanced Controls**: CFG scale, inference steps, negative prompts
- 🔄 **Job Persistence**: Resume after page refresh

### Technology Stack

**Backend:**
- FastAPI (Python web framework)
- Qwen-Image-Edit model via Hugging Face Diffusers
- PyTorch with CUDA support
- WebSocket for real-time communication
- Asyncio for background job processing

**Frontend:**
- React 18
- Vite (build tool)
- Tailwind CSS (styling)
- Axios (HTTP client)
- WebSocket API (real-time updates)

---

## Architecture Details

### Deployment Model

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR LOCAL MAC                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Frontend (React + Vite)                            │   │
│  │  - Runs on localhost:3000                           │   │
│  │  - Development server                               │   │
│  │  - User interface                                   │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      │ HTTPS/WSS
                      │ (via Internet)
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              RUNPOD A40 GPU SERVER                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Backend (FastAPI)                                   │   │
│  │  - Internal: 0.0.0.0:8000                           │   │
│  │  - External: https://...-8000.proxy.runpod.net      │   │
│  │  - REST API + WebSocket                             │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │  Qwen-Image-Edit Model                              │   │
│  │  - 20B parameters                                    │   │
│  │  - BF16 precision (~40GB VRAM)                      │   │
│  │  - Lazy loaded on first use                         │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────────┐   │
│  │  Storage (/workspace - PERSISTENT)                   │   │
│  │  ├─ huggingface_cache/ (~40GB model)                │   │
│  │  ├─ jobs/{job_id}/                                   │   │
│  │  │  ├─ input_1.jpg                                   │   │
│  │  │  ├─ input_2.jpg (optional)                        │   │
│  │  │  ├─ output.jpg                                    │   │
│  │  │  └─ metadata.json                                 │   │
│  │  └─ qwen-image-editor/backend/venv/                  │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Port Configuration

| Component | Internal Port | External Port | Access URL |
|-----------|--------------|---------------|------------|
| Backend (RunPod) | 8000 | 8000 | `https://<pod-id>-8000.proxy.runpod.net` |
| Frontend (Mac) | 3000 | 3000 | `http://localhost:3000` |

**Important**: RunPod's proxy allows external access to port 8000 without port forwarding.

### Data Flow

```
1. User uploads images + prompt
   └─> Frontend (ImageUpload.jsx)

2. Frontend sends POST /api/edit
   └─> Multipart form-data: [image1, image2?, config]
   └─> Backend receives and validates

3. Backend creates job
   └─> Saves images to /workspace/jobs/{job_id}/
   └─> Queues job for processing
   └─> Returns job_id to frontend

4. Frontend connects WebSocket
   └─> /ws/{job_id}
   └─> Receives real-time progress updates

5. Backend processes job (async worker)
   └─> Loads Qwen model (if not loaded)
   └─> Combines images (if 2 images)
   └─> Runs inference with prompt
   └─> Saves output.jpg
   └─> Broadcasts progress via WebSocket

6. Job completes
   └─> Frontend shows download button
   └─> User downloads edited image
   └─> Backend auto-cleans job files
```

---

## Prerequisites

### RunPod Requirements

✅ **GPU**: A40 with 48GB VRAM (minimum 40GB for BF16 model)
✅ **Storage**: 50GB volume mounted at `/workspace`
✅ **Container**: `runpod-torch-v280` or similar PyTorch image
✅ **Ports**: Port 8000 exposed via HTTP Services
✅ **SSH Access**: SSH keys configured

### Local Mac Requirements

✅ **Node.js**: Version 18+ (check: `node --version`)
✅ **npm**: Version 9+ (check: `npm --version`)
✅ **SSH Key**: Access to RunPod server
✅ **Internet**: For connecting to RunPod backend

### Your Current RunPod Details

```
Pod ID: 2ww93nrkflzjy2-644110bf
GPU: A40 x1 (48GB VRAM)
Storage: 50GB volume at /workspace
SSH: ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519
HTTP Service: Port 8000 (proxy URL pending)
```

---

## Complete Setup Process

### Phase 1: Prepare Backend Files on Mac

**Step 1.1**: Verify files exist

```bash
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor
ls -la backend/

# You should see:
# main.py, image_editor.py, job_manager.py, models.py
# cleanup.py, requirements.txt, setup.sh, start.sh
# .env.example
```

**Step 1.2**: Review backend configuration (optional)

```bash
cat backend/.env.example
```

---

### Phase 2: Deploy Backend to RunPod

**Step 2.1**: Connect to RunPod via SSH

```bash
# Option 1: Direct TCP (recommended)
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519

# Option 2: Proxied SSH
ssh 2ww93nrkflzjy2-644110bf@ssh.runpod.io -i ~/.ssh/id_ed25519
```

**Step 2.2**: Create directory structure on RunPod

```bash
# On RunPod server
cd /workspace
mkdir -p qwen-image-editor/backend
mkdir -p huggingface_cache
mkdir -p jobs

ls -la /workspace/
# Should show: qwen-image-editor, huggingface_cache, jobs
```

**Step 2.3**: Copy backend files from Mac to RunPod

Open a **new terminal on your Mac** (keep RunPod SSH open):

```bash
# On your Mac
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor

# Copy all backend files
scp -P 22101 -i ~/.ssh/id_ed25519 -r backend/* root@69.30.85.14:/workspace/qwen-image-editor/backend/

# Verify copy completed
# You should see: Transferred XXX files
```

**Step 2.4**: Verify files on RunPod

Back in your **RunPod SSH terminal**:

```bash
cd /workspace/qwen-image-editor/backend
ls -la

# You should see all backend files
# If main.py is missing, the copy failed
```

**Step 2.5**: Make scripts executable

```bash
chmod +x setup.sh start.sh
ls -la *.sh
# Both should show 'x' permission: -rwxr-xr-x
```

**Step 2.6**: Run setup script

```bash
./setup.sh
```

**What happens during setup:**
- Creates Python virtual environment (`venv/`)
- Installs PyTorch with CUDA 12.1
- Installs all dependencies from `requirements.txt`
- Creates `.env` file with default config
- Verifies CUDA availability

**Expected duration**: 5-10 minutes

**Expected output (end)**:
```
PyTorch version: 2.2.0
CUDA available: True
CUDA version: 12.1
GPU: NVIDIA A40

=== Setup Complete! ===
```

**Step 2.7**: Verify GPU

```bash
nvidia-smi

# Should show:
# +-----------------------------------------------------------------------------+
# | NVIDIA-SMI 535.xx       Driver Version: 535.xx       CUDA Version: 12.2    |
# |-------------------------------+----------------------+----------------------+
# | GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
# |   0  NVIDIA A40         On    | 00000000:00:05.0 Off |                    0 |
# | ...                                                                         |
# +-----------------------------------------------------------------------------+
```

---

### Phase 3: Start Backend Server

**Step 3.1**: Start the server

```bash
cd /workspace/qwen-image-editor/backend
./start.sh
```

**What happens on first start:**
- Activates virtual environment
- Loads environment variables from `.env`
- Starts FastAPI server on port 8000
- **Downloads Qwen model** (~40GB, 10-30 minutes on first run)
- Model cached in `/workspace/huggingface_cache`

**Expected output (initial)**:
```
=== Starting Qwen Image Editor Backend ===
Loading environment variables...
Activating virtual environment...
Configuration:
  Host: 0.0.0.0
  Port: 8000
  Jobs Directory: /workspace/jobs
  HuggingFace Cache: /workspace/huggingface_cache

Starting FastAPI server...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**First run only - Model download:**
```
Downloading (…)ain.safetensors: 100%|██████████| 40.2GB/40.2GB [15:23<00:00, 43.5MB/s]
```

**Step 3.2**: Test backend locally (on RunPod)

Open a **new SSH session** to RunPod:

```bash
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519

# Test health endpoint
curl http://localhost:8000/

# Expected response:
# {"status":"online","message":"Qwen Image Editor API is running","model":"Qwen-Image-Edit","gpu":"A40"}
```

✅ **If you see this response, backend is working!**

**Step 3.3**: Keep server running

Keep the first SSH terminal open with the server running, or use `screen`:

```bash
# Option 1: Keep terminal open (simple)
# Just leave it running

# Option 2: Use screen (advanced)
screen -S qwen
./start.sh
# Press Ctrl+A, then D to detach

# Reattach later:
screen -r qwen
```

---

### Phase 4: Get RunPod Proxy URL

**Step 4.1**: Open RunPod dashboard in browser

Go to: https://runpod.io/console/pods

**Step 4.2**: Find your pod

Look for pod: `2ww93nrkflzjy2-644110bf`

**Step 4.3**: Get HTTP Service URL

Click on the pod → Look for **"HTTP Services"** section:

```
Port 8000
HTTP Service: [Status: Ready]
URL: https://2ww93nrkflzjy2-644110bf-8000.proxy.runpod.net
```

**Copy this URL!** You'll need it for the frontend.

**Step 4.4**: Test external access

From your **Mac terminal**:

```bash
curl https://2ww93nrkflzjy2-644110bf-8000.proxy.runpod.net/

# Expected: Same JSON response as before
```

✅ **If this works, your backend is accessible from the internet!**

---

### Phase 5: Configure Frontend on Mac

**Step 5.1**: Open frontend directory

```bash
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor/frontend
```

**Step 5.2**: Edit `.env` file

```bash
nano .env
# Or use your preferred editor: code .env, vim .env, etc.
```

**Replace the content with your RunPod URL:**

```bash
# Before:
VITE_API_URL=http://localhost:8000

# After:
VITE_API_URL=https://2ww93nrkflzjy2-644110bf-8000.proxy.runpod.net
```

**Save and exit** (nano: Ctrl+O, Enter, Ctrl+X)

**Step 5.3**: Verify configuration

```bash
cat .env
# Should show your RunPod URL
```

---

### Phase 6: Start Frontend

**Step 6.1**: Install dependencies (first time only)

```bash
npm install
```

**Expected duration**: 2-3 minutes

**Expected output (end)**:
```
added 234 packages, and audited 235 packages in 2m

found 0 vulnerabilities
```

**Step 6.2**: Start development server

```bash
npm run dev
```

**Expected output:**
```
  VITE v5.0.11  ready in 523 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: http://192.168.1.x:3000/
  ➜  press h + enter to show help
```

**Step 6.3**: Browser should auto-open

If not, manually open: **http://localhost:3000**

You should see the Qwen Image Editor interface!

---

## Configuration Reference

### Backend Configuration (`backend/.env`)

```bash
# Hugging Face model cache - MUST be in /workspace for persistence
HF_HOME=/workspace/huggingface_cache
TRANSFORMERS_CACHE=/workspace/huggingface_cache
HF_DATASETS_CACHE=/workspace/huggingface_cache

# Job storage directory - MUST be in /workspace
JOBS_DIR=/workspace/jobs

# Server binding
HOST=0.0.0.0          # Bind to all interfaces
PORT=8000             # Internal port (exposed via RunPod proxy)

# GPU memory optimization
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

**Why `/workspace`?**
- RunPod deletes everything outside `/workspace` on pod restart
- Model cache (~40GB) would need re-download without this
- Jobs would be lost on restart

### Frontend Configuration (`frontend/.env`)

```bash
# Development (local backend testing)
VITE_API_URL=http://localhost:8000

# Production (RunPod backend)
VITE_API_URL=https://2ww93nrkflzjy2-644110bf-8000.proxy.runpod.net
```

**Note**: Must be prefixed with `VITE_` for Vite to expose it to the browser.

---

## Usage Guide

### Basic Workflow

**1. Upload Images**

- Click the upload area
- Select 1-2 images (PNG, JPG, JPEG)
- Preview appears with thumbnails
- Can remove images individually

**Single Image Mode:**
- Direct editing of one image
- Example: "change the sky to sunset colors"

**Two Image Mode:**
- Images combined side-by-side
- Then edited together
- Example: "blend the two scenes seamlessly"

**2. Configure Edit**

Required:
- **Prompt**: Describe the edit you want
  - Be specific and detailed
  - Example: "change the background to a starry night sky"

Optional:
- **Negative Prompt**: What to avoid
  - Example: "blurry, low quality, distorted"

Advanced Settings (click to expand):
- **Guidance Scale**: 1.0 to 10.0 (default: 4.0)
  - Higher = stronger adherence to prompt
  - Too high = over-saturated, unnatural
  - Recommended: 3.0-5.0

- **Inference Steps**: 20 to 100 (default: 50)
  - More steps = better quality, slower
  - 20 steps: ~20 seconds (fast, good quality)
  - 50 steps: ~45 seconds (balanced)
  - 100 steps: ~90 seconds (best quality)

**3. Generate**

- Click "Generate Edited Image"
- Watch real-time progress
- Shows current stage and ETA
- Can cancel if needed

**4. Download**

- Click "Download Image" when complete
- Saves as `edited_{job_id}.jpg`
- Job automatically cleaned up after download

### Example Editing Prompts

**Semantic Editing** (High-level changes):
```
"change the style to watercolor painting"
"make it look like a sunny day"
"convert to black and white"
"make the scene look like winter"
"add a sunset sky"
```

**Appearance Editing** (Precise modifications):
```
"remove the person in the background"
"change the car color to red"
"add glasses to the person"
"remove all text from the image"
"add a hat to the person"
```

**Text Editing** (Bilingual support):
```
"change the sign text to 'Welcome'"
"add Chinese text saying '欢迎'"
"remove all text"
"make the text bold and red"
```

**Multi-Image Combining**:
```
"blend the two images seamlessly"
"make them look like one continuous scene"
"combine them into a before/after comparison"
```

### Tips for Best Results

✅ **Be specific**: "change background to sunset" is better than "make it nice"
✅ **Use details**: "add a red Ferrari in the foreground" is better than "add a car"
✅ **Iterate**: If results aren't perfect, try adjusting the prompt
✅ **Guidance scale**: Start at 4.0, increase if prompt not followed
✅ **Negative prompts**: Use to avoid common issues like "blurry, low quality"

---

## API Documentation

### REST API Endpoints

#### Health Check
```http
GET /
```

**Response:**
```json
{
  "status": "online",
  "message": "Qwen Image Editor API is running",
  "model": "Qwen-Image-Edit",
  "gpu": "A40"
}
```

---

#### Create Edit Job
```http
POST /api/edit
Content-Type: multipart/form-data
```

**Request:**
```
Form Fields:
- image1: File (required) - Primary image
- image2: File (optional) - Second image for combining
- config: JSON string (required) - Edit configuration
```

**Config JSON Structure:**
```json
{
  "prompt": "change the background to sunset",
  "negative_prompt": "blurry, low quality",
  "true_cfg_scale": 4.0,
  "num_inference_steps": 50
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Image editing job created and queued"
}
```

---

#### Get Job Status
```http
GET /api/jobs/{job_id}/status
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "config": {
    "prompt": "change the background to sunset",
    "negative_prompt": "blurry",
    "true_cfg_scale": 4.0,
    "num_inference_steps": 50
  },
  "progress": {
    "stage": "editing",
    "message": "Applying edits with Qwen model...",
    "progress": 60,
    "updated_at": 1704067200.123
  },
  "error": null,
  "created_at": 1704067180.456
}
```

**Status Values:**
- `queued`: Job waiting to be processed
- `processing`: Currently generating
- `complete`: Editing finished
- `error`: Job failed

**Progress Stages:**
- `loading_model`: Loading Qwen model (first time only)
- `loading_images`: Loading input images
- `combining_images`: Merging two images (if applicable)
- `editing`: Running inference
- `saving`: Saving output
- `complete`: Done

---

#### Download Result
```http
GET /api/jobs/{job_id}/download
```

**Response:**
- Content-Type: `image/jpeg`
- Downloads as `edited_{job_id}.jpg`
- Triggers automatic cleanup in background

---

#### Delete Job
```http
DELETE /api/jobs/{job_id}
```

**Response:**
```json
{
  "message": "Job 550e8400-e29b-41d4-a716-446655440000 deleted successfully"
}
```

---

#### Manual Cleanup
```http
POST /api/cleanup?hours=1
```

**Parameters:**
- `hours`: Remove jobs older than N hours (default: 1)

**Response:**
```json
{
  "message": "Cleaned up 3 jobs older than 1 hour(s)",
  "deleted": [
    "job_id_1",
    "job_id_2",
    "job_id_3"
  ]
}
```

---

### WebSocket API

#### Connect to Job
```
WS /ws/{job_id}
```

**Connection:**
```javascript
const ws = new WebSocket('wss://your-pod-8000.proxy.runpod.net/ws/{job_id}')
```

**Incoming Messages:**
```json
{
  "status": "processing",
  "progress": {
    "stage": "editing",
    "message": "Applying edits with Qwen model...",
    "progress": 60,
    "updated_at": 1704067200.123
  },
  "error": null
}
```

**Message Types:**

1. **Initial Status** (on connect)
2. **Progress Updates** (during processing)
3. **Completion** (when done)
4. **Error** (if failed)

**Connection Lifecycle:**
```
1. Client connects → WebSocket accepts
2. Server sends initial status
3. Server broadcasts updates during processing
4. Job completes → final status sent
5. Client or server closes connection
```

---

## Maintenance & Operations

### Monitoring

#### Check Backend Status

```bash
# From RunPod SSH
curl http://localhost:8000/
```

#### Monitor GPU Usage

```bash
# Real-time monitoring
nvidia-smi

# Watch continuously (updates every second)
watch -n 1 nvidia-smi

# Check VRAM usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

#### View Server Logs

```bash
# If running with start.sh, logs are in stdout
# Use screen to keep it running in background

# Start with screen
screen -S qwen
./start.sh

# Detach: Ctrl+A, then D

# Reattach to view logs
screen -r qwen

# List screens
screen -ls
```

### Job Management

#### Using cleanup.py

```bash
cd /workspace/qwen-image-editor/backend
source venv/bin/activate

# Show disk usage statistics
python cleanup.py --status

# List all jobs with details
python cleanup.py --list

# Clean jobs older than 1 hour
python cleanup.py --hours 1

# Clean jobs older than 6 hours
python cleanup.py --hours 6

# Clean specific job
python cleanup.py --job 550e8400-e29b-41d4-a716-446655440000

# Clean jobs by status
python cleanup.py --by-status error
python cleanup.py --by-status complete

# Clean ALL jobs (asks for confirmation)
python cleanup.py --all
```

#### Manual Job Inspection

```bash
# List all jobs
ls -lh /workspace/jobs/

# View job metadata
cat /workspace/jobs/{job_id}/metadata.json | python -m json.tool

# Check job size
du -sh /workspace/jobs/{job_id}

# View all job sizes
du -sh /workspace/jobs/*
```

### Storage Management

#### Check Disk Usage

```bash
# Overall disk usage
df -h /workspace

# Directory sizes
du -sh /workspace/*

# Model cache size
du -sh /workspace/huggingface_cache

# Jobs directory size
du -sh /workspace/jobs

# Detailed breakdown
du -h --max-depth=1 /workspace | sort -h
```

#### Clean Model Cache (if needed)

```bash
# WARNING: This will require re-downloading the model (~40GB, 10-30 min)
rm -rf /workspace/huggingface_cache
mkdir -p /workspace/huggingface_cache

# Restart server to re-download
cd /workspace/qwen-image-editor/backend
./start.sh
```

### Restarting Services

#### Restart Backend

```bash
# If running in foreground: Ctrl+C, then
./start.sh

# If running in screen
screen -r qwen
# Ctrl+C to stop
./start.sh
```

#### Restart After Pod Restart

```bash
# After RunPod pod restart, everything outside /workspace is gone
# But /workspace persists!

# Just SSH in and start
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519
cd /workspace/qwen-image-editor/backend
./start.sh

# Model is already cached, so starts immediately
```

---

## Troubleshooting

### Backend Issues

#### Problem: Model not loading

**Symptoms:**
```
Error loading model: Out of memory
```

**Solutions:**
1. Check GPU memory:
   ```bash
   nvidia-smi
   # Free memory should be > 40GB
   ```

2. Kill other GPU processes:
   ```bash
   # List GPU processes
   nvidia-smi

   # Kill specific process
   kill -9 <PID>
   ```

3. Restart pod if GPU memory fragmented

#### Problem: Port 8000 not accessible externally

**Symptoms:**
- `curl http://localhost:8000/` works
- `curl https://...-8000.proxy.runpod.net/` fails

**Solutions:**
1. Check RunPod dashboard:
   - HTTP Services → Port 8000 → Status should be "Ready"

2. Verify server is listening on 0.0.0.0:
   ```bash
   netstat -tlnp | grep 8000
   # Should show: 0.0.0.0:8000
   ```

3. Check if RunPod proxy is up (rare issue):
   - Wait a few minutes
   - Restart pod if persistent

#### Problem: Dependencies installation fails

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement torch==2.2.0
```

**Solutions:**
1. Check Python version:
   ```bash
   python --version
   # Should be 3.10+
   ```

2. Update pip:
   ```bash
   pip install --upgrade pip
   ```

3. Install PyTorch manually:
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

#### Problem: CUDA not available

**Symptoms:**
```python
RuntimeError: CUDA out of memory
# or
RuntimeError: No CUDA GPUs are available
```

**Solutions:**
1. Verify GPU:
   ```bash
   nvidia-smi
   ```

2. Check PyTorch CUDA:
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. Reinstall PyTorch with CUDA:
   ```bash
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

### Frontend Issues

#### Problem: Cannot connect to backend

**Symptoms:**
- "Network Error" in browser console
- "Failed to start image editing"

**Solutions:**
1. Verify `VITE_API_URL` in `.env`:
   ```bash
   cat frontend/.env
   ```

2. Test backend directly:
   ```bash
   curl https://2ww93nrkflzjy2-644110bf-8000.proxy.runpod.net/
   ```

3. Check CORS (should be allow_origins=["*"])

4. Restart frontend:
   ```bash
   # Ctrl+C in terminal running npm run dev
   npm run dev
   ```

#### Problem: WebSocket connection fails

**Symptoms:**
- Progress not updating
- Console error: "WebSocket connection failed"

**Solutions:**
1. Verify URL protocol:
   - Should auto-convert `https://` → `wss://`
   - Check in browser Network tab

2. Test WebSocket manually:
   ```javascript
   const ws = new WebSocket('wss://your-pod-8000.proxy.runpod.net/ws/test-id')
   ws.onopen = () => console.log('Connected!')
   ```

3. Check backend WebSocket endpoint:
   ```bash
   # In backend logs, should see:
   # WebSocket connected for job {job_id}
   ```

#### Problem: Images not uploading

**Symptoms:**
- Upload button disabled
- "Invalid file type"

**Solutions:**
1. Check file type:
   - Must be image/png, image/jpeg, image/jpg

2. Check file size:
   - Backend has no hard limit, but large files may timeout
   - Recommended: < 10MB per image

3. Check browser console for errors

### Performance Issues

#### Problem: Editing too slow

**Expected times:**
- 20 steps: ~20 seconds
- 50 steps: ~45 seconds
- 100 steps: ~90 seconds

**If slower:**
1. Check GPU utilization:
   ```bash
   nvidia-smi
   # GPU util should be 90-100% during inference
   ```

2. Check if model is loaded:
   - First edit takes longer (loads model)
   - Subsequent edits should be faster

3. Reduce inference steps:
   - Use 20-30 steps for faster results

#### Problem: Out of VRAM

**Symptoms:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**
1. Check current VRAM:
   ```bash
   nvidia-smi
   # Model uses ~40GB, need 48GB total
   ```

2. Clear GPU cache:
   ```bash
   # Restart backend server
   ```

3. Use lower precision (if available):
   - Current: BF16 (~40GB)
   - Alternative: FP8 (~16GB, lower quality)

### Common Errors

#### Error: "Job not found"

**Cause**: Job was deleted or never created

**Solution**:
1. Check job ID is correct
2. Job may have been auto-cleaned (after download)
3. Create new job

#### Error: "Model loading failed"

**Cause**: First-time model download interrupted

**Solution**:
1. Check internet connection on RunPod
2. Check disk space: `df -h /workspace`
3. Delete partial download:
   ```bash
   rm -rf /workspace/huggingface_cache
   mkdir -p /workspace/huggingface_cache
   ```
4. Restart server to retry download

#### Error: "Invalid config"

**Cause**: JSON parsing error in config

**Solution**:
1. Check prompt is not empty
2. Check CFG scale is 1.0-10.0
3. Check inference steps is 10-100

---

## Technical Specifications

### Model Details

**Qwen-Image-Edit**
- **Parameters**: 20 billion
- **Architecture**: Built on Qwen2.5-VL
- **Precision**: BF16 (best quality, requires 40GB VRAM)
- **License**: Apache 2.0
- **Model Card**: https://huggingface.co/Qwen/Qwen-Image-Edit

**Capabilities:**
1. Semantic editing (style, lighting, composition)
2. Appearance editing (add/remove objects, modify attributes)
3. Text editing (bilingual: English, Chinese)

### Hardware Requirements

**Minimum (BF16):**
- GPU: 40GB VRAM (A40, A6000, A100)
- RAM: 16GB system RAM
- Storage: 50GB (40GB model + 10GB workspace)

**Your Setup (A40):**
- GPU: 48GB VRAM ✅
- RAM: 50GB ✅
- Storage: 50GB volume ✅

**Quantized Versions (if needed):**
- FP8: 16GB VRAM
- NF4: 16-20GB VRAM
- GGUF Q4: 8GB VRAM (lower quality)

### Performance Benchmarks

**On A40 GPU (BF16):**

| Steps | Time | Quality |
|-------|------|---------|
| 20 | ~20s | Good |
| 30 | ~30s | Better |
| 50 | ~45s | Best (recommended) |
| 75 | ~65s | Excellent |
| 100 | ~90s | Maximum |

**First run only:**
- Model load: ~2-3 minutes
- Model download: ~10-30 minutes (cached afterward)

### API Limits

**Request Size:**
- Max image size: No hard limit (tested up to 4096x4096)
- Recommended: < 2048x2048 for speed
- Max images: 2

**Timeout:**
- Frontend: 300 seconds (5 minutes)
- Backend: No timeout (async processing)

**Concurrent Jobs:**
- Sequential processing (one at a time)
- Queue-based system
- Prevents GPU OOM

---

## Development Notes

### Project Structure Explained

```
qwen-image-editor/
├── backend/
│   ├── main.py              # FastAPI app, routes, WebSocket
│   ├── image_editor.py      # Qwen model wrapper
│   ├── job_manager.py       # Job lifecycle, persistence
│   ├── models.py            # Pydantic validation models
│   ├── cleanup.py           # CLI utility for maintenance
│   ├── requirements.txt     # Python dependencies
│   ├── setup.sh            # One-time setup script
│   ├── start.sh            # Server startup script
│   └── .env.example        # Config template
│
└── frontend/
    ├── src/
    │   ├── App.jsx                    # Main orchestrator
    │   ├── main.jsx                   # Entry point
    │   ├── components/
    │   │   ├── ImageUpload.jsx        # Upload + preview
    │   │   ├── EditConfig.jsx         # Config form
    │   │   └── ProgressTracker.jsx    # Real-time progress
    │   └── utils/
    │       └── api.js                 # API client + WebSocket
    ├── package.json                   # Dependencies
    ├── vite.config.js                 # Vite config
    ├── tailwind.config.js             # Tailwind CSS
    └── .env                           # Backend URL
```

### Key Design Decisions

**1. Sequential Job Processing**
- Why: Prevents GPU OOM with multiple concurrent edits
- Trade-off: Jobs queued if multiple requests
- Implementation: asyncio.Queue in main.py

**2. Lazy Model Loading**
- Why: Faster server startup, memory efficient
- When: Loaded on first edit request only
- Cached: Stays in memory for subsequent requests

**3. WebSocket for Progress**
- Why: Real-time updates without polling
- Alternative: Could use SSE (Server-Sent Events)
- Implementation: FastAPI native WebSocket

**4. Job Persistence**
- Why: Survive page refreshes, pod restarts
- Mechanism: localStorage (frontend) + disk (backend)
- Cleanup: Automatic after download

**5. Multi-Image Support**
- Why: Qwen model supports image combinations
- Implementation: Side-by-side concatenation
- Use case: Before/after, comparisons, blending

### Adding New Features

**Example: Add image resolution limit**

Backend (`image_editor.py`):
```python
def _validate_image_size(self, image: Image.Image, max_size=2048):
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = tuple(int(dim * ratio) for dim in image.size)
        return image.resize(new_size, Image.Resampling.LANCZOS)
    return image
```

Frontend (`EditConfig.jsx`):
```javascript
const MAX_DIMENSION = 2048
// Add validation before upload
```

**Example: Add more model parameters**

1. Update `models.py`:
   ```python
   class EditConfig(BaseModel):
       seed: Optional[int] = None
   ```

2. Update `image_editor.py`:
   ```python
   def edit_image(..., seed=None):
       generator = torch.Generator().manual_seed(seed) if seed else None
   ```

3. Update `EditConfig.jsx`:
   ```javascript
   <input type="number" name="seed" />
   ```

### Testing Checklist

**Backend:**
- [ ] Health endpoint responds
- [ ] Model loads without errors
- [ ] Single image edit works
- [ ] Two image combine works
- [ ] Job persistence across server restart
- [ ] WebSocket broadcasts progress
- [ ] Download triggers cleanup
- [ ] GPU memory clears after edit

**Frontend:**
- [ ] Image upload works (1-2 images)
- [ ] Preview displays correctly
- [ ] Form validation works
- [ ] WebSocket connects
- [ ] Progress updates in real-time
- [ ] Download works
- [ ] Page refresh resumes job
- [ ] Error handling shows messages

---

## Quick Reference

### File Paths

```bash
# RunPod
/workspace/qwen-image-editor/backend/     # Backend code
/workspace/huggingface_cache/             # Model cache
/workspace/jobs/                          # Job storage

# Mac
~/coding_workshop/computer_utilities/qwen-image-editor/
```

### Commands

```bash
# RunPod - Start Backend
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519
cd /workspace/qwen-image-editor/backend
./start.sh

# Mac - Start Frontend
cd ~/coding_workshop/computer_utilities/qwen-image-editor/frontend
npm run dev

# Check GPU
nvidia-smi

# Cleanup
python cleanup.py --status
python cleanup.py --hours 1
```

### URLs

```
Frontend:  http://localhost:3000
Backend:   https://2ww93nrkflzjy2-644110bf-8000.proxy.runpod.net
Health:    https://2ww93nrkflzjy2-644110bf-8000.proxy.runpod.net/
```

### Default Configuration

```python
# Edit Configuration
prompt: str (required)
negative_prompt: str = ""
true_cfg_scale: float = 4.0
num_inference_steps: int = 50
```

---

## Support & Resources

### Documentation
- **Qwen Model**: https://huggingface.co/Qwen/Qwen-Image-Edit
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/
- **RunPod**: https://docs.runpod.io/

### Logs & Debugging

```bash
# Backend logs (if running with start.sh)
screen -r qwen

# Frontend logs
# Check browser console (F12)

# GPU logs
nvidia-smi dmon  # Real-time GPU monitoring
```

### Community
- Qwen GitHub: https://github.com/QwenLM/Qwen
- Hugging Face Forums: https://discuss.huggingface.co/

---

**Document Version**: 1.0
**Last Updated**: 2025-01-26
**Model Version**: Qwen-Image-Edit (20B)
**Compatible RunPod Template**: runpod-torch-v280
