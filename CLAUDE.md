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
- Balatro uses fixed pixel-art sprites. Try OpenCV `cv2.matchTemplate` against known assets before any ML.
- If multi-scale issues arise: try multi-scale matching. If compression artifacts from footage: try grayscale + normalized cross-correlation.
- Only escalate to YOLOv8 fine-tuning if template matching demonstrably fails.

### Detection Order
Start with **Skip Tags** for the first PoC because they are common, unobscured, consistent location, and limited in number (~30). Once this works, the detector + test harness pattern becomes the template for all other element types.

### Decision Detection (deferred)
How to identify *when* a decision was made: compare consecutive frames for inventory delta (item appears/disappears from shop). This comes after element detection is proven.

## Current Phase

**Phase 0 — Skip Tag Template Matching PoC** (not yet started)

- `detectors/skip_tags.py`: detect skip tags in a screenshot via template matching
- `test_harness.py`: visual output tool — load test screenshots, draw bounding boxes, save results for manual review
- Success = 90%+ accuracy, no false positives

## Repo Contents (what already exists)

- `game_asset_images/` — PNG sprites for all game element types (blinds, boosters, jokers, tags, etc.), already downloaded
- `game_asset_urls/` — scraped Balatro wiki HTMLs and JSON files of image URLs per category; `web_scraper.py`
- `gameplay_sources/gameplay_footage/` — Gold Stake mp4 files
- `architecture.md` — full architecture plan (keep in sync with this file)

## Tech Stack

- Python, OpenCV (cv2), Pillow
- YOLOv8 (Ultralytics) + PyTorch — for Phase 1+ if template matching insufficient
- SQLite or PostgreSQL — run/decision knowledge base (TBD, not started)
- Labeling suite TBD (possibly Label Studio or custom with voice input)

## Working Style Notes

- Don't build until the plan is agreed on. Design/propose first.
- Keep this file and `architecture.md` in sync as decisions evolve.
