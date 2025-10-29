# Complete Model Guide - 6 AI Models

## Overview

The Image Editor now supports **6 different AI models** organized into two categories:
- **Local Models (2):** Free, run on your Mac
- **Cloud Models (4):** Paid, run on Replicate API

---

## Local Models (FREE)

### 1. Qwen-Image-Edit (Standard)
- **Cost:** FREE
- **Speed:** ~45s (50 steps)
- **VRAM:** 40-60GB
- **Quality:** Highest
- **Input:** 1-2 images (combines side-by-side)
- **Output:** 1 image
- **Use Case:** Best quality local editing, but requires significant resources

### 2. Qwen-Image-Edit-2509-GGUF (Quantized)
- **Cost:** FREE
- **Speed:** ~32s (50 steps) ⚡ **20-30% faster**
- **VRAM:** 7-22GB (depends on quantization)
- **Quality:** Very good (Q5_K_S recommended)
- **Input:** 1-2 images (combines side-by-side)
- **Output:** 1 image
- **Quantization Options:**
  - Q2_K: 7GB VRAM, fastest, lowest quality
  - Q4_K_M: 14GB VRAM, good quality
  - Q5_K_S: 17GB VRAM, **recommended**, best balance
  - Q8_0: 22GB VRAM, highest quantized quality
- **Use Case:** ⭐ **RECOMMENDED** - Best for most users, great balance of speed/quality/resources

---

## Cloud Models (PAID)

All cloud models require `REPLICATE_API_TOKEN` in `.env`

### 3. Qwen-Image-Edit (Cloud) - Cheapest
- **Cost:** $0.01 per prediction
- **Speed:** ~20-40s
- **Input:** 1 image
- **Output:** 1 image
- **Use Case:** Simple, quick edits at lowest cost
- **API:** `qwen/qwen-image-edit`
- **Parameters:**
  - `prompt` - Edit instruction
  - `output_quality` - 0-100 (default: 100)
  - `output_format` - webp/jpg/png (default: png)

### 4. Qwen-Image-Edit-Plus - Pose/Style Transfer
- **Cost:** $0.02 per prediction
- **Speed:** ~30-50s
- **Input:** 1-2 images
- **Output:** 1 image
- **Use Case:** Pose transfer, style copying between images
- **API:** `qwen/qwen-image-edit-plus`
- **Special Feature:** Can transfer pose/style from one image to another
- **Example Prompt:** "The person in image 2 adopts the pose from image 1"
- **Parameters:**
  - `prompt` - Edit instruction
  - `go_fast` - Enable fast mode (default: false)
  - `aspect_ratio` - Aspect ratio (default: match_input_image)
  - `output_format` - webp/jpg/png (default: png)
  - `output_quality` - 0-100 (default: 100)

### 5. Qwen-Image - Text-to-Image Generation
- **Cost:** $0.015 per prediction
- **Speed:** ~40-60s
- **Input:** **None** (text-to-image)
- **Output:** 1 image
- **Use Case:** Create images from text descriptions, no input image needed
- **API:** `qwen/qwen-image`
- **Special Feature:** Excellent text rendering in images
- **Example Prompt:** "A bookstore window with sign 'New Arrivals This Week'"
- **Parameters:**
  - `prompt` - Text description
  - `negative_prompt` - What to avoid
  - `num_inference_steps` - 10-100 (default: 50)
  - `guidance` - Guidance scale 1-20 (default: 4)
  - `strength` - Generation strength 0-1 (default: 0.9)
  - `lora_scale` - LoRA scale 0-2 (default: 1)
  - `image_size` - optimize_for_quality/optimize_for_speed
  - `aspect_ratio` - 1:1, 4:3, 16:9, etc (default: 16:9)
  - `enhance_prompt` - LLM enhancement (default: false)
  - `output_format` - webp/jpg/png (default: png)
  - `output_quality` - 0-100 (default: 80)
  - `go_fast` - Fast mode (default: false)

### 6. Seedream-4 - Multi-Image Output
- **Cost:** $0.03 per output image
- **Speed:** ~30-60s
- **Input:** 1-10 images (used as references)
- **Output:** **1-15 images** (configurable)
- **Use Case:** Generate multiple variations, complex compositions
- **API:** `bytedance/seedream-4`
- **Special Feature:** Only model that can generate multiple outputs
- **Parameters:**
  - `prompt` - Generation instruction
  - `max_images` - 1-15 output images
  - `sequential_image_generation` - auto/disabled
  - `size` - 1K, 2K, 4K
  - `aspect_ratio` - 1:1, 4:3, 16:9, etc
  - `enhance_prompt` - LLM enhancement (default: false)
  - `output_format` - webp/jpg/png
  - `output_quality` - 0-100

---

## Model Comparison Table

| Model | Type | Cost | Speed | Inputs | Outputs | Best For |
|-------|------|------|-------|--------|---------|----------|
| **Qwen Standard** | Local | FREE | ~45s | 1-2 | 1 | Highest quality, have resources |
| **GGUF Quantized** ⭐ | Local | FREE | ~32s | 1-2 | 1 | **Most users, best balance** |
| **Qwen Edit** | Cloud | $0.01 | ~30s | 1 | 1 | Simple edits, cheapest |
| **Qwen Edit+** | Cloud | $0.02 | ~40s | 1-2 | 1 | Pose/style transfer |
| **Qwen Image** | Cloud | $0.015 | ~50s | 0 | 1 | Text-to-image, no input |
| **Seedream-4** | Cloud | $0.03/img | ~40s | 1-10 | 1-15 | Multiple outputs |

---

## Use Case Guide

### "I want to edit a photo for free"
→ **GGUF Quantized** (fastest free option)
→ **Qwen Standard** (if you have 64GB RAM and want highest quality)

### "I want to make quick, cheap edits"
→ **Qwen Edit** ($0.01, simple and fast)

### "I want to transfer a pose from one person to another"
→ **Qwen Edit+** ($0.02, pose/style transfer)

### "I want to create an image from scratch (text-to-image)"
→ **Qwen Image** ($0.015, no input image needed)

### "I want to generate multiple variations"
→ **Seedream-4** ($0.03/image, can generate 1-15 outputs)

### "I'm on a limited VRAM system (< 32GB)"
→ **GGUF Q2_K or Q4_K_M** (7-14GB VRAM)
→ Or use any cloud model

---

## Cost Comparison Examples

### Single Edit Workflows
```
Qwen Standard:        FREE
GGUF Quantized:       FREE
Qwen Edit:            $0.01
Qwen Edit+:           $0.02
Qwen Image:           $0.015
Seedream-4 (1 img):   $0.03
```

### Multiple Output Workflows
```
Seedream-4:
  1 output  → $0.03
  4 outputs → $0.12
  10 outputs → $0.30
  15 outputs → $0.45

All others: Only 1 output supported
```

### Batch Processing (100 images)
```
Qwen Standard:   FREE (but ~75 minutes)
GGUF Q5_K_S:     FREE (but ~53 minutes)
Qwen Edit:       $1.00
Qwen Edit+:      $2.00
Qwen Image:      $1.50
```

---

## Backend Implementation

### Routing in `main.py`

```python
# Routes to appropriate handler:
- qwen → generate_image_task() → Local Qwen
- qwen_gguf → generate_image_task() → Local GGUF
- qwen_image_edit → generate_image_qwen_cloud()
- qwen_image_edit_plus → generate_image_qwen_plus()
- qwen_image → generate_image_qwen_text_to_image()
- seedream → generate_image_seedream()
```

### Replicate Client Methods

```python
class ReplicateClient:
    def edit_image()  # Seedream-4
    def edit_image_qwen_cloud()  # qwen/qwen-image-edit
    def edit_image_qwen_plus()  # qwen/qwen-image-edit-plus
    def generate_image_qwen()  # qwen/qwen-image
    def calculate_cost(model_type, num_images)
```

---

## Frontend UI

### Model Selection Layout

```
┌─────────────────────────────────────────────────────┐
│ Local Models (Free)                                 │
├─────────────────────┬──────────────────────────────┤
│ Qwen Standard [FREE]│ GGUF Quantized [RECOMMENDED]│
├─────────────────────┴──────────────────────────────┤
│ Cloud Models (Paid via Replicate)                   │
├─────────┬───────────┬──────────────┬───────────────┤
│Qwen Edit│Qwen Edit+ │ Qwen Image   │ Seedream-4    │
│ $0.01   │  $0.02    │   $0.015     │  $0.03/img    │
└─────────┴───────────┴──────────────┴───────────────┘
```

### Color Coding
- 🟣 Purple: Qwen Standard (local)
- 🟢 Green: GGUF (local, recommended)
- 🟠 Orange: Qwen Edit (cheapest cloud)
- 🩷 Pink: Qwen Edit+ (pose transfer)
- 🟣 Indigo: Qwen Image (text-to-image)
- 🔵 Blue: Seedream-4 (multi-output)

---

## Common Parameters

### All Cloud Models Support
- `output_format` - webp/jpg/png (default: png)
- `output_quality` - 0-100 (default: 100)
- `go_fast` - Fast mode (default: false)
- `disable_safety_checker` - Disable NSFW filter (default: false)

### Local Models Only
- `true_cfg_scale` - CFG scale 1-20
- `num_inference_steps` - Steps 10-100
- `negative_prompt` - What to avoid

### Seedream Only
- `max_images` - 1-15 outputs
- `sequential_image_generation` - auto/disabled
- `size` - 1K/2K/4K

### Qwen-Image Only
- `guidance`, `strength`, `lora_scale`, `image_size`
- Text-to-image specific parameters

---

## Error Handling

All cloud models have **automatic retry logic** (3 attempts, 5s delays):
- ✅ Handles "Prediction interrupted" errors
- ✅ Handles timeout errors
- ✅ Handles 503/502 server errors
- ✅ User sees retry progress
- ✅ Failed retries cost $0

---

## Testing Checklist

### Local Models
- [ ] Qwen Standard: Upload 1 image, edit, download
- [ ] Qwen Standard: Upload 2 images, combine, edit, download
- [ ] GGUF Q2_K: Fast test
- [ ] GGUF Q5_K_S: Quality test
- [ ] GGUF Q8_0: Max quality test

### Cloud Models
- [ ] Qwen Edit: Simple edit, check $0.01 cost
- [ ] Qwen Edit+: 2-image pose transfer, check $0.02 cost
- [ ] Qwen Image: Text-to-image (no input), check $0.015 cost
- [ ] Seedream-4: Multi-output (4 images), check $0.12 cost

### Features
- [ ] Prompt history saves for all models
- [ ] Output gallery shows for all cloud models
- [ ] Cost displayed correctly for each model
- [ ] Model cards visually distinct
- [ ] Image count warnings work

---

## Pricing Summary

### FREE Options (Local)
```
Qwen Standard: $0.00 (requires 64GB RAM)
GGUF Q5_K_S:   $0.00 (requires 17GB VRAM) ⭐ BEST
```

### Cloud Options (by Price)
```
Qwen Edit:        $0.01  (cheapest)
Qwen Image:       $0.015
Qwen Edit+:       $0.02
Seedream-4:       $0.03 per image (multi-output)
```

### When to Pay
- **Need fast results & don't have Mac/GPU** → Qwen Edit ($0.01)
- **Need pose transfer** → Qwen Edit+ ($0.02)
- **Creating from text only** → Qwen Image ($0.015)
- **Need multiple variations** → Seedream-4 ($0.03-0.45)

---

## Recommended Workflow

### For Most Users
1. Start with **GGUF Q5_K_S** (free, fast, good quality)
2. If quality insufficient → Try **Qwen Standard** (free, slower, best quality)
3. If too slow → Try **Qwen Edit** ($0.01, fast)

### For Special Cases
- **Pose transfer:** Qwen Edit+ only
- **Text-to-image:** Qwen Image only
- **Multiple outputs:** Seedream-4 only
- **Low VRAM (<16GB):** GGUF Q2_K or cloud models

---

## Files Modified

### Backend
- `models.py` - Added 3 new ModelType values + parameters
- `replicate_client.py` - Added 3 new handler methods + pricing
- `main.py` - Added 3 new routing functions

### Frontend
- `EditConfig.jsx` - 6 model cards + pricing + info badges
- `App.jsx` - Updated footer stats (6 models)

---

## API Reference

### New Models in Health Endpoint

```bash
curl http://localhost:8000/

{
  "status": "online",
  "models": {
    "qwen": { "cost": "free", "inputs": "1-2", "outputs": "1" },
    "qwen_gguf": { "cost": "free", "inputs": "1-2", "outputs": "1" },
    "qwen_image_edit": { "cost": "$0.01/prediction", "inputs": "1", "outputs": "1" },
    "qwen_image_edit_plus": { "cost": "$0.02/prediction", "inputs": "1-2", "outputs": "1" },
    "qwen_image": { "cost": "$0.015/prediction", "inputs": "text only", "outputs": "1" },
    "seedream": { "cost": "$0.03/image", "inputs": "1-10", "outputs": "1-15" }
  }
}
```

### Request Format

```javascript
// All models
{
  model_type: "qwen_image_edit",  // or qwen_gguf, qwen_image, etc.
  prompt: "change the sky to sunset",
  ...model-specific params
}
```

---

## Known Limitations

### By Model
- **Qwen Standard/GGUF:** Max 2 input images, always 1 output
- **Qwen Edit:** Max 1 input image only
- **Qwen Edit+:** Max 2 input images
- **Qwen Image:** No input images (text-to-image only)
- **Seedream-4:** Max 10 inputs, max 15 outputs

### General
- Cloud models require API token
- Cloud models cost money (except failures)
- Local models require Mac with sufficient RAM/VRAM
- First-time model downloads take 10-30 minutes

---

## Troubleshooting

### "GGUF model won't load"
```bash
pip install 'gguf>=0.10.0'
```

### "Replicate API error"
- Check `REPLICATE_API_TOKEN` in `.env`
- Check account has credits
- Wait for auto-retry (3 attempts)

### "Out of memory with Qwen Standard"
- Use GGUF Q2_K (7GB) or Q4_K_M (14GB)
- Or use cloud models

### "Qwen-Image shows 'no input images' error"
- This is normal - Qwen-Image is text-to-image only
- Don't upload images, just enter prompt

---

## Future Enhancements

Potential additions:
1. **Flux models** - Another text-to-image option
2. **Stable Diffusion XL** - Popular alternative
3. **Model ensembling** - Combine multiple models
4. **A/B testing** - Generate with multiple models, compare
5. **Cost optimizer** - Auto-select cheapest model for task
6. **Batch API** - Process multiple images with one API call

---

## Documentation

- `CLAUDE.md` - Main project documentation
- `CHANGELOG.md` - Version history
- `ALL_MODELS_GUIDE.md` - This file (complete model reference)
- `UI_IMPROVEMENTS.md` - UI changelog

---

## Support

For issues:
1. Check logs in terminal where `./start` is running
2. Check browser console (F12)
3. Verify `.env` has REPLICATE_API_TOKEN
4. Try different model if one fails
5. Check Replicate status: https://status.replicate.com/
