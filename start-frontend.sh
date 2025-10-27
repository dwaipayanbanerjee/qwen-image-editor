#!/bin/bash

# Qwen Image Editor - Frontend Startup Script
# This script checks backend connectivity and starts the frontend

set -e

echo "========================================"
echo "  Qwen Image Editor - Starting Frontend"
echo "========================================"
echo ""

# Get the backend URL from .env
BACKEND_URL=$(grep VITE_API_URL frontend/.env | cut -d '=' -f2)
echo "Backend URL: $BACKEND_URL"
echo ""

# Test backend connectivity
echo "Testing backend connection..."
if curl -s --connect-timeout 5 "$BACKEND_URL/" > /dev/null 2>&1; then
    echo "✅ Backend is online and responding!"
else
    echo "❌ Backend is NOT responding!"
    echo ""
    echo "Please ensure:"
    echo "1. You're connected to RunPod via SSH"
    echo "2. Backend is running: cd /workspace/qwen-image-editor/backend && ./start.sh"
    echo "3. The backend URL in frontend/.env is correct"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to abort..."
fi

echo ""
echo "Starting frontend development server..."
echo "Frontend will be available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd frontend
npm run dev
