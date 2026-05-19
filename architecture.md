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

Accuracy of the tool requires near-100% recognition of gameplay elements. For this reason, there is a separate detection layer per element category rather than one general-purpose model.

Gameplay element categories (sorted by importance):

0. Jokers
1. Stickers
2. Balance $
3. Skip Tags
4. Booster Packs
5. Tarot Cards
6. Planet Cards
7. Vouchers (easiest)
8. Spectral Cards

Elements often appear at different locations, angles, or partially obscured. Detection must handle this.

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

## CV Approach (Phased)

**Phase 0 — Template Matching (try first):** Balatro uses fixed pixel-art sprites at consistent sizes. OpenCV template matching against known asset images (`game_asset_images/`) may achieve near-100% accuracy with no training required. Start here because it's the simplest possible approach.

- If resolution/scale mismatch is an issue: try multi-scale matching.
- If compression artifacts (from footage frames) are an issue: try grayscale matching with normalized cross-correlation.

**Phase 1 — Object Detection (if template matching fails):** Fine-tune a YOLOv8 model on labeled screenshots. This handles occlusion and variable rendering better at the cost of requiring labeled training data.

Decision detection (identifying *when* a decision was made by comparing consecutive frames for state delta) comes **after** element detection is proven. Approach: compare consecutive frames, detect inventory delta (item appears/disappears from shop).

## Data Storage

A database with related objects to represent everything in a run. Architecture TBD — needs refinement once CV layer is proven.

## Score Generation (MVP)

Focus on purchase decisions in a shop. "Not buying" is also a decision and carries weight. Given a detected game state, compare against the knowledge base to recommend an action.

# Implementation Plan

## Phase 0: Skip Tag Template Matching PoC

Skip Tags are the first target because they are:

- Common in every run
- Usually unobstructed
- In a consistent screen location
- Limited in number (~30 tags total)

**Deliverables:**

1. `detectors/skip_tags.py` — takes a screenshot, runs `cv2.matchTemplate` against each asset in `game_asset_images/`, returns bounding boxes + tag names above confidence threshold
2. `test_harness.py` — takes a folder of test screenshots, runs detector on each, saves visual output (screenshot with colored bounding boxes and labels drawn on) for manual evaluation

**Success criteria:** Correctly identifies tags in 90%+ of test screenshots with no false positives on non-tag UI elements.

Once skip tags work, this same pattern (detector + test harness) becomes the reusable template for all other element types.

## Repo Structure

```text
./gameplay_sources
  /gameplay_footage        # mp4 files (YouTube footage, Gold Stake runs)
./game_asset_images        # PNGs of each game asset, organized by type
  /blind_images
  /booster_images
  /joker_images
  /tag_images
  ... (etc.)
./game_asset_urls          # scraped asset URLs and HTML from Balatro wiki
  /htmls
  *.json                   # image URL lists per asset category
  web_scraper.py
./detectors                # one detector module per element category (to be built)
./training_data            # labeled images for ML phases (future)
./runs_db                  # run and decision storage (future)
```

# Tech Stack

- **Python** — primary language
- **OpenCV (cv2)** — template matching, image preprocessing, bounding box rendering
- **Pillow** — image handling
- **YOLOv8 (Ultralytics)** — object detection if template matching insufficient (Phase 1+)
- **PyTorch** — model training backbone
- **SQLite or PostgreSQL** — run/decision knowledge base storage (TBD)
- Labeling suite TBD — possibly Label Studio or custom with voice input for speed
