#!/usr/bin/env python3
"""
model_oc.py
===========
Outcome-conditioned fork of balatro-policy-transformer/model.py.

The only change: ``desired_outcome`` (a float32 scalar per step) is appended
to the numeric inputs of ``GlobalEncoder``. All other architecture, weights,
and hyperparameters are identical to the upstream model.

At training time, desired_outcome == run_outcome (0.0 loss, 1.0 win).
At inference time, always pass 1.0 to condition on winning behavior.

Finetuning from Marco's pretrained checkpoint
---------------------------------------------
The sole incompatibility with the pretrained weights is ``GlobalEncoder.proj``:
the first Linear grows from (n_cat + n_num) to (n_cat + n_num + 1) input units.
Everything else loads cleanly.

To finetune:

    ckpt = torch.load("path/to/marco/best.pt", map_location="cpu")
    cfg = load_model_config_oc(n_actions=ckpt["n_actions"])
    model = PolicyTransformerOC(cfg)

    state = ckpt["model_state_dict"]
    # Expand proj weight by one zero column for the new outcome input.
    old_w = state["global_encoder.proj.0.weight"]  # (d_model, n_cat+n_num)
    new_col = torch.zeros(old_w.shape[0], 1)
    state["global_encoder.proj.0.weight"] = torch.cat([old_w, new_col], dim=1)
    model.load_state_dict(state, strict=True)

The appended zero column means the outcome input starts with zero gradient
signal and the model smoothly learns to use it during finetuning.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import torch
from torch import nn

# -- vendor path injection ---------------------------------------------------
_VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "balatro-policy-transformer"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

import model as _upstream  # noqa: E402

# Re-export everything unchanged so downstream code can import from here.
ModelConfig = _upstream.ModelConfig
load_model_config = _upstream.load_model_config
CardLikeTokenEncoder = _upstream.CardLikeTokenEncoder
n_params = _upstream.n_params
_embed = _upstream._embed
# ---------------------------------------------------------------------------


def load_model_config_oc(
    n_actions: int,
    vocab_path: Path = _VENDOR / "artifacts/vocab.json",
    feature_config_path: Path = _VENDOR / "artifacts/feature_config.json",
    **overrides: Any,
) -> ModelConfig:
    """Load ModelConfig with vendor artifact paths as defaults."""
    return _upstream.load_model_config(
        n_actions=n_actions,
        vocab_path=vocab_path,
        feature_config_path=feature_config_path,
        **overrides,
    )


class GlobalEncoderOC(nn.Module):
    """GlobalEncoder + desired_outcome scalar.

    Identical to upstream GlobalEncoder except n_num is incremented by 1
    and desired_outcome is concatenated last in the numeric block.
    """

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        s = cfg.vocab_sizes

        self.emb_page = _embed(s["page"], cfg.cat_embed_dim)
        self.emb_deck_class = _embed(s["deck_class_id"], cfg.cat_embed_dim)
        self.emb_stake_class = _embed(s["stake_class_id"], cfg.cat_embed_dim)
        self.emb_last_tarot_planet = _embed(s["last_tarot_planet_class_id"], cfg.cat_embed_dim)
        self.emb_ante_boss_blind = _embed(s["ante_boss_blind_class_id"], cfg.cat_embed_dim)
        self.emb_small_status = _embed(s["small_status"], cfg.cat_embed_dim)
        self.emb_big_status = _embed(s["big_status"], cfg.cat_embed_dim)

        n_cat = 7 * cfg.cat_embed_dim
        n_num = (
            cfg.n_ocr
            + cfg.n_state_num
            + cfg.n_ocr   # ocr_valid
            + cfg.n_flags
            + 3 * cfg.n_hands
            + cfg.n_vouchers
            + cfg.n_bosses
            + 1            # desired_outcome scalar
        )
        self.proj = nn.Sequential(
            nn.Linear(n_cat + n_num, cfg.d_model),
            nn.GELU(),
            nn.Linear(cfg.d_model, cfg.d_model),
        )

    def forward(self, x: dict[str, torch.Tensor]) -> torch.Tensor:
        cat = torch.cat(
            [
                self.emb_page(x["page_id"]),
                self.emb_deck_class(x["deck_class_id"]),
                self.emb_stake_class(x["stake_class_id"]),
                self.emb_last_tarot_planet(x["last_tarot_planet_class_id"]),
                self.emb_ante_boss_blind(x["ante_boss_blind_class_id"]),
                self.emb_small_status(x["small_status_id"]),
                self.emb_big_status(x["big_status_id"]),
            ],
            dim=-1,
        )
        num = torch.cat(
            [
                x["ocr_numeric"],
                x["state_numeric"],
                x["ocr_valid"].float(),
                x["flags"].float(),
                x["hand_levels"],
                x["hand_played"],
                x["hand_played_this_round"],
                x["vouchers_redeemed"].float(),
                x["bosses_used"].float(),
                x["desired_outcome"].float().unsqueeze(-1),
            ],
            dim=-1,
        )
        return self.proj(torch.cat([cat, num], dim=-1))


class PolicyTransformerOC(nn.Module):
    """PolicyTransformer with outcome conditioning via GlobalEncoderOC."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg

        self.class_id_embedding = _embed(cfg.vocab_sizes["class_id"], cfg.cat_embed_dim)

        self.global_encoder = GlobalEncoderOC(cfg)  # only difference from upstream
        self.object_encoder = CardLikeTokenEncoder(
            cfg, self.class_id_embedding,
            with_zone=True, with_position=True, with_debuff=True,
            with_stickers=True, with_object_type=True,
        )
        self.deck_encoder = CardLikeTokenEncoder(
            cfg, self.class_id_embedding,
            with_zone=False, with_position=False, with_debuff=False,
            with_stickers=False, with_object_type=False,
        )

        self.cls_token = nn.Parameter(torch.zeros(1, 1, cfg.d_model))
        self.global_type = nn.Parameter(torch.zeros(1, 1, cfg.d_model))
        self.object_type = nn.Parameter(torch.zeros(1, 1, cfg.d_model))
        self.deck_type = nn.Parameter(torch.zeros(1, 1, cfg.d_model))
        nn.init.normal_(self.cls_token, std=0.02)
        nn.init.normal_(self.global_type, std=0.02)
        nn.init.normal_(self.object_type, std=0.02)
        nn.init.normal_(self.deck_type, std=0.02)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.n_heads,
            dim_feedforward=cfg.dim_feedforward,
            dropout=cfg.dropout,
            batch_first=True,
            norm_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=cfg.n_layers)
        self.norm = nn.LayerNorm(cfg.d_model)
        self.head = nn.Linear(cfg.d_model, cfg.n_actions)

    def forward(self, x: dict[str, torch.Tensor]) -> torch.Tensor:
        b = x["page_id"].shape[0]

        global_token = self.global_encoder(x).unsqueeze(1) + self.global_type
        object_tokens = self.object_encoder(x, "object_") + self.object_type
        deck_tokens = self.deck_encoder(x, "deck_card_") + self.deck_type

        cls = self.cls_token.expand(b, -1, -1)
        tokens = torch.cat([cls, global_token, object_tokens, deck_tokens], dim=1)

        n_obj = object_tokens.shape[1]
        n_deck = deck_tokens.shape[1]
        device = tokens.device
        pad = torch.zeros(b, 2 + n_obj + n_deck, dtype=torch.bool, device=device)
        pad[:, 2 : 2 + n_obj] = ~x["object_mask"]
        pad[:, 2 + n_obj :] = ~x["deck_card_mask"]

        out = self.encoder(tokens, src_key_padding_mask=pad)
        cls_out = self.norm(out[:, 0])
        logits = self.head(cls_out)

        action_mask = x["action_mask"].bool()
        logits = logits.masked_fill(~action_mask, float("-inf"))
        return logits


def expand_pretrained_checkpoint(ckpt_path: Path, out_path: Path | None = None) -> dict:
    """Load a Marco pretrained checkpoint and expand GlobalEncoder.proj for outcome conditioning.

    The new desired_outcome input column in proj.0.weight is initialized to
    zeros so finetuning starts from the pretrained behavior with no outcome
    signal and gradually learns to use it.

    Args:
        ckpt_path: Path to Marco's best.pt checkpoint.
        out_path: If provided, save the expanded checkpoint there.

    Returns:
        The expanded state dict (ready for model.load_state_dict).
    """
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    state = {k: v.clone() for k, v in ckpt["model_state_dict"].items()}

    proj_key = "global_encoder.proj.0.weight"
    if proj_key not in state:
        raise KeyError(f"{proj_key} not found in checkpoint — wrong model?")

    old_w = state[proj_key]  # (d_model, n_cat + n_num_old)
    new_col = torch.zeros(old_w.shape[0], 1, dtype=old_w.dtype)
    state[proj_key] = torch.cat([old_w, new_col], dim=1)

    if out_path is not None:
        expanded = dict(ckpt)
        expanded["model_state_dict"] = state
        expanded["outcome_conditioned"] = True
        torch.save(expanded, out_path)
        print(f"saved expanded checkpoint -> {out_path}")

    return state
