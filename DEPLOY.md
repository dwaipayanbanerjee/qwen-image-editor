# Quick Deployment Guide

## Full-Stack Deployment on RunPod (Recommended)

This guide shows how to deploy both backend and frontend on the same RunPod server using git.

### Prerequisites

- RunPod A40 GPU instance running
- SSH access configured
- GitHub repository access

### Step-by-Step Deployment

#### 1. Push Latest Changes (Local Machine)

```bash
cd /Users/dwaipayanbanerjee/coding_workshop/computer_utilities/qwen-image-editor
git add -A
git commit -m "Your commit message"
git push origin main
```

#### 2. SSH into RunPod

```bash
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519
```

#### 3. Clone or Update Repository

**First time (clone):**
```bash
cd /workspace
git clone https://github.com/dwaipayanbanerjee/qwen-image-editor.git
cd qwen-image-editor
```

**Subsequent updates (pull):**
```bash
cd /workspace/qwen-image-editor
git pull origin main
```

#### 4. Initial Setup (First Time Only)

**Backend setup (~10-30 minutes):**
```bash
cd /workspace/qwen-image-editor/backend
./setup.sh
```

This will:
- Create Python virtual environment
- Install PyTorch with CUDA support
- Install dependencies
- Download Qwen-Image-Edit model (~40GB)

**Frontend setup (~2-5 minutes):**
```bash
cd /workspace/qwen-image-editor/frontend
npm install
```

#### 5. Start Both Services

```bash
cd /workspace/qwen-image-editor

# Option A: Using tmux (recommended for session management)
./start-all-tmux.sh

# Option B: Using background processes (simpler)
./start-all.sh
```

#### 6. Configure RunPod Port Exposure

In RunPod dashboard:
1. Go to your pod → **HTTP Services**
2. Ensure ports **8000** and **3000** are exposed
3. Note the proxy URLs:
   - Frontend: `https://<pod-id>-3000.proxy.runpod.net`
   - Backend: `https://<pod-id>-8000.proxy.runpod.net`

#### 7. Access Your Application

Open the frontend URL in your browser:
```
https://<pod-id>-3000.proxy.runpod.net
```

## Managing Services

### Using tmux (if started with start-all-tmux.sh)

**Attach to session:**
```bash
tmux attach -t qwen-image-editor
```

**Switch between windows:**
- Press `Ctrl+B`, then `0` for backend
- Press `Ctrl+B`, then `1` for frontend

**Detach from session:**
- Press `Ctrl+B`, then `D`

**Kill session:**
```bash
tmux kill-session -t qwen-image-editor
```

### Using background processes (if started with start-all.sh)

**View logs:**
```bash
tail -f logs/backend.log
tail -f logs/frontend.log
```

**Stop services:**
```bash
# Kill by PID (saved in .running_services)
source .running_services
kill $BACKEND_PID $FRONTEND_PID

# Or kill by process name
pkill -f 'python main.py'
pkill -f 'vite'
```

## Updating the Application

Whenever you make changes:

```bash
# 1. Local: Commit and push
git add -A
git commit -m "Description of changes"
git push origin main

# 2. RunPod: Pull and restart
cd /workspace/qwen-image-editor
git pull origin main

# 3. Restart services
tmux kill-session -t qwen-image-editor  # If using tmux
./start-all-tmux.sh

# Or for background processes
source .running_services && kill $BACKEND_PID $FRONTEND_PID
./start-all.sh
```

## Troubleshooting

**Check if services are running:**
```bash
# Check processes
ps aux | grep python
ps aux | grep vite

# Check ports
netstat -tlnp | grep 8000
netstat -tlnp | grep 3000

# Test backend health
curl http://localhost:8000/

# Check GPU
nvidia-smi
```

**Services won't start:**
- Check if ports are already in use: `lsof -ti:8000 | xargs kill -9`
- Check GPU memory: `nvidia-smi`
- Check logs: `tail -f logs/*.log`

**Frontend can't connect to backend:**
- Verify backend is running: `curl http://localhost:8000/`
- Check `frontend/.env` contains: `VITE_API_URL=http://localhost:8000`
- Restart frontend after .env changes

**Model download fails:**
- Check disk space: `df -h /workspace`
- Check internet connection
- Manually clear cache: `rm -rf /workspace/huggingface_cache/*`

## Quick Command Reference

```bash
# SSH to RunPod
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519

# Update and restart
cd /workspace/qwen-image-editor && git pull && ./start-all-tmux.sh

# View tmux session
tmux attach -t qwen-image-editor

# Check GPU
watch -n 1 nvidia-smi

# Clean old jobs
cd backend && source venv/bin/activate && python cleanup.py --hours 1
```
