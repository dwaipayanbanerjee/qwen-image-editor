"""
Image Editor using Qwen-Image-Edit-2509-GGUF model
Handles loading, inference, and image combining
"""

import torch
from PIL import Image
from typing import List, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class ImageEditor:
    """
    Wrapper for Qwen-Image-Edit-2509-GGUF pipeline
    Supports single image editing and multi-image combining
    """

    def __init__(self, progress_callback: Optional[Callable[[int], None]] = None, use_gguf: bool = True, quantization_level: str = "Q5_K_S"):
        """
        Initialize and load the Qwen-Image-Edit-2509-GGUF model

        Args:
            progress_callback: Optional callback for download progress (receives percentage 0-100)
            use_gguf: Whether to use GGUF quantized model (faster, less VRAM)
            quantization_level: GGUF quantization level (Q2_K, Q4_K_M, Q5_K_S, Q8_0)
        """
        self.pipeline = None
        self.use_gguf = use_gguf
        self.quantization_level = quantization_level
        self.device, self.dtype = self._get_device_and_dtype()
        self._load_model(progress_callback)

    def _get_device_and_dtype(self):
        """
        Get the optimal device and dtype for the current system.
        Priority: MPS (Apple Silicon) > CUDA (NVIDIA) > CPU

        Returns:
            Tuple of (device, dtype)
        """
        if torch.backends.mps.is_available():
            logger.info("Using MPS (Apple Silicon GPU)")
            return "mps", torch.bfloat16
        elif torch.cuda.is_available():
            logger.info("Using CUDA (NVIDIA GPU)")
            return "cuda", torch.bfloat16
        else:
            logger.info("Using CPU (no GPU acceleration)")
            return "cpu", torch.float32

    def _load_model(self, progress_callback: Optional[Callable[[int], None]] = None):
        """
        Lazy load the Qwen-Image-Edit-2509-GGUF pipeline with retry logic

        Args:
            progress_callback: Optional callback for progress updates
        """
        if self.use_gguf:
            self._load_gguf_model(progress_callback)
        else:
            # Fallback to standard model (kept for compatibility)
            self._load_standard_model(progress_callback)

    def _load_gguf_model(self, progress_callback: Optional[Callable[[int], None]] = None):
        """
        Load GGUF quantized model for faster inference and lower VRAM usage

        Args:
            progress_callback: Optional callback for progress updates
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                from diffusers import QwenImageTransformer2DModel, GGUFQuantizationConfig, QwenImageEditPipeline
                import gc

                logger.info(f"Loading Qwen-Image-Edit-2509 GGUF pipeline ({self.quantization_level}) (attempt {retry_count + 1}/{max_retries})...")

                # Clear GPU cache before loading
                if retry_count > 0:
                    logger.info("Clearing GPU cache before retry...")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    elif torch.backends.mps.is_available():
                        torch.mps.empty_cache()
                    gc.collect()

                if progress_callback:
                    progress_callback(0)

                # GGUF model URL mapping
                gguf_urls = {
                    "Q2_K": "https://huggingface.co/QuantStack/Qwen-Image-Edit-2509-GGUF/blob/main/Qwen-Image-Edit-2509-Q2_K.gguf",
                    "Q4_K_M": "https://huggingface.co/QuantStack/Qwen-Image-Edit-2509-GGUF/blob/main/Qwen-Image-Edit-2509-Q4_K_M.gguf",
                    "Q5_K_S": "https://huggingface.co/QuantStack/Qwen-Image-Edit-2509-GGUF/blob/main/Qwen-Image-Edit-2509-Q5_K_S.gguf",
                    "Q8_0": "https://huggingface.co/QuantStack/Qwen-Image-Edit-2509-GGUF/blob/main/Qwen-Image-Edit-2509-Q8_0.gguf"
                }

                model_url = gguf_urls.get(self.quantization_level)
                if not model_url:
                    raise ValueError(f"Unsupported quantization level: {self.quantization_level}. Supported: {list(gguf_urls.keys())}")

                logger.info(f"Loading transformer from {model_url}")

                if progress_callback:
                    progress_callback(20)

                # Load quantized transformer
                transformer = QwenImageTransformer2DModel.from_single_file(
                    model_url,
                    quantization_config=GGUFQuantizationConfig(compute_dtype=self.dtype),
                    torch_dtype=self.dtype,
                    config="Qwen/Qwen-Image-Edit-2509",
                    subfolder="transformer"
                )

                if progress_callback:
                    progress_callback(60)

                # Load the pipeline with quantized transformer
                self.pipeline = QwenImageEditPipeline.from_pretrained(
                    "Qwen/Qwen-Image-Edit-2509",
                    transformer=transformer,
                    torch_dtype=self.dtype
                )

                if progress_callback:
                    progress_callback(80)

                # Move to device (CPU offloading recommended for GGUF)
                if self.device == "mps" or self.device == "cuda":
                    self.pipeline.enable_model_cpu_offload()
                    logger.info(f"Enabled CPU offloading for GGUF model on {self.device}")
                else:
                    self.pipeline.to(self.device)

                if progress_callback:
                    progress_callback(100)

                logger.info(f"GGUF model ({self.quantization_level}) loaded successfully on {self.device}")

                # Log GPU memory usage
                if torch.cuda.is_available():
                    allocated = torch.cuda.memory_allocated() / 1024**3
                    reserved = torch.cuda.memory_reserved() / 1024**3
                    logger.info(f"GPU Memory: {allocated:.2f} GB allocated, {reserved:.2f} GB reserved")
                elif self.device == "mps":
                    logger.info("MPS device active (memory stats not available on MPS)")

                return

            except Exception as e:
                retry_count += 1

                # Aggressive cleanup on failure
                import gc
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif torch.backends.mps.is_available():
                    torch.mps.empty_cache()
                gc.collect()

                if retry_count >= max_retries:
                    logger.error(f"Failed to load GGUF model after {max_retries} attempts: {str(e)}")
                    raise
                else:
                    logger.warning(f"Failed to load GGUF model (attempt {retry_count}), retrying: {str(e)}")
                    import time
                    time.sleep(5)

    def _load_standard_model(self, progress_callback: Optional[Callable[[int], None]] = None):
        """
        Load standard (non-quantized) model

        Args:
            progress_callback: Optional callback for progress updates
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                from diffusers import QwenImageEditPipeline
                import gc

                logger.info(f"Loading Qwen-Image-Edit pipeline (attempt {retry_count + 1}/{max_retries})...")

                # Clear GPU cache before loading (critical for retry attempts)
                if retry_count > 0:
                    logger.info("Clearing GPU cache before retry...")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    elif torch.backends.mps.is_available():
                        torch.mps.empty_cache()
                    gc.collect()

                # Note: Hugging Face doesn't provide granular download progress easily,
                # but we can report key milestones
                if progress_callback:
                    progress_callback(0)

                self.pipeline = QwenImageEditPipeline.from_pretrained(
                    "Qwen/Qwen-Image-Edit",
                    torch_dtype=self.dtype
                )

                if progress_callback:
                    progress_callback(80)

                self.pipeline.to(self.device)

                if progress_callback:
                    progress_callback(100)

                logger.info(f"Model loaded successfully on {self.device}")

                # Log GPU memory usage (CUDA only - MPS doesn't expose memory stats)
                if torch.cuda.is_available():
                    allocated = torch.cuda.memory_allocated() / 1024**3
                    reserved = torch.cuda.memory_reserved() / 1024**3
                    logger.info(f"GPU Memory: {allocated:.2f} GB allocated, {reserved:.2f} GB reserved")
                elif self.device == "mps":
                    logger.info("MPS device active (memory stats not available on MPS)")

                return

            except Exception as e:
                retry_count += 1

                # Aggressive cleanup on failure
                import gc
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif torch.backends.mps.is_available():
                    torch.mps.empty_cache()
                gc.collect()

                if retry_count >= max_retries:
                    logger.error(f"Failed to load Qwen-Image-Edit model after {max_retries} attempts: {str(e)}")
                    raise
                else:
                    logger.warning(f"Failed to load model (attempt {retry_count}), retrying: {str(e)}")
                    import time
                    time.sleep(5)  # Wait before retry

    def edit_image(
        self,
        image_paths: List[str],
        prompt: str,
        negative_prompt: Optional[str] = None,
        true_cfg_scale: float = 4.0,
        num_inference_steps: int = 50,
        output_path: str = "output.jpg",
        progress_callback: Optional[Callable] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Edit image(s) using Qwen-Image-Edit-2509-GGUF model

        Args:
            image_paths: List of 1-2 image paths
            prompt: Edit instruction
            negative_prompt: What to avoid in the output
            true_cfg_scale: Classifier-free guidance scale (default: 4.0)
            num_inference_steps: Number of diffusion steps (default: 50)
            output_path: Where to save the edited image
            progress_callback: Optional callback for progress updates
            is_cancelled: Optional callback to check if job is cancelled

        Returns:
            Path to the edited image

        Raises:
            Exception: If cancelled or error occurs
        """
        try:
            # Check cancellation at start
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled before loading images")

            if progress_callback:
                progress_callback("loading_images", "Loading input images...", 30)

            # Load images with EXIF preservation
            images = []
            exif_data = None
            for i, img_path in enumerate(image_paths):
                img = Image.open(img_path)
                # Preserve EXIF from first image
                if i == 0 and hasattr(img, 'info'):
                    exif_data = img.info.get('exif')
                img = img.convert('RGB')
                images.append(img)
                logger.info(f"Loaded image: {img_path}, size: {img.size}")

            # Check cancellation
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled during image loading")

            # Handle single vs multi-image
            if len(images) == 1:
                input_image = images[0]
            else:
                # Combine two images side-by-side
                if progress_callback:
                    progress_callback("combining_images", "Combining images...", 35)
                input_image = self._combine_images(images[0], images[1])

            # Check cancellation
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled before inference")

            if progress_callback:
                progress_callback("editing", "Applying edits with Qwen model...", 40)

            # Run inference
            logger.info(f"Starting inference with prompt: '{prompt}'")
            output = self.pipeline(
                image=input_image,
                prompt=prompt,
                negative_prompt=negative_prompt or "",
                true_cfg_scale=true_cfg_scale,
                num_inference_steps=num_inference_steps,
            )

            # Check cancellation after inference
            if is_cancelled and is_cancelled():
                raise Exception("Job cancelled after inference")

            # Extract the edited image
            edited_image = output.images[0]

            if progress_callback:
                progress_callback("saving", "Saving edited image...", 95)

            # Save output with EXIF if available
            save_kwargs = {'quality': 95}
            if exif_data:
                save_kwargs['exif'] = exif_data

            edited_image.save(output_path, **save_kwargs)
            logger.info(f"Saved edited image to: {output_path}")

            # Aggressive GPU cache cleanup after inference
            import gc
            # Delete intermediate tensors
            del output
            del edited_image
            del input_image
            del images
            # Force garbage collection
            gc.collect()
            # Clear PyTorch cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                # Log memory usage
                allocated = torch.cuda.memory_allocated() / 1024**3
                reserved = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"GPU Memory after cleanup: {allocated:.2f} GB allocated, {reserved:.2f} GB reserved")
            elif self.device == "mps":
                torch.mps.empty_cache()
                logger.info("MPS cache cleared after inference")

            return output_path

        except Exception as e:
            # Aggressive cleanup on error too
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            elif self.device == "mps":
                torch.mps.empty_cache()
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
        dtype_str = "bfloat16" if self.dtype == torch.bfloat16 else "float32"
        model_name = f"Qwen-Image-Edit-2509-{self.quantization_level}" if self.use_gguf else "Qwen-Image-Edit"
        return {
            "model": model_name,
            "device": self.device,
            "dtype": dtype_str,
            "quantized": self.use_gguf,
            "loaded": self.pipeline is not None
        }
