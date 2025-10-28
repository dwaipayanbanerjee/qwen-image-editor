# Qwen Image Editor

AI-powered image editing application using the Qwen-Image-Edit model (20B parameters) running **locally on Mac with Apple Silicon (MPS)**. Edit single images or combine two images with natural language prompts.

## 🚀 Quick Start (Mac Local Deployment)

### Prerequisites
- Mac with Apple Silicon (M1/M2/M3/M4)
- 64GB+ unified memory recommended
- ~70GB free disk space
- Python 3.9+ and Node.js 18+ installed

### Installation

**One-Time Setup (Run Once):**

```bash
# Navigate to project
cd ~/coding_workshop/computer_utilities/qwen-image-editor

# Run unified setup script
./setup.sh
```

The setup script will:
- ✅ Check system prerequisites (Python, Node.js, memory, disk space)
- ✅ Create data directories in `~/qwen-image-editor/`
- ✅ Set up backend Python virtual environment
- ✅ Install all Python dependencies
- ✅ Set up frontend npm dependencies
- ✅ Create configuration files
- ✅ Verify PyTorch MPS support

**Start the Application:**

```bash
# After setup completes, start with:
./start
```

That's it! The `./start` script:
- ✅ Kills any existing instances automatically
- ✅ Validates your setup
- ✅ Starts both backend (port 8000) and frontend (port 3000)
- ✅ Shows all logs in one terminal (color-coded)
- ✅ Cleans up everything when you press Ctrl+C

**First Run:** Model will download ~57.7GB (takes 10-30 min). Subsequent runs start in seconds.

## Architecture

- **Backend**: FastAPI server running locally on Apple Silicon with MPS
- **Frontend**: React + Vite + Tailwind CSS (localhost:3000)
- **Model**: Qwen-Image-Edit (20B params, BF16 precision)
- **Device**: MPS (Metal Performance Shaders) for Apple Silicon GPU acceleration
- **Communication**: REST API + WebSocket for real-time progress

## Features

- ✨ **Natural Language Editing**: Edit images using text prompts
- 🖼️ **Image Combining**: Merge two images side-by-side before editing
- 🎨 **Advanced Controls**: Guidance scale, inference steps, negative prompts
- ⚡ **Fast Processing**: ~30-60 seconds per edit on M2/M3 Mac
- 📊 **Real-time Progress**: WebSocket-based progress tracking
- 💾 **Persistent Storage**: All data stored in `~/qwen-image-editor/`
- 🍎 **Apple Silicon Optimized**: Native MPS support for M1/M2/M3/M4

## Project Structure

```
qwen-image-editor/
├── backend/                    # FastAPI backend
│   ├── main.py                 # Main API server
│   ├── image_editor.py         # Qwen model wrapper (MPS support)
│   ├── job_manager.py          # Job lifecycle management
│   ├── models.py               # Pydantic models
│   ├── cleanup.py              # Cleanup utility
│   ├── requirements.txt        # Python dependencies
│   ├── start.sh                # Server startup script
│   └── .env                    # Environment config
│
└── frontend/                   # React frontend
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
    └── .env                       # Backend URL (localhost:8000)
```

## Usage

### Basic Workflow

1. **Upload Images**: Upload 1-2 images
   - Single image: Direct editing
   - Two images: Combined side-by-side before editing
   - Optimal size: 512-4096px

2. **Configure Edit**: Enter your edit prompt
   - Example: "change the background to a sunset sky"
   - Example: "make the person wearing a red dress"
   - Example: "add snow to the scene"

3. **Advanced Settings** (optional):
   - **Guidance Scale**: 1.0-10.0 (default: 4.0)
     - Higher = stronger adherence to prompt
   - **Inference Steps**: 20-100 (default: 50)
     - More steps = better quality but slower

4. **Process**: Wait ~30-60 seconds for processing (M2/M3 Mac)

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

**Text Editing** (English/Chinese):
- "change the sign text to 'Welcome'"
- "remove all text from the image"

## API Endpoints

### REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check (shows device: mps/cuda/cpu) |
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

## Maintenance

### Cleanup Old Jobs

Jobs are automatically cleaned up after download. Manual cleanup:

```bash
cd backend
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

### Monitor System Resources

```bash
# Check MPS availability
python -c "import torch; print('MPS available:', torch.backends.mps.is_available())"

# Monitor memory usage
top -o MEM

# Check disk space
df -h ~
du -sh ~/qwen-image-editor
```

## Troubleshooting

### Model Issues

**Model not loading:**
- Check available memory: System Settings → General → About → Memory
- Ensure 64GB+ unified memory available
- Verify `~/qwen-image-editor/huggingface_cache` exists
- Check MPS: `python -c "import torch; print(torch.backends.mps.is_available())"`

**MPS not available:**
- Verify you're on Apple Silicon Mac (not Intel)
- Check macOS version (requires macOS 12.3+)
- Ensure PyTorch version supports MPS (2.0+)
- Will fallback to CPU if MPS unavailable (much slower)

### Server Issues

**Port 8000 not accessible:**
- Check server is running: `curl http://localhost:8000/`
- Verify no firewall blocking localhost
- Check for other processes using port: `lsof -i :8000`

**Frontend can't connect:**
- Verify `VITE_API_URL=http://localhost:8000` in `frontend/.env`
- Test backend directly in browser: `http://localhost:8000/`
- Check both services running: `ps aux | grep -E "(uvicorn|vite)"`

### Performance Issues

**Out of memory:**
- Restart Mac to clear memory
- Close other memory-intensive apps
- Ensure you have 64GB+ unified memory
- Model requires ~40GB in memory during inference

**Slow processing:**
- Normal: 30-60s for 50 steps on M2/M3
- Check Activity Monitor → GPU tab for Metal usage
- First run slower due to model download
- Reduce inference steps for faster results (lower quality)

**WebSocket connection fails:**
- Check browser console for errors
- Verify backend is running on localhost:8000
- Try HTTP polling fallback (automatic)

## Technical Details

### Model Specifications

- **Name**: Qwen-Image-Edit
- **Size**: 20B parameters
- **Precision**: BF16 on MPS/CUDA, FP32 on CPU
- **Disk Cache**: ~57.7GB (downloaded once)
- **Memory**: ~40GB during inference
- **Architecture**: Built on Qwen2.5-VL
- **License**: Apache 2.0

### System Requirements

- **Mac**: Apple Silicon (M1/M2/M3/M4)
- **Memory**: 64GB+ unified memory recommended
- **Disk**: 70GB free space minimum
- **OS**: macOS 12.3+ (for MPS support)
- **Python**: 3.9+
- **Node.js**: 18+

### Processing Time (M2/M3 Mac)

- **20 steps** (faster): ~20 seconds
- **50 steps** (default): ~45 seconds
- **100 steps** (best quality): ~90 seconds

*Tested on M3 Ultra with 64GB memory: ~42 seconds for 50 steps*

### Storage Layout

```
~/qwen-image-editor/
├── huggingface_cache/          # ~57.7GB model cache
└── jobs/{job_id}/              # 2-5MB per job
    ├── input_1.jpg
    ├── input_2.jpg (optional)
    ├── output.jpg
    └── metadata.json
```

## Development

### Running Services Separately

**Backend only:**
```bash
cd backend
source venv/bin/activate
python main.py
```

**Frontend only:**
```bash
cd frontend
npm run dev
```

### Building for Production

```bash
cd frontend
npm run build      # Production build
npm run preview    # Preview production build
```

### Configuration Files

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

## Resources

- **Qwen-Image-Edit Model**: https://huggingface.co/Qwen/Qwen-Image-Edit
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **PyTorch MPS**: https://pytorch.org/docs/stable/notes/mps.html

## License

Apache 2.0 (same as Qwen-Image-Edit model)

## Acknowledgments

- **Qwen Team** for the Qwen-Image-Edit model
- **Ivan Fioravanti** for qwen-image-mps implementation reference
- **Apple** for Metal Performance Shaders (MPS)
