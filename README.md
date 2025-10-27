# Qwen Image Editor

AI-powered image editing application using the Qwen-Image-Edit model (20B parameters). Edit single images or combine two images with natural language prompts.

## Architecture

- **Backend**: FastAPI server running on RunPod A40 GPU (48GB VRAM)
- **Frontend**: React + Vite + Tailwind CSS (runs locally on your Mac)
- **Model**: Qwen-Image-Edit (20B params, BF16 precision)
- **Communication**: REST API + WebSocket for real-time progress

## Features

- ✨ **Natural Language Editing**: Edit images using text prompts
- 🖼️ **Image Combining**: Merge two images side-by-side before editing
- 🎨 **Advanced Controls**: Guidance scale, inference steps, negative prompts
- ⚡ **Fast Processing**: ~30-60 seconds per edit on A40 GPU
- 📊 **Real-time Progress**: WebSocket-based progress tracking
- 💾 **Persistent Storage**: All data stored in `/workspace` (survives pod restarts)

## Project Structure

```
qwen-image-editor/
├── backend/                    # FastAPI backend (deploy to RunPod)
│   ├── main.py                 # Main API server
│   ├── image_editor.py         # Qwen model wrapper
│   ├── job_manager.py          # Job lifecycle management
│   ├── models.py               # Pydantic models
│   ├── cleanup.py              # Cleanup utility
│   ├── requirements.txt        # Python dependencies
│   ├── setup.sh                # First-time setup script
│   ├── start.sh                # Server startup script
│   └── .env.example            # Environment config template
│
└── frontend/                   # React frontend (runs locally)
    ├── src/
    │   ├── components/
    │   │   ├── ImageUpload.jsx    # Image upload (1-2 images)
    │   │   ├── EditConfig.jsx     # Edit configuration
    │   │   └── ProgressTracker.jsx # Real-time progress
    │   ├── utils/
    │   │   └── api.js             # API client
    │   ├── App.jsx                # Main app orchestrator
    │   └── main.jsx               # Entry point
    ├── package.json
    └── .env                       # Backend URL configuration
```

---

## Setup Instructions

### Part 1: RunPod Backend Setup

#### Step 1: SSH into RunPod

```bash
# Using proxied SSH
ssh 2ww93nrkflzjy2-644110bf@ssh.runpod.io -i ~/.ssh/id_ed25519

# OR using direct TCP
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519
```

#### Step 2: Create Workspace Directory

```bash
cd /workspace
mkdir -p qwen-image-editor/backend
cd qwen-image-editor/backend
```

#### Step 3: Copy Backend Files

From your local Mac, copy the backend files to RunPod:

```bash
# On your local Mac
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor

# Copy backend files to RunPod (adjust SSH command as needed)
scp -i ~/.ssh/id_ed25519 -r backend/* root@69.30.85.14:/workspace/qwen-image-editor/backend/
```

#### Step 4: Run Setup Script

Back on the RunPod server:

```bash
cd /workspace/qwen-image-editor/backend
chmod +x setup.sh start.sh
./setup.sh
```

This will:
- Create Python virtual environment
- Install all dependencies (~5-10 minutes)
- Set up directory structure
- Create `.env` file

#### Step 5: Configure Environment

Edit `.env` if needed (default values should work):

```bash
nano .env
```

Default configuration:
```bash
HF_HOME=/workspace/huggingface_cache
TRANSFORMERS_CACHE=/workspace/huggingface_cache
HF_DATASETS_CACHE=/workspace/huggingface_cache
JOBS_DIR=/workspace/jobs
HOST=0.0.0.0
PORT=8002
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

#### Step 6: Start Backend Server

```bash
./start.sh
```

**On first run**: The model will be downloaded (~40GB, takes 10-30 minutes depending on connection speed).

The server will start on port 8002. RunPod will expose this via port 8002 on the proxy URL.

#### Step 7: Verify Backend

In another terminal, test the health endpoint:

```bash
# From RunPod server
curl http://localhost:8002/

# Expected response:
# {"status": "online", "message": "Qwen Image Editor API is running", ...}
```

---

### Part 2: Local Frontend Setup

#### Step 1: Install Dependencies

```bash
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor/frontend
npm install
```

#### Step 2: Configure Backend URL

Edit `frontend/.env`:

```bash
# Replace with your RunPod URL once backend is running
VITE_API_URL=https://<your-pod-id>-8002.proxy.runpod.net

# For your current pod, it should look like:
# VITE_API_URL=https://2ww93nrkflzjy2-644110bf-8002.proxy.runpod.net
```

To find your exact URL:
1. Go to RunPod dashboard
2. Click on your pod
3. Look for "HTTP Services" section
4. Port 8002 should show the proxy URL

#### Step 3: Start Frontend

```bash
npm run dev
```

The app will open at `http://localhost:3001`

---

## Usage

### Basic Workflow

1. **Upload Images**: Upload 1-2 images
   - Single image: Direct editing
   - Two images: Combined side-by-side before editing

2. **Configure Edit**: Enter your edit prompt
   - Example: "change the background to a sunset sky"
   - Example: "make the person wearing a red dress"
   - Example: "add snow to the scene"

3. **Advanced Settings** (optional):
   - **Guidance Scale**: 1.0-10.0 (default: 4.0)
     - Higher = stronger adherence to prompt
   - **Inference Steps**: 20-100 (default: 50)
     - More steps = better quality but slower

4. **Process**: Wait ~30-60 seconds for processing

5. **Download**: Download your edited image

### Example Prompts

**Semantic Editing** (high-level changes):
- "change the style to watercolor painting"
- "make it look like a sunny day"
- "rotate the object 90 degrees"

**Appearance Editing** (precise changes):
- "remove the person in the background"
- "change the car color to red"
- "add a hat to the person"

**Text Editing**:
- "change the sign text to 'Welcome'"
- "remove all text from the image"

---

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/api/edit` | Create editing job |
| GET | `/api/jobs/{job_id}/status` | Get job status |
| GET | `/api/jobs/{job_id}/download` | Download result |
| DELETE | `/api/jobs/{job_id}` | Cancel/delete job |
| POST | `/api/cleanup` | Cleanup old jobs |

### WebSocket

- **Endpoint**: `/ws/{job_id}`
- **Purpose**: Real-time progress updates
- **Message Format**:
```json
{
  "status": "processing",
  "progress": {
    "stage": "editing",
    "message": "Applying edits...",
    "progress": 50
  },
  "error": null
}
```

---

## Maintenance

### Cleanup Old Jobs

Jobs are automatically cleaned up after download. Manual cleanup:

```bash
# On RunPod server
cd /workspace/qwen-image-editor/backend
source venv/bin/activate

# Show disk usage
python cleanup.py --status

# List all jobs
python cleanup.py --list

# Clean jobs older than 1 hour
python cleanup.py --hours 1

# Clean specific job
python cleanup.py --job <job_id>

# Clean all jobs (with confirmation)
python cleanup.py --all
```

### Monitor GPU Usage

```bash
nvidia-smi
watch -n 1 nvidia-smi  # Live monitoring
```

### View Server Logs

```bash
# If running with start.sh, logs are in stdout
# For background operation, use screen or tmux:

screen -S qwen
./start.sh
# Press Ctrl+A, then D to detach

# Reattach later:
screen -r qwen
```

---

## Troubleshooting

### Backend Issues

**Model not loading:**
- Check VRAM: `nvidia-smi`
- Ensure A40 with 48GB VRAM
- Check HuggingFace cache: `ls -lh /workspace/huggingface_cache`

**Port 8002 not accessible:**
- Verify server is running: `curl http://localhost:8002/`
- Check RunPod dashboard: Ensure port 8002 is exposed
- Check firewall/security settings

**Out of memory:**
- Model requires ~40GB VRAM (BF16)
- Check if other processes are using GPU
- Restart pod if memory is fragmented

### Frontend Issues

**Cannot connect to backend:**
- Verify `VITE_API_URL` in `frontend/.env`
- Check backend health: Visit the URL in browser
- Check CORS settings in `backend/main.py`

**WebSocket connection fails:**
- Ensure URL protocol is `wss://` (not `ws://`)
- Check browser console for errors
- Verify backend WebSocket endpoint works

### Performance Issues

**Slow processing:**
- Normal: 30-60 seconds for 50 steps
- Check GPU utilization: `nvidia-smi`
- Reduce `num_inference_steps` for faster results

---

## Technical Details

### Model Specifications

- **Name**: Qwen-Image-Edit
- **Size**: 20B parameters
- **Precision**: BF16 (requires 40GB VRAM)
- **Architecture**: Built on Qwen2.5-VL
- **License**: Apache 2.0

### Storage Requirements

- **Model cache**: ~40GB (downloaded once)
- **Per job**: 2-5MB (input + output images)
- **Recommended volume**: 50GB minimum

### Processing Time

- **50 steps** (default): ~45 seconds
- **20 steps** (faster): ~20 seconds
- **100 steps** (best quality): ~90 seconds

---

## Development

### Running Backend Locally (for testing)

If you have a local GPU with 40GB+ VRAM:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Edit .env to use local paths
export PORT=8002
python main.py
```

### Building Frontend

```bash
cd frontend
npm run build      # Production build
npm run preview    # Preview production build
```

---

## Configuration Files

### Backend `.env`

```bash
HF_HOME=/workspace/huggingface_cache          # Model cache
TRANSFORMERS_CACHE=/workspace/huggingface_cache
HF_DATASETS_CACHE=/workspace/huggingface_cache
JOBS_DIR=/workspace/jobs                      # Job storage
HOST=0.0.0.0                                  # Bind to all interfaces
PORT=8002                                     # Internal port
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True  # GPU memory optimization
```

### Frontend `.env`

```bash
VITE_API_URL=https://<your-pod-id>-8002.proxy.runpod.net
```

---

## Resources

- **Qwen-Image-Edit**: https://huggingface.co/Qwen/Qwen-Image-Edit
- **RunPod**: https://runpod.io/
- **FastAPI**: https://fastapi.tiangolo.com/
- **React**: https://react.dev/

---

## License

Apache 2.0 (same as Qwen-Image-Edit model)

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review backend logs
3. Check browser console for frontend errors
4. Verify all prerequisites are met
