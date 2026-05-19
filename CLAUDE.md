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

### CV Strategy: Template Matching First

- Balatro uses fixed pixel-art sprites. Use OpenCV `cv2.matchTemplate` against known assets.
- **Critical finding:** Wiki/asset sprites do NOT match in-game rendering. Video compression and in-game rendering shift pixels enough that scores max at ~0.65, well below the 0.75 threshold.
- **Correct approach:** Extract templates directly from real gameplay footage using `tools/extract_templates.py`. Store in `recorded_gameplay_asset_images/<type>/`. Templates from footage match footage.
- Scale must be derived from video resolution: `base_scale = video_width / 1280`. Search at `[base * 0.85, base, base * 1.15]`.
- Only escalate to YOLOv8 fine-tuning if template matching demonstrably fails even with footage-extracted templates.

### Detection Order
Start with **Skip Tags** for the first PoC. Once this works, the detector + test harness pattern becomes the template for all other element types.

### Skip Tag ROI

Tags appear on the blind selection screen. Confirmed working ROI: `x=0.25–0.65, y=0.55–0.90` (fractions of frame). Tune via `--roi` flag and `--save-all` to visually verify.

### Decision Detection (deferred)
Compare consecutive frames for inventory delta (item appears/disappears from shop). Comes after element detection is proven.

### Labeling Suite

Built custom — `python main.py extract BU1`. Features: voice input (Whisper), zoom/pan, autocomplete asset names from reference library, fuzzy name matching to enforce naming convention, undo, Tab/Shift+Tab to cycle asset types. Saves to `recorded_gameplay_asset_images/<type>/`.

## Current Phase

**Phase 0 — Skip Tag Template Matching PoC** (in progress, blocked on template collection)

- `detectors/skip_tags.py` — built and working. Auto-scales to video resolution, ROI cropping, NMS, debug mode.
- `test_harness.py` — built. `--frames`, `--debug`, `--save-all`, `--n-frames`, `--roi` flags.
- **Blocker:** Need to collect footage-extracted templates via the labeling tool before detection can be validated.
- Success = 90%+ accuracy, no false positives.

## Repo Contents

- `game_asset_images/` — wiki PNG sprites (use as name reference only, NOT as templates)
- `recorded_gameplay_asset_images/` — footage-extracted templates (source of truth for detection)
- `gameplay_sources/gameplay_footage/` — Gold Stake mp4 files (aliased as BU1, BU2, …)
- `gameplay_sources/downloader.py` — yt-dlp wrapper
- `detectors/skip_tags.py` — skip tag detector
- `test_harness.py` — detection test harness
- `tools/extract_templates.py` — labeling GUI (voice + zoom)
- `tools/assets.py` — asset inspector (`stats`, `browse`)
- `tools/videos.py` — BU alias resolver
- `main.py` — unified CLI entry point
- `architecture.md` — full architecture plan (keep in sync with this file)

## CLI Entry Point

Everything runs through `main.py`:

```bash
python main.py videos                        # list footage BU aliases
python main.py download <url>                # download YouTube footage
python main.py detect BU1 [--debug] ...      # run detection
python main.py extract BU1 [--frame N]       # labeling GUI
python main.py assets stats [type]           # coverage report
python main.py assets browse [type]          # thumbnail grid
```

Tab completion: `echo 'eval "$(register-python-argcomplete main.py)"' >> ~/.bashrc`

## Tech Stack

- Python, OpenCV (cv2), Pillow
- `argcomplete` — CLI tab completion
- `openai-whisper` + `sounddevice` — voice input in labeling tool
- YOLOv8 (Ultralytics) + PyTorch — for Phase 1+ if template matching insufficient
- SQLite or PostgreSQL — run/decision knowledge base (TBD, not started)

## Working Style Notes

- Don't build until the plan is agreed on. Design/propose first.
- Keep this file and `architecture.md` in sync as decisions evolve.
