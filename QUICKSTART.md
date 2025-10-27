# Quick Start Guide

## Why Two Servers?

This application has a **split architecture** for a good reason:

- **Backend (RunPod):** Requires A40 GPU with 48GB VRAM to run the 20B parameter Qwen model
- **Frontend (Your Mac):** Runs locally for fast development and easy access

Your Mac doesn't have the GPU hardware needed for the backend, so it **must** run on RunPod.

---

## Starting the Application

### Step 1: Start Backend (RunPod) - One Time Setup

Open a terminal and SSH into RunPod (keep this terminal open):

```bash
ssh root@69.30.85.14 -p 22101 -i ~/.ssh/id_ed25519
cd /workspace/qwen-image-editor/backend
./start.sh
```

**Tip:** Use `screen` to keep it running in background:
```bash
screen -S qwen
./start.sh
# Press Ctrl+A, then D to detach
```

### Step 2: Start Frontend (Your Mac) - Every Time

From this project directory:

```bash
./start-frontend.sh
```

This script will:
- Check if backend is online
- Start the frontend dev server
- Open http://localhost:3000 in your browser

---

## Quick Reference

### Backend is Running?
```bash
curl https://YOUR-POD-ID-8000.proxy.runpod.net/
```

Should return: `{"status":"online",...}`

### Update Backend URL?

Edit `frontend/.env`:
```bash
VITE_API_URL=https://YOUR-NEW-POD-URL-8000.proxy.runpod.net
```

### Stop Everything?

**Frontend:** Press `Ctrl+C` in the terminal running the frontend

**Backend:**
```bash
# In RunPod SSH terminal
Ctrl+C
```

---

## Troubleshooting

**"Backend is NOT responding"**
1. Check RunPod dashboard - is the pod running?
2. Get the current proxy URL from "HTTP Services" section
3. Update `frontend/.env` with the new URL
4. SSH into RunPod and start backend: `./start.sh`

**"502 Error"**
- Backend server stopped or crashed
- RunPod pod restarted (URL changed)
- Check backend logs in RunPod terminal

**"Port 3000 already in use"**
```bash
# Kill existing process
lsof -ti:3000 | xargs kill -9
# Or use a different port
PORT=3002 npm run dev
```

---

## Daily Workflow

1. **Morning:** SSH into RunPod, start backend once
2. **Work:** Use `./start-frontend.sh` on your Mac whenever you want to use the app
3. **Evening:** Stop frontend (Ctrl+C), optionally stop backend

The backend can stay running on RunPod 24/7 if you want!
