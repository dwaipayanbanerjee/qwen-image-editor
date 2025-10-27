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


class EditConfig(BaseModel):
    """
    Configuration for image editing request

    Attributes:
        prompt: Edit instruction (e.g., "make the sky sunset colors")
        negative_prompt: What to avoid in the output
        true_cfg_scale: Classifier-free guidance scale (higher = more prompt adherence)
        num_inference_steps: Number of diffusion steps (higher = better quality but slower)
    """
    prompt: str = Field(..., description="Edit instruction or description")
    negative_prompt: Optional[str] = Field(
        None,
        description="What to avoid in the edited image"
    )
    true_cfg_scale: float = Field(
        4.0,
        ge=1.0,
        le=20.0,
        description="Classifier-free guidance scale"
    )
    num_inference_steps: int = Field(
        50,
        ge=10,
        le=100,
        description="Number of diffusion steps"
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
    """
    job_id: str
    status: str
    config: dict
    progress: Optional[ProgressInfo] = None
    error: Optional[str] = None
    created_at: float


class JobCreateResponse(BaseModel):
    """Response model for job creation"""
    job_id: str
    status: str
    message: str


class ErrorResponse(BaseModel):
    """Error response model"""
    detail: str
