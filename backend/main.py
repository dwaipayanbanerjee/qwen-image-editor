"""
Image Editor/Generator API - FastAPI Backend
Supports two distinct workflows:
- IMAGE EDITING: Preserves input dimensions exactly (qwen_gguf, qwen_image_edit, qwen_image_edit_plus)
- IMAGE GENERATION: Text-to-image with aspect ratio control (hunyuan, qwen_image)
- HYBRID: Flexible editing or generation (seedream)
"""

import os
from dotenv import load_dotenv

# CRITICAL: Load .env BEFORE importing torch (via image_editor)
# PYTORCH_CUDA_ALLOC_CONF must be set before PyTorch initialization
load_dotenv()

# Apply PyTorch memory optimization if not already set
if 'PYTORCH_CUDA_ALLOC_CONF' not in os.environ:
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from pathlib import Path
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import json
import logging
from PIL import Image

from image_editor import ImageEditor
from job_manager import JobManager, JobStatus
from models import EditConfig, JobStatusResponse, ProgressInfo, ModelType
from replicate_client import (
    ReplicateClient,
    SEEDREAM_PRICE_PER_IMAGE,
    QWEN_IMAGE_EDIT_PRICE,
    QWEN_IMAGE_EDIT_PLUS_PRICE,
    QWEN_IMAGE_PRICE,
    HUNYUAN_IMAGE_PRICE
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment setup for RunPod persistence
os.environ['HF_HOME'] = os.getenv('HF_HOME', '/workspace/huggingface_cache')
os.environ['TRANSFORMERS_CACHE'] = os.getenv('TRANSFORMERS_CACHE', '/workspace/huggingface_cache')
os.environ['HF_DATASETS_CACHE'] = os.getenv('HF_DATASETS_CACHE', '/workspace/huggingface_cache')

# Configuration
JOBS_DIR = Path(os.getenv('JOBS_DIR', '/workspace/jobs'))
INPUT_FOLDER = Path(os.path.expanduser(os.getenv('INPUT_FOLDER', '~/input')))
OUTPUT_FOLDER = Path(os.path.expanduser(os.getenv('OUTPUT_FOLDER', '~/output')))
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', '8000'))
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')

# Global instances
job_manager = JobManager(JOBS_DIR)
image_editor: Optional[ImageEditor] = None  # Standard Qwen model
image_editor_gguf: Optional[ImageEditor] = None  # GGUF quantized model
replicate_client: Optional[ReplicateClient] = None
job_queue: asyncio.Queue = asyncio.Queue(maxsize=10)  # Limit concurrent jobs
active_job_semaphore: asyncio.Semaphore = asyncio.Semaphore(1)  # Only 1 job at a time on GPU
executor_futures: Dict[str, Any] = {}  # Track futures for cleanup


def copy_outputs_to_folder(job_id: str, output_images: List[str]) -> None:
    """
    Copy output images to the default output folder (~/output)

    Args:
        job_id: Job identifier
        output_images: List of output image filenames
    """
    try:
        job_dir = JOBS_DIR / job_id

        for filename in output_images:
            source = job_dir / filename
            if source.exists():
                # Create unique filename with job_id prefix to avoid conflicts
                dest_filename = f"{job_id}_{filename}"
                dest = OUTPUT_FOLDER / dest_filename

                import shutil
                shutil.copy2(source, dest)
                logger.info(f"Copied {filename} to output folder as {dest_filename}")

    except Exception as e:
        logger.error(f"Error copying outputs to folder for job {job_id}: {str(e)}")
        # Non-critical, don't raise


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

    # Validate actual image format using PIL
    try:
        img = Image.open(BytesIO(content))
        image_format = img.format.lower() if img.format else None

        # Verify image can be loaded
        img.verify()

        # Check format is supported
        allowed_formats = ['jpeg', 'png', 'webp', 'bmp', 'jpg']
        if image_format not in allowed_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Allowed: JPEG, PNG, WebP, BMP. Detected: {image_format or 'unknown'}"
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or corrupted image file: {str(e)}"
        )

    return content


async def generate_image_qwen_cloud(job_id: str) -> None:
    """Execute simple image editing using qwen/qwen-image-edit"""
    global replicate_client

    try:
        if replicate_client is None:
            logger.info("Initializing Replicate client...")
            replicate_client = ReplicateClient()

        if job_manager.is_cancelled(job_id):
            return

        job = job_manager.get_job(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")

        config = EditConfig(**job['config'])
        job_dir = JOBS_DIR / job_id

        input_paths = []
        if (job_dir / 'input_1.jpg').exists():
            input_paths.append(str(job_dir / 'input_1.jpg'))

        if not input_paths:
            raise Exception("No input images found")

        def progress_callback(stage: str, message: str, progress: int = 0):
            if job_manager.is_cancelled(job_id):
                raise asyncio.CancelledError("Job cancelled by user")
            job_manager.update_progress(job_id, stage=stage, message=message, progress=progress)

        progress_callback("preparing", "Starting Qwen-Image-Edit cloud...", 5)

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            replicate_client.edit_image_qwen_cloud,
            input_paths,
            config.prompt,
            config.output_quality,
            config.output_format,
            config.disable_safety_checker,
            job_dir,
            progress_callback,
            lambda: job_manager.is_cancelled(job_id)
        )
        executor_futures[job_id] = future

        try:
            output_paths = await future
        finally:
            if job_id in executor_futures:
                del executor_futures[job_id]

        if job_manager.is_cancelled(job_id):
            return

        output_filenames = [Path(p).name for p in output_paths]
        job_manager.update_job_data(job_id, {
            'cost': QWEN_IMAGE_EDIT_PRICE,
            'images_generated': len(output_paths),
            'output_images': output_filenames
        })

        # Copy outputs to ~/output folder
        copy_outputs_to_folder(job_id, output_filenames)

        job_manager.set_status(job_id, JobStatus.COMPLETE)
        progress_callback("complete", f"Qwen-Image-Edit complete! Cost: ${QWEN_IMAGE_EDIT_PRICE:.3f}", 100)
        logger.info(f"Job {job_id} completed with qwen/qwen-image-edit")

    except asyncio.CancelledError:
        job_manager.set_status(job_id, JobStatus.ERROR, error="Job cancelled by user")
    except Exception as e:
        logger.error(f"Error in Qwen-Image-Edit for job {job_id}: {str(e)}", exc_info=True)
        job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))


async def generate_image_qwen_plus(job_id: str) -> None:
    """Execute advanced editing using qwen/qwen-image-edit-plus"""
    global replicate_client

    try:
        if replicate_client is None:
            replicate_client = ReplicateClient()

        if job_manager.is_cancelled(job_id):
            return

        job = job_manager.get_job(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")

        config = EditConfig(**job['config'])
        job_dir = JOBS_DIR / job_id

        input_paths = []
        for i in range(1, 4):  # Support 1-3 images per API spec
            path = job_dir / f'input_{i}.jpg'
            if path.exists():
                input_paths.append(str(path))

        if not input_paths:
            raise Exception("No input images found")

        def progress_callback(stage: str, message: str, progress: int = 0):
            if job_manager.is_cancelled(job_id):
                raise asyncio.CancelledError("Job cancelled by user")
            job_manager.update_progress(job_id, stage=stage, message=message, progress=progress)

        progress_callback("preparing", "Starting Qwen-Image-Edit-Plus...", 5)

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            replicate_client.edit_image_qwen_plus,
            input_paths,
            config.prompt,
            config.go_fast,
            "match_input_image",  # ALWAYS match input for EDIT models
            config.output_format,
            config.output_quality,
            config.disable_safety_checker,
            job_dir,
            progress_callback,
            lambda: job_manager.is_cancelled(job_id)
        )
        executor_futures[job_id] = future

        try:
            output_paths = await future
        finally:
            if job_id in executor_futures:
                del executor_futures[job_id]

        if job_manager.is_cancelled(job_id):
            return

        output_filenames = [Path(p).name for p in output_paths]
        job_manager.update_job_data(job_id, {
            'cost': QWEN_IMAGE_EDIT_PLUS_PRICE,
            'images_generated': len(output_paths),
            'output_images': output_filenames
        })

        # Copy outputs to ~/output folder
        copy_outputs_to_folder(job_id, output_filenames)

        job_manager.set_status(job_id, JobStatus.COMPLETE)
        progress_callback("complete", f"Qwen-Image-Edit-Plus complete! Cost: ${QWEN_IMAGE_EDIT_PLUS_PRICE:.3f}", 100)
        logger.info(f"Job {job_id} completed with qwen/qwen-image-edit-plus")

    except asyncio.CancelledError:
        job_manager.set_status(job_id, JobStatus.ERROR, error="Job cancelled by user")
    except Exception as e:
        logger.error(f"Error in Qwen-Image-Edit-Plus for job {job_id}: {str(e)}", exc_info=True)
        job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))


async def generate_image_qwen_text_to_image(job_id: str) -> None:
    """Execute text-to-image generation using qwen/qwen-image"""
    global replicate_client

    try:
        if replicate_client is None:
            replicate_client = ReplicateClient()

        if job_manager.is_cancelled(job_id):
            return

        job = job_manager.get_job(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")

        config = EditConfig(**job['config'])
        job_dir = JOBS_DIR / job_id

        def progress_callback(stage: str, message: str, progress: int = 0):
            if job_manager.is_cancelled(job_id):
                raise asyncio.CancelledError("Job cancelled by user")
            job_manager.update_progress(job_id, stage=stage, message=message, progress=progress)

        progress_callback("preparing", "Starting Qwen-Image text-to-image...", 5)

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            replicate_client.generate_image_qwen,
            config.prompt,
            config.negative_prompt or " ",
            config.go_fast,
            config.guidance,
            config.strength,
            config.image_size,
            config.lora_scale,
            config.aspect_ratio or "16:9",
            config.output_format,
            config.enhance_prompt_qwen,
            config.output_quality,
            config.num_inference_steps,
            config.disable_safety_checker,
            job_dir,
            progress_callback,
            lambda: job_manager.is_cancelled(job_id)
        )
        executor_futures[job_id] = future

        try:
            output_paths = await future
        finally:
            if job_id in executor_futures:
                del executor_futures[job_id]

        if job_manager.is_cancelled(job_id):
            return

        output_filenames = [Path(p).name for p in output_paths]
        job_manager.update_job_data(job_id, {
            'cost': QWEN_IMAGE_PRICE,
            'images_generated': len(output_paths),
            'output_images': output_filenames
        })

        # Copy outputs to ~/output folder
        copy_outputs_to_folder(job_id, output_filenames)

        job_manager.set_status(job_id, JobStatus.COMPLETE)
        progress_callback("complete", f"Qwen-Image complete! Cost: ${QWEN_IMAGE_PRICE:.3f}", 100)
        logger.info(f"Job {job_id} completed with qwen/qwen-image")

    except asyncio.CancelledError:
        job_manager.set_status(job_id, JobStatus.ERROR, error="Job cancelled by user")
    except Exception as e:
        logger.error(f"Error in Qwen-Image for job {job_id}: {str(e)}", exc_info=True)
        job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))


async def generate_image_seedream(job_id: str) -> None:
    """
    Execute image generation using Seedream-4 via Replicate API
    """
    global replicate_client

    try:
        # Lazy load Replicate client
        if replicate_client is None:
            logger.info("Initializing Replicate client...")
            replicate_client = ReplicateClient()

        # Check for cancellation
        if job_manager.is_cancelled(job_id):
            logger.info(f"Job {job_id} was cancelled before starting")
            return

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
            if job_manager.is_cancelled(job_id):
                raise asyncio.CancelledError("Job cancelled by user")
            job_manager.update_progress(job_id, stage=stage, message=message, progress=progress)

        progress_callback("preparing", "Starting Seedream-4 generation...", 5)

        # Calculate cost
        estimated_cost = replicate_client.calculate_cost("seedream", config.max_images)
        logger.info(f"Estimated cost for job {job_id}: ${estimated_cost:.2f} ({config.max_images} images)")

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            replicate_client.edit_image,
            input_paths,
            config.prompt,
            config.size,
            config.aspect_ratio,
            config.enhance_prompt,
            config.sequential_image_generation,
            config.max_images,
            config.disable_safety_checker,
            job_dir,
            progress_callback,
            lambda: job_manager.is_cancelled(job_id)
        )
        executor_futures[job_id] = future

        try:
            output_paths = await future
        finally:
            if job_id in executor_futures:
                del executor_futures[job_id]

        # Check cancellation
        if job_manager.is_cancelled(job_id):
            logger.info(f"Job {job_id} cancelled after generation")
            return

        # Calculate actual cost based on output images
        actual_cost = replicate_client.calculate_cost("seedream", len(output_paths))

        # Get relative paths for output images
        output_filenames = [Path(p).name for p in output_paths]

        # Update job with cost info and output images list
        job_manager.update_job_data(job_id, {
            'cost': actual_cost,
            'images_generated': len(output_paths),
            'output_images': output_filenames
        })

        # Copy outputs to ~/output folder
        copy_outputs_to_folder(job_id, output_filenames)

        # Mark as complete
        job_manager.set_status(job_id, JobStatus.COMPLETE)
        progress_callback("complete", f"Seedream-4 complete! Generated {len(output_paths)} image(s). Cost: ${actual_cost:.2f}", 100)
        logger.info(f"Job {job_id} completed successfully. Generated {len(output_paths)} images. Cost: ${actual_cost:.2f}")

    except asyncio.CancelledError:
        logger.info(f"Job {job_id} was cancelled")
        job_manager.set_status(job_id, JobStatus.ERROR, error="Job cancelled by user")
    except Exception as e:
        logger.error(f"Error in Seedream generation for job {job_id}: {str(e)}", exc_info=True)
        job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))


async def generate_image_hunyuan(job_id: str) -> None:
    """
    Execute image generation using Hunyuan Image 3 via Replicate API
    """
    global replicate_client

    try:
        # Lazy load Replicate client
        if replicate_client is None:
            logger.info("Initializing Replicate client...")
            replicate_client = ReplicateClient()

        # Check for cancellation
        if job_manager.is_cancelled(job_id):
            logger.info(f"Job {job_id} was cancelled before starting")
            return

        # Get job metadata
        job = job_manager.get_job(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")

        config = EditConfig(**job['config'])
        job_dir = JOBS_DIR / job_id

        # Progress callback
        def progress_callback(stage: str, message: str, progress: int = 0):
            if job_manager.is_cancelled(job_id):
                raise asyncio.CancelledError("Job cancelled by user")
            job_manager.update_progress(job_id, stage=stage, message=message, progress=progress)

        progress_callback("preparing", "Starting Hunyuan Image 3 generation...", 5)

        # Calculate cost
        estimated_cost = replicate_client.calculate_cost("hunyuan", 1)
        logger.info(f"Estimated cost for job {job_id}: ${estimated_cost:.2f}")

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            replicate_client.generate_image_hunyuan,
            config.prompt,
            config.aspect_ratio or "1:1",
            config.go_fast,
            config.seed,
            config.output_format,
            config.output_quality,
            config.disable_safety_checker,
            job_dir,
            progress_callback,
            lambda: job_manager.is_cancelled(job_id)
        )
        executor_futures[job_id] = future

        try:
            output_paths = await future
        finally:
            if job_id in executor_futures:
                del executor_futures[job_id]

        # Check cancellation
        if job_manager.is_cancelled(job_id):
            logger.info(f"Job {job_id} cancelled after generation")
            return

        # Calculate actual cost
        actual_cost = replicate_client.calculate_cost("hunyuan", len(output_paths))

        # Get relative paths for output images
        output_filenames = [Path(p).name for p in output_paths]

        # Update job with cost info and output images list
        job_manager.update_job_data(job_id, {
            'cost': actual_cost,
            'images_generated': len(output_paths),
            'output_images': output_filenames
        })

        # Copy outputs to ~/output folder
        copy_outputs_to_folder(job_id, output_filenames)

        # Mark as complete
        job_manager.set_status(job_id, JobStatus.COMPLETE)
        progress_callback("complete", f"Hunyuan Image 3 complete! Cost: ${actual_cost:.2f}", 100)
        logger.info(f"Job {job_id} completed successfully. Cost: ${actual_cost:.2f}")

    except asyncio.CancelledError:
        logger.info(f"Job {job_id} was cancelled")
        job_manager.set_status(job_id, JobStatus.ERROR, error="Job cancelled by user")
    except Exception as e:
        logger.error(f"Error in Hunyuan generation for job {job_id}: {str(e)}", exc_info=True)
        job_manager.set_status(job_id, JobStatus.ERROR, error=str(e))


async def generate_image_task(job_id: str) -> None:
    """
    Execute image editing/generation task - routes to appropriate model

    WORKFLOW CATEGORIES:
    - EDIT models: qwen_gguf, qwen_image_edit, qwen_image_edit_plus (preserve dimensions)
    - GENERATION models: hunyuan, qwen_image (aspect ratio control)
    - HYBRID models: seedream (flexible)

    Supports cancellation and proper error handling
    """
    global image_editor, image_editor_gguf

    try:
        # Get job config to determine which model to use
        job = job_manager.get_job(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")

        config = EditConfig(**job['config'])

        # Route to appropriate model (GENERATION models first)
        if config.model_type == ModelType.HUNYUAN:
            logger.info(f"Job {job_id} using Hunyuan Image 3 (GENERATION)")
            await generate_image_hunyuan(job_id)
            return
        elif config.model_type == ModelType.QWEN_IMAGE:
            logger.info(f"Job {job_id} using Qwen-Image text-to-image (GENERATION)")
            await generate_image_qwen_text_to_image(job_id)
            return
        # HYBRID model
        elif config.model_type == ModelType.SEEDREAM:
            logger.info(f"Job {job_id} using Seedream-4 model")
            await generate_image_seedream(job_id)
            return
        # EDIT models (cloud)
        elif config.model_type == ModelType.QWEN_IMAGE_EDIT:
            logger.info(f"Job {job_id} using Qwen-Image-Edit cloud (EDIT - preserves dimensions)")
            await generate_image_qwen_cloud(job_id)
            return
        elif config.model_type == ModelType.QWEN_IMAGE_EDIT_PLUS:
            logger.info(f"Job {job_id} using Qwen-Image-Edit-Plus (EDIT - preserves dimensions)")
            await generate_image_qwen_plus(job_id)
            return
        # EDIT model (local)
        elif config.model_type == ModelType.QWEN_GGUF:
            logger.info(f"Job {job_id} using Qwen GGUF (EDIT - preserves dimensions, {config.quantization_level})")
            use_gguf = True
            editor_instance_name = "image_editor_gguf"
        else:
            raise Exception(f"Unknown model type: {config.model_type}")

        # Qwen processing starts here (both standard and GGUF)
        # Acquire semaphore to limit concurrent GPU jobs
        async with active_job_semaphore:
            # Check for cancellation
            if job_manager.is_cancelled(job_id):
                logger.info(f"Job {job_id} was cancelled before starting")
                return

            # Lazy load the model (only on first use)
            editor = image_editor_gguf if use_gguf else image_editor

            if editor is None:
                model_desc = f"GGUF ({config.quantization_level})" if use_gguf else "standard"
                logger.info(f"Loading Qwen-Image-Edit {model_desc} model...")
                job_manager.update_progress(
                    job_id,
                    stage="loading_model",
                    message=f"Loading Qwen {model_desc} model (first time: ~10-30 min, subsequent: ~30 sec)...",
                    progress=5
                )

                # Create progress callback that updates job progress
                def model_loading_callback(progress_percent):
                    """Callback for model loading progress"""
                    if progress_percent < 80:
                        message = f"Downloading model files... {progress_percent}%"
                    else:
                        message = f"Loading model to GPU... {progress_percent}%"

                    job_manager.update_progress(
                        job_id,
                        stage="loading_model",
                        message=message,
                        progress=5 + int(progress_percent * 0.15)  # 5-20%
                    )

                # Create the appropriate editor instance
                if use_gguf:
                    image_editor_gguf = ImageEditor(
                        progress_callback=model_loading_callback,
                        use_gguf=True,
                        quantization_level=config.quantization_level
                    )
                    editor = image_editor_gguf
                else:
                    image_editor = ImageEditor(progress_callback=model_loading_callback)
                    editor = image_editor

                # Mark model loading complete
                job_manager.update_progress(
                    job_id,
                    stage="loading_model",
                    message=f"Model loaded successfully ({model_desc})",
                    progress=20
                )
                logger.info(f"Model loaded successfully ({model_desc})")

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

            # Track the future for cleanup
            future = loop.run_in_executor(
                None,
                editor.edit_image,
                input_paths,
                config.prompt,
                config.negative_prompt,
                config.true_cfg_scale,
                config.num_inference_steps,
                str(job_dir / 'output.jpg'),
                progress_callback,
                lambda: job_manager.is_cancelled(job_id)  # Cancellation checker
            )
            executor_futures[job_id] = future

            try:
                output_path = await future
            finally:
                # Clean up future reference
                if job_id in executor_futures:
                    del executor_futures[job_id]

            # Final cancellation check
            if job_manager.is_cancelled(job_id):
                logger.info(f"Job {job_id} cancelled after inference")
                return

            # Mark as complete and store output image
            output_filenames = ['output.jpg']
            job_manager.update_job_data(job_id, {
                'output_images': output_filenames  # Qwen always generates single output
            })

            # Copy outputs to ~/output folder
            copy_outputs_to_folder(job_id, output_filenames)

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
    logger.info("Starting Image Editor API...")
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    logger.info(f"Input folder: {INPUT_FOLDER}")
    logger.info(f"Output folder: {OUTPUT_FOLDER}")

    # Set event loop in job_manager for WebSocket broadcasting
    loop = asyncio.get_running_loop()
    job_manager.set_event_loop(loop)
    logger.info("Event loop registered with JobManager")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Request cancellation for all active jobs
    for job_id in list(job_manager.job_tasks.keys()):
        logger.info(f"Requesting cancellation for job {job_id}")
        job_manager.request_cancellation(job_id)

    # Cancel asyncio tasks
    for job_id, task in list(job_manager.job_tasks.items()):
        if not task.done():
            logger.info(f"Cancelling asyncio task for job {job_id}")
            task.cancel()

    # Wait for executor futures with timeout
    if executor_futures:
        logger.warning(f"Waiting up to 5 seconds for {len(executor_futures)} inference thread(s) to finish...")
        logger.warning("Note: Diffusers pipeline cannot be interrupted mid-inference")

        try:
            # Give threads 5 seconds to finish gracefully
            await asyncio.wait_for(
                asyncio.gather(*[f for f in executor_futures.values()], return_exceptions=True),
                timeout=5.0
            )
            logger.info("All inference threads completed")
        except asyncio.TimeoutError:
            logger.warning("Inference threads did not complete in time - forcing shutdown")
            logger.warning("GPU memory may not be fully released until process terminates")

    # Force GPU cleanup if image_editor is loaded
    if image_editor is not None:
        try:
            logger.info("Clearing GPU cache...")
            import torch
            import gc
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif torch.backends.mps.is_available():
                torch.mps.empty_cache()
            gc.collect()
            logger.info("GPU cache cleared")
        except Exception as e:
            logger.error(f"Error clearing GPU cache: {e}")

    logger.info("Shutdown complete")


# FastAPI app
app = FastAPI(
    title="Image Editor API",
    description="AI-powered image editing with Qwen, GGUF, and Seedream models",
    version="2.0.0",
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


@app.get("/api/input-folder/list")
async def list_input_folder():
    """
    List images in the default input folder (~/input)

    Returns:
        List of image files with metadata
    """
    try:
        if not INPUT_FOLDER.exists():
            return {
                "folder": str(INPUT_FOLDER),
                "images": [],
                "count": 0
            }

        # Supported image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

        images = []
        for file_path in INPUT_FOLDER.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                try:
                    from PIL import Image
                    img = Image.open(file_path)
                    images.append({
                        'filename': file_path.name,
                        'size_bytes': file_path.stat().st_size,
                        'width': img.width,
                        'height': img.height,
                        'modified': file_path.stat().st_mtime
                    })
                except:
                    # If can't open as image, just include basic info
                    images.append({
                        'filename': file_path.name,
                        'size_bytes': file_path.stat().st_size,
                        'modified': file_path.stat().st_mtime
                    })

        # Sort by modified time (newest first)
        images.sort(key=lambda x: x.get('modified', 0), reverse=True)

        return {
            "folder": str(INPUT_FOLDER),
            "images": images,
            "count": len(images)
        }

    except Exception as e:
        logger.error(f"Error listing input folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Health check endpoint"""
    import torch

    # Detect device
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"

    return {
        "status": "online",
        "message": "Image Editor API is running",
        "device": device,
        "input_folder": str(INPUT_FOLDER),
        "output_folder": str(OUTPUT_FOLDER),
        "models": {
            "qwen_gguf": {
                "name": "Qwen-Image-Edit-2509-GGUF",
                "type": "local_edit",
                "workflow": "editing",
                "cost": "free",
                "description": "Local quantized model - preserves input dimensions",
                "inputs": "1-2 images",
                "outputs": "1 image (matches input size)"
            },
            "qwen_image_edit": {
                "name": "Qwen-Image-Edit",
                "type": "cloud_edit",
                "workflow": "editing",
                "cost": f"${QWEN_IMAGE_EDIT_PRICE}/prediction",
                "description": "Simple cloud editing - preserves input dimensions",
                "inputs": "1 image",
                "outputs": "1 image (matches input size)"
            },
            "qwen_image_edit_plus": {
                "name": "Qwen-Image-Edit-Plus",
                "type": "cloud_edit",
                "workflow": "editing",
                "cost": f"${QWEN_IMAGE_EDIT_PLUS_PRICE}/prediction",
                "description": "Advanced multi-image editing - preserves input dimensions",
                "inputs": "1-3 images",
                "outputs": "1 image (matches first image size)"
            },
            "hunyuan": {
                "name": "Tencent Hunyuan Image 3",
                "type": "cloud_generation",
                "workflow": "generation",
                "cost": f"${HUNYUAN_IMAGE_PRICE}/prediction",
                "description": "80B text-to-image model - configurable aspect ratio",
                "inputs": "text only",
                "outputs": "1 image (user-controlled size)"
            },
            "qwen_image": {
                "name": "Qwen-Image",
                "type": "cloud_generation",
                "workflow": "generation",
                "cost": f"${QWEN_IMAGE_PRICE}/prediction",
                "description": "Text-to-image generation - configurable aspect ratio",
                "inputs": "text only",
                "outputs": "1 image (user-controlled size)"
            },
            "seedream": {
                "name": "ByteDance Seedream-4",
                "type": "cloud_hybrid",
                "workflow": "hybrid",
                "cost": f"${SEEDREAM_PRICE_PER_IMAGE}/image",
                "description": "Hybrid model - can edit (with images) or generate (text-only)",
                "inputs": "0-10 images (optional)",
                "outputs": "1-15 images (flexible size)"
            }
        }
    }


@app.get("/api/input-folder/image/{filename}")
async def get_input_folder_image(filename: str):
    """
    Serve an image from the input folder

    Args:
        filename: Image filename

    Returns:
        Image file
    """
    try:
        # SECURITY: Prevent path traversal attacks
        # Resolve the path and ensure it stays within INPUT_FOLDER
        file_path = (INPUT_FOLDER / filename).resolve()
        input_folder_resolved = INPUT_FOLDER.resolve()

        # Check if the resolved path is within INPUT_FOLDER
        try:
            file_path.relative_to(input_folder_resolved)
        except ValueError:
            # Path is outside INPUT_FOLDER
            logger.warning(f"Path traversal attempt blocked: {filename}")
            raise HTTPException(status_code=403, detail="Access denied: path traversal detected")

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Image not found in input folder")

        if file_path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}:
            raise HTTPException(status_code=400, detail="Invalid image format")

        # Determine media type
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp'
        }
        media_type = media_type_map.get(file_path.suffix.lower(), 'image/jpeg')

        return FileResponse(
            file_path,
            media_type=media_type,
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving input folder image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/input-folder/load")
async def load_from_input_folder(filenames: list[str]):
    """
    Load images from input folder by filename

    Args:
        filenames: List of filenames to load from ~/input

    Returns:
        Job ID with loaded images
    """
    try:
        # Validate files exist
        file_paths = []
        input_folder_resolved = INPUT_FOLDER.resolve()

        for filename in filenames[:10]:  # Max 10 images
            # SECURITY: Prevent path traversal attacks
            file_path = (INPUT_FOLDER / filename).resolve()

            # Check if the resolved path is within INPUT_FOLDER
            try:
                file_path.relative_to(input_folder_resolved)
            except ValueError:
                logger.warning(f"Path traversal attempt blocked: {filename}")
                raise HTTPException(status_code=403, detail=f"Access denied: path traversal detected for {filename}")

            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"File not found: {filename}")
            if file_path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}:
                raise HTTPException(status_code=400, detail=f"Invalid image format: {filename}")
            file_paths.append(file_path)

        if not file_paths:
            raise HTTPException(status_code=400, detail="No valid images specified")

        return {
            "status": "success",
            "images_loaded": len(file_paths),
            "filenames": [p.name for p in file_paths],
            "message": f"Loaded {len(file_paths)} images from input folder"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading from input folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/edit")
async def edit_image(
    image1: Optional[UploadFile] = File(None, description="Primary input image (optional for text-to-image models)"),
    image2: Optional[UploadFile] = File(None, description="Optional second image for combining"),
    config: str = Form(..., description="JSON config with prompt and parameters")
):
    """
    Create new image editing job

    Args:
        image1: Primary image file (required for image editing, optional for text-to-image)
        image2: Second image file (optional, for combining)
        config: JSON string with EditConfig fields

    Returns:
        Job ID and status
    """
    try:
        # Parse and validate config
        config_dict = json.loads(config)
        edit_config = EditConfig(**config_dict)

        # Text-to-image models (no input images required)
        text_to_image_models = {ModelType.HUNYUAN, ModelType.QWEN_IMAGE}

        # Validate that appropriate images are provided
        if edit_config.model_type not in text_to_image_models and not image1:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{edit_config.model_type}' requires at least one input image"
            )

        # Validate image files (size and format)
        image1_content = None
        if image1:
            image1_content = await validate_image_file(image1)

        image2_content = None
        if image2:
            image2_content = await validate_image_file(image2)

        # Create job
        job_id = job_manager.create_job(edit_config.model_dump())
        job_dir = JOBS_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Save validated input images (if any)
        image_count = 0
        if image1_content:
            image1_path = job_dir / 'input_1.jpg'
            with open(image1_path, 'wb') as f:
                f.write(image1_content)
            image_count += 1

        if image2_content:
            image2_path = job_dir / 'input_2.jpg'
            with open(image2_path, 'wb') as f:
                f.write(image2_content)
            image_count += 1

        logger.info(f"Created job {job_id} with {image_count} image(s) for model {edit_config.model_type}")

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


@app.get("/api/jobs/{job_id}/images")
async def list_output_images(job_id: str):
    """
    List all output images for a job

    Returns:
        List of output image filenames with metadata
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job['status'] != JobStatus.COMPLETE.value:
        raise HTTPException(status_code=400, detail="Job not complete yet")

    output_images = job.get('output_images', ['output.jpg'])
    job_dir = JOBS_DIR / job_id

    # Build response with image metadata
    images_info = []
    for index, filename in enumerate(output_images):
        img_path = job_dir / filename
        if img_path.exists():
            from PIL import Image
            try:
                img = Image.open(img_path)
                images_info.append({
                    'index': index,
                    'filename': filename,
                    'width': img.width,
                    'height': img.height,
                    'size_bytes': img_path.stat().st_size,
                    'download_url': f"/api/jobs/{job_id}/images/{index}"
                })
            except:
                images_info.append({
                    'index': index,
                    'filename': filename,
                    'download_url': f"/api/jobs/{job_id}/images/{index}"
                })

    return {
        'job_id': job_id,
        'images_count': len(images_info),
        'images': images_info
    }


@app.get("/api/jobs/{job_id}/images/{image_index}")
async def download_image_by_index(job_id: str, image_index: int):
    """
    Download specific output image by index

    Args:
        job_id: Job identifier
        image_index: Index of the image (0-based)

    Returns:
        Image file
    """
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job['status'] != JobStatus.COMPLETE.value:
        raise HTTPException(status_code=400, detail="Job not complete yet")

    output_images = job.get('output_images', ['output.jpg'])

    if image_index < 0 or image_index >= len(output_images):
        raise HTTPException(status_code=404, detail=f"Image index {image_index} out of range (0-{len(output_images)-1})")

    filename = output_images[image_index]
    output_path = JOBS_DIR / job_id / filename

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output image not found")

    return FileResponse(
        output_path,
        media_type="image/jpeg",
        filename=f"edited_{job_id}_{image_index}.jpg"
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
