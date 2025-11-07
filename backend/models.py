"""
Pydantic models for request/response validation

CRITICAL DESIGN PRINCIPLE - EDIT vs GENERATION:

1. IMAGE EDITING models (qwen_gguf, qwen_image_edit, qwen_image_edit_plus):
   - Require input images
   - PRESERVE input dimensions exactly (no resizing)
   - aspect_ratio is FORCED to "match_input_image" in backend
   - Do NOT expose aspect_ratio to users for these models
   - Output dimensions = Input dimensions

2. IMAGE GENERATION models (hunyuan, qwen_image):
   - No input images (text-to-image)
   - User controls aspect_ratio (1:1, 4:3, 16:9, etc.)
   - Output dimensions determined by aspect_ratio selection

3. HYBRID models (seedream):
   - Optional input images (0-10)
   - Flexible aspect_ratio control
   - Can edit (with images) or generate (without images)
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
    """Available image editing and generation models"""
    # LOCAL EDIT MODELS (require input images, preserve dimensions)
    QWEN_GGUF = "qwen_gguf"  # Qwen-Image-Edit-2509 GGUF (free, 1-2 images → 1 image, matches input size)

    # CLOUD GENERATION MODELS (text-to-image, aspect ratio control)
    HUNYUAN = "hunyuan"  # Tencent Hunyuan Image 3 ($0.02/image, text → 1 image)
    QWEN_IMAGE = "qwen_image"  # Qwen-Image ($0.015/image, text → 1 image)

    # CLOUD EDIT MODELS (require input images, preserve dimensions)
    QWEN_IMAGE_EDIT = "qwen_image_edit"  # Qwen-Image-Edit ($0.01/image, 1 image → 1 image, matches input size)
    QWEN_IMAGE_EDIT_PLUS = "qwen_image_edit_plus"  # Qwen-Image-Edit-Plus ($0.02/image, 1-3 images → 1 image, matches input size)

    # HYBRID MODEL (can edit or generate, flexible aspect ratio)
    SEEDREAM = "seedream"  # ByteDance Seedream-4 ($0.03/image, 0-10 images → 1-15 images)


class EditConfig(BaseModel):
    """
    Configuration for image editing/generation request

    CRITICAL DESIGN PRINCIPLE:
    - EDIT models (qwen_gguf, qwen_image_edit, qwen_image_edit_plus):
      → PRESERVE input dimensions exactly (no resizing, aspect_ratio always "match_input_image")
    - GENERATION models (hunyuan, qwen_image):
      → User controls aspect_ratio (text-to-image, no input images)
    - HYBRID models (seedream):
      → Flexible (can edit or generate)

    Attributes:
        model_type: Which model to use
        prompt: Edit instruction or generation prompt
        negative_prompt: What to avoid in the output (Qwen only)

        # Qwen GGUF-specific (LOCAL EDIT):
        quantization_level: Quantization level (Q5_K_S recommended)
        true_cfg_scale: Guidance scale (higher = more prompt adherence)
        num_inference_steps: Diffusion steps (higher = better quality, slower)

        # Hunyuan-specific (CLOUD GENERATION):
        seed: Random seed for reproducibility
        aspect_ratio: Output aspect ratio (1:1, 4:3, 16:9, etc.)

        # Qwen-Image-Edit-Plus-specific (CLOUD EDIT):
        → aspect_ratio is FORCED to "match_input_image" in backend (not user-controlled)

        # Seedream-specific (HYBRID):
        size: Image resolution (1K, 2K, 4K)
        aspect_ratio: Can use "match_input_image" or custom (4:3, 16:9, etc.)
        enhance_prompt: Enable prompt enhancement
        sequential_image_generation: Enable auto multi-image generation
        max_images: Max images to generate
    """
    model_type: ModelType = Field(
        ModelType.QWEN_GGUF,
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

    # Hunyuan-specific parameters
    seed: Optional[int] = Field(
        None,
        description="Random seed for reproducible generation (Hunyuan only)"
    )

    # Seedream-specific parameters
    size: Optional[str] = Field(
        "2K",
        description="Image resolution: 1K, 2K, 4K, or custom (Seedream only)"
    )
    aspect_ratio: Optional[str] = Field(
        "4:3",
        description="Aspect ratio like '4:3', '16:9', '1:1' - also used by Hunyuan (Seedream/Hunyuan)"
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
