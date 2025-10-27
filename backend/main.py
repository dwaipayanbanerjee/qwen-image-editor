"""
Qwen Image Editor API - FastAPI Backend
Runs on RunPod A40 GPU, designed for persistence in /workspace
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
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

# Global instances
job_manager = JobManager(JOBS_DIR)
image_editor: Optional[ImageEditor] = None
generation_queue = asyncio.Queue()


async def process_generation_queue():
    """Background worker to process image editing jobs sequentially"""
    global image_editor

    while True:
        job_id = await generation_queue.get()
        logger.info(f"Processing job {job_id}")

        try:
            await generate_image_task(job_id)
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {str(e)}")
            job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))
        finally:
            generation_queue.task_done()


async def generate_image_task(job_id: str):
    """Execute image editing task in thread pool executor"""
    global image_editor

    # Lazy load the model (only on first use)
    if image_editor is None:
        logger.info("Loading Qwen-Image-Edit model...")
        job_manager.update_progress(
            job_id,
            stage="loading_model",
            message="Loading Qwen model (first time only)..."
        )
        image_editor = ImageEditor()
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

    # Progress callback
    def progress_callback(stage: str, message: str, progress: int = 0):
        job_manager.update_progress(
            job_id,
            stage=stage,
            message=message,
            progress=progress
        )

    # Update status to processing
    job_manager.set_status(job_id, JobStatus.PROCESSING)
    progress_callback("editing", "Starting image editing...", 0)

    try:
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
            progress_callback
        )

        # Mark as complete
        job_manager.set_status(job_id, JobStatus.COMPLETE)
        progress_callback("complete", "Image editing complete!", 100)
        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Error editing image for job {job_id}: {str(e)}")
        job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Qwen Image Editor API...")
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    # Start background worker
    worker_task = asyncio.create_task(process_generation_queue())

    yield

    # Shutdown
    logger.info("Shutting down...")
    worker_task.cancel()


# FastAPI app
app = FastAPI(
    title="Qwen Image Editor API",
    description="AI-powered image editing using Qwen-Image-Edit model",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        # Parse config
        config_dict = json.loads(config)
        edit_config = EditConfig(**config_dict)

        # Validate images
        if not image1.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="image1 must be an image file")

        if image2 and not image2.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="image2 must be an image file")

        # Create job
        job_id = job_manager.create_job(edit_config.dict())
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Save input images
        image1_path = job_dir / 'input_1.jpg'
        with open(image1_path, 'wb') as f:
            content = await image1.read()
            f.write(content)

        if image2:
            image2_path = job_dir / 'input_2.jpg'
            with open(image2_path, 'wb') as f:
                content = await image2.read()
                f.write(content)

        logger.info(f"Created job {job_id} with {2 if image2 else 1} image(s)")

        # Queue for processing
        await generation_queue.put(job_id)

        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Image editing job created and queued"
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in config parameter")
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get status of an image editing job"""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(**job)


@app.get("/api/jobs/{job_id}/download")
async def download_image(job_id: str, background_tasks: BackgroundTasks):
    """
    Download edited image
    Triggers automatic cleanup in background after download starts
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job['status'] != JobStatus.COMPLETE.value:
        raise HTTPException(status_code=400, detail="Job not complete yet")

    output_path = JOBS_DIR / job_id / 'output.jpg'
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output image not found")

    # Trigger cleanup in background after download
    background_tasks.add_task(job_manager.delete_job, job_id)

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
        log_level="info"
    )
