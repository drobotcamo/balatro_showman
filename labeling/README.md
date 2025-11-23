# Balatro Asset Detection - Labeling System

A reusable, incremental annotation workflow for training YOLO object detection models on game assets.

## 📁 Directory Structure

```
labeling/
├── README.md                      ← You are here
├── 1_sample_frames.py             ← Sample frames for annotation
├── 2_prepare_for_labeling.py      ← Set up Label Studio project
├── 3_export_to_yolo.py            ← Convert annotations to YOLO format
├── config.json                    ← Auto-generated state tracking
└── requirements.txt               ← Python dependencies
```

After running, you'll also have:
```
dataset/
├── batches/
│   ├── batch_001/                 ← First 50 sampled frames
│   ├── batch_002/                 ← Next 50 frames
│   └── ...
└── yolo/                          ← Final YOLO training dataset
    ├── images/
    │   ├── train/
    │   └── val/
    ├── labels/
    │   ├── train/
    │   └── val/
    ├── dataset.yaml               ← YOLO config file
    └── classes.txt                ← Class names
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install label-studio ultralytics pillow
```

### 2. Sample Your First Batch

```bash
python 1_sample_frames.py --batch-size 50
```

### 3. Set Up Label Studio

```bash
python 2_prepare_for_labeling.py --asset-json ../image_urls/joker_images.json
label-studio start
```

Follow the printed instructions to configure Label Studio.

### 4. Annotate!

Open http://localhost:8080 and start drawing boxes around jokers.

### 5. Export & Convert

In Label Studio: Export → JSON → Download

```bash
python 3_export_to_yolo.py label_studio_export.json
```

### 6. Train YOLO

```bash
yolo detect train data=dataset/yolo/dataset.yaml model=yolov8n.pt epochs=100
```

---

## 📖 Detailed Script Usage

### `1_sample_frames.py` - Frame Sampler

Intelligently samples frames from your gameplay footage, tracking what's already been sampled.

#### Commands

```bash
# Sample 50 frames (default)
python 1_sample_frames.py

# Sample 100 frames
python 1_sample_frames.py --batch-size 100

# Use distributed sampling (evenly spaced through footage)
python 1_sample_frames.py --batch-size 50 --strategy distributed

# Show sampling statistics without sampling
python 1_sample_frames.py --stats

# Full help
python 1_sample_frames.py --help
```

#### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--batch-size` | int | 50 | Number of frames to sample |
| `--strategy` | choice | random | Sampling strategy: `random` or `distributed` |
| `--stats` | flag | - | Show statistics only, don't sample |
| `--help` | flag | - | Show help message |

#### Examples

```bash
# Sample your first batch of 50 frames
python 1_sample_frames.py

# Check progress
python 1_sample_frames.py --stats

# Sample another 50 frames (automatically creates batch_002)
python 1_sample_frames.py --batch-size 50

# Sample 100 frames with even distribution
python 1_sample_frames.py --batch-size 100 --strategy distributed
```

#### Output

Creates a new batch directory with sampled frames:
- `dataset/batches/batch_001/` (first run)
- `dataset/batches/batch_002/` (second run)
- etc.

Updates `config.json` with sampling history.

---

### `2_prepare_for_labeling.py` - Label Studio Setup

Generates Label Studio configuration and import files for your batches.

#### Commands

```bash
# Prepare for all batches (default)
python 2_prepare_for_labeling.py

# Prepare specific asset type
python 2_prepare_for_labeling.py --asset-json ../image_urls/voucher_images.json

# Prepare only a specific batch
python 2_prepare_for_labeling.py --batch 2

# Full help
python 2_prepare_for_labeling.py --help
```

#### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--asset-json` | str | `../image_urls/joker_images.json` | Path to asset JSON file |
| `--batch` | int | None | Specific batch number (optional) |
| `--help` | flag | - | Show help message |

#### Examples

```bash
# Prepare Label Studio for jokers (first time)
python 2_prepare_for_labeling.py

# Add batch 2 to existing project
python 2_prepare_for_labeling.py --batch 2

# Prepare for different asset type
python 2_prepare_for_labeling.py --asset-json ../image_urls/planet_images.json
```

#### Output

Creates:
- `label_studio_config.xml` - Labeling interface configuration
- `label_studio_import_batch_X.json` - Import file for Label Studio
- Prints detailed setup instructions

---

### `3_export_to_yolo.py` - YOLO Converter

Converts Label Studio annotations to YOLO training format with train/val split.

#### Commands

```bash
# Convert annotations (basic)
python 3_export_to_yolo.py label_studio_export.json

# Specify asset type
python 3_export_to_yolo.py label_studio_export.json --asset-json ../image_urls/joker_images.json

# Custom output directory
python 3_export_to_yolo.py label_studio_export.json --output my_dataset

# Custom train/val split (default 80/20)
python 3_export_to_yolo.py label_studio_export.json --train-split 0.9

# Full help
python 3_export_to_yolo.py --help
```

#### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `export_json` | str | - | **Required**: Path to Label Studio export JSON |
| `--asset-json` | str | `../image_urls/joker_images.json` | Path to asset JSON file |
| `--output` | str | `dataset/yolo` | Output directory for YOLO dataset |
| `--train-split` | float | 0.8 | Training split ratio (0.0-1.0) |
| `--help` | flag | - | Show help message |

#### Examples

```bash
# Standard conversion
python 3_export_to_yolo.py label_studio_export.json

# 90% train, 10% validation
python 3_export_to_yolo.py label_studio_export.json --train-split 0.9

# Export to custom directory
python 3_export_to_yolo.py label_studio_export.json --output ../training_data

# Different asset type
python 3_export_to_yolo.py vouchers_export.json --asset-json ../image_urls/voucher_images.json
```

#### Output

Creates complete YOLO dataset:
- Images organized into `train/` and `val/`
- Labels in corresponding directories
- `dataset.yaml` configuration file
- `classes.txt` with class names

---

## 🔄 Complete Workflow Example

### Initial Training (Week 1)

```bash
# 1. Sample 50 frames
python 1_sample_frames.py --batch-size 50

# 2. Set up Label Studio
python 2_prepare_for_labeling.py
label-studio start

# 3. Annotate in Label Studio (45 minutes)
# Open http://localhost:8080, follow setup instructions

# 4. Export from Label Studio
# Click Export → JSON → Save as label_studio_export_v1.json

# 5. Convert to YOLO
python 3_export_to_yolo.py label_studio_export_v1.json

# 6. Train initial model
yolo detect train data=dataset/yolo/dataset.yaml model=yolov8n.pt epochs=100
```

### Adding More Data (Week 2)

```bash
# 1. Sample another batch
python 1_sample_frames.py --batch-size 50

# 2. Import new batch into existing Label Studio project
python 2_prepare_for_labeling.py --batch 2

# 3. Import in Label Studio
# Go to project → Import → Upload label_studio_import_batch_2.json

# 4. Annotate new frames (45 minutes)

# 5. Export everything from Label Studio
# Export now includes ALL annotations (batch 1 + batch 2)
# Save as label_studio_export_v2.json

# 6. Re-convert with more data
python 3_export_to_yolo.py label_studio_export_v2.json

# 7. Re-train with expanded dataset
yolo detect train data=dataset/yolo/dataset.yaml model=yolov8n.pt epochs=100
```

---

## 📊 Monitoring Progress

### Check Sampling Status

```bash
python 1_sample_frames.py --stats
```

Output:
```
📊 Sampling Statistics
==================================================
Total frames available:  10800
Frames sampled:          150 (1.4%)
Frames remaining:        10650
Batches created:         3
==================================================

📦 Batch History:
  batch_001: 50 frames (2025-11-23)
  batch_002: 50 frames (2025-11-25)
  batch_003: 50 frames (2025-11-27)
```

### Check YOLO Dataset

After conversion, check the dataset summary printed by `3_export_to_yolo.py`:

```
📊 Train: 120 images, 450 boxes
📊 Val:   30 images, 112 boxes
```

---

## 💡 Tips & Best Practices

### Sampling Strategy

- **Start with 50 frames** - Good balance of effort vs. initial results
- **Use random sampling first** - Gets diverse scenes
- **Add batches incrementally** - 50 frames every few days as you test
- **Switch to distributed** - If random misses important gameplay phases

### Annotation Tips

- **Take breaks** - Annotate 25 images, take 5 min break
- **Be consistent** - Always include the same parts of assets (full card vs. just icon)
- **Difficult cases** - If asset is <50% visible, skip it or annotate visible portion only
- **Overlapping assets** - Annotate all visible assets, even if they overlap
- **Keyboard shortcuts** - Use number keys (1-9) for quick class selection

### Training Recommendations

- **Start small** - 50-100 annotated images can give initial results
- **Iterate** - Train → Test → Add more data where model fails → Retrain
- **Monitor metrics** - Watch mAP (mean Average Precision) during training
- **Target metric** - Aim for mAP50 > 0.7 for good detection

### Growing Your Dataset

| Dataset Size | Expected Quality | Use Case |
|--------------|------------------|----------|
| 50 images | Basic detection | Proof of concept |
| 100 images | Fair detection | Early testing |
| 200 images | Good detection | Practical use |
| 300+ images | Excellent detection | Production ready |

---

## 🐛 Troubleshooting

### Label Studio won't start

```bash
# Try specifying a port
label-studio start --port 8090
```

### Images not loading in Label Studio

Make sure you:
1. Configured local storage correctly
2. Used absolute paths in storage settings
3. Have read permissions on the batch directories

### Script can't find config.json

Run from the `labeling/` directory:
```bash
cd labeling/
python 1_sample_frames.py
```

### No frames left to sample

```bash
# Check status
python 1_sample_frames.py --stats

# You've sampled everything! Either:
# 1. Capture more gameplay footage
# 2. Reset sampling (delete config.json) - WARNING: loses history
```

### YOLO training fails

Check:
- `dataset.yaml` has correct absolute paths
- Images and labels exist in train/val directories
- At least 10+ images in training set
- PyTorch and ultralytics are installed

---

## 🔧 Configuration

### config.json Structure

```json
{
  "screenshots_dir": "gameplay_screenshots",
  "output_dir": "dataset",
  "sampled_frames": ["path/to/frame1.png", "..."],
  "batches": [
    {
      "batch_num": 1,
      "batch_name": "batch_001",
      "batch_dir": "dataset/batches/batch_001",
      "frame_count": 50,
      "sampled_at": "2025-11-23T10:30:00",
      "files": ["..."]
    }
  ],
  "current_batch": 1
}
```

### Resetting State

To start fresh (loses sampling history):
```bash
rm config.json
python 1_sample_frames.py  # Creates new config
```

---

## 📚 Additional Resources

- [Label Studio Documentation](https://labelstud.io/guide/)
- [YOLO Documentation](https://docs.ultralytics.com/)
- [YOLO Training Tips](https://docs.ultralytics.com/guides/model-training-tips/)

---

## 🎯 Next Steps

After your first successful training:

1. **Test the model** on new gameplay footage
2. **Identify failure cases** (missed detections, false positives)
3. **Sample more frames** from problem areas
4. **Annotate** the new frames
5. **Retrain** with expanded dataset
6. **Iterate** until satisfied with performance

Good luck! 🚀
