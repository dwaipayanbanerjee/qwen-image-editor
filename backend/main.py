"""
Qwen Image Editor API - FastAPI Backend
Runs on RunPod A40 GPU, designed for persistence in /workspace
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
import imghdr

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv
import json
import logging

from image_editor import ImageEditor
from job_manager import JobManager, JobStatus
from models import EditConfig, JobStatusResponse, ProgressInfo

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment setup for RunPod persistence
os.environ['HF_HOME'] = os.getenv('HF_HOME', '/workspace/huggingface_cache')
os.environ['TRANSFORMERS_CACHE'] = os.getenv('TRANSFORMERS_CACHE', '/workspace/huggingface_cache')
os.environ['HF_DATASETS_CACHE'] = os.getenv('HF_DATASETS_CACHE', '/workspace/huggingface_cache')

# Configuration
JOBS_DIR = Path(os.getenv('JOBS_DIR', '/workspace/jobs'))
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')

# Global instances
job_manager = JobManager(JOBS_DIR)
image_editor: Optional[ImageEditor] = None
job_queue: asyncio.Queue = asyncio.Queue(maxsize=10)  # Limit concurrent jobs
active_job_semaphore: asyncio.Semaphore = asyncio.Semaphore(1)  # Only 1 job at a time on GPU


async def validate_image_file(file: UploadFile, max_size: int = MAX_FILE_SIZE) -> bytes:
    """
    Validate image file format and size

    Args:
        file: Uploaded file
        max_size: Maximum allowed file size in bytes

    Returns:
        File content as bytes

    Raises:
        HTTPException: If validation fails
    """
    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        )

    # Validate actual image format using magic bytes
    image_type = imghdr.what(None, h=content)
    if image_type not in ['jpeg', 'jpg', 'png', 'webp', 'bmp']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format. Allowed: JPEG, PNG, WebP, BMP. Detected: {image_type or 'unknown'}"
        )

    return content


async def generate_image_task(job_id: str) -> None:
    """
    Execute image editing task in thread pool executor
    Supports cancellation and proper error handling
    """
    global image_editor

    try:
        # Acquire semaphore to limit concurrent GPU jobs
        async with active_job_semaphore:
            # Check for cancellation
            if job_manager.is_cancelled(job_id):
                logger.info(f"Job {job_id} was cancelled before starting")
                return

            # Lazy load the model (only on first use)
            if image_editor is None:
                logger.info("Loading Qwen-Image-Edit model...")
                job_manager.update_progress(
                    job_id,
                    stage="loading_model",
                    message="Loading Qwen model (first time only, ~10-30 min)...",
                    progress=5
                )
                image_editor = ImageEditor(progress_callback=lambda p: job_manager.update_progress(
                    job_id,
                    stage="loading_model",
                    message=f"Downloading model... {p}%",
                    progress=5 + int(p * 0.15)  # 5-20%
                ))
                logger.info("Model loaded successfully")

            # Get job metadata
            job = job_manager.get_job(job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")

            config = EditConfig(**job['config'])
            job_dir = JOBS_DIR / job_id

            # Load input images
            input_paths = []
            if (job_dir / 'input_1.jpg').exists():
                input_paths.append(str(job_dir / 'input_1.jpg'))
            if (job_dir / 'input_2.jpg').exists():
                input_paths.append(str(job_dir / 'input_2.jpg'))

            if not input_paths:
                raise Exception("No input images found")

            # Progress callback with cancellation check
            def progress_callback(stage: str, message: str, progress: int = 0):
                # Check for cancellation
                if job_manager.is_cancelled(job_id):
                    raise asyncio.CancelledError("Job cancelled by user")

                job_manager.update_progress(
                    job_id,
                    stage=stage,
                    message=message,
                    progress=progress
                )

            # Start image editing
            progress_callback("editing", "Starting image editing...", 25)

            # Check cancellation before running
            if job_manager.is_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled before inference")
                return

            # Run image editing in executor to avoid blocking
            loop = asyncio.get_event_loop()
            output_path = await loop.run_in_executor(
                None,
                image_editor.edit_image,
                input_paths,
                config.prompt,
                config.negative_prompt,
                config.true_cfg_scale,
                config.num_inference_steps,
                str(job_dir / 'output.jpg'),
                progress_callback,
                lambda: job_manager.is_cancelled(job_id)  # Cancellation checker
            )

            # Final cancellation check
            if job_manager.is_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled after inference")
                return

            # Mark as complete
            job_manager.set_status(job_id, JobStatus.COMPLETE)
            progress_callback("complete", "Image editing complete!", 100)
            logger.info(f"Job {job_id} completed successfully")

    except asyncio.CancelledError:
        logger.info(f"Job {job_id} was cancelled")
        job_manager.set_status(job_id, JobStatus.ERROR, error="Job cancelled by user")
    except Exception as e:
        logger.error(f"Error editing image for job {job_id}: {str(e)}", exc_info=True)
        job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Qwen Image Editor API...")
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    # Set event loop in job_manager for WebSocket broadcasting
    loop = asyncio.get_running_loop()
    job_manager.set_event_loop(loop)
    logger.info("Event loop registered with JobManager")

    yield

    # Shutdown
    logger.info("Shutting down...")
    # Cancel any remaining tasks
    for job_id, task in list(job_manager.job_tasks.items()):
        if not task.done():
            logger.info(f"Cancelling job {job_id}")
            task.cancel()
    logger.info("Shutdown complete")


# FastAPI app
app = FastAPI(
    title="Qwen Image Editor API",
    description="AI-powered image editing using Qwen-Image-Edit model",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware with WebSocket support
# Add RunPod proxy domains if running on RunPod
if os.getenv('RUNPOD_POD_ID'):
    pod_id = os.getenv('RUNPOD_POD_ID')
    ALLOWED_ORIGINS.extend([
        f"https://{pod_id}-3000.proxy.runpod.net",
        f"https://{pod_id}-5173.proxy.runpod.net"
    ])

# Allow wildcard for development, specific origins for production
allow_origins = ["*"] if os.getenv('ENV', 'development') == 'development' else ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "Qwen Image Editor API is running",
        "model": "Qwen-Image-Edit",
        "gpu": "A40"
    }


@app.post("/api/edit")
async def edit_image(
    image1: UploadFile = File(..., description="Primary input image"),
    image2: Optional[UploadFile] = File(None, description="Optional second image for combining"),
    config: str = Form(..., description="JSON config with prompt and parameters")
):
    """
    Create new image editing job

    Args:
        image1: Primary image file (required)
        image2: Second image file (optional, for combining)
        config: JSON string with EditConfig fields

    Returns:
        Job ID and status
    """
    try:
        # Parse and validate config
        config_dict = json.loads(config)
        edit_config = EditConfig(**config_dict)

        # Validate image files (size and format)
        image1_content = await validate_image_file(image1)

        image2_content = None
        if image2:
            image2_content = await validate_image_file(image2)

        # Create job
        job_id = job_manager.create_job(edit_config.model_dump())
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Save validated input images
        image1_path = job_dir / 'input_1.jpg'
        with open(image1_path, 'wb') as f:
            f.write(image1_content)

        if image2_content:
            image2_path = job_dir / 'input_2.jpg'
            with open(image2_path, 'wb') as f:
                f.write(image2_content)

        logger.info(f"Created job {job_id} with {2 if image2_content else 1} image(s)")

        # Start processing in background and register task
        task = asyncio.create_task(generate_image_task(job_id))
        job_manager.register_task(job_id, task)

        # Add exception callback to log unhandled errors
        def task_done_callback(t):
            try:
                t.result()  # This will raise if task had an exception
            except asyncio.CancelledError:
                pass  # Expected for cancelled tasks
            except Exception as e:
                logger.error(f"Unhandled error in background task for job {job_id}: {e}", exc_info=True)

        task.add_done_callback(task_done_callback)

        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Image editing job created and processing"
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in config parameter")
    except HTTPException:
        raise  # Re-raise HTTP exceptions from validation
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of an image editing job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(**job)


@app.get("/api/jobs/{job_id}/download")
async def download_image(job_id: str):
    """
    Download edited image
    Cleanup happens client-side after successful download
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job['status'] != JobStatus.COMPLETE.value:
        raise HTTPException(status_code=400, detail="Job not complete yet")

    output_path = JOBS_DIR / job_id / 'output.jpg'
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output image not found")

    # Note: Cleanup should be done by DELETE endpoint after successful download
    # Don't auto-delete here as download could fail/be interrupted
    return FileResponse(
        output_path,
        media_type="image/jpeg",
        filename=f"edited_{job_id}.jpg"
    )


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Manually delete a job and its files"""
    if not job_manager.get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")

    success = job_manager.delete_job(job_id)
    if success:
        return {"message": f"Job {job_id} deleted successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete job")


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time progress updates
    Broadcasts job status and progress to connected clients
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for job {job_id}")

    # Register connection
    job_manager.add_ws_connection(job_id, websocket)

    try:
        # Send initial status
        job = job_manager.get_job(job_id)
        if job:
            await websocket.send_json({
                "status": job['status'],
                "progress": job.get('progress'),
                "error": job.get('error')
            })

        # Keep connection alive and listen for disconnect
        while True:
            try:
                # Just receive to detect disconnection
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {str(e)}")

    finally:
        # Cleanup connection
        job_manager.remove_ws_connection(job_id, websocket)
        logger.info(f"WebSocket disconnected for job {job_id}")


@app.post("/api/cleanup")
async def cleanup_old_jobs(hours: int = 1):
    """
    Manually trigger cleanup of old jobs
    Default: Remove jobs older than 1 hour
    """
    try:
        import time
        cutoff_time = time.time() - (hours * 3600)
        deleted = []

        for job_id in list(job_manager.jobs.keys()):
            job = job_manager.get_job(job_id)
            if job and job.get('created_at', 0) < cutoff_time:
                if job_manager.delete_job(job_id):
                    deleted.append(job_id)

        return {
            "message": f"Cleaned up {len(deleted)} jobs older than {hours} hour(s)",
            "deleted": deleted
        }

    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        log_level="info",
        ws_ping_interval=20,  # Send ping every 20 seconds
        ws_ping_timeout=20,   # Wait 20 seconds for pong
        timeout_keep_alive=75,  # Keep connections alive longer
        proxy_headers=True,   # Trust proxy headers (X-Forwarded-*)
        forwarded_allow_ips="*"  # Allow all IPs for proxy forwarding
    )
