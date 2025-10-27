"""
Image Editor using Qwen-Image-Edit model
Handles loading, inference, and image combining
"""

import torch
from PIL import Image
from typing import List, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class ImageEditor:
    """
    Wrapper for Qwen-Image-Edit pipeline
    Supports single image editing and multi-image combining
    """

    def __init__(self):
        """Initialize and load the Qwen-Image-Edit model"""
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()

    def _load_model(self):
        """Lazy load the Qwen-Image-Edit pipeline"""
        try:
            from diffusers import QwenImageEditPipeline

            logger.info("Loading Qwen-Image-Edit pipeline...")
            self.pipeline = QwenImageEditPipeline.from_pretrained(
                "Qwen/Qwen-Image-Edit",
                torch_dtype=torch.bfloat16
            )
            self.pipeline.to(self.device)

            logger.info(f"Model loaded successfully on {self.device}")

        except Exception as e:
            logger.error(f"Failed to load Qwen-Image-Edit model: {str(e)}")
            raise

    def edit_image(
        self,
        image_paths: List[str],
        prompt: str,
        negative_prompt: Optional[str] = None,
        true_cfg_scale: float = 4.0,
        num_inference_steps: int = 50,
        output_path: str = "output.jpg",
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Edit image(s) using Qwen-Image-Edit model

        Args:
            image_paths: List of 1-2 image paths
            prompt: Edit instruction
            negative_prompt: What to avoid in the output
            true_cfg_scale: Classifier-free guidance scale (default: 4.0)
            num_inference_steps: Number of diffusion steps (default: 50)
            output_path: Where to save the edited image
            progress_callback: Optional callback for progress updates

        Returns:
            Path to the edited image
        """
        try:
            if progress_callback:
                progress_callback("loading_images", "Loading input images...", 10)

            # Load images
            images = []
            for img_path in image_paths:
                img = Image.open(img_path).convert('RGB')
                images.append(img)
                logger.info(f"Loaded image: {img_path}, size: {img.size}")

            # Handle single vs multi-image
            if len(images) == 1:
                input_image = images[0]
            else:
                # Combine two images side-by-side
                if progress_callback:
                    progress_callback("combining_images", "Combining images...", 20)
                input_image = self._combine_images(images[0], images[1])

            if progress_callback:
                progress_callback("editing", "Applying edits with Qwen model...", 30)

            # Run inference
            logger.info(f"Starting inference with prompt: '{prompt}'")
            output = self.pipeline(
                image=input_image,
                prompt=prompt,
                negative_prompt=negative_prompt or "",
                true_cfg_scale=true_cfg_scale,
                num_inference_steps=num_inference_steps,
            )

            # Extract the edited image
            edited_image = output.images[0]

            if progress_callback:
                progress_callback("saving", "Saving edited image...", 90)

            # Save output
            edited_image.save(output_path, quality=95)
            logger.info(f"Saved edited image to: {output_path}")

            # Clear GPU cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            return output_path

        except Exception as e:
            logger.error(f"Error during image editing: {str(e)}")
            raise

    def _combine_images(self, img1: Image.Image, img2: Image.Image) -> Image.Image:
        """
        Combine two images side-by-side for multi-image editing

        Args:
            img1: First image
            img2: Second image

        Returns:
            Combined image
        """
        # Resize to same height
        target_height = min(img1.height, img2.height)

        # Calculate new widths maintaining aspect ratio
        new_width1 = int(img1.width * (target_height / img1.height))
        new_width2 = int(img2.width * (target_height / img2.height))

        # Resize both images
        img1_resized = img1.resize((new_width1, target_height), Image.Resampling.LANCZOS)
        img2_resized = img2.resize((new_width2, target_height), Image.Resampling.LANCZOS)

        # Create combined canvas
        total_width = new_width1 + new_width2
        combined = Image.new('RGB', (total_width, target_height))

        # Paste images side-by-side
        combined.paste(img1_resized, (0, 0))
        combined.paste(img2_resized, (new_width1, 0))

        logger.info(f"Combined images: {combined.size}")
        return combined

    def get_model_info(self) -> dict:
        """Get information about the loaded model"""
        return {
            "model": "Qwen-Image-Edit",
            "device": self.device,
            "dtype": "bfloat16",
            "loaded": self.pipeline is not None
        }
