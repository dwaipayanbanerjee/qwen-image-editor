#!/bin/bash
# Start script for Qwen Image Editor backend server
# Activates venv and starts the FastAPI server

set -e  # Exit on error

echo "=== Starting Qwen Image Editor Backend ==="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Creating default .env file..."
    cat > .env << EOF
# Hugging Face cache (persistent on RunPod)
HF_HOME=/workspace/huggingface_cache
TRANSFORMERS_CACHE=/workspace/huggingface_cache
HF_DATASETS_CACHE=/workspace/huggingface_cache

# Jobs directory
JOBS_DIR=/workspace/jobs

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

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Verify directories exist
echo "Verifying directory structure..."
mkdir -p $JOBS_DIR
mkdir -p $HF_HOME

# Show configuration
echo ""
echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Jobs Directory: $JOBS_DIR"
echo "  HuggingFace Cache: $HF_HOME"
echo ""

# Check GPU
echo "GPU Information:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader || echo "nvidia-smi not available"
echo ""

# Start the server
echo "Starting FastAPI server..."
echo "Press Ctrl+C to stop"
echo ""

python main.py
