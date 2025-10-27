#!/bin/bash
# Full-stack deployment script using tmux
# Starts both backend and frontend on the same server
# Recommended for RunPod deployment

set -e

echo "========================================"
echo "  Qwen Image Editor - Full Stack Start"
echo "  Using tmux for session management"
echo "========================================"
echo ""

# Check if tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "ERROR: tmux is not installed!"
    echo "Install with: apt-get update && apt-get install -y tmux"
    exit 1
fi

# Check if session already exists
if tmux has-session -t qwen-image-editor 2>/dev/null; then
    echo "Existing tmux session found!"
    echo "To attach: tmux attach -t qwen-image-editor"
    echo "To kill old session and restart: tmux kill-session -t qwen-image-editor && ./start-all-tmux.sh"
    exit 1
fi

# Create frontend .env for same-server deployment
echo "Configuring frontend for same-server deployment..."
cat > frontend/.env << 'EOF'
# Same-server deployment: Frontend connects to backend on localhost
VITE_API_URL=http://localhost:8000
EOF

# Verify backend setup
if [ ! -f "backend/venv/bin/activate" ]; then
    echo "ERROR: Backend not set up!"
    echo "Run: cd backend && ./setup.sh"
    exit 1
fi

# Verify frontend setup
if [ ! -d "frontend/node_modules" ]; then
    echo "ERROR: Frontend not set up!"
    echo "Run: cd frontend && npm install"
    exit 1
fi

echo "Starting new tmux session: qwen-image-editor"
echo ""

# Create tmux session with backend
tmux new-session -d -s qwen-image-editor -n backend "cd backend && ./start.sh"

# Create new window for frontend
tmux new-window -t qwen-image-editor -n frontend "cd frontend && npm run dev"

# Select backend window
tmux select-window -t qwen-image-editor:backend

echo "✅ Services started in tmux session!"
echo ""
echo "Session layout:"
echo "  - Window 0 (backend):  Backend API on port 8000"
echo "  - Window 1 (frontend): Frontend UI on port 3000"
echo ""
echo "Commands:"
echo "  Attach to session:  tmux attach -t qwen-image-editor"
echo "  Switch windows:     Ctrl+B, then 0 or 1"
echo "  Detach from tmux:   Ctrl+B, then D"
echo "  Kill session:       tmux kill-session -t qwen-image-editor"
echo ""
echo "Access points:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo ""
echo "For external access (RunPod), expose ports 8000 and 3000 in HTTP Services"
echo "  Frontend: https://<pod-id>-3000.proxy.runpod.net"
echo "  Backend:  https://<pod-id>-8000.proxy.runpod.net"
echo ""
