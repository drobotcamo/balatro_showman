# Balatro Showman — Claude Knowledge Base

Read this at the start of every session. It captures all key decisions and context so work can continue without re-explaining.

## What This Project Is

A tool that advises on shop decisions in Balatro at **Gold Stake** (hardest difficulty). It uses computer vision on gameplay footage to build a knowledge base of decisions correlated with run outcomes, then recommends actions given a current game state.

**Scope:** Shop decisions only (buy, sell, skip). In-round gameplay is explicitly out of scope for now.

## Key Decisions Made

### Difficulty & Data
- Target: Gold Stake only. Wins are rare and highly valuable signal.
- Training footage: YouTube, top/skilled players only. This keeps shop decisions high quality and makes in-round mistakes a non-issue.
- Both wins and losses are valuable — wins validate full decision chains, losses are informative failures.

### CV Strategy: YOLO26 Object Detection

- **Template matching was abandoned.** Produced zero hits on small assets (stickers). Shop slot positions are not fixed enough for a two-pass (slot detect → classify) approach.
- **Current approach:** Fine-tune YOLO26s (`yolo26s.pt`) on footage-labeled bounding boxes. One unified model detects all asset types in a single pass per frame.
- **Class naming convention:** `type:name` (e.g. `joker:Strength`, `tarot:Death`, `sticker:Eternal`). Type-prefixed to prevent cross-type name collisions and make detections self-describing.
- Training: freeze first 10 backbone layers (`freeze=10`), fine-tune from pretrained weights. Upgrade to `yolo26m.pt` if accuracy is insufficient after more data.

### Labeling Suite

`python main.py extract BU1` — draw bbox around every visible asset in a frame, name it, press Enter. Repeat for all visible assets, move to next frame.

- Voice input (Whisper), zoom/pan, asset name autocomplete + fuzzy match, undo, Tab/Shift+Tab to cycle asset types.
- Each save writes two files to `recorded_gameplay_asset_images/<type>/`:
  - `AssetName.png` — cropped region (for `assets browse/stats`)
  - `AssetName.json` — sidecar with `video_path`, `frame_idx`, `frame_w`, `frame_h`, `asset_type`, `asset_name`, `bbox_xyxy`
- The sidecar JSON is what enables YOLO dataset building. **Crops without sidecars cannot be used for training.**

### Decision Detection (deferred)
Compare consecutive frames for inventory delta (item appears/disappears from shop). Comes after element detection is proven.

## Current Phase

**Phase 1 — YOLO Object Detection** (in progress — labeling data, not yet trained)

The pipeline:
1. Label footage: `python main.py extract BU1` — label every visible asset per frame
2. Build dataset: `python main.py dataset build` — extracts full frames + writes YOLO format
3. Train: `python main.py train --name balatro --epochs 100`
4. Detect: `python main.py detect BU1 --model runs/detect/balatro/weights/best.pt`

Dataset build is idempotent. Re-label → rebuild → retrain as coverage grows.

## Repo Contents

- `game_asset_images/` — wiki PNG sprites (name reference only, NOT for detection)
- `recorded_gameplay_asset_images/` — labeled crops + sidecar JSONs (source of truth)
- `gameplay_sources/gameplay_footage/` — Gold Stake mp4 files (aliased as BU1, BU2, ...)
- `gameplay_sources/downloader.py` — yt-dlp wrapper
- `detectors/yolo_detector.py` — YoloDetector: wraps ultralytics YOLO, parses `type:name` classes
- `detectors/assets.py` — (deprecated) template-matching detector, kept for reference
- `tools/detect.py` — `detect` command: samples frames, runs YOLO, writes annotated JPEGs + detections.jsonl
- `tools/extract_templates.py` — labeling GUI (voice + zoom, writes crop + sidecar JSON)
- `tools/build_dataset.py` — builds YOLO dataset from labeled sidecar JSONs
- `tools/build_synthetic_dataset.py` — builds synthetic YOLO dataset by compositing wiki sprites onto footage frames
- `tools/train.py` — wraps ultralytics YOLO train
- `tools/models.py` — trained model registry; active model tracking via `.model` file
- `tools/assets.py` — asset inspector (`stats`, `browse`); defines `ASSET_TYPE_TO_DIR`
- `tools/videos.py` — BU alias resolver
- `main.py` — unified CLI entry point
- `architecture.md` — full architecture plan (keep in sync with this file)

## CLI Entry Point

Everything runs through `main.py`:

```bash
python main.py videos                                           # list footage BU aliases
python main.py download <url>                                   # download YouTube footage
python main.py extract BU1                                     # labeling GUI
python main.py dataset build [--output-dir dataset]            # build YOLO dataset from sidecars
python main.py dataset synthetic [--output-dir dataset_synthetic]  # build synthetic dataset from wiki sprites
python main.py train [--name balatro] [--epochs 100]           # train YOLO26s
python main.py models                                           # list trained models + mAP50
python main.py models use balatro_synthetic                     # set active model
python main.py detect BU1                                       # run detection (uses active model)
python main.py detect BU1 --model balatro_v2                    # run detection (override model)
python main.py assets stats [type]                             # coverage report
python main.py assets browse [type]                            # thumbnail grid
```

Tab completion: `echo 'eval "$(register-python-argcomplete main.py)"' >> ~/.bashrc`

## Tech Stack

- Python, OpenCV (cv2), Pillow
- YOLO26 (Ultralytics) + PyTorch — primary CV engine
- `argcomplete` — CLI tab completion
- `openai-whisper` + `sounddevice` — voice input in labeling tool
- `pyyaml` — dataset YAML writing
- SQLite or PostgreSQL — run/decision knowledge base (TBD, not started)

## Working Style Notes

- Don't build until the plan is agreed on. Design/propose first.
- Keep this file and `architecture.md` in sync as decisions evolve.

## Model Selection

YOLO26 comes in a size ladder. Bigger = more parameters = more capacity = needs more data and more time to train:

| Model | Params | When to use |
|---|---|---|
| `yolo26n.pt` | 2.6M | Fastest iteration, very sparse data |
| `yolo26s.pt` | 9.4M | Default. Sparse data (<500 labeled frames), good balance of speed and accuracy |
| `yolo26m.pt` | 20M | Step up when small confuses visually similar assets with good label coverage |
| `yolo26l.pt` | 25M | Hundreds of labeled frames, accuracy is the priority over speed |
| `yolo26x.pt` | 56M | Large dataset, maximum accuracy, offline use only |

**Signal to upgrade:** if the trained model confuses visually similar assets (e.g. one joker for another) even after adding more labels, that's a capacity problem — increase model size. If it's missing detections entirely, that's a data problem — label more.

**GPU acceleration:** This machine has an AMD RX 6800S — no CUDA. Use DirectML:
```bash
pip install torch-directml   # one-time install
python main.py train --data dataset_synthetic/dataset.yaml --name balatro_v2 --device directml
```
`--device` accepts `""` (auto/CPU), `"cpu"`, `"0"` (CUDA GPU 0), or `"directml"` (AMD/Intel on Windows).

**Active model** is tracked in `.model` (gitignored). Manage with:
```bash
python main.py models                       # list all trained runs + mAP50
python main.py models use balatro_synthetic # set active
python main.py detect BU1                   # uses active model automatically
python main.py detect BU1 --model balatro_v2  # override by run name
```

`--model` accepts either a run name (resolved to `runs/detect/<name>/weights/best.pt`) or a full `.pt` path.

## Code Conventions

**Progress bars are mandatory for any operation that may take more than a second** — frame extraction, dataset building, training loops, video sampling, etc. Use `from utils import progress` (never import tqdm directly). The `progress()` wrapper keeps defaults consistent and provides a single place to change output behavior globally.

```python
# iterable form
for frame in progress(frames, desc="Processing", unit="frame"):
    ...

# context manager form (when total is known but loop is internal)
with progress(total=500, desc="Extracting", unit="frame") as bar:
    ...
    bar.update(1)
```
