# Quick Start Guide

## First Time Setup

```bash
# 1. Clone the repo
cd /workspace
git clone https://github.com/<YOUR_USERNAME>/qwen-image-editor.git
cd qwen-image-editor

# 2. Set up backend (one time only)
cd backend
./setup.sh  # Downloads model (~40GB), takes 10-30 min
cd ..

# 3. Start everything
./start
```

Done! Access at:
- Frontend: `https://<pod-id>-3000.proxy.runpod.net`
- Backend: `https://<pod-id>-8000.proxy.runpod.net`

---

## Every Subsequent Start

```bash
cd /workspace/qwen-image-editor
./start
```

That's it! The script:
- ✅ Kills any old instances
- ✅ Validates setup
- ✅ Starts both services
- ✅ Shows all logs (color-coded)

Press **Ctrl+C** to stop everything.

---

## Updating Code

```bash
# On your local machine
git add .
git commit -m "Your changes"
git push origin main

# On RunPod
cd /workspace/qwen-image-editor
git pull
./start  # Automatically restarts with new code
```

---

## Common Tasks

### View GPU Usage
```bash
nvidia-smi
# or watch it live
watch -n 1 nvidia-smi
```

### Clean Up Old Jobs
```bash
cd backend
source venv/bin/activate
python cleanup.py --all  # Removes all jobs
```

### View Logs
All logs appear in the terminal when you run `./start`

---

## Troubleshooting

### "Port already in use"
The `./start` script should auto-kill old processes. If it doesn't:
```bash
# Manual cleanup
pkill -f uvicorn
pkill -f npm
./start
```

### "Backend not responding"
Check the logs in the terminal where `./start` is running. Look for errors in blue `[BACKEND]` lines.

### "Frontend can't connect"
Check `frontend/.env`:
```bash
# For RunPod full-stack
VITE_API_URL=http://localhost:8000

# For split deployment
VITE_API_URL=https://<pod-id>-8000.proxy.runpod.net
```

### "Model loading stuck"
First-time model download takes 10-30 minutes. You'll see:
```
[BACKEND] Downloading model files... 45%
```

Just wait - it's working!

---

## File Structure

```
qwen-image-editor/
├── start                    # ← RUN THIS
├── start-foreground.py      # (called by ./start)
├── backend/
│   ├── setup.sh            # First-time setup
│   └── start.sh            # Internal use
└── frontend/
    └── .env                # API URL config
```

---

## That's It!

Remember:
1. **First time**: `cd backend && ./setup.sh`
2. **Every time**: `./start`
3. **Stop**: Press **Ctrl+C**

Simple as that! 🚀
