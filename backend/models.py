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
    # Local models (free)
    QWEN = "qwen"  # Local Qwen-Image-Edit model (free, slower)
    QWEN_GGUF = "qwen_gguf"  # Quantized Qwen-Image-Edit-2509 model (free, faster, less VRAM)

    # Cloud models (paid via Replicate)
    SEEDREAM = "seedream"  # ByteDance Seedream-4 ($0.03/image, multi-output)
    QWEN_IMAGE_EDIT = "qwen_image_edit"  # Qwen-Image-Edit cloud ($0.01/image, simple edits)
    QWEN_IMAGE_EDIT_PLUS = "qwen_image_edit_plus"  # Qwen-Image-Edit-Plus ($0.02/image, pose/style transfer)
    QWEN_IMAGE = "qwen_image"  # Qwen-Image ($0.015/image, text-to-image generation)


class EditConfig(BaseModel):
    """
    Configuration for image editing request

    Attributes:
        model_type: Which model to use (qwen, qwen_gguf, or seedream)
        prompt: Edit instruction (e.g., "make the sky sunset colors")
        negative_prompt: What to avoid in the output (Qwen only)

        # Qwen-specific parameters:
        true_cfg_scale: Classifier-free guidance scale (higher = more prompt adherence)
        num_inference_steps: Number of diffusion steps (higher = better quality but slower)

        # Qwen GGUF-specific parameters:
        quantization_level: Quantization level (Q5_K_S recommended for balance)

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

    # Qwen GGUF-specific parameters
    quantization_level: Optional[str] = Field(
        "Q5_K_S",
        description="Quantization level: Q2_K (7GB), Q4_K_M (14GB), Q5_K_S (17GB), Q8_0 (22GB) (GGUF only)"
    )

    # Replicate cloud model common parameters
    output_format: Optional[str] = Field(
        "png",
        description="Output format: webp, jpg, png (Cloud models only)"
    )
    output_quality: int = Field(
        100,
        ge=0,
        le=100,
        description="Output quality 0-100 (Cloud models only)"
    )
    go_fast: bool = Field(
        False,
        description="Enable fast mode for quicker generation (Cloud models only)"
    )
    disable_safety_checker: bool = Field(
        True,
        description="Disable safety checker for generated images (Cloud models only)"
    )

    # Qwen-Image-Edit-Plus specific parameters
    # (Uses same prompt/negative_prompt/true_cfg_scale as local Qwen)

    # Qwen-Image specific parameters (text-to-image generation)
    image_size: Optional[str] = Field(
        "optimize_for_quality",
        description="Image size mode: optimize_for_quality, optimize_for_speed (Qwen-Image only)"
    )
    guidance: float = Field(
        4.0,
        ge=1.0,
        le=20.0,
        description="Guidance scale for text-to-image (Qwen-Image only)"
    )
    strength: float = Field(
        0.9,
        ge=0.0,
        le=1.0,
        description="Strength of image generation (Qwen-Image only)"
    )
    lora_scale: float = Field(
        1.0,
        ge=0.0,
        le=2.0,
        description="LoRA scale (Qwen-Image only)"
    )
    enhance_prompt_qwen: bool = Field(
        False,
        description="Enable prompt enhancement for Qwen-Image (text-to-image only)"
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
