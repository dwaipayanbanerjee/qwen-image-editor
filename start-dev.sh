#!/bin/bash
set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Qwen Image Editor (Development Mode)${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Change to script directory
cd "$(dirname "$0")"

# Cleanup function to kill all child processes
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    wait
    echo -e "${GREEN}All services stopped${NC}"
    exit 0
}

# Trap Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM

# Function to prefix output
prefix_output() {
    local prefix="$1"
    local color="$2"
    while IFS= read -r line; do
        echo -e "${color}[${prefix}]${NC} $line"
    done
}

# Start backend
echo -e "${BLUE}Starting backend (port 8000)...${NC}"
(cd backend && source venv/bin/activate && python main.py 2>&1 | prefix_output "BACKEND" "$BLUE") &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend (port 3000)...${NC}"
(cd frontend && npm run dev 2>&1 | prefix_output "FRONTEND" "$GREEN") &
FRONTEND_PID=$!

echo -e "\n${GREEN}✓ Services started${NC}"
echo -e "${BLUE}  Backend:  http://localhost:8000${NC}"
echo -e "${GREEN}  Frontend: http://localhost:3000${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for any process to exit
wait -n

# If one exits, kill the other
cleanup
