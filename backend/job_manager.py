"""
Job Manager for tracking image editing jobs
Handles in-memory state, disk persistence, and WebSocket broadcasting
"""

import json
import time
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Optional, List, Any
from threading import Lock, Event
import logging

from models import JobStatus

logger = logging.getLogger(__name__)


class JobManager:
    """
    Manages image editing jobs lifecycle
    - In-memory state tracking
    - Disk persistence (metadata.json)
    - WebSocket connection registry
    """

    def __init__(self, jobs_dir: Path, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        """
        Initialize JobManager

        Args:
            jobs_dir: Base directory for storing job files
            event_loop: Event loop for WebSocket broadcasting (set during app startup)
        """
        self.jobs_dir = Path(jobs_dir)
        self.jobs: Dict[str, dict] = {}
        self.ws_connections: Dict[str, List] = {}  # job_id -> [websockets]
        self.cancellation_events: Dict[str, Event] = {}  # job_id -> cancellation event
        self.job_tasks: Dict[str, asyncio.Task] = {}  # job_id -> background task
        self.lock = Lock()
        self.event_loop = event_loop
        self._pending_writes: Dict[str, float] = {}  # job_id -> last_update_time
        self._write_interval = 2.0  # Write to disk at most every 2 seconds

        # Ensure jobs directory exists
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

        # Load existing jobs from disk
        self._load_jobs_from_disk()

    def _load_jobs_from_disk(self):
        """
        Load existing job metadata from disk on startup
        Clean up corrupted or old jobs automatically
        """
        if not self.jobs_dir.exists():
            return

        cleaned_count = 0
        loaded_count = 0

        for job_dir in self.jobs_dir.iterdir():
            if job_dir.is_dir():
                metadata_file = job_dir / 'metadata.json'

                # If metadata file doesn't exist or is empty, delete the job
                if not metadata_file.exists() or metadata_file.stat().st_size == 0:
                    logger.warning(f"Removing job {job_dir.name} - missing or empty metadata")
                    try:
                        shutil.rmtree(job_dir)
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Error removing corrupted job {job_dir.name}: {str(e)}")
                    continue

                try:
                    with open(metadata_file, 'r') as f:
                        job_data = json.load(f)

                    # Only load completed or error jobs (not processing)
                    # Processing jobs from previous run are invalid
                    if job_data.get('status') == 'processing':
                        logger.info(f"Removing stale processing job {job_dir.name} from previous run")
                        shutil.rmtree(job_dir)
                        cleaned_count += 1
                    else:
                        self.jobs[job_dir.name] = job_data
                        loaded_count += 1
                        logger.info(f"Loaded job {job_dir.name} from disk")

                except json.JSONDecodeError as e:
                    logger.warning(f"Removing job {job_dir.name} - corrupted metadata: {str(e)}")
                    try:
                        shutil.rmtree(job_dir)
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"Error removing corrupted job {job_dir.name}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error loading job {job_dir.name}: {str(e)}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} corrupted/stale jobs on startup")
        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} valid jobs from disk")

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
                'status': JobStatus.PROCESSING.value,
                'config': config,
                'progress': None,
                'error': None,
                'created_at': time.time()
            }
            # Create cancellation event for this job
            self.cancellation_events[job_id] = Event()

        # Save to disk immediately for new jobs
        self._save_job_metadata(job_id, force=True)

        logger.info(f"Created job {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job data by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def update_job_data(self, job_id: str, updates: dict) -> None:
        """
        Update job data fields and save to disk

        Args:
            job_id: Job identifier
            updates: Dictionary of fields to update
        """
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} not found")
                return
            self.jobs[job_id].update(updates)

        # Save to disk immediately
        self._save_job_metadata(job_id, force=True)
        logger.info(f"Updated job {job_id} data: {list(updates.keys())}")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for WebSocket broadcasting"""
        self.event_loop = loop
        logger.info("Event loop set for JobManager")

    def register_task(self, job_id: str, task: asyncio.Task) -> None:
        """Register a background task for a job"""
        with self.lock:
            self.job_tasks[job_id] = task
        logger.info(f"Registered task for job {job_id}")

    def is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled"""
        with self.lock:
            event = self.cancellation_events.get(job_id)
            return event.is_set() if event else False

    def request_cancellation(self, job_id: str) -> bool:
        """Request cancellation of a job"""
        with self.lock:
            if job_id in self.cancellation_events:
                self.cancellation_events[job_id].set()
                logger.info(f"Cancellation requested for job {job_id}")
                return True
            return False

    def set_status(self, job_id: str, status: JobStatus, error: Optional[str] = None) -> None:
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

        # Always save immediately for status changes (critical state)
        self._save_job_metadata(job_id, force=True)

        # Broadcast to WebSocket clients
        self._schedule_broadcast(job_id)

        logger.info(f"Job {job_id} status: {status.value}")

    def update_progress(
        self,
        job_id: str,
        stage: str,
        message: str,
        progress: int = 0
    ) -> None:
        """
        Update job progress information

        Args:
            job_id: Job identifier
            stage: Current processing stage
            message: Human-readable progress message
            progress: Progress percentage (0-100)
        """
        current_time = time.time()

        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Job {job_id} not found")
                return

            self.jobs[job_id]['progress'] = {
                'stage': stage,
                'message': message,
                'progress': progress,
                'updated_at': current_time
            }

            # Track pending write
            last_write = self._pending_writes.get(job_id, 0)
            force_write = (current_time - last_write) >= self._write_interval

        # Save to disk only if enough time has passed (batching)
        # or if it's a critical progress point (0%, 100%)
        if force_write or progress in [0, 100]:
            self._save_job_metadata(job_id, force=True)
            with self.lock:
                self._pending_writes[job_id] = current_time
        else:
            # Just mark as dirty, will be written on next forced write
            self._save_job_metadata(job_id, force=False)

        # Broadcast to WebSocket clients
        self._schedule_broadcast(job_id)

    def _save_job_metadata(self, job_id: str, force: bool = False) -> None:
        """
        Save job metadata to disk

        Args:
            job_id: Job identifier
            force: If True, write immediately; if False, skip if recently written
        """
        if not force:
            # Skip write if not forced (batching optimization)
            return

        try:
            with self.lock:
                if job_id not in self.jobs:
                    return
                job_data = self.jobs[job_id].copy()

            job_dir = self.jobs_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            metadata_file = job_dir / 'metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(job_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving metadata for job {job_id}: {str(e)}")

    def delete_job(self, job_id: str) -> bool:
        """
        Delete job and all associated files
        Also cancels the job if it's still running

        Args:
            job_id: Job identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Request cancellation first
            self.request_cancellation(job_id)

            # Cancel the task if it exists
            with self.lock:
                if job_id in self.job_tasks:
                    task = self.job_tasks[job_id]
                    if not task.done():
                        task.cancel()
                    del self.job_tasks[job_id]

                # Remove cancellation event
                if job_id in self.cancellation_events:
                    del self.cancellation_events[job_id]

                # Remove pending writes tracking
                if job_id in self._pending_writes:
                    del self._pending_writes[job_id]

                # Remove from memory
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

    def _schedule_broadcast(self, job_id: str) -> None:
        """
        Schedule a broadcast to all WebSocket clients for a job
        Safely handles being called from worker threads
        """
        if not self.event_loop:
            logger.warning(f"Event loop not set, cannot broadcast for job {job_id}")
            return

        try:
            # Always use run_coroutine_threadsafe with the saved event loop
            # This is safe whether called from async context or worker thread
            asyncio.run_coroutine_threadsafe(
                self._broadcast_progress(job_id),
                self.event_loop
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
