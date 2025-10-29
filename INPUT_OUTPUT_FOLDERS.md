# ~/input and ~/output Folder Feature

## Overview

The Image Editor now supports **default input and output folders** for a streamlined workflow:
- **~/input** - Drop images here for quick access
- **~/output** - All generated images automatically copied here

---

## Quick Workflow

### Traditional (Upload Files)
```
1. Click "Upload" button
2. Browse filesystem
3. Select images
4. Upload
5. Configure & Generate
6. Download from browser
```

### New (Folder-Based)
```
1. Drop images in ~/input
2. Open app → See "N images found in ~/input"
3. Click "Browse Folder"
4. Click images to add them
5. Configure & Generate
6. ✨ Outputs automatically in ~/output
```

---

## Features

### ✅ 1. Input Folder Browser

**UI:**
```
┌────────────────────────────────────────────────┐
│ 📁 5 images found in ~/input                  │
│    Drop images in ~/input folder for quick... │
│                              [Browse Folder]   │
└────────────────────────────────────────────────┘

↓ Click "Browse Folder" ↓

┌──────────┬──────────┬──────────┬──────────┐
│ [Thumb 1]│ [Thumb 2]│ [Thumb 3]│ [Thumb 4]│
│ image.jpg│ photo.png│ pic.webp │ shot.jpg │
│ 2048×1536│ 1920×1080│ 3840×2160│ 1024×768 │
└──────────┴──────────┴──────────┴──────────┘
     ↑ Click any thumbnail to add to selection
```

**Features:**
- Auto-detects images in ~/input on page load
- Shows count: "5 images found"
- Click "Browse Folder" to expand grid
- Shows actual image thumbnails (not icons!)
- Displays dimensions below each thumbnail
- Hover shows "Click to add"
- Click thumbnail → Adds to selected images
- Sorted by modified time (newest first)
- Lazy loading for performance

---

### ✅ 2. Automatic Output Copying

**All generated images automatically copied to ~/output**

**File Naming:**
```
~/output/
├── {job-id}_output_0.jpg
├── {job-id}_output_1.jpg
├── {job-id}_output_2.jpg
└── {job-id}_output.jpg
```

Example:
```
22967f30-92c6-4d9d-9ebe-99a9921f3112_output_0.webp
22967f30-92c6-4d9d-9ebe-99a9921f3112_output_1.webp
```

**Benefits:**
- ✅ Persist outputs even after job cleanup
- ✅ Easy to find all your generated images
- ✅ Job ID prefix prevents filename conflicts
- ✅ Works for all 6 models
- ✅ Works for single and multi-image outputs
- ✅ Non-blocking (doesn't slow down completion)

**UI Indicator:**
```
Output Images (3)
📁 Also saved to ~/output/
```

---

## Configuration

### Backend (.env)
```bash
# Default input/output folders
INPUT_FOLDER=~/input
OUTPUT_FOLDER=~/output
```

### Directories Created Automatically
```bash
# On app startup:
mkdir -p ~/input
mkdir -p ~/output
```

**Logs show:**
```
INFO: Input folder: /Users/you/input
INFO: Output folder: /Users/you/output
```

---

## API Endpoints

### GET /api/input-folder/list
List all images in ~/input folder

**Response:**
```json
{
  "folder": "/Users/you/input",
  "images": [
    {
      "filename": "photo.jpg",
      "path": "/Users/you/input/photo.jpg",
      "size_bytes": 2458624,
      "width": 2048,
      "height": 1536,
      "modified": 1698765432.123
    },
    ...
  ],
  "count": 5
}
```

### GET /api/input-folder/image/{filename}
Serve a specific image from ~/input

**Example:**
```
GET /api/input-folder/image/photo.jpg
→ Returns image file
```

**Supported Formats:**
- .jpg, .jpeg
- .png
- .webp
- .bmp

---

## User Experience

### Setup
```bash
# 1. Create folders (happens automatically on first run)
mkdir -p ~/input ~/output

# 2. Add images to input folder
cp ~/Pictures/*.jpg ~/input/

# 3. Start app
./start
```

### Usage Flow
```
1. Open browser → http://localhost:3000
2. See notification: "5 images found in ~/input"
3. Click "Browse Folder"
4. See thumbnail grid of all images
5. Click thumbnails to add them (up to 10)
6. Selected images appear in main preview
7. Click "Next: Configure Edit"
8. Select model, enter prompt
9. Generate
10. ✨ Outputs saved to ~/output automatically
11. Download individual images if needed
12. Check ~/output for all generated images
```

---

## Implementation Details

### Backend (main.py)

**Configuration:**
```python
INPUT_FOLDER = Path(os.path.expanduser('~/input'))
OUTPUT_FOLDER = Path(os.path.expanduser('~/output'))
```

**Startup:**
```python
INPUT_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
```

**Output Copying:**
```python
def copy_outputs_to_folder(job_id, output_images):
    for filename in output_images:
        source = JOBS_DIR / job_id / filename
        dest = OUTPUT_FOLDER / f"{job_id}_{filename}"
        shutil.copy2(source, dest)
```

Called after every job completion (all 6 models).

### Frontend (ImageUpload.jsx)

**State:**
```javascript
const [inputFolderImages, setInputFolderImages] = useState([])
const [showInputFolder, setShowInputFolder] = useState(false)
```

**Load on Mount:**
```javascript
useEffect(() => {
  loadInputFolderImages()
}, [])
```

**Click Handler:**
```javascript
onClick={async () => {
  const response = await fetch(`/api/input-folder/image/${img.filename}`)
  const blob = await response.blob()
  const file = new File([blob], img.filename, ...)
  // Add to selected files
}}
```

---

## File Organization

### Before (Manual Downloads)
```
~/Downloads/
├── edited_abc123.jpg
├── edited_def456.jpg
├── edited_ghi789.jpg
└── ... (scattered, hard to find)
```

### After (Automatic Organization)
```
~/input/
├── photo1.jpg     ← You drop images here
├── photo2.png
└── photo3.webp

~/output/
├── abc123_output_0.jpg  ← Automatically saved here
├── abc123_output_1.jpg
├── def456_output.jpg
└── ghi789_output_0.webp
```

---

## Benefits

### For Users
- ✅ **Faster workflow** - No file browser dialogs
- ✅ **Quick access** - Drop files in ~/input once
- ✅ **Organized outputs** - All in one place
- ✅ **No manual saving** - Auto-copied to ~/output
- ✅ **Persistent** - Outputs remain after job cleanup
- ✅ **Easy sharing** - Point others to ~/output folder

### For Batch Processing
```bash
# Add 50 images
cp ~/Photos/*.jpg ~/input/

# Process them one by one using folder browser
# All outputs accumulate in ~/output/

# Easy to find all results
ls ~/output/
```

---

## Advanced Usage

### Scripting with Folders
```bash
# 1. Clear output folder
rm ~/output/*

# 2. Add input images
cp source_images/*.jpg ~/input/

# 3. Process via app
# (manually or with automation)

# 4. Collect all results
cp ~/output/* final_results/
```

### Monitoring Output Folder
```bash
# Watch for new outputs in real-time
watch -n 1 ls -lh ~/output/

# Count total outputs
ls ~/output/ | wc -l

# Find outputs from specific job
ls ~/output/*abc123*
```

---

## Limitations

### Input Folder
- Max 10 images displayed at once
- Must be valid image formats (jpg, png, webp, bmp)
- Files must be readable by backend
- No subdirectory scanning (flat structure only)

### Output Folder
- Files prefixed with job ID (can't customize)
- Old outputs not auto-deleted (manual cleanup needed)
- Copies files (doesn't move) - job folder keeps originals

---

## Troubleshooting

### "No images found in ~/input"
```bash
# Check folder exists
ls -la ~/input

# Add some images
cp ~/Pictures/*.jpg ~/input/

# Refresh page
```

### "Failed to load image from ~/input folder"
- Check file permissions: `chmod 644 ~/input/*`
- Check file isn't corrupted
- Check backend has access to ~/input
- Check backend logs for specific error

### "Outputs not appearing in ~/output"
- Check folder exists: `ls ~/output`
- Check backend logs for copy errors
- Check disk space: `df -h ~`
- Check folder permissions: `ls -la ~/ | grep output`

### "Too many files in ~/output"
```bash
# Clean old outputs (manually)
rm ~/output/*

# Or keep only recent (last 24 hours)
find ~/output -type f -mtime +1 -delete
```

---

## Security Notes

- ✅ Input folder only serves to authenticated sessions
- ✅ Path traversal prevented (filename validation)
- ✅ File type validation (only images)
- ✅ Size limits still apply (100MB max)
- ✅ Folders isolated to user's home directory

---

## Performance

### Input Folder Loading
- Fetches file list on page load (~10-100ms)
- Lazy loads thumbnails (only visible ones)
- Efficient for 100+ images

### Output Copying
- Happens asynchronously after job completes
- Non-blocking (doesn't delay UI)
- Errors logged but don't fail job
- Uses shutil.copy2 (preserves metadata)

---

## Future Enhancements

Potential improvements:
1. **Auto-process ~/input** - Watch folder, auto-generate
2. **Subdirectory support** - Organize inputs in folders
3. **Smart naming** - Custom output filename patterns
4. **Output cleanup** - Auto-delete old outputs
5. **Input folder upload** - Drag folder to upload all
6. **ZIP export** - Download ~/output as ZIP
7. **Folder sync** - Cloud storage integration
8. **Batch mode** - Process all ~/input images automatically

---

## Testing

### Test Input Folder
```bash
# 1. Add test images
cp test1.jpg test2.png ~/input/

# 2. Start app
./start

# 3. Upload page should show:
"2 images found in ~/input"

# 4. Click "Browse Folder"
# 5. See thumbnails of test1.jpg and test2.png
# 6. Click a thumbnail
# 7. Image added to selection
```

### Test Output Folder
```bash
# 1. Generate any image
# 2. Wait for completion
# 3. Check output folder:
ls ~/output/

# Should see:
# {job-id}_output_0.jpg (or .webp/.png)

# 4. Verify file exists and opens correctly
open ~/output/*.jpg
```

### Test with Multiple Outputs
```bash
# 1. Use Seedream-4 with max_images: 4
# 2. Generate
# 3. Check ~/output:
ls ~/output/

# Should see:
# {job-id}_output_0.jpg
# {job-id}_output_1.jpg
# {job-id}_output_2.jpg
# {job-id}_output_3.jpg
```

---

## Files Modified

### Backend
- `.env` - Added INPUT_FOLDER and OUTPUT_FOLDER paths
- `main.py` - Added endpoints, copy function, folder initialization

### Frontend
- `utils/api.js` - Added listInputFolderImages()
- `ImageUpload.jsx` - Added folder browser UI
- `ProgressTracker.jsx` - Added output folder indicator

---

## Command Reference

### Setup
```bash
# Create folders
mkdir -p ~/input ~/output

# Add images
cp images/*.jpg ~/input/
```

### Monitor
```bash
# Watch input folder
ls -lh ~/input/

# Watch output folder (live updates)
watch -n 1 ls -lh ~/output/

# Count outputs
ls ~/output/ | wc -l
```

### Cleanup
```bash
# Clear input folder
rm ~/input/*

# Clear output folder
rm ~/output/*

# Keep only recent outputs (last hour)
find ~/output -type f -mmin +60 -delete
```

### Organize
```bash
# Move outputs to organized folders
mkdir ~/output/batch1
mv ~/output/*abc123* ~/output/batch1/

# Archive old outputs
tar -czf outputs_$(date +%Y%m%d).tar.gz ~/output/
```

---

## Summary

### What You Can Do Now

1. **Drop images in ~/input** - No need to browse every time
2. **Browse visually** - See thumbnails of all input images
3. **Click to add** - Quick selection from folder
4. **Auto-saved outputs** - All results in ~/output automatically
5. **Organized workflow** - Input → Process → Output (all in folders)

### Key Advantages

- ⚡ **Faster** - No file dialogs
- 📂 **Organized** - Dedicated folders
- 🔄 **Reusable** - Keep inputs, accumulate outputs
- 🤖 **Scriptable** - Easy to automate
- 🎯 **Focused** - See only relevant images

---

## Real-World Examples

### Photo Editing Batch
```
Day 1:
cp vacation_photos/*.jpg ~/input/
Process 20 images → 20 outputs in ~/output/

Day 2:
cp work_photos/*.png ~/input/
Process 15 images → 35 outputs total in ~/output/

Day 3:
Archive: tar -czf week1_outputs.tar.gz ~/output/
Clean: rm ~/output/*
```

### Style Transfer Project
```
~/input/
├── style_reference.jpg
├── portrait1.jpg
├── portrait2.jpg
└── portrait3.jpg

Generate 3 jobs with Qwen Edit+ (pose transfer)

~/output/
├── job1_output_0.jpg  (portrait1 + style)
├── job2_output_0.jpg  (portrait2 + style)
└── job3_output_0.jpg  (portrait3 + style)
```

### Text-to-Image Collection
```
Use Qwen-Image (text-to-image)
No ~/input needed

Generate 10 different prompts

~/output/
├── job1_output_0.webp  (prompt 1)
├── job2_output_0.webp  (prompt 2)
├── ...
└── job10_output_0.webp (prompt 10)

All in one place!
```

---

Ready to test! Drop some images in ~/input and try the new workflow! 🚀
