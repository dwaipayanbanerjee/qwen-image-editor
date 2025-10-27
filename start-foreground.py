#!/usr/bin/env python3
"""
Qwen Image Editor - Single Entrypoint Startup Script

This is the ONLY script you need to start the application.

Features:
- Automatically detects and kills existing instances
- Runs both backend and frontend in foreground
- Color-coded output for easy debugging
- Graceful cleanup on exit (Ctrl+C)
- Validates setup before starting

Usage:
    ./start-foreground.py

    Press Ctrl+C to stop all services cleanly.
"""

import subprocess
import sys
import os
import signal
import threading
import time
import re
from pathlib import Path
from typing import List, Optional

# ANSI color codes
BLUE = '\033[0;34m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color
BOLD = '\033[1m'

def print_colored(prefix, color, message):
    """Print message with colored prefix"""
    print(f"{color}[{prefix}]{NC} {message}", flush=True)

def run_command(cmd: str, capture_output: bool = True) -> Optional[str]:
    """Run a shell command and optionally return output"""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=False)
            return None
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        return None

def find_existing_processes(script_dir: Path) -> List[int]:
    """
    Find existing backend and frontend processes
    Returns list of PIDs to kill
    """
    pids = []

    # Find backend processes (uvicorn/python main.py)
    backend_dir = str(script_dir / 'backend')
    cmd = f"ps aux | grep -E '(uvicorn|python.*main\\.py)' | grep -v grep | grep '{backend_dir}'"
    output = run_command(cmd)
    if output:
        for line in output.split('\n'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    pid = int(parts[1])
                    pids.append(pid)
                    print_colored("CLEANUP", YELLOW, f"Found existing backend process: PID {pid}")
                except ValueError:
                    pass

    # Find frontend processes (npm/vite)
    frontend_dir = str(script_dir / 'frontend')
    cmd = f"ps aux | grep -E '(npm|vite)' | grep -v grep | grep '{frontend_dir}'"
    output = run_command(cmd)
    if output:
        for line in output.split('\n'):
            parts = line.split()
            if len(parts) > 1:
                try:
                    pid = int(parts[1])
                    pids.append(pid)
                    print_colored("CLEANUP", YELLOW, f"Found existing frontend process: PID {pid}")
                except ValueError:
                    pass

    return pids

def kill_processes(pids: List[int]):
    """Kill processes gracefully, then forcefully if needed"""
    if not pids:
        return

    print_colored("CLEANUP", YELLOW, f"Stopping {len(pids)} existing process(es)...")

    # Try graceful shutdown first (SIGTERM)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass  # Process already gone
        except PermissionError:
            print_colored("WARNING", RED, f"No permission to kill PID {pid}")

    # Wait for processes to die
    time.sleep(2)

    # Check what's still alive and force kill (SIGKILL)
    for pid in pids:
        try:
            # Check if process still exists
            os.kill(pid, 0)
            # If we get here, process is still alive - force kill
            print_colored("CLEANUP", YELLOW, f"Force killing PID {pid}")
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # Process is gone, good

    print_colored("CLEANUP", GREEN, "All existing processes stopped")

def stream_output(process, prefix, color):
    """Stream output from process with colored prefix"""
    while True:
        line = process.stdout.readline()
        if not line:
            break
        print_colored(prefix, color, line.rstrip())

def validate_setup(script_dir: Path) -> bool:
    """Validate that the environment is properly set up"""
    backend_dir = script_dir / 'backend'
    frontend_dir = script_dir / 'frontend'

    # Check directories exist
    if not backend_dir.exists():
        print_colored("ERROR", RED, f"Backend directory not found: {backend_dir}")
        return False

    if not frontend_dir.exists():
        print_colored("ERROR", RED, f"Frontend directory not found: {frontend_dir}")
        return False

    # Check backend venv
    venv_path = backend_dir / 'venv' / 'bin' / 'activate'
    if not venv_path.exists():
        print_colored("ERROR", RED, "Backend virtual environment not found!")
        print_colored("ERROR", RED, "Please run: cd backend && ./setup.sh")
        return False

    # Check frontend node_modules
    node_modules = frontend_dir / 'node_modules'
    if not node_modules.exists():
        print_colored("INFO", CYAN, "Frontend dependencies not installed, installing now...")
        try:
            subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print_colored("INFO", GREEN, "Frontend dependencies installed successfully")
        except subprocess.CalledProcessError:
            print_colored("ERROR", RED, "Failed to install frontend dependencies")
            return False
        except FileNotFoundError:
            print_colored("ERROR", RED, "npm not found. Please install Node.js")
            return False

    return True

def main():
    # Print banner
    print(f"\n{CYAN}{'=' * 70}{NC}")
    print(f"{GREEN}{BOLD}  Qwen Image Editor - Single Entrypoint Startup{NC}")
    print(f"{CYAN}{'=' * 70}{NC}\n")

    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    backend_dir = script_dir / 'backend'
    frontend_dir = script_dir / 'frontend'

    # Step 1: Find and kill existing processes
    print_colored("STEP 1", CYAN, "Checking for existing instances...")
    existing_pids = find_existing_processes(script_dir)
    if existing_pids:
        kill_processes(existing_pids)
    else:
        print_colored("STEP 1", GREEN, "No existing instances found")

    # Step 2: Validate setup
    print_colored("STEP 2", CYAN, "Validating environment setup...")
    if not validate_setup(script_dir):
        sys.exit(1)
    print_colored("STEP 2", GREEN, "Environment validated successfully")

    # Step 3: Start services
    print_colored("STEP 3", CYAN, "Starting services...")
    print(f"\n{YELLOW}All output will appear below. Press Ctrl+C to stop all services.{NC}\n")

    processes = []
    cleanup_done = False

    def cleanup():
        """Cleanup function to terminate all processes"""
        nonlocal cleanup_done
        if cleanup_done:
            return
        cleanup_done = True

        print(f"\n{YELLOW}{'=' * 70}{NC}")
        print_colored("SHUTDOWN", YELLOW, "Stopping all services...")

        for proc in processes:
            if proc.poll() is None:  # Process is still running
                try:
                    proc.terminate()
                except:
                    pass

        # Wait for graceful shutdown
        time.sleep(2)

        # Force kill if needed
        for proc in processes:
            if proc.poll() is None:
                try:
                    proc.kill()
                except:
                    pass

        # Find any stragglers and kill them
        print_colored("SHUTDOWN", YELLOW, "Cleaning up any remaining processes...")
        remaining_pids = find_existing_processes(script_dir)
        if remaining_pids:
            kill_processes(remaining_pids)

        print_colored("SHUTDOWN", GREEN, "All services stopped cleanly")
        print(f"{YELLOW}{'=' * 70}{NC}\n")

    def signal_handler(sig, frame):
        """Handle Ctrl+C gracefully"""
        cleanup()
        sys.exit(0)

    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start backend
        print_colored("BACKEND", BLUE, "Starting on port 8000...")
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
        time.sleep(3)

        # Start frontend
        print_colored("FRONTEND", GREEN, "Starting on port 3000...")
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

        # Wait a moment for services to start
        time.sleep(2)

        # Print success message
        print(f"\n{GREEN}{'=' * 70}{NC}")
        print(f"{GREEN}{BOLD}✓ Services Started Successfully{NC}")
        print(f"{GREEN}{'=' * 70}{NC}")
        print(f"\n  {BLUE}Backend API: {NC}  http://localhost:8000")
        print(f"  {GREEN}Frontend UI: {NC}  http://localhost:3000")
        print(f"\n  {YELLOW}Press Ctrl+C to stop all services{NC}")
        print(f"{GREEN}{'=' * 70}{NC}\n")

        # Monitor processes
        while True:
            # Check if any process has died
            for i, proc in enumerate(processes):
                if proc.poll() is not None:
                    service = "Backend" if i == 0 else "Frontend"
                    returncode = proc.poll()

                    if returncode != 0:
                        print_colored("ERROR", RED, f"{service} crashed with exit code {returncode}")
                    else:
                        print_colored("INFO", YELLOW, f"{service} exited normally")

                    # Cleanup and exit
                    cleanup()
                    sys.exit(1 if returncode != 0 else 0)

            time.sleep(0.5)

    except Exception as e:
        print_colored("ERROR", RED, f"Unexpected error: {str(e)}")
        cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
