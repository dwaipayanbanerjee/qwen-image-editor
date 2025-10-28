#!/bin/bash
# Start script for Qwen Image Editor backend server
# Note: Use the root ./start script to start both backend and frontend
# This script is for backend-only startup if needed

set -e  # Exit on error

echo "=== Starting Qwen Image Editor Backend ==="
echo ""

# Detect workspace root (parent of backend directory)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if virtual environment exists (.venv or venv)
if [ -d "$SCRIPT_DIR/.venv" ]; then
    VENV_DIR="$SCRIPT_DIR/.venv"
elif [ -d "$SCRIPT_DIR/venv" ]; then
    VENV_DIR="$SCRIPT_DIR/venv"
else
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "WARNING: .env file not found!"
    echo "Creating default .env file..."
    cat > "$SCRIPT_DIR/.env" << EOF
# Hugging Face cache (persistent storage)
HF_HOME=$WORKSPACE_ROOT/huggingface_cache
TRANSFORMERS_CACHE=$WORKSPACE_ROOT/huggingface_cache
HF_DATASETS_CACHE=$WORKSPACE_ROOT/huggingface_cache

# Jobs directory
JOBS_DIR=$WORKSPACE_ROOT/jobs

# Server configuration
HOST=0.0.0.0
PORT=8000

# PyTorch GPU optimization
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
EOF
fi

# Load environment variables safely
echo "Loading environment variables..."
if [ -f ".env" ]; then
    # Read .env file line by line, safely handling spaces and special characters
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        if [[ -z "$key" || "$key" =~ ^#.* ]]; then
            continue
        fi
        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        # Only export valid variable names
        if [[ "$key" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
            export "$key=$value"
        fi
    done < .env
fi

# Change to script directory
cd "$SCRIPT_DIR"

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Verify directories exist
echo "Verifying directory structure..."
mkdir -p "${JOBS_DIR:-$WORKSPACE_ROOT/jobs}"
mkdir -p "${HF_HOME:-$WORKSPACE_ROOT/huggingface_cache}"

# Show configuration
echo ""
echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Jobs Directory: $JOBS_DIR"
echo "  HuggingFace Cache: $HF_HOME"
echo ""

# Check GPU/MPS availability
echo "Device Information:"
python -c "import torch; print(f'MPS (Apple Silicon) available: {torch.backends.mps.is_available()}') if hasattr(torch.backends, 'mps') else None; print(f'CUDA available: {torch.cuda.is_available()}')" 2>/dev/null || echo "PyTorch not available yet"
echo ""

# Start the server
echo "Starting FastAPI server..."
echo "Press Ctrl+C to stop"
echo ""

python main.py
