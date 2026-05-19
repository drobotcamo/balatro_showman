# Balatro Showman

Tool that will make informed decisions in Balatro at the highest difficulty (Gold Stake / Black Stake). The goal is to advise on shop decisions — what to buy, sell, or skip.

## System Overview

**Computer Vision** — CV extracts accurate game data from Balatro gameplay footage or screenshots. Data is used to recreate game states and form them into events.

**Knowledge Acquisition** — Game states from footage are analyzed to identify decisions (via before/after state deltas) and associate them with the run's outcome (win or loss). This builds a knowledge base of shop decisions correlated with run outcomes.

**Value Proposal** — Given a screenshot or game state, a recommended decision is generated based on the stored knowledge.

## Difficulty & Data Context

- Target difficulty: **Gold Stake** (hardest). Wins are rare and represent highly valuable decision sets.
- Training data source: YouTube footage from **top/skilled players only**. This omits in-round gameplay mistakes (unlikely for seasoned players anyway) and keeps the knowledge base focused on shop-level strategy.
- Both wins and losses are valuable training signal — wins validate full decision chains, losses are informative failures.
- **In-round gameplay is explicitly out of scope for now.** Only shop decisions are being modeled.

## Precision: Important

Accuracy of the tool requires near-100% recognition of gameplay elements. For this reason, detection uses a single unified YOLO11 model that detects all asset types in one pass, with type-prefixed class names (`joker:Strength`, `tarot:Death`, etc.) to make detections self-describing.

Gameplay element categories (sorted by importance):

0. Jokers
1. Stickers
2. Balance $
3. Skip Tags
4. Booster Packs
5. Tarot Cards
6. Planet Cards
7. Vouchers
8. Spectral Cards

## Gameplay States

State transitions that need to be detected:

1. Winning a run
2. Losing a run
3. Starting a run
4. Restarting a run
5. Entering a new shop
6. Exiting a shop
7. Selling a purchaseable
8. Buying a purchaseable

## CV Approach

**Phase 0 — Template Matching (abandoned):** Attempted first due to simplicity. Produced zero hits on small assets (stickers). Shop slot positions are not predictable enough for a fixed-slot approach. Superseded.

**Phase 1 — YOLO11 Object Detection (current):** Fine-tune YOLO11s on footage-labeled bounding boxes. Handles variable asset positions, small assets, and occlusion without per-asset template management.

- Class naming: `type:name` (e.g. `joker:Strength`, `sticker:Eternal`). Type-prefixed to prevent cross-type name collisions and make detections self-describing.
- One unified model detects all asset types in a single pass per frame.
- Base model: `yolo11s.pt`. Upgrade to `yolo11m.pt` if accuracy is insufficient.
- Training: fine-tune from pretrained weights with `freeze=10` (backbone layers frozen).

Decision detection (identifying *when* a decision was made by comparing consecutive frames for state delta) comes **after** element detection is proven.

## Dataset Pipeline

```
python main.py extract <video>        # label assets in footage (GUI)
                                      # saves crop PNG + sidecar JSON per labeled asset
                                      # sidecar contains: video_path, frame_idx, bbox_xyxy

python main.py dataset build          # reads all sidecars, extracts full frames from videos,
                                      # writes YOLO-format images/ + labels/ + dataset.yaml

python main.py train                  # fine-tunes YOLO11s on the built dataset
                                      # output: runs/detect/balatro/weights/best.pt

python main.py detect <video>         # runs best.pt on sampled frames, saves annotated output
```

Re-label → rebuild dataset → retrain as coverage grows. Dataset build is idempotent.

## Data Storage

A database with related objects to represent everything in a run. Architecture TBD — needs refinement once CV layer is proven.

## Score Generation (MVP)

Focus on purchase decisions in a shop. "Not buying" is also a decision and carries weight. Given a detected game state, compare against the knowledge base to recommend an action.

# Repo Structure

```text
main.py                          # unified CLI entry point (python main.py <command>)
test_harness.py                  # detection test harness (detect subcommand)

./gameplay_sources
  /gameplay_footage              # mp4 files — aliased as BU1, BU2, ... by mtime
  downloader.py                  # yt-dlp wrapper: downloads YouTube footage at 1080p

./game_asset_images              # wiki PNG sprites — name reference ONLY, not for detection
  /blind_images
  /booster_images
  /joker_images
  /tag_images
  ... (etc.)

./recorded_gameplay_asset_images # footage-extracted crops + sidecar JSONs (source of truth)
  /jokers                        # each PNG has a matching .json with bbox metadata
  /tags
  ... (etc.)

./game_asset_urls                # scraped asset URLs and HTML from Balatro wiki
  /htmls
  *.json

./detectors
  yolo_detector.py               # YoloDetector: wraps ultralytics YOLO, parses type:name classes
  assets.py                      # (deprecated) template-matching detector, kept for reference

./tools
  extract_templates.py           # labeling GUI: draws bbox, names asset, saves crop + sidecar JSON
  build_dataset.py               # builds YOLO dataset from sidecars (images/ + labels/ + yaml)
  train.py                       # wraps ultralytics YOLO train
  assets.py                      # asset inspector: coverage stats + thumbnail browse
  videos.py                      # BU alias resolver and video listing

./dataset                        # YOLO-format training dataset (gitignored)
  images/train/  images/val/
  labels/train/  labels/val/
  dataset.yaml
  classes.txt

./runs                           # ultralytics training output (gitignored)
  /detect/balatro/weights/best.pt

./runs_db                        # run and decision storage (future)
```

# Tech Stack

- **Python** — primary language
- **YOLO11s (Ultralytics)** — object detection, fine-tuned from pretrained weights
- **PyTorch** — model training backbone
- **OpenCV (cv2)** — frame extraction, image preprocessing, bounding box rendering
- **Pillow** — image handling
- **SQLite or PostgreSQL** — run/decision knowledge base storage (TBD)
- `argcomplete` — CLI tab completion (bash)
- `openai-whisper` + `sounddevice` — voice input in labeling tool
- Labeling suite: custom-built (`tools/extract_templates.py`) with voice, zoom, autocomplete
