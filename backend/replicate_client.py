"""
Replicate API client for Seedream-4 image generation
"""

import os
import logging
from typing import List, Callable, Optional
import replicate
from pathlib import Path
import requests

logger = logging.getLogger(__name__)

# Pricing configuration
SEEDREAM_PRICE_PER_IMAGE = 0.03  # $0.03 per output image


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
        try:
            if progress_callback:
                progress_callback("preparing", "Preparing images for Seedream-4...", 10)

            # Check cancellation
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled before API call")

            # Prepare input images
            image_inputs = []
            for img_path in image_paths[:10]:  # Max 10 images
                with open(img_path, 'rb') as f:
                    # Upload to Replicate's file service
                    image_inputs.append(open(img_path, 'rb'))

            if progress_callback:
                progress_callback("uploading", "Uploading images to Replicate...", 20)

            # Build API input
            input_data = {
                "prompt": prompt,
                "size": size,
                "aspect_ratio": aspect_ratio,
                "enhance_prompt": enhance_prompt,
                "sequential_image_generation": sequential_image_generation,
                "max_images": max_images,
            }

            # Add image inputs if provided
            if image_inputs:
                input_data["image_input"] = image_inputs

            logger.info(f"Calling Seedream-4 with prompt: {prompt[:100]}...")

            if progress_callback:
                progress_callback("generating", "Generating with Seedream-4 (this may take 30-60s)...", 30)

            # Check cancellation before API call
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled before generation")

            # Run prediction
            output = replicate.run(
                "bytedance/seedream-4",
                input=input_data
            )

            # Check cancellation after API call
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled after generation")

            if progress_callback:
                progress_callback("downloading", "Downloading results from Replicate...", 70)

            # Download output images
            output_paths = []
            if not output_dir:
                output_dir = Path(".")

            for index, item in enumerate(output):
                if is_cancelled and is_cancelled():
                    raise Exception("Job cancelled during download")

                output_path = output_dir / f"output_{index}.jpg"

                # Download image from URL
                if isinstance(item, str):  # URL string
                    response = requests.get(item, timeout=60)
                    response.raise_for_status()
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                else:  # File handle from replicate
                    with open(output_path, 'wb') as f:
                        f.write(item.read())

                output_paths.append(str(output_path))
                logger.info(f"Downloaded output image {index + 1} to {output_path}")

                if progress_callback:
                    download_progress = 70 + int((index + 1) / len(output) * 25)
                    progress_callback(
                        "downloading",
                        f"Downloaded {index + 1}/{len(output)} images...",
                        download_progress
                    )

            if progress_callback:
                progress_callback("complete", "Seedream-4 generation complete!", 95)

            logger.info(f"Successfully generated {len(output_paths)} images with Seedream-4")
            return output_paths

        except Exception as e:
            logger.error(f"Error calling Seedream-4: {str(e)}", exc_info=True)
            raise

    def calculate_cost(self, num_output_images: int) -> float:
        """
        Calculate cost for Seedream-4 generation

        Args:
            num_output_images: Number of output images that will be generated

        Returns:
            Cost in USD
        """
        return num_output_images * SEEDREAM_PRICE_PER_IMAGE

    @staticmethod
    def get_price_per_image() -> float:
        """Get price per output image for Seedream-4"""
        return SEEDREAM_PRICE_PER_IMAGE
