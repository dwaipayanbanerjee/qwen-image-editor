#!/usr/bin/env python3
"""
Foreground startup script for Qwen Image Editor
Runs both backend and frontend in the foreground with colored output
Allows easy debugging by showing all output in one terminal
"""

import subprocess
import sys
import os
import signal
import threading
import select
from pathlib import Path

# ANSI color codes
BLUE = '\033[0;34m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color
BOLD = '\033[1m'

def print_colored(prefix, color, message):
    """Print message with colored prefix"""
    print(f"{color}[{prefix}]{NC} {message}", flush=True)

def stream_output(process, prefix, color):
    """Stream output from process with colored prefix"""
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print_colored(prefix, color, line.rstrip())

def main():
    print(f"{GREEN}{BOLD}Starting Qwen Image Editor (Foreground Debug Mode){NC}")
    print(f"{YELLOW}All backend and frontend output will appear here{NC}")
    print(f"{YELLOW}Press Ctrl+C to stop all services{NC}\n")

    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    backend_dir = script_dir / 'backend'
    frontend_dir = script_dir / 'frontend'

    # Check if directories exist
    if not backend_dir.exists():
        print_colored("ERROR", RED, f"Backend directory not found: {backend_dir}")
        sys.exit(1)

    if not frontend_dir.exists():
        print_colored("ERROR", RED, f"Frontend directory not found: {frontend_dir}")
        sys.exit(1)

    # Check if backend venv exists
    venv_path = backend_dir / 'venv' / 'bin' / 'activate'
    if not venv_path.exists():
        print_colored("ERROR", RED, "Backend virtual environment not found!")
        print_colored("ERROR", RED, "Please run: cd backend && ./setup.sh")
        sys.exit(1)

    # Check if frontend node_modules exists
    node_modules = frontend_dir / 'node_modules'
    if not node_modules.exists():
        print_colored("WARNING", YELLOW, "Frontend dependencies not installed!")
        print_colored("INFO", BLUE, "Installing frontend dependencies...")
        try:
            subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        except subprocess.CalledProcessError:
            print_colored("ERROR", RED, "Failed to install frontend dependencies")
            sys.exit(1)

    processes = []

    def cleanup():
        """Cleanup function to terminate all processes"""
        print(f"\n{YELLOW}Shutting down services...{NC}")
        for proc in processes:
            if proc.poll() is None:  # Process is still running
                proc.terminate()

        # Wait for processes to terminate
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        print(f"{GREEN}All services stopped{NC}")

    def signal_handler(sig, frame):
        """Handle Ctrl+C gracefully"""
        cleanup()
        sys.exit(0)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start backend
        print_colored("STARTUP", BLUE, "Starting backend (port 8000)...")
        backend_cmd = f"cd {backend_dir} && source venv/bin/activate && python main.py"
        backend_process = subprocess.Popen(
            backend_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            executable='/bin/bash'
        )
        processes.append(backend_process)

        # Start backend output thread
        backend_thread = threading.Thread(
            target=stream_output,
            args=(backend_process, "BACKEND", BLUE),
            daemon=True
        )
        backend_thread.start()

        # Give backend a moment to start
        import time
        time.sleep(2)

        # Start frontend
        print_colored("STARTUP", GREEN, "Starting frontend (port 3000)...")
        frontend_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(frontend_process)

        # Start frontend output thread
        frontend_thread = threading.Thread(
            target=stream_output,
            args=(frontend_process, "FRONTEND", GREEN),
            daemon=True
        )
        frontend_thread.start()

        print(f"\n{GREEN}✓ Services started{NC}")
        print(f"{BLUE}  Backend:  http://localhost:8000{NC}")
        print(f"{GREEN}  Frontend: http://localhost:3000{NC}")
        print(f"\n{YELLOW}Press Ctrl+C to stop all services{NC}\n")

        # Wait for any process to exit
        while all(proc.poll() is None for proc in processes):
            time.sleep(0.5)

        # If we get here, one process exited
        for i, proc in enumerate(processes):
            if proc.poll() is not None:
                service = "Backend" if i == 0 else "Frontend"
                returncode = proc.poll()
                if returncode != 0:
                    print_colored("ERROR", RED, f"{service} exited with code {returncode}")
                else:
                    print_colored("INFO", YELLOW, f"{service} exited")

        cleanup()
        sys.exit(1)

    except Exception as e:
        print_colored("ERROR", RED, f"Error: {str(e)}")
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
