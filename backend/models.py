"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    """Job status enumeration"""
    PROCESSING = "processing"
    COMPLETE = "complete"
    ERROR = "error"


class ModelType(str, Enum):
    """Available image editing models"""
    QWEN = "qwen"  # Local Qwen-Image-Edit model (free, slower)
    SEEDREAM = "seedream"  # Replicate Seedream-4 model ($0.03/image, faster)


class EditConfig(BaseModel):
    """
    Configuration for image editing request

    Attributes:
        model_type: Which model to use (qwen or seedream)
        prompt: Edit instruction (e.g., "make the sky sunset colors")
        negative_prompt: What to avoid in the output (Qwen only)

        # Qwen-specific parameters:
        true_cfg_scale: Classifier-free guidance scale (higher = more prompt adherence)
        num_inference_steps: Number of diffusion steps (higher = better quality but slower)

        # Seedream-specific parameters:
        size: Image resolution (1K, 2K, 4K, or custom)
        aspect_ratio: Aspect ratio (e.g., "4:3", "16:9", "match_input_image")
        enhance_prompt: Enable prompt enhancement for better quality
        sequential_image_generation: Enable auto multi-image generation
        max_images: Max images to generate when sequential mode is auto
    """
    model_type: ModelType = Field(
        ModelType.QWEN,
        description="Which model to use for image editing"
    )
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Edit instruction or description"
    )
    negative_prompt: Optional[str] = Field(
        None,
        max_length=300,
        description="What to avoid in the edited image (Qwen only)"
    )

    # Qwen-specific parameters
    true_cfg_scale: float = Field(
        4.0,
        ge=1.0,
        le=20.0,
        description="Classifier-free guidance scale (Qwen only)"
    )
    num_inference_steps: int = Field(
        50,
        ge=10,
        le=100,
        description="Number of diffusion steps (Qwen only)"
    )

    # Seedream-specific parameters
    size: Optional[str] = Field(
        "2K",
        description="Image resolution: 1K, 2K, 4K, or custom (Seedream only)"
    )
    aspect_ratio: Optional[str] = Field(
        "4:3",
        description="Aspect ratio like '4:3', '16:9', or 'match_input_image' (Seedream only)"
    )
    enhance_prompt: bool = Field(
        False,
        description="Enable prompt enhancement for better quality (Seedream only, slower)"
    )
    sequential_image_generation: Optional[str] = Field(
        "disabled",
        description="'disabled' or 'auto' for multi-image generation (Seedream only)"
    )
    max_images: int = Field(
        1,
        ge=1,
        le=15,
        description="Max images to generate in sequential mode (Seedream only)"
    )


class ProgressInfo(BaseModel):
    """
    Progress information for job tracking

    Attributes:
        stage: Current processing stage
        message: Human-readable progress message
        progress: Progress percentage (0-100)
        updated_at: Timestamp of last update
    """
    stage: str
    message: str
    progress: int = Field(ge=0, le=100)
    updated_at: float


class JobStatusResponse(BaseModel):
    """
    Response model for job status endpoint

    Attributes:
        job_id: Unique job identifier
        status: Current job status
        config: Original edit configuration
        progress: Current progress information (if processing)
        error: Error message (if failed)
        created_at: Job creation timestamp
        cost: Cost in USD (for paid models like Seedream)
        images_generated: Number of images generated (for multi-image generation)
    """
    job_id: str
    status: str
    config: dict
    progress: Optional[ProgressInfo] = None
    error: Optional[str] = None
    created_at: float
    cost: Optional[float] = None
    images_generated: Optional[int] = None


class JobCreateResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str
