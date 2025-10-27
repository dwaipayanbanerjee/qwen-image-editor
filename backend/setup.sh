#!/bin/bash
# Setup script for Qwen Image Editor backend
# Run this once when setting up a new RunPod instance

set -e  # Exit on error

echo "=== Qwen Image Editor Backend Setup ==="
echo ""

# Check if we're in /workspace (RunPod requirement)
if [[ "$PWD" != /workspace/qwen-image-editor/backend* ]]; then
    echo "WARNING: You should run this from /workspace/qwen-image-editor/backend"
    echo "Current directory: $PWD"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create necessary directories
echo "Creating directory structure..."
mkdir -p /workspace/huggingface_cache
mkdir -p /workspace/jobs
mkdir -p logs

# Check Python version
echo "Checking Python version..."
python --version

# Check for CUDA
echo "Checking CUDA availability..."
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')" || echo "PyTorch not installed yet"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python -m venv venv
else
    echo ""
    echo "Virtual environment already exists, skipping creation"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install PyTorch with CUDA support first
echo ""
echo "Installing PyTorch with CUDA support..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install other requirements
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Verify CUDA after installation
echo ""
echo "Verifying CUDA installation..."
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env file. Please edit it with your configuration."
    else
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
else
    echo ""
    echo ".env file already exists, skipping"
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Verify your .env file configuration"
echo "2. Start the server with: ./start.sh"
echo ""
echo "Model will be downloaded on first run (~40GB)"
echo "Expected download time: 10-30 minutes depending on connection"
echo ""
