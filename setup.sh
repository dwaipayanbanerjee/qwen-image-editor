#!/bin/bash
# Qwen Image Editor - Unified First-Time Setup Script
# For Mac with Apple Silicon (MPS)
#
# This script:
# - Checks system prerequisites
# - Sets up backend Python environment
# - Sets up frontend Node.js environment
# - Creates necessary directories
# - Configures environment files
#
# Usage: ./setup.sh

set -e  # Exit on error

# ANSI color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'  # No Color
BOLD='\033[1m'

# Print colored messages
print_header() {
    echo -e "\n${CYAN}${BOLD}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
DATA_DIR="$HOME/qwen-image-editor"

# Print banner
echo -e "\n${CYAN}${BOLD}"
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║           Qwen Image Editor - First-Time Setup                    ║"
echo "║           Mac with Apple Silicon (MPS)                            ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Step 1: Check System Prerequisites
print_header "Step 1: Checking System Prerequisites"

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_warning "Not running on macOS. This script is optimized for Mac."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Apple Silicon
if [[ "$OSTYPE" == "darwin"* ]]; then
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        print_success "Running on Apple Silicon ($ARCH)"
    elif [[ "$ARCH" == "x86_64" ]]; then
        print_warning "Running on Intel Mac - MPS acceleration not available"
        print_info "Model will use CPU (much slower)"
    fi
fi

# Check available memory
if [[ "$OSTYPE" == "darwin"* ]]; then
    TOTAL_MEM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
    print_info "Total memory: ${TOTAL_MEM_GB}GB"

    if [[ $TOTAL_MEM_GB -lt 64 ]]; then
        print_warning "Recommended memory: 64GB+. You have ${TOTAL_MEM_GB}GB"
        print_info "Model may run slower or fail with insufficient memory"
    else
        print_success "Memory check passed (${TOTAL_MEM_GB}GB)"
    fi
fi

# Check disk space
if [[ "$OSTYPE" == "darwin"* ]]; then
    AVAILABLE_GB=$(df -g "$HOME" | awk 'NR==2 {print $4}')
    print_info "Available disk space: ${AVAILABLE_GB}GB"

    if [[ $AVAILABLE_GB -lt 70 ]]; then
        print_error "Insufficient disk space! Need at least 70GB free."
        print_info "Model cache requires ~57.7GB + working space"
        exit 1
    else
        print_success "Disk space check passed (${AVAILABLE_GB}GB available)"
    fi
fi

# Check Python
print_info "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [[ $PYTHON_MAJOR -ge 3 ]] && [[ $PYTHON_MINOR -ge 9 ]]; then
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3.9+ required. Found: $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 not found!"
    print_info "Install via: brew install python@3.11"
    exit 1
fi

# Check Node.js
print_info "Checking Node.js installation..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)

    if [[ $NODE_MAJOR -ge 18 ]]; then
        print_success "Node.js v$NODE_VERSION found"
    else
        print_error "Node.js 18+ required. Found: v$NODE_VERSION"
        print_info "Update via: brew upgrade node"
        exit 1
    fi
else
    print_error "Node.js not found!"
    print_info "Install via: brew install node"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_success "npm v$NPM_VERSION found"
else
    print_error "npm not found! (should come with Node.js)"
    exit 1
fi

echo ""

# Step 2: Create Data Directories
print_header "Step 2: Creating Data Directories"

print_info "Creating directories in $DATA_DIR..."

mkdir -p "$DATA_DIR/huggingface_cache"
mkdir -p "$DATA_DIR/jobs"

print_success "Created: $DATA_DIR/huggingface_cache"
print_success "Created: $DATA_DIR/jobs"

echo ""

# Step 3: Backend Setup
print_header "Step 3: Setting Up Backend"

cd "$BACKEND_DIR"

# Check if venv exists
if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists"
    read -p "Recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing virtual environment..."
        rm -rf .venv
    else
        print_info "Skipping virtual environment creation"
    fi
fi

# Create virtual environment with Python 3.11 (for better compatibility)
if [ ! -d ".venv" ]; then
    print_info "Creating Python virtual environment..."

    # Try python3.11 first, fall back to python3
    if command -v python3.11 &> /dev/null; then
        print_info "Using Python 3.11 for better compatibility..."
        python3.11 -m venv .venv
    else
        print_info "Using default Python 3..."
        python3 -m venv .venv
    fi

    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
print_success "pip upgraded"

# Install dependencies
print_info "Installing Python dependencies (this may take 5-10 minutes)..."
echo -e "${YELLOW}⏳ Installing PyTorch, transformers, diffusers, and other ML libraries...${NC}"

pip install -r requirements.txt

print_success "Python dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    print_info "Creating .env file..."
    cp .env.example .env
    print_success ".env file created"
else
    print_info ".env file already exists"
fi

# Deactivate venv
deactivate

cd "$SCRIPT_DIR"
echo ""

# Step 4: Frontend Setup
print_header "Step 4: Setting Up Frontend"

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ -d "node_modules" ]; then
    print_warning "node_modules already exists"
    read -p "Reinstall dependencies? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Removing existing node_modules..."
        rm -rf node_modules package-lock.json
    else
        print_info "Skipping npm install"
        cd "$SCRIPT_DIR"
        echo ""

        # Skip to final steps if not reinstalling
        print_header "Setup Complete!"
        echo -e "${GREEN}${BOLD}✓ All setup steps completed successfully!${NC}\n"

        print_info "Next steps:"
        echo -e "  1. ${CYAN}Start the application:${NC}"
        echo -e "     ${BOLD}./start${NC}"
        echo ""
        echo -e "  2. ${CYAN}Access the application:${NC}"
        echo -e "     Backend:  ${BOLD}http://localhost:8000${NC}"
        echo -e "     Frontend: ${BOLD}http://localhost:3000${NC}"
        echo ""

        print_warning "First run will download ~57.7GB model (takes 10-30 min)"

        echo -e "\n${CYAN}${BOLD}═══════════════════════════════════════════════════════════${NC}\n"

        exit 0
    fi
fi

# Install npm dependencies
if [ ! -d "node_modules" ]; then
    print_info "Installing npm dependencies (this may take 2-5 minutes)..."
    npm install
    print_success "npm dependencies installed"
fi

cd "$SCRIPT_DIR"
echo ""

# Step 5: Verify Setup
print_header "Step 5: Verifying Setup"

# Check backend venv
if [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
    print_success "Backend virtual environment: OK"
else
    print_error "Backend virtual environment: MISSING"
    exit 1
fi

# Check backend .env
if [ -f "$BACKEND_DIR/.env" ]; then
    print_success "Backend .env file: OK"
else
    print_error "Backend .env file: MISSING"
    exit 1
fi

# Check frontend node_modules
if [ -d "$FRONTEND_DIR/node_modules" ]; then
    print_success "Frontend dependencies: OK"
else
    print_error "Frontend dependencies: MISSING"
    exit 1
fi

# Check frontend .env
if [ -f "$FRONTEND_DIR/.env" ]; then
    print_success "Frontend .env file: OK"
else
    print_warning "Frontend .env file: MISSING (using defaults)"
fi

# Check data directories
if [ -d "$DATA_DIR/huggingface_cache" ]; then
    print_success "HuggingFace cache directory: OK"
else
    print_error "HuggingFace cache directory: MISSING"
    exit 1
fi

if [ -d "$DATA_DIR/jobs" ]; then
    print_success "Jobs directory: OK"
else
    print_error "Jobs directory: MISSING"
    exit 1
fi

# Check PyTorch MPS (only on macOS)
if [[ "$OSTYPE" == "darwin"* ]] && [[ "$ARCH" == "arm64" ]]; then
    print_info "Checking PyTorch MPS support..."
    cd "$BACKEND_DIR"
    source .venv/bin/activate

    MPS_CHECK=$(python -c "import torch; print(torch.backends.mps.is_available())" 2>/dev/null || echo "false")

    if [ "$MPS_CHECK" == "True" ]; then
        print_success "PyTorch MPS (Apple Silicon GPU): Available ✓"
    else
        print_warning "PyTorch MPS: Not available (will use CPU)"
    fi

    deactivate
    cd "$SCRIPT_DIR"
fi

echo ""

# Final Summary
print_header "Setup Complete!"

echo -e "${GREEN}${BOLD}✓ All setup steps completed successfully!${NC}\n"

echo -e "${CYAN}Configuration Summary:${NC}"
echo -e "  Data Directory:    ${BOLD}$DATA_DIR${NC}"
echo -e "  Model Cache:       ${BOLD}~57.7GB${NC} (downloads on first run)"
echo -e "  Backend Port:      ${BOLD}8000${NC}"
echo -e "  Frontend Port:     ${BOLD}3000${NC}"

if [[ "$OSTYPE" == "darwin"* ]] && [[ "$ARCH" == "arm64" ]] && [[ "$MPS_CHECK" == "True" ]]; then
    echo -e "  GPU Acceleration:  ${BOLD}${GREEN}MPS (Apple Silicon)${NC}"
else
    echo -e "  GPU Acceleration:  ${BOLD}${YELLOW}CPU${NC}"
fi

echo ""

print_info "Next steps:"
echo -e "  1. ${CYAN}Start the application:${NC}"
echo -e "     ${BOLD}./start${NC}"
echo ""
echo -e "  2. ${CYAN}Access the application:${NC}"
echo -e "     Backend:  ${BOLD}http://localhost:8000${NC}"
echo -e "     Frontend: ${BOLD}http://localhost:3000${NC}"
echo ""

print_warning "First run will download ~57.7GB model (takes 10-30 min)"
print_info "Subsequent runs will be much faster (model is cached)"

echo ""
echo -e "${CYAN}${BOLD}For help:${NC}"
echo -e "  - View README.md for usage guide"
echo -e "  - View CLAUDE.md for technical details"
echo -e "  - Check troubleshooting section if you encounter issues"

echo -e "\n${CYAN}${BOLD}═══════════════════════════════════════════════════════════${NC}\n"
