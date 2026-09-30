# Next Steps — Outcome-Conditioned Balatro Agent

## What Was Built This Session

The outcome-conditioning layer is complete. Four files in `policy/`:

| File | What it does |
|------|-------------|
| `label_outcomes.py` | Scans `data/granularized/` → `policy/data/outcomes.json` (win/loss per run) |
| `tensorize_oc.py` | Fork of `vendor/balatro-policy-transformer/tensorize.py`; adds `desired_outcome` float32 to every step's `.npz` |
| `model_oc.py` | Fork of `model.py`; `GlobalEncoderOC` takes one extra scalar — proj input grows 368→369 |
| `train_oc.py` | Fork of `train.py`; outcome-stratified eval (win=1 vs win=0 sweeps), optional `--win-weight`, `--pretrained` finetuning |

All policy code imports from `vendor/balatro-policy-transformer` via sys.path; only the three touched modules are forked. Smoke-tested: imports clean, model forward pass verified, proj dim delta confirmed at +1.

---

## Assets In Place

- **YOLO model** (`marco-costa-ml/balatro-yolo`, YOLOv8m, 400 classes): copied to `vendor/balatro-cv-pipeline/external/runs/detect/train/weights/best.pt`. Ready to run.
- **OCR boxes**: `vendor/balatro-cv-pipeline/assets/text_boxes.json` defines fixed pixel regions for 14 OCR fields. **Designed for ~640x360 resolution.** BU videos are 1920x1080 — scale all bbox coords by 3× before use, or resize frames to 640x360 before OCR.
- **cv-pipeline scripts**: `detect_single.py` and `ocr_single.py` both hardcode `cuda:1` — change to `device='cpu'` or `'directml'` (AMD RX 6800S, no CUDA).

---

## Critical Gap: The Event Extraction Tool is Missing

Marco's pipeline from VIDEO → training data requires a step he has not published:

```
BU*.mp4
  → cv-pipeline (YOLO detection CSV + OCR CSV)        ← vendor/balatro-cv-pipeline
  → [MISSING] event extraction tool                    ← NOT PUBLISHED
  → data/extracted/video_id=*/events.json
  → parse_events.py → data/parsed/
  → granularize.py  → data/granularized/              ← outcome code plugs in here
  → ...
```

The `events.json` format needs per-frame: page_name, ocr state dict, zones dict (objects grouped by zone), and action labels (what the player did). The action labels in particular require temporal reasoning — Marco built but did not release the tool that infers actions from frame-to-frame changes.

**The BU1-BU26 videos cannot be processed into training data with published tools.**

---

## Path B Implementation — DONE

`policy/record_server.py` and `policy/granularize_live.py` are now written and smoke-tested.

**record_server.py** — two modes:
- `--mode assist`: loads a checkpoint, AI plays, every (snapshot, model_action) is saved. No Lua changes needed.
- `--mode observe`: expects Lua to set `snapshot.action_taken = "<label>"` before writing snapshot.json; echoes it back so Lua advances.

Sessions saved to `data/live_sessions/<run_id>/steps.ndjson` + `session.json`.

Run-end signals: write `<io_dir>/run_end.json: {"run_id": <id>, "outcome": "win"|"loss"}` to finalize a session with its outcome.

**granularize_live.py** — converts sessions to granularized format:
- Parses action labels to zone+position
- Synthesizes SWAP steps between events when CurrentJokers reorder
- Runs `state_reducer` to produce `data/persistent_state/`
- Output goes straight into the `tensorize_oc.py` pipeline

**Lua bridge change required (observe mode only)**:
```lua
-- In agent_bridge.lua, before writing snapshot.json:
snapshot.action_taken = action_label  -- e.g. "BuyShopItem_TopShelfShopOfferings_0"
-- After run ends:
-- Write <io_dir>/run_end.json: {"run_id": <id>, "outcome": "win"}
```

**Full recording pipeline**:
```bash
# 1. Record (human plays with modified Lua bridge):
python policy/record_server.py --mode observe

# 2. Convert to granularized format:
python policy/granularize_live.py

# 3. Label outcomes (or they come from run_end.json signals):
python policy/label_outcomes.py

# 4. Tensorize:
python policy/tensorize_oc.py --outcomes policy/data/outcomes.json \
    --src data/granularized --persistent data/persistent_state \
    --out data/tensorized_oc

# 5. Train:
python policy/train_oc.py --tensorized data/tensorized_oc \
    --splits artifacts/splits_goldstake.json --epochs 20 --win-weight 5
```

---

## Two Paths Forward

### Path A — Reproduce the Event Extractor (medium effort)

Write `policy/extract_events.py` that takes cv-pipeline CSVs and produces `events.json`.

What you need to understand to implement this:
1. **Page detection**: which UI screen is visible? Detectable from class IDs (e.g. shop objects only appear on shop page). Read `vendor/balatro-policy-transformer/data/class_map.csv` for class_id → name mapping.
2. **Zone reconstruction**: group detected objects into zones (CurrentHand, CurrentJokersAll, ShopOfferings, etc.) using bounding box positions relative to frame resolution.
3. **Action detection**: the hard part. Infer actions from temporal deltas: card appears in hand → PlayHand; item disappears from shop + money decreases → BuyShopItem. Some actions (SelectCard micro-steps) may be derivable from which objects appear/disappear between frames.

Reference: `vendor/balatro-policy-transformer/parse_events.py` shows exactly what fields events.json needs (lines 405-435 define `parse_event()` input format). The OCR fields map directly to cv-pipeline OCR labels in `vendor/balatro-cv-pipeline/assets/` (there should be a `text_boxes.json` defining OCR regions).

**Start here:** `vendor/balatro-cv-pipeline/assets/text_boxes.json` for OCR label names, `vendor/balatro-policy-transformer/data/class_map.csv` for detection class semantics.

### Path B — Lua Live Data Collection (lower effort, better data quality)

Install Balatro + Steamodded mod loader. Use the Lua scripts in `vendor/balatro-policy-transformer/live/` to extract game state directly while playing.

The live agent already exists. The recording side needs a small modification: instead of just inferring actions at inference time, write a recording mode that saves each (state, action_taken) pair.

**Outcome labeling is trivial with Lua** — the game tells you directly when you win or lose. No inference needed.

**This is the recommended path** for generating Gold Stake-specific outcome-conditioned data because:
- Clean, unambiguous action labels
- Perfect win/loss labels
- No CV pipeline to debug
- Each session directly adds labeled Gold Stake data

---

## Checking for Marco's Pretrained Checkpoint

Before starting Path A or B, check if Marco published model weights:

```bash
# Check HuggingFace
python -c "
from huggingface_hub import hf_hub_download
try:
    path = hf_hub_download('marco-costa-ml/balatro-policy-transformer', 'best.pt')
    print('found:', path)
except Exception as e:
    print('not found:', e)
"
```

If weights exist, finetuning (`policy/train_oc.py --pretrained <path>`) is far better than training from scratch on 26 videos. The `expand_pretrained_checkpoint()` function in `policy/model_oc.py` handles adding the outcome column with zero-init.

Note: Marco's n_actions=134 (from his training_report.json). Our code derives n_actions from the dataset automatically, so there's no hardcoded mismatch.

---

## If You Have Granularized Data to Test With

If you manage to produce `data/granularized/` by either path, the rest of the pipeline is ready to run:

```bash
# Step 1: label outcomes
python policy/label_outcomes.py --summary   # spot-check first
python policy/label_outcomes.py             # write policy/data/outcomes.json

# Step 2: tensorize with outcome conditioning
python policy/tensorize_oc.py \
    --outcomes policy/data/outcomes.json \
    --src data/granularized \
    --persistent data/persistent_state \
    --out data/tensorized_oc

# Step 3: build Gold Stake splits
# Copy vendor/balatro-policy-transformer/compute_splits.py and filter to BU video IDs only
# Output: artifacts/splits_goldstake.json

# Step 4: train
python policy/train_oc.py \
    --tensorized data/tensorized_oc \
    --splits artifacts/splits_goldstake.json \
    --epochs 20 \
    --win-weight 5
```

---

## Verification Checklist

Once you have training data and a trained model, verify outcome conditioning is working:

1. `policy/data/outcomes.json` exists with ~10-20% wins across BU runs
2. `data/tensorized_oc/` shards have `desired_outcome` key with values in {0.0, 1.0}
3. Training log shows `conditioning_delta` growing over epochs (win=1 top-1 > win=0 top-1)
4. At inference: `desired_outcome=1.0` produces different top action distributions than `desired_outcome=0.0` for shop decision steps

---

## Key Files Quick Reference

```
policy/
├── label_outcomes.py      # win/loss labeling
├── tensorize_oc.py        # adds desired_outcome to .npz shards
├── model_oc.py            # GlobalEncoderOC, expand_pretrained_checkpoint()
├── train_oc.py            # outcome-conditioned training
└── NEXTUP.md              # this file

vendor/
├── balatro-policy-transformer/   # Marco's model + pipeline (read-only)
│   ├── parse_events.py           # events.json → data/parsed/
│   ├── granularize.py            # data/parsed/ → data/granularized/
│   ├── compute_persistent_state.py
│   ├── tensorize.py              # (upstream, don't edit)
│   ├── model.py                  # (upstream, don't edit)
│   ├── train.py                  # (upstream, don't edit)
│   ├── live/                     # live Lua agent
│   ├── artifacts/                # vocab.json, normalization.json, feature_config.json
│   └── data/action_space_config.json
└── balatro-cv-pipeline/          # YOLO+OCR on video (Path A only)
    ├── scripts/detect/detect_single.py
    └── scripts/ocr/ocr_single.py
```
