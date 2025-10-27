"""
Job Manager for tracking image editing jobs
Handles in-memory state, disk persistence, and WebSocket broadcasting
"""

import json
import time
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Optional, List
from enum import Enum
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class JobManager:
    """
    Manages image editing jobs lifecycle
    - In-memory state tracking
    - Disk persistence (metadata.json)
    - WebSocket connection registry
    """

    def __init__(self, jobs_dir: Path):
        """
        Initialize JobManager

        Args:
            jobs_dir: Base directory for storing job files
        """
        self.jobs_dir = Path(jobs_dir)
        self.jobs: Dict[str, dict] = {}
        self.ws_connections: Dict[str, List] = {}  # job_id -> [websockets]
        self.lock = Lock()

        # Ensure jobs directory exists
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

        # Load existing jobs from disk
        self._load_jobs_from_disk()

    def _load_jobs_from_disk(self):
        """Load existing job metadata from disk on startup"""
        if not self.jobs_dir.exists():
            return

        for job_dir in self.jobs_dir.iterdir():
            if job_dir.is_dir():
                metadata_file = job_dir / 'metadata.json'
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            job_data = json.load(f)
                            self.jobs[job_dir.name] = job_data
                            logger.info(f"Loaded job {job_dir.name} from disk")
                    except Exception as e:
                        logger.error(f"Error loading job {job_dir.name}: {str(e)}")

    def create_job(self, config: dict) -> str:
        """
        Create a new job

        Args:
            config: Job configuration dictionary

        Returns:
            job_id: Unique job identifier
        """
        import uuid

        job_id = str(uuid.uuid4())

        with self.lock:
            self.jobs[job_id] = {
                'job_id': job_id,
                'status': JobStatus.QUEUED.value,
                'config': config,
                'progress': None,
                'error': None,
                'created_at': time.time()
            }

        # Save to disk
        self._save_job_metadata(job_id)

        logger.info(f"Created job {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job data by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def set_status(self, job_id: str, status: JobStatus, error: Optional[str] = None):
        """
        Update job status

        Args:
            job_id: Job identifier
            status: New status
            error: Error message if status is ERROR
        """
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} not found")
                return

            self.jobs[job_id]['status'] = status.value
            if error:
                self.jobs[job_id]['error'] = error

        # Save to disk
        self._save_job_metadata(job_id)

        # Broadcast to WebSocket clients
        self._schedule_broadcast(job_id)

        logger.info(f"Job {job_id} status: {status.value}")

    def update_progress(
        self,
        job_id: str,
        stage: str,
        message: str,
        progress: int = 0
    ):
        """
        Update job progress information

        Args:
            job_id: Job identifier
            stage: Current processing stage
            message: Human-readable progress message
            progress: Progress percentage (0-100)
        """
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} not found")
                return

            self.jobs[job_id]['progress'] = {
                'stage': stage,
                'message': message,
                'progress': progress,
                'updated_at': time.time()
            }

        # Save to disk
        self._save_job_metadata(job_id)

        # Broadcast to WebSocket clients
        self._schedule_broadcast(job_id)

    def _save_job_metadata(self, job_id: str):
        """Save job metadata to disk"""
        try:
            job_dir = self.jobs_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            metadata_file = job_dir / 'metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(self.jobs[job_id], f, indent=2)

        except Exception as e:
            logger.error(f"Error saving metadata for job {job_id}: {str(e)}")

    def delete_job(self, job_id: str) -> bool:
        """
        Delete job and all associated files

        Args:
            job_id: Job identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from memory
            with self.lock:
                if job_id in self.jobs:
                    del self.jobs[job_id]

            # Remove from disk
            job_dir = self.jobs_dir / job_id
            if job_dir.exists():
                shutil.rmtree(job_dir)

            logger.info(f"Deleted job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            return False

    # WebSocket connection management

    def add_ws_connection(self, job_id: str, websocket):
        """Register a WebSocket connection for a job"""
        with self.lock:
            if job_id not in self.ws_connections:
                self.ws_connections[job_id] = []
            self.ws_connections[job_id].append(websocket)

        logger.info(f"WebSocket added for job {job_id}")

    def remove_ws_connection(self, job_id: str, websocket):
        """Unregister a WebSocket connection"""
        with self.lock:
            if job_id in self.ws_connections:
                if websocket in self.ws_connections[job_id]:
                    self.ws_connections[job_id].remove(websocket)

                # Clean up empty lists
                if not self.ws_connections[job_id]:
                    del self.ws_connections[job_id]

        logger.info(f"WebSocket removed for job {job_id}")

    def _schedule_broadcast(self, job_id: str):
        """
        Schedule a broadcast to all WebSocket clients for a job
        Safely handles being called from worker threads
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, schedule the broadcast
                asyncio.create_task(self._broadcast_progress(job_id))
            else:
                # We're in a worker thread, schedule on the event loop
                asyncio.run_coroutine_threadsafe(
                    self._broadcast_progress(job_id),
                    loop
                )
        except Exception as e:
            logger.error(f"Error scheduling broadcast for job {job_id}: {str(e)}")

    async def _broadcast_progress(self, job_id: str):
        """Broadcast progress update to all WebSocket clients"""
        job = self.get_job(job_id)
        if not job:
            return

        message = {
            'status': job['status'],
            'progress': job.get('progress'),
            'error': job.get('error')
        }

        # Get connections to broadcast to
        with self.lock:
            connections = self.ws_connections.get(job_id, []).copy()

        # Broadcast to all connections
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {str(e)}")
                # Remove dead connections
                self.remove_ws_connection(job_id, ws)

    def get_stats(self) -> dict:
        """Get statistics about jobs"""
        with self.lock:
            total = len(self.jobs)
            by_status = {}

            for job in self.jobs.values():
                status = job['status']
                by_status[status] = by_status.get(status, 0) + 1

        return {
            'total_jobs': total,
            'by_status': by_status,
            'active_ws_connections': sum(len(conns) for conns in self.ws_connections.values())
        }
