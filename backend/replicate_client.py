"""
Replicate API client for Seedream-4 image generation
"""

import os
import json
import logging
from typing import List, Callable, Optional, Tuple
import replicate
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

# Pricing configuration
SEEDREAM_PRICE_PER_IMAGE = 0.03  # $0.03 per output image
QWEN_IMAGE_EDIT_PRICE = 0.01  # $0.01 per prediction
QWEN_IMAGE_EDIT_PLUS_PRICE = 0.02  # $0.02 per prediction
QWEN_IMAGE_PRICE = 0.015  # $0.015 per prediction


class ReplicateClient:
    """
    Client for interacting with ByteDance Seedream-4 on Replicate
    """

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Replicate client

        Args:
            api_token: Replicate API token (or use REPLICATE_API_TOKEN env var)
        """
        self.api_token = api_token or os.getenv('REPLICATE_API_TOKEN')
        if not self.api_token:
            raise ValueError(
                "Replicate API token not found. Set REPLICATE_API_TOKEN environment variable "
                "or pass api_token parameter."
            )

        # Set API token for replicate library
        os.environ['REPLICATE_API_TOKEN'] = self.api_token

    def edit_image(
        self,
        image_paths: List[str],
        prompt: str,
        size: str = "2K",
        aspect_ratio: str = "4:3",
        enhance_prompt: bool = False,
        sequential_image_generation: str = "disabled",
        max_images: int = 1,
        disable_safety_checker: bool = True,
        output_dir: Path = None,
        progress_callback: Optional[Callable] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[str]:
        """
        Edit image(s) using Seedream-4 on Replicate

        Args:
            image_paths: List of input image paths (1-10 images)
            prompt: Text prompt for image generation/editing
            size: Image resolution (1K, 2K, 4K, or custom)
            aspect_ratio: Aspect ratio (e.g., "4:3", "16:9", "match_input_image")
            enhance_prompt: Enable prompt enhancement
            sequential_image_generation: "disabled" or "auto"
            max_images: Max images to generate (1-15)
            output_dir: Directory to save output images
            progress_callback: Callback for progress updates
            is_cancelled: Callback to check if job is cancelled

        Returns:
            List of output image paths

        Raises:
            Exception: If API call fails or is cancelled
        """
        file_handles = []  # Track file handles for cleanup

        try:
            if progress_callback:
                progress_callback("preparing", "Preparing images for Seedream-4...", 10)

            # Check cancellation
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled before API call")

            # Prepare input images - open file handles
            for img_path in image_paths[:10]:  # Max 10 images
                fh = open(img_path, 'rb')
                file_handles.append(fh)

            if progress_callback:
                progress_callback("uploading", "Uploading images to Replicate...", 20)

            # Calculate width/height based on size and aspect ratio
            size_map = {
                "1K": 1024,
                "2K": 2048,
                "4K": 4096
            }
            base_resolution = size_map.get(size, 2048)

            # Calculate dimensions based on aspect ratio
            if aspect_ratio == "match_input_image" or ":" not in aspect_ratio:
                width, height = base_resolution, base_resolution
            else:
                w_ratio, h_ratio = map(float, aspect_ratio.split(":"))
                if w_ratio >= h_ratio:
                    width = base_resolution
                    height = int(base_resolution * (h_ratio / w_ratio))
                else:
                    height = base_resolution
                    width = int(base_resolution * (w_ratio / h_ratio))
                # Ensure dimensions are multiples of 8
                width = (width // 8) * 8
                height = (height // 8) * 8

            logger.info(f"Calculated dimensions: {width}x{height} for {size} @ {aspect_ratio}")

            # Build API input matching official Seedream-4 API format
            # Reference: https://replicate.com/bytedance/seedream-4
            input_data = {
                "size": size,                       # "1K", "2K", or "4K"
                "width": width,                     # Calculated from size + aspect_ratio
                "height": height,                   # Calculated from size + aspect_ratio
                "prompt": prompt,                   # Text prompt for generation
                "aspect_ratio": aspect_ratio,       # "1:1", "4:3", "16:9", etc.
                "enhance_prompt": enhance_prompt,   # True/False - LLM prompt enhancement
                "sequential_image_generation": sequential_image_generation,  # "disabled" or "auto"
                "max_images": max_images,           # 1-15 output images
                "disable_safety_checker": disable_safety_checker,  # Disable NSFW filter
            }

            # Add image inputs if provided (array of file handles or URLs)
            if file_handles:
                input_data["image_input"] = file_handles

            logger.info(f"Seedream-4 API input: {json.dumps({k: v if k != 'image_input' else f'<{len(file_handles)} files>' for k, v in input_data.items()}, indent=2)}")

            logger.info(f"Calling Seedream-4 with prompt: {prompt[:100]}...")
            logger.info(f"Resolution: {width}x{height}, Aspect ratio: {aspect_ratio}, Max images: {max_images}")

            if progress_callback:
                progress_callback("generating", "Generating with Seedream-4 (this may take 30-60s)...", 30)

            # Check cancellation before API call
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled before generation")

            # Run prediction using official Seedream-4 API with retry logic
            # Example from docs:
            # output = replicate.run("bytedance/seedream-4", input={...})
            # output[0].url() - Get image URL
            # output[0].read() - Get image bytes

            max_retries = 3
            retry_delay = 5  # seconds
            last_error = None

            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
                        if progress_callback:
                            progress_callback(
                                "retrying",
                                f"Retrying Seedream-4 (attempt {attempt + 1}/{max_retries})...",
                                30 + (attempt * 5)
                            )
                        import time
                        time.sleep(retry_delay)

                        # Check cancellation before retry
                        if is_cancelled and is_cancelled():
                            raise Exception("Job cancelled during retry")

                    output = replicate.run(
                        "bytedance/seedream-4",
                        input=input_data
                    )

                    logger.info(f"Seedream-4 API returned {len(output) if hasattr(output, '__len__') else 1} output(s)")
                    break  # Success, exit retry loop

                except Exception as e:
                    last_error = e
                    error_msg = str(e)

                    # Check if this is a retryable error
                    is_retryable = (
                        "interrupted" in error_msg.lower() or
                        "code: PA" in error_msg or
                        "timeout" in error_msg.lower() or
                        "503" in error_msg or
                        "502" in error_msg
                    )

                    if is_retryable and attempt < max_retries - 1:
                        logger.warning(f"Replicate API error (attempt {attempt + 1}/{max_retries}): {error_msg}")
                        logger.warning(f"This appears to be a transient error. Retrying in {retry_delay}s...")
                        continue
                    else:
                        # Non-retryable error or final attempt
                        logger.error(f"Replicate API error (final attempt): {error_msg}")
                        raise
            else:
                # All retries exhausted
                raise last_error if last_error else Exception("Unknown error during Replicate API call")

            # Close file handles after upload
            for fh in file_handles:
                try:
                    fh.close()
                except:
                    pass
            file_handles.clear()

            # Check cancellation after API call
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled after generation")

            if progress_callback:
                progress_callback("downloading", "Downloading results from Replicate...", 70)

            # Download output images
            output_paths = []
            if not output_dir:
                output_dir = Path(".")

            # Convert output to list if it isn't already
            if not isinstance(output, list):
                output = [output]

            logger.info(f"Received {len(output)} output(s) from Seedream-4")

            for index, item in enumerate(output):
                if is_cancelled and is_cancelled():
                    raise Exception("Job cancelled during download")

                output_path = output_dir / f"output_{index}.jpg"

                # Handle output using official Seedream-4 API patterns
                # Pattern 1: output[0].url() - returns URL string
                # Pattern 2: output[0].read() - returns bytes
                try:
                    # Method 1: Try .read() first (most direct, official API pattern)
                    if hasattr(item, 'read'):
                        logger.info(f"Output {index + 1}: Using .read() method (official API pattern)")
                        with open(output_path, 'wb') as f:
                            f.write(item.read())
                        logger.info(f"✓ Saved {output_path}")

                    # Method 2: Try .url() (official API pattern for URL access)
                    elif hasattr(item, 'url'):
                        url = item.url()
                        logger.info(f"Output {index + 1}: Using .url() method (official API pattern)")
                        logger.info(f"  URL: {url}")
                        response = requests.get(url, timeout=60)
                        response.raise_for_status()
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"✓ Downloaded and saved {output_path}")

                    # Method 3: Fallback - treat as direct URL string
                    elif isinstance(item, str):
                        logger.info(f"Output {index + 1}: Direct URL string (fallback)")
                        logger.info(f"  URL: {item}")
                        response = requests.get(item, timeout=60)
                        response.raise_for_status()
                        with open(output_path, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"✓ Downloaded and saved {output_path}")

                    else:
                        logger.error(f"❌ Unknown output type for item {index}: {type(item)}")
                        logger.error(f"   Available methods: {dir(item)}")
                        raise ValueError(f"Unexpected output type: {type(item)}")

                    output_paths.append(str(output_path))

                    if progress_callback:
                        download_progress = 70 + int((index + 1) / len(output) * 25)
                        progress_callback(
                            "downloading",
                            f"Downloaded {index + 1}/{len(output)} images...",
                            download_progress
                        )

                except Exception as e:
                    logger.error(f"❌ Error downloading output {index + 1}: {str(e)}", exc_info=True)
                    raise

            if progress_callback:
                progress_callback("complete", "Seedream-4 generation complete!", 95)

            logger.info(f"Successfully generated {len(output_paths)} images with Seedream-4")
            return output_paths

        except Exception as e:
            logger.error(f"Error calling Seedream-4: {str(e)}", exc_info=True)
            raise

        finally:
            # Ensure all file handles are closed
            for fh in file_handles:
                try:
                    fh.close()
                except:
                    pass

    def edit_image_qwen_cloud(
        self,
        image_paths: List[str],
        prompt: str,
        output_quality: int = 80,
        output_format: str = "webp",
        disable_safety_checker: bool = False,
        output_dir: Path = None,
        progress_callback: Optional[Callable] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[str]:
        """
        Simple image editing using qwen/qwen-image-edit on Replicate

        Args:
            image_paths: Single input image path
            prompt: Edit instruction
            output_quality: Output quality (1-100)
            output_format: Output format (webp, jpg, png)
            output_dir: Directory to save output
            progress_callback: Progress callback
            is_cancelled: Cancellation checker

        Returns:
            List of output image paths
        """
        file_handle = None
        try:
            if progress_callback:
                progress_callback("preparing", "Preparing for Qwen-Image-Edit cloud...", 10)

            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled")

            # Open first image
            file_handle = open(image_paths[0], 'rb')

            input_data = {
                "image": file_handle,
                "prompt": prompt,
                "output_quality": output_quality,
                "disable_safety_checker": disable_safety_checker
            }

            logger.info(f"Calling qwen/qwen-image-edit with prompt: {prompt[:100]}...")

            if progress_callback:
                progress_callback("generating", "Editing with Qwen-Image-Edit cloud...", 30)

            output = replicate.run("qwen/qwen-image-edit", input=input_data)

            # Close file handle
            if file_handle:
                file_handle.close()
                file_handle = None

            if progress_callback:
                progress_callback("downloading", "Downloading result...", 70)

            # Download output
            output_paths = []
            if not output_dir:
                output_dir = Path(".")

            if not isinstance(output, list):
                output = [output]

            for index, item in enumerate(output):
                if is_cancelled and is_cancelled():
                    raise Exception("Job cancelled during download")

                output_path = output_dir / f"output_{index}.{output_format}"

                if hasattr(item, 'read'):
                    with open(output_path, 'wb') as f:
                        f.write(item.read())
                elif hasattr(item, 'url'):
                    response = requests.get(item.url(), timeout=60)
                    response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                else:
                    response = requests.get(item, timeout=60)
                    response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(response.content)

                output_paths.append(str(output_path))

            if progress_callback:
                progress_callback("complete", "Qwen-Image-Edit cloud complete!", 95)

            logger.info(f"Generated {len(output_paths)} image(s) with qwen/qwen-image-edit")
            return output_paths

        except Exception as e:
            logger.error(f"Error calling qwen/qwen-image-edit: {str(e)}", exc_info=True)
            raise
        finally:
            if file_handle:
                try:
                    file_handle.close()
                except:
                    pass

    def edit_image_qwen_plus(
        self,
        image_paths: List[str],
        prompt: str,
        go_fast: bool = True,
        aspect_ratio: str = "match_input_image",
        output_format: str = "webp",
        output_quality: int = 95,
        disable_safety_checker: bool = False,
        output_dir: Path = None,
        progress_callback: Optional[Callable] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[str]:
        """
        Advanced editing with pose/style transfer using qwen/qwen-image-edit-plus

        Args:
            image_paths: 1-2 input images
            prompt: Edit instruction (e.g., "person in image 2 adopts pose from image 1")
            go_fast: Enable fast mode
            aspect_ratio: Aspect ratio
            output_format: Output format
            output_quality: Output quality
            output_dir: Output directory
            progress_callback: Progress callback
            is_cancelled: Cancellation checker

        Returns:
            List of output image paths
        """
        file_handles = []
        try:
            if progress_callback:
                progress_callback("preparing", "Preparing for Qwen-Image-Edit-Plus...", 10)

            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled")

            # Open image files
            for img_path in image_paths[:2]:
                fh = open(img_path, 'rb')
                file_handles.append(fh)

            input_data = {
                "image": file_handles,
                "prompt": prompt,
                "go_fast": go_fast,
                "aspect_ratio": aspect_ratio,
                "output_format": output_format,
                "output_quality": output_quality,
                "disable_safety_checker": disable_safety_checker
            }

            logger.info(f"Calling qwen/qwen-image-edit-plus with {len(file_handles)} image(s)")

            if progress_callback:
                progress_callback("generating", "Processing with Qwen-Image-Edit-Plus...", 30)

            output = replicate.run("qwen/qwen-image-edit-plus", input=input_data)

            # Close file handles
            for fh in file_handles:
                try:
                    fh.close()
                except:
                    pass
            file_handles.clear()

            if progress_callback:
                progress_callback("downloading", "Downloading result...", 70)

            # Download output
            output_paths = []
            if not output_dir:
                output_dir = Path(".")

            if not isinstance(output, list):
                output = [output]

            for index, item in enumerate(output):
                output_path = output_dir / f"output_{index}.{output_format}"

                if hasattr(item, 'read'):
                    with open(output_path, 'wb') as f:
                        f.write(item.read())
                elif hasattr(item, 'url'):
                    response = requests.get(item.url(), timeout=60)
                    response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                else:
                    response = requests.get(item, timeout=60)
                    response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(response.content)

                output_paths.append(str(output_path))

            if progress_callback:
                progress_callback("complete", "Qwen-Image-Edit-Plus complete!", 95)

            logger.info(f"Generated {len(output_paths)} image(s) with qwen/qwen-image-edit-plus")
            return output_paths

        except Exception as e:
            logger.error(f"Error calling qwen/qwen-image-edit-plus: {str(e)}", exc_info=True)
            raise
        finally:
            for fh in file_handles:
                try:
                    fh.close()
                except:
                    pass

    def generate_image_qwen(
        self,
        prompt: str,
        negative_prompt: str = " ",
        go_fast: bool = True,
        guidance: float = 4.0,
        strength: float = 0.9,
        image_size: str = "optimize_for_quality",
        lora_scale: float = 1.0,
        aspect_ratio: str = "16:9",
        output_format: str = "webp",
        enhance_prompt: bool = False,
        output_quality: int = 80,
        num_inference_steps: int = 50,
        disable_safety_checker: bool = False,
        output_dir: Path = None,
        progress_callback: Optional[Callable] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> List[str]:
        """
        Text-to-image generation using qwen/qwen-image

        Args:
            prompt: Text description for image generation
            negative_prompt: What to avoid
            go_fast: Fast mode
            guidance: Guidance scale
            strength: Generation strength
            image_size: Quality mode
            lora_scale: LoRA scale
            aspect_ratio: Aspect ratio
            output_format: Output format
            enhance_prompt: Enable prompt enhancement
            output_quality: Output quality
            num_inference_steps: Number of steps
            output_dir: Output directory
            progress_callback: Progress callback
            is_cancelled: Cancellation checker

        Returns:
            List of output image paths
        """
        try:
            if progress_callback:
                progress_callback("preparing", "Preparing for Qwen-Image generation...", 10)

            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled")

            input_data = {
                "prompt": prompt,
                "go_fast": go_fast,
                "guidance": guidance,
                "strength": strength,
                "image_size": image_size,
                "lora_scale": lora_scale,
                "aspect_ratio": aspect_ratio,
                "output_format": output_format,
                "enhance_prompt": enhance_prompt,
                "output_quality": output_quality,
                "negative_prompt": negative_prompt,
                "num_inference_steps": num_inference_steps,
                "disable_safety_checker": disable_safety_checker
            }

            logger.info(f"Calling qwen/qwen-image for text-to-image generation")
            logger.info(f"Prompt: {prompt[:100]}...")

            if progress_callback:
                progress_callback("generating", "Generating image with Qwen-Image...", 30)

            output = replicate.run("qwen/qwen-image", input=input_data)

            if progress_callback:
                progress_callback("downloading", "Downloading result...", 70)

            # Download output
            output_paths = []
            if not output_dir:
                output_dir = Path(".")

            if not isinstance(output, list):
                output = [output]

            for index, item in enumerate(output):
                output_path = output_dir / f"output_{index}.{output_format}"

                if hasattr(item, 'read'):
                    with open(output_path, 'wb') as f:
                        f.write(item.read())
                elif hasattr(item, 'url'):
                    response = requests.get(item.url(), timeout=60)
                    response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                else:
                    response = requests.get(item, timeout=60)
                    response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(response.content)

                output_paths.append(str(output_path))

            if progress_callback:
                progress_callback("complete", "Qwen-Image generation complete!", 95)

            logger.info(f"Generated {len(output_paths)} image(s) with qwen/qwen-image")
            return output_paths

        except Exception as e:
            logger.error(f"Error calling qwen/qwen-image: {str(e)}", exc_info=True)
            raise

    def calculate_cost(self, model_type: str, num_output_images: int = 1) -> float:
        """
        Calculate cost for Replicate generation

        Args:
            model_type: Model identifier
            num_output_images: Number of output images (for Seedream)

        Returns:
            Cost in USD
        """
        if model_type == "seedream":
            return num_output_images * SEEDREAM_PRICE_PER_IMAGE
        elif model_type == "qwen_image_edit":
            return QWEN_IMAGE_EDIT_PRICE
        elif model_type == "qwen_image_edit_plus":
            return QWEN_IMAGE_EDIT_PLUS_PRICE
        elif model_type == "qwen_image":
            return QWEN_IMAGE_PRICE
        return 0.0

    @staticmethod
    def get_price_info() -> dict:
        """Get pricing information for all models"""
        return {
            "seedream": SEEDREAM_PRICE_PER_IMAGE,
            "qwen_image_edit": QWEN_IMAGE_EDIT_PRICE,
            "qwen_image_edit_plus": QWEN_IMAGE_EDIT_PLUS_PRICE,
            "qwen_image": QWEN_IMAGE_PRICE
        }
