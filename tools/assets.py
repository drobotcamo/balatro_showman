"""
Asset collection inspector.

Usage:
    python tools/assets.py stats               # counts for all types
    python tools/assets.py stats tags          # counts for one type
    python tools/assets.py browse             # thumbnail grid for all types
    python tools/assets.py browse tags        # thumbnail grid for one type
"""

import argparse
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageTk

RECORDED = Path("recorded_gameplay_asset_images")
REFERENCE = Path("game_asset_images")

ASSET_TYPE_TO_DIR = {
    "tags":      "tag_images",
    "jokers":    "joker_images",
    "boosters":  "booster_images",
    "blinds":    "blind_images",
    "vouchers":  "voucher_images",
    "tarots":    "tarot_images",
    "planets":   "planet_images",
    "spectrals": "spectral_images",
    "modifiers": "modifier_images",
    "stakes":    "stake_images",
    "stickers":  "sticker_images",
    "ui":        None,
}

THUMB_SIZE = 80
GRID_COLS = 8


# ── Data helpers ──────────────────────────────────────────────────────────────

def _reference_names(asset_type):
    dir_name = ASSET_TYPE_TO_DIR.get(asset_type)
    if not dir_name:
        return set()
    ref_dir = REFERENCE / dir_name
    if not ref_dir.exists():
        return set()
    return {p.stem.replace("_", " ") for p in ref_dir.glob("*.png")}


def _recorded_files(asset_type):
    d = RECORDED / asset_type
    if not d.exists():
        return []
    return sorted(d.glob("*.png"))


def _stem_to_name(stem):
    """'Small_Blind_1' → 'Small Blind'  (strip trailing _N)"""
    import re
    return re.sub(r"_\d+$", "", stem).replace("_", " ")


def _collect_stats(types):
    rows = []
    for t in types:
        files = _recorded_files(t)
        ref = _reference_names(t)
        covered = {_stem_to_name(f.stem) for f in files}
        rows.append({
            "type": t,
            "instances": len(files),
            "unique": len(covered),
            "reference": len(ref),
            "missing": sorted(ref - covered) if ref else [],
        })
    return rows


# ── CLI stats ─────────────────────────────────────────────────────────────────

def cmd_stats(types):
    rows = _collect_stats(types)
    col_w = max(len(t) for t in types) + 2

    header = f"{'TYPE':<{col_w}} {'INSTANCES':>10}  {'UNIQUE':>7}  {'REFERENCE':>10}  {'COVERAGE':>9}"
    print(header)
    print("-" * len(header))

    for r in rows:
        if r["reference"]:
            pct = f"{r['unique'] / r['reference'] * 100:.0f}%"
        else:
            pct = "n/a"
        print(f"{r['type']:<{col_w}} {r['instances']:>10}  {r['unique']:>7}  {r['reference']:>10}  {pct:>9}")
        if r["missing"]:
            preview = ", ".join(r["missing"][:6])
            tail = f"  +{len(r['missing']) - 6} more" if len(r["missing"]) > 6 else ""
            print(f"  {'missing:':>{col_w - 2}} {preview}{tail}")

    total_inst = sum(r["instances"] for r in rows)
    total_uniq = sum(r["unique"] for r in rows)
    print("-" * len(header))
    print(f"{'TOTAL':<{col_w}} {total_inst:>10}  {total_uniq:>7}")


# ── Browse UI ─────────────────────────────────────────────────────────────────

class AssetBrowser:
    def __init__(self, types):
        self.types = types
        self.deleted = []

        self.root = tk.Tk()
        self.root.title("Asset Browser")
        self.root.bind("<Control-z>", lambda e: self._undo())

        self._build_ui()
        self._load_type(self.types[0])
        self.root.mainloop()

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(top, text="Asset type:").pack(side=tk.LEFT)
        self.type_var = tk.StringVar(value=self.types[0])
        cb = ttk.Combobox(top, textvariable=self.type_var, values=self.types,
                          width=14, state="readonly")
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._load_type(self.type_var.get()))

        self.status_var = tk.StringVar()
        tk.Label(top, textvariable=self.status_var, anchor="w").pack(side=tk.LEFT, padx=12)
        tk.Label(top, text="click thumbnail to delete  |  Ctrl+Z to undo",
                 fg="gray").pack(side=tk.RIGHT)

        # Scrollable canvas
        container = tk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(container, bg="#1e1e1e")
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        self.grid_frame = tk.Frame(self.canvas, bg="#1e1e1e")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_frame_configure(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self.canvas_window, width=e.width)

    def _load_type(self, asset_type):
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self._photos = []

        files = _recorded_files(asset_type)
        ref_names = _reference_names(asset_type)

        # Group files by asset name
        groups = {}
        for f in files:
            name = _stem_to_name(f.stem)
            groups.setdefault(name, []).append(f)

        # Also show missing reference names with placeholder
        all_names = sorted(groups.keys() | (ref_names - set(groups.keys())))

        col = 0
        for name in all_names:
            group_files = groups.get(name, [])
            in_ref = name in ref_names

            # Group label
            label_text = name + ("" if in_ref else " *")
            label_color = "white" if group_files else "#888"
            tk.Label(self.grid_frame, text=label_text, fg=label_color, bg="#1e1e1e",
                     font=("TkDefaultFont", 8)).grid(
                row=col * 3, column=0, columnspan=GRID_COLS, sticky="w", padx=4, pady=(8, 0))

            if group_files:
                for i, fpath in enumerate(group_files):
                    thumb = self._make_thumb(fpath)
                    if thumb is None:
                        continue
                    self._photos.append(thumb)
                    btn = tk.Label(self.grid_frame, image=thumb, bg="#1e1e1e",
                                   relief="flat", cursor="hand2", bd=1)
                    btn.grid(row=col * 3 + 1, column=i % GRID_COLS,
                             padx=3, pady=2, sticky="nw")
                    btn.bind("<Button-1>", lambda e, p=fpath, b=btn: self._delete(p, b))
                    if i % GRID_COLS == GRID_COLS - 1:
                        col += 1
            else:
                tk.Label(self.grid_frame, text="— no instances recorded —",
                         fg="#555", bg="#1e1e1e", font=("TkDefaultFont", 8)).grid(
                    row=col * 3 + 1, column=0, columnspan=GRID_COLS, sticky="w", padx=8)

            col += 1

        covered = len([n for n in all_names if n in groups])
        total_inst = sum(len(v) for v in groups.values())
        self.status_var.set(
            f"{asset_type}:  {total_inst} instances  |  {covered}/{len(all_names)} names covered"
        )

    def _make_thumb(self, path):
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            return None
        if img.shape[2] == 4:
            alpha = img[:, :, 3:] / 255.0
            bgr = img[:, :, :3].astype(np.float32)
            bg = np.full_like(bgr, 40.0)
            img = (bgr * alpha + bg * (1 - alpha)).astype(np.uint8)
        else:
            img = img[:, :, :3]
        h, w = img.shape[:2]
        scale = THUMB_SIZE / max(h, w)
        tw, th = max(1, int(w * scale)), max(1, int(h * scale))
        resized = cv2.resize(img, (tw, th), interpolation=cv2.INTER_AREA)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        return ImageTk.PhotoImage(Image.fromarray(rgb))

    def _delete(self, path, btn):
        try:
            path.unlink()
            self.deleted.append(path)
            btn.configure(bg="red")
            self.root.after(300, btn.destroy)
            self.status_var.set(f"Deleted {path.name}  |  Ctrl+Z to undo")
        except FileNotFoundError:
            btn.destroy()

    def _undo(self):
        if not self.deleted:
            self.status_var.set("Nothing to undo.")
            return
        # Can't restore the image data — just report
        last = self.deleted.pop()
        self.status_var.set(f"Can't restore binary file {last.name} — undo not available for browse deletes")


# ── Entry point ───────────────────────────────────────────────────────────────

def run(args):
    all_types = list(ASSET_TYPE_TO_DIR.keys())
    types = [args.type] if getattr(args, "type", None) else all_types
    for t in types:
        if t not in ASSET_TYPE_TO_DIR:
            print(f"Unknown type '{t}'. Valid: {', '.join(all_types)}")
            sys.exit(1)
    if args.cmd == "stats":
        cmd_stats(types)
    elif args.cmd == "browse":
        AssetBrowser(types)


def main():
    parser = argparse.ArgumentParser(description="Inspect recorded gameplay asset crops")
    sub = parser.add_subparsers(dest="cmd")
    sub.required = True

    p_stats = sub.add_parser("stats", help="Print coverage statistics")
    p_stats.add_argument("type", nargs="?", help="Asset type (omit for all)")

    p_browse = sub.add_parser("browse", help="Open thumbnail grid browser")
    p_browse.add_argument("type", nargs="?", help="Asset type (omit for all)")

    run(parser.parse_args())


if __name__ == "__main__":
    main()
