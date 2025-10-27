#!/bin/bash
# Full-stack deployment script using background processes
# Starts both backend and frontend on the same server
# Alternative to tmux for simpler deployment

set -e

echo "========================================"
echo "  Qwen Image Editor - Full Stack Start"
echo "  Using background processes"
echo "========================================"
echo ""

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

# Create logs directory
mkdir -p logs

# Check if services are already running
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "ERROR: Port 8000 is already in use (Backend)"
    echo "Stop the service with: lsof -ti:8000 | xargs kill -9"
    exit 1
fi

if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "ERROR: Port 3000 is already in use (Frontend)"
    echo "Stop the service with: lsof -ti:3000 | xargs kill -9"
    exit 1
fi

echo "Starting backend on port 8000..."
cd backend
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
nohup python main.py > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to be ready..."
sleep 5
if ! curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "WARNING: Backend might not be ready yet, check logs/backend.log"
else
    echo "✅ Backend is online!"
fi

echo ""
echo "Starting frontend on port 3000..."
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend PID: $FRONTEND_PID"

# Save PIDs for easy stopping
cat > .running_services << EOF
BACKEND_PID=$BACKEND_PID
FRONTEND_PID=$FRONTEND_PID
EOF

echo ""
echo "✅ Services started!"
echo ""
echo "Access points:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo ""
echo "For external access (RunPod), expose ports 8000 and 3000 in HTTP Services"
echo "  Frontend: https://<pod-id>-3000.proxy.runpod.net"
echo "  Backend:  https://<pod-id>-8000.proxy.runpod.net"
echo ""
echo "Logs:"
echo "  Backend:  tail -f logs/backend.log"
echo "  Frontend: tail -f logs/frontend.log"
echo ""
echo "To stop services:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  Or use: pkill -f 'python main.py' && pkill -f 'vite'"
echo ""
