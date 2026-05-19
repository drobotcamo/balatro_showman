import argparse
import difflib
import json
import threading
import tkinter as tk
from tkinter import ttk
import cv2
import numpy as np
from pathlib import Path
from PIL import Image, ImageTk

try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

OUTPUT_ROOT = Path("recorded_gameplay_asset_images")
GAME_ASSET_IMAGES = Path("game_asset_images")
MAX_DISPLAY = (1280, 720)
SAMPLE_RATE = 16000

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
ASSET_TYPES = list(ASSET_TYPE_TO_DIR.keys())

NAV_KEYS = {
    ",": -1, ".": 1,
    "j": -500, "l": 500,
    "u": -1000, "o": 1000,
    "y": -5000, "p": 5000,
    "a": -5000, "d": 5000,
    "A": -500, "D": 500,   # Shift+a / Shift+d
}


def _best_match(raw, names):
    """Return the closest name from names to raw, or raw itself if names is empty."""
    if not names:
        return raw
    scored = [(difflib.SequenceMatcher(None, raw.lower(), n.lower()).ratio(), n) for n in names]
    return max(scored, key=lambda x: x[0])[1]


def _names_for_type(asset_type):
    dir_name = ASSET_TYPE_TO_DIR.get(asset_type)
    if not dir_name:
        return []
    asset_dir = GAME_ASSET_IMAGES / dir_name
    if not asset_dir.exists():
        return []
    return sorted(p.stem.replace("_", " ") for p in asset_dir.glob("*.png"))


class TemplateExtractor:
    def __init__(self, video_path, start_frame=0, whisper_model_name="base"):
        self.cap = cv2.VideoCapture(str(video_path))
        self.video_path = Path(video_path).resolve()
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame = None
        self.frame_idx = start_frame

        # View region in native pixel coords [x1, y1, x2, y2]
        self.view = [0.0, 0.0, float(self.frame_w), float(self.frame_h)]
        self.canvas_w = MAX_DISPLAY[0]
        self.canvas_h = MAX_DISPLAY[1]

        # Selection (native coords)
        self.sel_start_canvas = None
        self.sel_native = None
        self.rect_id = None
        self.pan_start = None
        self.saved_files = []

        # Audio
        self.whisper_model = None
        self.recording = False
        self.audio_chunks = []
        self.audio_thread = None

        self._build_ui()
        self._load_frame(start_frame)
        threading.Thread(target=self._load_whisper, args=(whisper_model_name,), daemon=True).start()
        self.root.mainloop()

    # ── Whisper ───────────────────────────────────────────────────────────────

    def _load_whisper(self, model_name):
        try:
            import whisper
            self.root.after(0, lambda: self.status_var.set("Loading Whisper…"))
            self.whisper_model = whisper.load_model(model_name)
            self.root.after(0, lambda: self.status_var.set("Ready — draw a box to begin"))
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Whisper unavailable ({e}) — type names manually"))

    def _start_listening(self):
        if not AUDIO_AVAILABLE or self.whisper_model is None:
            self.status_var.set("Box drawn — type name and press Enter")
            return
        self.audio_chunks = []
        self.recording = True
        self.status_var.set("🎤  Listening…   speak the asset name, then press Enter")
        self.audio_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.audio_thread.start()

    def _record_audio(self):
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            while self.recording:
                chunk, _ = stream.read(1024)
                self.audio_chunks.append(chunk.copy())

    def _transcribe(self):
        self.recording = False
        if self.audio_thread:
            self.audio_thread.join(timeout=2.0)
        if not self.audio_chunks or self.whisper_model is None:
            return ""
        self.status_var.set("Transcribing…")
        self.root.update()
        audio = np.concatenate(self.audio_chunks).flatten()
        result = self.whisper_model.transcribe(audio, fp16=False, language="en")
        return result["text"].strip().strip(".,!? ")

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("Template Extractor")

        for key, delta in NAV_KEYS.items():
            self.root.bind(f"<KeyPress-{key}>", lambda e, d=delta: self._nav_key(d))
        self.root.bind("<Return>", self._save_crop)
        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<KeyPress-e>", lambda e: self._nav_key_action(self._save_crop))
        self.root.bind("<Tab>", lambda e: (self._cycle_asset_type(1), "break")[-1])
        self.root.bind("<Shift-Tab>", lambda e: (self._cycle_asset_type(-1), "break")[-1])

        # Top bar
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(top, text="Asset type:").pack(side=tk.LEFT)
        self.asset_type = tk.StringVar(value=ASSET_TYPES[0])
        type_combo = ttk.Combobox(top, textvariable=self.asset_type, values=ASSET_TYPES,
                                  width=12, state="readonly")
        type_combo.pack(side=tk.LEFT, padx=4)
        type_combo.bind("<<ComboboxSelected>>", self._on_asset_type_change)

        tk.Label(top, text="Name:").pack(side=tk.LEFT, padx=(12, 0))
        self.name_var = tk.StringVar()
        self._all_names = _names_for_type(ASSET_TYPES[0])
        self.name_combo = ttk.Combobox(top, textvariable=self.name_var,
                                       values=self._all_names, width=28)
        self.name_combo.pack(side=tk.LEFT, padx=4)
        self.name_combo.bind("<KeyRelease>", self._on_name_key)
        self.name_combo.bind("<Return>", self._save_crop)

        tk.Button(top, text="Save  [Enter]", command=self._save_crop).pack(side=tk.LEFT, padx=8)

        self.status_var = tk.StringVar(value="Loading Whisper…")
        tk.Label(top, textvariable=self.status_var, fg="green", width=52, anchor="w").pack(side=tk.LEFT)

        # Canvas
        self.canvas = tk.Canvas(self.root, cursor="crosshair", bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<ButtonPress-3>", self._on_pan_start)
        self.canvas.bind("<B3-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonRelease-3>", self._on_pan_end)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-4>", self._on_scroll)
        self.canvas.bind("<Button-5>", self._on_scroll)

        # Nav bar
        nav = tk.Frame(self.root)
        nav.pack(fill=tk.X, padx=8, pady=4)

        for label, delta, key in [("<< 5k", -5000, "y"), ("< 1k", -1000, "u"),
                                   ("< 500", -500, "j"), ("< 1", -1, ",")]:
            tk.Button(nav, text=f"{label}  [{key}]", width=10,
                      command=lambda d=delta: self._step_frame(d)).pack(side=tk.LEFT, padx=2)

        tk.Label(nav, text="  Frame:").pack(side=tk.LEFT)
        self.frame_var = tk.StringVar()
        fe = tk.Entry(nav, textvariable=self.frame_var, width=8)
        fe.pack(side=tk.LEFT, padx=2)
        fe.bind("<Return>", self._jump_to_frame)
        tk.Button(nav, text="Go", command=self._jump_to_frame).pack(side=tk.LEFT)
        self.frame_info = tk.StringVar()
        tk.Label(nav, textvariable=self.frame_info, width=20, anchor="w").pack(side=tk.LEFT, padx=4)

        for label, delta, key in [("1 >", 1, "."), ("500 >", 500, "l"),
                                   ("1k >", 1000, "o"), ("5k >>", 5000, "p")]:
            tk.Button(nav, text=f"[{key}]  {label}", width=10,
                      command=lambda d=delta: self._step_frame(d)).pack(side=tk.LEFT, padx=2)

        tk.Label(nav, text="   scroll=zoom   right-drag=pan", fg="gray").pack(side=tk.LEFT, padx=8)

    # ── Frame loading & rendering ─────────────────────────────────────────────

    def _load_frame(self, idx):
        idx = max(0, min(idx, self.total_frames - 1))
        self.frame_idx = idx
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret:
            return
        self.frame = frame
        self.view = [0.0, 0.0, float(self.frame_w), float(self.frame_h)]
        self._clear_selection()
        self._redraw()
        ts = idx / self.fps
        self.frame_var.set(str(idx))
        self.frame_info.set(f"/ {self.total_frames - 1}   ({ts:.1f}s)")

    def _redraw(self):
        if self.frame is None:
            return
        x1, y1, x2, y2 = self.view
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(self.frame_w, int(x2)), min(self.frame_h, int(y2))
        region = self.frame[y1:y2, x1:x2]
        rh, rw = region.shape[:2]
        if rw == 0 or rh == 0:
            return

        scale = min(MAX_DISPLAY[0] / rw, MAX_DISPLAY[1] / rh)
        dw, dh = max(1, int(rw * scale)), max(1, int(rh * scale))
        self.canvas_w, self.canvas_h = dw, dh
        self.canvas.config(width=dw, height=dh)

        display = cv2.resize(region, (dw, dh), interpolation=cv2.INTER_AREA)
        self._photo = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(display, cv2.COLOR_BGR2RGB)))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)

        if self.sel_native:
            self._draw_sel_rect()

    def _c2n(self, cx, cy):
        vx1, vy1, vx2, vy2 = self.view
        nx = vx1 + cx * (vx2 - vx1) / self.canvas_w
        ny = vy1 + cy * (vy2 - vy1) / self.canvas_h
        return int(np.clip(nx, 0, self.frame_w)), int(np.clip(ny, 0, self.frame_h))

    def _n2c(self, nx, ny):
        vx1, vy1, vx2, vy2 = self.view
        cx = (nx - vx1) * self.canvas_w / (vx2 - vx1)
        cy = (ny - vy1) * self.canvas_h / (vy2 - vy1)
        return int(cx), int(cy)

    # ── Selection ─────────────────────────────────────────────────────────────

    def _clear_selection(self):
        self.sel_start_canvas = None
        self.sel_native = None
        self.recording = False
        self.audio_chunks = []
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

    def _draw_sel_rect(self):
        if not self.sel_native:
            return
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        nx0, ny0, nx1, ny1 = self.sel_native
        cx0, cy0 = self._n2c(nx0, ny0)
        cx1, cy1 = self._n2c(nx1, ny1)
        self.rect_id = self.canvas.create_rectangle(cx0, cy0, cx1, cy1, outline="lime", width=2)

    def _on_press(self, e):
        self._clear_selection()
        self.sel_start_canvas = (e.x, e.y)

    def _on_drag(self, e):
        if not self.sel_start_canvas:
            return
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        cx0, cy0 = self.sel_start_canvas
        self.rect_id = self.canvas.create_rectangle(cx0, cy0, e.x, e.y, outline="lime", width=2)
        nx0, ny0 = self._c2n(cx0, cy0)
        nx1, ny1 = self._c2n(e.x, e.y)
        self.sel_native = (min(nx0, nx1), min(ny0, ny1), max(nx0, nx1), max(ny0, ny1))

    def _on_release(self, e):
        if not self.sel_start_canvas:
            return
        nx0, ny0 = self._c2n(*self.sel_start_canvas)
        nx1, ny1 = self._c2n(e.x, e.y)
        self.sel_native = (min(nx0, nx1), min(ny0, ny1), max(nx0, nx1), max(ny0, ny1))
        self._start_listening()

    # ── Zoom & pan ────────────────────────────────────────────────────────────

    def _on_scroll(self, e):
        if self.frame is None:
            return
        direction = (1 if e.delta > 0 else -1) if hasattr(e, "delta") else (1 if e.num == 4 else -1)
        factor = 0.8 if direction > 0 else 1.25

        vx1, vy1, vx2, vy2 = self.view
        vw, vh = vx2 - vx1, vy2 - vy1
        cx = vx1 + e.x * vw / self.canvas_w
        cy = vy1 + e.y * vh / self.canvas_h

        new_vw = max(64, min(float(self.frame_w), vw * factor))
        new_vh = max(64, min(float(self.frame_h), vh * factor))
        new_x1 = np.clip(cx - e.x * new_vw / self.canvas_w, 0, self.frame_w - new_vw)
        new_y1 = np.clip(cy - e.y * new_vh / self.canvas_h, 0, self.frame_h - new_vh)
        self.view = [new_x1, new_y1, new_x1 + new_vw, new_y1 + new_vh]
        self._redraw()

    def _on_pan_start(self, e):
        self.pan_start = (e.x, e.y)

    def _on_pan_drag(self, e):
        if not self.pan_start:
            return
        vx1, vy1, vx2, vy2 = self.view
        vw, vh = vx2 - vx1, vy2 - vy1
        dx = (e.x - self.pan_start[0]) * vw / self.canvas_w
        dy = (e.y - self.pan_start[1]) * vh / self.canvas_h
        new_x1 = np.clip(vx1 - dx, 0, self.frame_w - vw)
        new_y1 = np.clip(vy1 - dy, 0, self.frame_h - vh)
        self.view = [new_x1, new_y1, new_x1 + vw, new_y1 + vh]
        self.pan_start = (e.x, e.y)
        self._redraw()

    def _on_pan_end(self, e):
        self.pan_start = None

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save_crop(self, _=None):
        if self.sel_native is None:
            self.status_var.set("Draw a selection first.")
            return

        # Transcribe voice if no name typed yet
        if (self.recording or self.audio_chunks) and not self.name_var.get().strip():
            spoken = self._transcribe()
            if spoken:
                self.name_var.set(spoken)

        raw = self.name_var.get().strip()
        if not raw:
            self.status_var.set("No name — speak or type one, then press Enter.")
            return

        name = _best_match(raw, self._all_names)
        if name != raw:
            self.name_var.set(name)

        x0, y0, x1, y1 = self.sel_native
        crop = self.frame[y0:y1, x0:x1]
        if crop.size == 0:
            self.status_var.set("Selection too small.")
            return

        out_dir = OUTPUT_ROOT / self.asset_type.get()
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = name.replace(" ", "_")
        out_path = out_dir / f"{stem}.png"
        n = 1
        while out_path.exists():
            out_path = out_dir / f"{stem}_{n}.png"
            n += 1
        cv2.imwrite(str(out_path), crop)
        out_path.with_suffix(".json").write_text(json.dumps({
            "video_path": str(self.video_path),
            "frame_idx":  self.frame_idx,
            "frame_w":    self.frame_w,
            "frame_h":    self.frame_h,
            "asset_type": self.asset_type.get(),
            "asset_name": name,
            "bbox_xyxy":  [x0, y0, x1, y1],
        }, indent=2))
        self.saved_files.append(out_path)

        matched_note = f"  (matched from '{raw}')" if name != raw else ""
        self.status_var.set(f"Saved → {out_path.name}{matched_note}   |   draw next box")
        self.name_var.set("")
        self._clear_selection()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _nav_key(self, delta):
        if isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox)):
            return
        self._step_frame(delta)

    def _nav_key_action(self, fn):
        if isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox)):
            return
        fn()

    def _undo(self):
        if not self.saved_files:
            self.status_var.set("Nothing to undo.")
            return
        path = self.saved_files.pop()
        try:
            path.unlink()
            sidecar = path.with_suffix(".json")
            if sidecar.exists():
                sidecar.unlink()
            self.status_var.set(f"Undone — deleted {path.name}")
        except FileNotFoundError:
            self.status_var.set(f"Undo: {path.name} already gone")

    def _cycle_asset_type(self, direction):
        if isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox)):
            return
        idx = (ASSET_TYPES.index(self.asset_type.get()) + direction) % len(ASSET_TYPES)
        self.asset_type.set(ASSET_TYPES[idx])
        self._on_asset_type_change()

    def _step_frame(self, delta):
        self._load_frame(self.frame_idx + delta)

    def _jump_to_frame(self, _=None):
        try:
            self._load_frame(int(self.frame_var.get()))
        except ValueError:
            pass

    # ── Autocomplete ──────────────────────────────────────────────────────────

    def _on_asset_type_change(self, _=None):
        self._all_names = _names_for_type(self.asset_type.get())
        self.name_combo["values"] = self._all_names
        self.name_var.set("")

    def _on_name_key(self, _=None):
        typed = self.name_var.get().lower()
        self.name_combo["values"] = (
            [n for n in self._all_names if typed in n.lower()] if typed else self._all_names
        )


def run(args):
    TemplateExtractor(Path(args.video), start_frame=args.frame,
                      whisper_model_name=args.whisper_model)


def _add_args(parser):
    parser.add_argument("video", help="Path to gameplay footage mp4")
    parser.add_argument("--frame", type=int, default=0, help="Starting frame index (default 0)")
    parser.add_argument("--whisper-model", default="base",
                        help="Whisper model size: tiny/base/small (default base)")


def main():
    parser = argparse.ArgumentParser(description="Extract template crops from gameplay footage")
    _add_args(parser)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
