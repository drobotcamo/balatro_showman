#!/usr/bin/env python3
"""
train_oc.py
===========
Outcome-conditioned training loop for the Balatro policy transformer.

Forks balatro-policy-transformer/train.py with three additions:

1. Outcome-stratified eval
   During each validation pass, the loop runs two extra sweeps:
     - desired_outcome overridden to 1.0 for ALL samples (win conditioning)
     - desired_outcome overridden to 0.0 for ALL samples (loss conditioning)
   The win-cond top-1 on winning-run steps should exceed loss-cond top-1
   once outcome conditioning kicks in — this is the primary signal that the
   conditioning is working.

2. Optional outcome loss weighting  (--win-weight N, default 1.0)
   Each step's CE loss is multiplied by win_weight if desired_outcome==1,
   else 1.0. Set --win-weight 5 to 10 to aggressively upweight the rare
   winning-run steps.

3. Finetuning from pretrained checkpoint  (--pretrained path/to/best.pt)
   Calls expand_pretrained_checkpoint() to add the outcome column and loads
   the result before training. All other weights are frozen-compatible with
   standard AdamW finetuning.

Usage
-----
    # Train from scratch on Gold Stake data
    python policy/train_oc.py \\
        --tensorized data/tensorized_oc \\
        --splits artifacts/splits_goldstake.json \\
        --out artifacts/checkpoints_oc \\
        --epochs 20 --win-weight 5

    # Finetune from Marco's pretrained checkpoint
    python policy/train_oc.py \\
        --tensorized data/tensorized_oc \\
        --splits artifacts/splits_goldstake.json \\
        --out artifacts/checkpoints_oc \\
        --pretrained vendor/balatro-policy-transformer/artifacts/checkpoints/best.pt \\
        --epochs 10 --lr 1e-4 --win-weight 5
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch import nn

# -- vendor path injection ---------------------------------------------------
_VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "balatro-policy-transformer"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from action_map import compute_action_map  # noqa: E402
from dataset import BalatroStepDataset, load_split  # noqa: E402
from model_oc import PolicyTransformerOC, load_model_config_oc, n_params, expand_pretrained_checkpoint  # noqa: E402

# Bring in the helpers that haven't changed.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import train as _upstream_train  # noqa: E402
_seed_everything = _upstream_train._seed_everything
_label_to_family = _upstream_train._label_to_family
_format_eta = _upstream_train._format_eta
iter_batches = _upstream_train.iter_batches
CHECKPOINT_SCHEMA_VERSION = _upstream_train.CHECKPOINT_SCHEMA_VERSION
# ---------------------------------------------------------------------------


def _build_dataset(tensorized: Path, splits_path: Path, name: str, device: torch.device) -> BalatroStepDataset:
    return BalatroStepDataset(
        tensorized_root=tensorized,
        split_videos=load_split(splits_path, name),
        include_unresolved=False,
        device=device,
    )


@torch.no_grad()
def _evaluate_oc(
    model: PolicyTransformerOC,
    dataset: BalatroStepDataset,
    batch_size: int,
    device: torch.device,
    index_to_family: list[str],
    *,
    label: str = "eval",
    outcome_override: float | None = None,
) -> dict:
    """Evaluate the model, optionally overriding desired_outcome for all samples.

    outcome_override=None  -> use the true desired_outcome from each sample
    outcome_override=1.0   -> force win conditioning for all samples
    outcome_override=0.0   -> force loss conditioning for all samples
    """
    model.eval()
    total_loss = 0.0
    total_steps = 0
    n_top1 = 0
    n_top3 = 0
    per_family_total: collections.Counter = collections.Counter()
    per_family_top1: collections.Counter = collections.Counter()

    n = len(dataset)
    for idx in iter_batches(n, batch_size, shuffle=False, device=device):
        batch = dataset.gather_batch(idx)
        if outcome_override is not None:
            batch = dict(batch)
            batch["desired_outcome"] = torch.full_like(
                batch["desired_outcome"].float(), outcome_override
            )
        target = batch["target_action_id"].long().view(-1)
        logits = model(batch)
        loss = nn.functional.cross_entropy(logits, target, reduction="sum")
        total_loss += float(loss.item())

        top3 = logits.topk(3, dim=-1).indices
        preds = top3[:, 0]
        n_top1 += int((preds == target).sum().item())
        n_top3 += int((top3 == target.unsqueeze(-1)).any(dim=-1).sum().item())
        total_steps += int(target.numel())

        tgt_np = target.detach().cpu().numpy()
        pred_np = preds.detach().cpu().numpy()
        for tgt, p in zip(tgt_np, pred_np):
            fam = index_to_family[int(tgt)]
            per_family_total[fam] += 1
            if int(p) == int(tgt):
                per_family_top1[fam] += 1

    return {
        "loss": total_loss / max(total_steps, 1),
        "top1": n_top1 / max(total_steps, 1),
        "top3": n_top3 / max(total_steps, 1),
        "n_steps": total_steps,
        "outcome_override": outcome_override,
        "per_family_top1": {
            fam: per_family_top1[fam] / per_family_total[fam]
            for fam in per_family_total
        },
        "per_family_total": dict(per_family_total),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tensorized", type=Path, default=Path("data/tensorized_oc"))
    ap.add_argument("--splits", type=Path, default=Path("artifacts/splits_goldstake.json"))
    ap.add_argument("--action-config", type=Path, default=_VENDOR / "data/action_space_config.json")
    ap.add_argument("--out", type=Path, default=Path("artifacts/checkpoints_oc"))
    ap.add_argument("--pretrained", type=Path, default=None,
                    help="Path to Marco's best.pt; expand and finetune from it.")
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch-size", type=int, default=256)
    ap.add_argument("--eval-batch-size", type=int, default=512)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--win-weight", type=float, default=1.0,
                    help="Loss multiplier for winning-run steps (default 1.0 = no weighting).")
    ap.add_argument("--limit-train", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--n-layers", type=int, default=4)
    ap.add_argument("--n-heads", type=int, default=4)
    ap.add_argument("--dim-feedforward", type=int, default=256)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--device", type=str, default="auto")
    ap.add_argument("--log-every", type=int, default=20)
    ap.add_argument("--amp", action="store_true")
    args = ap.parse_args()

    _seed_everything(args.seed)
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    use_amp = args.amp and device.type == "cuda"
    print(f"device: {device}  amp={use_amp}  win_weight={args.win_weight}")

    t_load = time.time()
    print("loading datasets...")
    train_ds = _build_dataset(args.tensorized, args.splits, "train", device)
    val_ds = _build_dataset(args.tensorized, args.splits, "val", device)
    test_ds = _build_dataset(args.tensorized, args.splits, "test", device)
    n_actions = train_ds.n_actions()
    print(
        f"  train={len(train_ds):>6d}  val={len(val_ds):>5d}  test={len(test_ds):>5d}  "
        f"N_ACTIONS={n_actions}  ({time.time()-t_load:.1f}s)"
    )

    if args.limit_train > 0 and args.limit_train < len(train_ds):
        train_ds._valid = train_ds._valid[: args.limit_train]
        print(f"  limiting train to first {args.limit_train} steps")

    print("building model...")
    cfg = load_model_config_oc(
        n_actions=n_actions,
        d_model=args.d_model,
        n_layers=args.n_layers,
        n_heads=args.n_heads,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
    )
    model = PolicyTransformerOC(cfg).to(device)

    if args.pretrained is not None:
        print(f"  expanding pretrained checkpoint: {args.pretrained}")
        expanded_state = expand_pretrained_checkpoint(args.pretrained)
        model.load_state_dict(expanded_state, strict=True)
        print("  pretrained weights loaded (outcome column initialized to zero)")
    else:
        print("  training from scratch")

    print(f"  params: {n_params(model):,}")

    action_map = compute_action_map(json.loads(args.action_config.read_text(encoding="utf-8")))
    index_to_family = [_label_to_family(label) for label in action_map["index_to_label"]]

    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scaler = torch.amp.GradScaler("cuda") if use_amp else None

    args.out.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    best_val = float("inf")
    best_path: Path | None = None

    n_train = len(train_ds)
    n_batches_train = (n_train + args.batch_size - 1) // args.batch_size
    train_gen = torch.Generator(device=device).manual_seed(args.seed)
    use_win_weight = args.win_weight != 1.0

    print()
    print(f"--- training {args.epochs} epochs ({n_batches_train} train batches/epoch) ---")
    overall_t0 = time.time()

    for epoch in range(1, args.epochs + 1):
        model.train()
        epoch_t0 = time.time()
        window_t0 = epoch_t0
        window_loss = window_steps = window_correct = 0.0
        running_loss = running_steps = running_correct = 0.0

        for it, idx in enumerate(
            iter_batches(n_train, args.batch_size, shuffle=True, generator=train_gen, device=device),
            1,
        ):
            batch = train_ds.gather_batch(idx)
            target = batch["target_action_id"].long().view(-1)

            optim.zero_grad(set_to_none=True)
            if use_amp:
                with torch.amp.autocast("cuda"):
                    logits = model(batch)
                    loss = _masked_ce(logits, target, batch, use_win_weight, args.win_weight)
                scaler.scale(loss).backward()
                scaler.unscale_(optim)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                scaler.step(optim)
                scaler.update()
            else:
                logits = model(batch)
                loss = _masked_ce(logits, target, batch, use_win_weight, args.win_weight)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optim.step()

            with torch.no_grad():
                correct = int((logits.argmax(-1) == target).sum().item())
            n = int(target.numel())
            lv = float(loss.item())
            window_loss += lv * n; window_steps += n; window_correct += correct
            running_loss += lv * n; running_steps += n; running_correct += correct

            if args.log_every and it % args.log_every == 0:
                now = time.time()
                w_sps = window_steps / max(now - window_t0, 1e-6)
                avg_loss = running_loss / max(running_steps, 1)
                avg_top1 = running_correct / max(running_steps, 1)
                w_loss = window_loss / max(window_steps, 1)
                w_top1 = window_correct / max(window_steps, 1)
                cum_sps = running_steps / max(now - epoch_t0, 1e-6)
                rem = (n_batches_train - it) + n_batches_train * (args.epochs - epoch)
                eta = rem * args.batch_size / max(cum_sps, 1e-6)
                print(
                    f"  e{epoch}/{args.epochs} it {it:4d}/{n_batches_train}  "
                    f"loss(win/run)={w_loss:.4f}/{avg_loss:.4f}  "
                    f"top1(win/run)={w_top1:.4f}/{avg_top1:.4f}  "
                    f"sps={w_sps:7.0f}  ETA={_format_eta(eta)}"
                )
                window_t0 = now
                window_loss = window_steps = window_correct = 0.0

        train_loss = running_loss / max(running_steps, 1)
        train_top1 = running_correct / max(running_steps, 1)
        epoch_secs = time.time() - epoch_t0
        print(
            f"epoch {epoch}/{args.epochs} TRAIN  "
            f"loss={train_loss:.4f}  top1={train_top1:.4f}  ({epoch_secs:.1f}s)"
        )

        # Standard val pass (true desired_outcome).
        val_true = _evaluate_oc(model, val_ds, args.eval_batch_size, device,
                                index_to_family, label=f"val(e{epoch})")
        # Outcome-conditioned sweeps.
        val_win = _evaluate_oc(model, val_ds, args.eval_batch_size, device,
                               index_to_family, outcome_override=1.0)
        val_loss_cond = _evaluate_oc(model, val_ds, args.eval_batch_size, device,
                                     index_to_family, outcome_override=0.0)

        print(
            f"epoch {epoch}/{args.epochs} VAL(true)    "
            f"loss={val_true['loss']:.4f}  top1={val_true['top1']:.4f}  top3={val_true['top3']:.4f}"
        )
        print(
            f"epoch {epoch}/{args.epochs} VAL(win=1)   "
            f"loss={val_win['loss']:.4f}  top1={val_win['top1']:.4f}"
        )
        print(
            f"epoch {epoch}/{args.epochs} VAL(win=0)   "
            f"loss={val_loss_cond['loss']:.4f}  top1={val_loss_cond['top1']:.4f}"
        )
        delta = val_win["top1"] - val_loss_cond["top1"]
        print(f"  conditioning delta (win1 - win0 top1): {delta:+.4f}")

        history.append({
            "epoch": epoch,
            "train_loss": train_loss, "train_top1": train_top1,
            "val_loss": val_true["loss"], "val_top1": val_true["top1"], "val_top3": val_true["top3"],
            "val_win_cond_top1": val_win["top1"],
            "val_loss_cond_top1": val_loss_cond["top1"],
            "conditioning_delta": delta,
            "epoch_seconds": epoch_secs,
        })

        if val_true["loss"] < best_val:
            best_val = val_true["loss"]
            best_path = args.out / "best.pt"
            torch.save({
                "schema_version": CHECKPOINT_SCHEMA_VERSION,
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optim.state_dict(),
                "val_loss": val_true["loss"],
                "val_top1": val_true["top1"],
                "val_win_cond_top1": val_win["top1"],
                "outcome_conditioned": True,
                "model_config": cfg.__dict__,
                "n_actions": n_actions,
            }, best_path)
            print(f"  -> saved {best_path}")

    elapsed_total = time.time() - overall_t0
    print(f"\ntraining complete in {_format_eta(elapsed_total)}")

    if best_path is not None:
        ckpt = torch.load(best_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        print(f"loaded best checkpoint from epoch {ckpt['epoch']}")

    test_true = _evaluate_oc(model, test_ds, args.eval_batch_size, device,
                             index_to_family, label="test")
    test_win = _evaluate_oc(model, test_ds, args.eval_batch_size, device,
                            index_to_family, outcome_override=1.0)
    test_loss_cond = _evaluate_oc(model, test_ds, args.eval_batch_size, device,
                                  index_to_family, outcome_override=0.0)
    print(
        f"TEST(true)   loss={test_true['loss']:.4f}  "
        f"top1={test_true['top1']:.4f}  top3={test_true['top3']:.4f}"
    )
    print(f"TEST(win=1)  top1={test_win['top1']:.4f}")
    print(f"TEST(win=0)  top1={test_loss_cond['top1']:.4f}")
    print(f"conditioning delta: {test_win['top1'] - test_loss_cond['top1']:+.4f}")

    report = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "n_params": n_params(model),
        "n_actions": n_actions,
        "outcome_conditioned": True,
        "device": str(device),
        "elapsed_seconds": elapsed_total,
        "history": history,
        "test_metrics": test_true,
        "test_win_cond_top1": test_win["top1"],
        "test_loss_cond_top1": test_loss_cond["top1"],
        "best_checkpoint": best_path.as_posix() if best_path else None,
    }
    (args.out / "training_report_oc.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nwrote {args.out / 'training_report_oc.json'}")


def _masked_ce(
    logits: torch.Tensor,
    target: torch.Tensor,
    batch: dict[str, torch.Tensor],
    use_win_weight: bool,
    win_weight: float,
) -> torch.Tensor:
    if not use_win_weight:
        return nn.functional.cross_entropy(logits, target)
    per_step = nn.functional.cross_entropy(logits, target, reduction="none")
    outcome = batch["desired_outcome"].float().view(-1)
    weights = torch.where(outcome > 0.5,
                          torch.full_like(per_step, win_weight),
                          torch.ones_like(per_step))
    return (per_step * weights).mean()


if __name__ == "__main__":
    main()
