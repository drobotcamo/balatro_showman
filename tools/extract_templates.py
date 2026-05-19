import argparse
import difflib
import json
import random
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

from tools.videos import list_videos, resolve_video
from game_assets import ASSET_NAMES

OUTPUT_ROOT = Path("recorded_gameplay_asset_images")
MAX_DISPLAY = (1280, 720)
SAMPLE_RATE = 16000

ASSET_TYPES = list(ASSET_NAMES.keys())


_FUZZY_THRESHOLD = 0.4


def _best_match(raw, names):
    if not names:
        return raw
    scored = [(difflib.SequenceMatcher(None, raw.lower(), n.lower()).ratio(), n) for n in names]
    best_score, best_name = max(scored, key=lambda x: x[0])
    return best_name if best_score >= _FUZZY_THRESHOLD else raw


def _names_for_type(asset_type):
    return list(ASSET_NAMES.get(asset_type, []))


def _build_pool(video_paths, pool_size):
    """Return a shuffled list of (Path, frame_idx) sampled proportionally across all videos."""
    entries = []
    for vp in video_paths:
        cap = cv2.VideoCapture(str(vp))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if total > 0:
            entries.append((Path(vp), total))

    if not entries:
        return []

    total_all = sum(t for _, t in entries)
    pool = []
    for vp, total in entries:
        count = max(1, round(pool_size * total / total_all))
        idxs = random.sample(range(total), min(count, total))
        pool.extend((vp, idx) for idx in idxs)

    random.shuffle(pool)
    return pool[:pool_size]


class TemplateExtractor:
    def __init__(self, video_paths, pool_size=300, video_aliases=None, whisper_model_name="base"):
        self.pool = _build_pool(video_paths, pool_size)
        if not self.pool:
            print("No valid video frames found.")
            return

        self.video_aliases = video_aliases or {}  # str(resolved_path) -> "BU1" etc.
        self.pool_idx = 0
        self._caps = {}  # str(video_path) -> cv2.VideoCapture

        # Current frame state (populated by _load_pool_frame)
        self.video_path = None
        self.frame = None
        self.frame_idx = 0
        self.frame_w = 1920
        self.frame_h = 1080
        self.fps = 30.0
        self.total_frames = 0

        self.view = [0.0, 0.0, float(self.frame_w), float(self.frame_h)]
        self.canvas_w = MAX_DISPLAY[0]
        self.canvas_h = MAX_DISPLAY[1]

        self.sel_start_canvas = None
        self.sel_native = None
        self.rect_id = None
        self.pan_start = None
        self.saved_files = []
        self.session_count = 0
        self._confirm_pending = False
        self._label_index = {}  # (video_name, frame_idx) -> label count, built in background

        self.whisper_model = None
        self.recording = False
        self.audio_chunks = []
        self.audio_thread = None

        self._build_ui()
        self._load_pool_frame(0)
        threading.Thread(target=self._load_whisper, args=(whisper_model_name,), daemon=True).start()
        threading.Thread(target=self._build_label_index, daemon=True).start()
        self.root.mainloop()

        for cap in self._caps.values():
            cap.release()

    # ── Whisper ───────────────────────────────────────────────────────────────

    def _query_mic(self):
        if not AUDIO_AVAILABLE:
            return "mic: unavailable"
        try:
            return f"mic: {sd.query_devices(kind='input')['name'][:40]}"
        except Exception:
            return "mic: unknown"

    def _load_whisper(self, model_name):
        try:
            import whisper
            self.root.after(0, lambda: self.status_var.set("Loading Whisper..."))
            self.whisper_model = whisper.load_model(model_name)
            self.root.after(0, lambda: self.status_var.set("Ready -- draw a box to begin"))
        except Exception:
            self.root.after(0, lambda: self.status_var.set("Whisper unavailable -- type names manually"))

    def _start_listening(self):
        if not AUDIO_AVAILABLE or self.whisper_model is None:
            self.status_var.set("Box drawn -- type name and press Enter / E")
            return
        self.audio_chunks = []
        self.recording = True
        self.status_var.set("Listening...  speak the asset name, then press Enter")
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
        self.status_var.set("Transcribing...")
        self.root.update()
        audio = np.concatenate(self.audio_chunks).flatten()
        result = self.whisper_model.transcribe(audio, fp16=False, language="en")
        return result["text"].strip().strip(".,!? ")

    def _build_label_index(self):
        index = {}
        for asset_type in ASSET_TYPES:
            asset_dir = OUTPUT_ROOT / asset_type
            if not asset_dir.exists():
                continue
            for json_file in asset_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text())
                    key = (data["video_path"], data["frame_idx"])
                    index[key] = index.get(key, 0) + 1
                except Exception:
                    pass
        self._label_index = index

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title("Balatro Labeler")
        self.root.minsize(900, 500)

        # Navigation keys (guarded -- inactive when focus is in a text field)
        self.root.bind("<KeyPress-r>", lambda e: self._key_guard(self._next_frame))
        self.root.bind("<KeyPress-s>", lambda e: self._key_guard(self._next_frame))
        self.root.bind("<KeyPress-w>", lambda e: self._key_guard(self._prev_frame))
        self.root.bind("<KeyPress-z>", lambda e: self._key_guard(self._undo))
        self.root.bind("<KeyPress-x>", lambda e: self._key_guard(self._clear_selection))
        self.root.bind("<KeyPress-g>", lambda e: self._key_guard(self._focus_name))
        self.root.bind("<KeyPress-q>", lambda e: self._key_guard(self.root.destroy))
        self.root.bind("<KeyPress-e>", lambda e: self._key_guard(self._save_crop))
        self.root.bind("<KeyPress-0>", lambda e: self._key_guard(self._reset_zoom))
        self.root.bind("<Home>", lambda e: self._key_guard(self._reset_zoom))
        self.root.bind("<Return>", self._save_crop)
        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Tab>", self._on_tab)
        self.root.bind("<Shift-Tab>", self._on_shift_tab)

        # Number keys 1-9 select asset type
        for i, atype in enumerate(ASSET_TYPES[:9], 1):
            self.root.bind(f"<KeyPress-{i}>",
                           lambda e, t=atype: self._key_guard(lambda: self._set_asset_type(t)))

        # ── Top bar ───────────────────────────────────────────────────────────
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=8, pady=4)

        tk.Label(top, text="Type [Tab]:").pack(side=tk.LEFT)
        self.asset_type = tk.StringVar(value=ASSET_TYPES[0])
        type_combo = ttk.Combobox(top, textvariable=self.asset_type, values=ASSET_TYPES,
                                  width=12, state="readonly")
        type_combo.pack(side=tk.LEFT, padx=4)
        type_combo.bind("<<ComboboxSelected>>", self._on_asset_type_change)

        hints = "  ".join(f"{i}:{t[:3]}" for i, t in enumerate(ASSET_TYPES[:9], 1))
        tk.Label(top, text=hints, fg="gray", font=("Courier", 8)).pack(side=tk.LEFT, padx=6)

        tk.Label(top, text="  Name [G]:").pack(side=tk.LEFT, padx=(8, 0))
        self.name_var = tk.StringVar()
        self._all_names = _names_for_type(ASSET_TYPES[0])
        self.name_combo = ttk.Combobox(top, textvariable=self.name_var,
                                       values=self._all_names, width=28)
        self.name_combo.pack(side=tk.LEFT, padx=4)
        self.name_combo.bind("<KeyRelease>", self._on_name_key)
        self.name_combo.bind("<Return>", self._save_crop)

        tk.Button(top, text="Save [E/Enter]", command=self._save_crop).pack(side=tk.LEFT, padx=8)

        self.status_var = tk.StringVar(value="Loading Whisper...")
        tk.Label(top, textvariable=self.status_var, fg="green", width=50, anchor="w").pack(side=tk.LEFT)

        # ── Canvas ────────────────────────────────────────────────────────────
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

        # ── Nav / info bar ────────────────────────────────────────────────────
        nav = tk.Frame(self.root)
        nav.pack(fill=tk.X, padx=8, pady=4)

        tk.Button(nav, text="[W] Back", width=9,
                  command=self._prev_frame).pack(side=tk.LEFT, padx=2)

        self.pool_label = tk.StringVar(value="0 / 0")
        tk.Label(nav, textvariable=self.pool_label, width=12, anchor="center",
                 relief="sunken", padx=4).pack(side=tk.LEFT, padx=4)

        tk.Button(nav, text="[R/S] Next", width=9,
                  command=self._next_frame).pack(side=tk.LEFT, padx=2)

        tk.Label(nav, text="  ").pack(side=tk.LEFT)

        self.frame_label = tk.StringVar(value="")
        tk.Label(nav, textvariable=self.frame_label, width=36, anchor="w").pack(side=tk.LEFT)

        self.save_label = tk.StringVar(value="")
        tk.Label(nav, textvariable=self.save_label, fg="gray", anchor="w").pack(side=tk.LEFT, padx=12)

        self.count_label = tk.StringVar(value="Session: 0 labels")
        tk.Label(nav, textvariable=self.count_label, fg="blue", anchor="e").pack(side=tk.RIGHT, padx=8)
        tk.Label(nav, text="[0] zoom↺", fg="gray", font=("Courier", 8)).pack(side=tk.RIGHT, padx=4)

        self.mic_var = tk.StringVar(value=self._query_mic())
        tk.Label(nav, textvariable=self.mic_var, fg="gray", anchor="e").pack(side=tk.RIGHT, padx=8)

    # ── Frame loading & rendering ─────────────────────────────────────────────

    def _load_pool_frame(self, pool_idx):
        if pool_idx < 0 or pool_idx >= len(self.pool):
            return
        self.pool_idx = pool_idx
        video_path, frame_idx = self.pool[pool_idx]

        key = str(video_path)
        if key not in self._caps:
            self._caps[key] = cv2.VideoCapture(key)
        cap = self._caps[key]

        self.video_path = video_path
        self.frame_idx = frame_idx
        self.frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            if pool_idx + 1 < len(self.pool):
                self._load_pool_frame(pool_idx + 1)
            return

        self.frame = frame
        self.view = [0.0, 0.0, float(self.frame_w), float(self.frame_h)]
        self._clear_selection()
        self._redraw()
        self._update_info()

    def _update_info(self):
        self.pool_label.set(f"{self.pool_idx + 1} / {len(self.pool)}")
        alias = self.video_aliases.get(str(self.video_path.resolve()),
                                       self.video_path.stem[:14])
        ts = self.frame_idx / self.fps
        key = (self.video_path.name, self.frame_idx)
        existing = self._label_index.get(key, 0)
        badge = f"  [{existing} labeled]" if existing else ""
        self.frame_label.set(f"{alias}   frame {self.frame_idx:,}   ({ts:.1f}s){badge}")
        out_dir = OUTPUT_ROOT / self.asset_type.get()
        self.save_label.set(f"-> {out_dir}")

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
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=0.15)
        self.audio_chunks = []
        self._confirm_pending = False
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
        if self._confirm_pending:
            self.status_var.set("Press Enter to confirm, or Undo/Z to cancel")
            return
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
        x0, y0, x1, y1 = self.sel_native
        if x1 - x0 < 4 or y1 - y0 < 4:
            self._clear_selection()
            return
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

        if (self.recording or self.audio_chunks) and not self.name_var.get().strip():
            spoken = self._transcribe()
            if spoken:
                self.name_var.set(spoken)

        raw = self.name_var.get().strip()
        if not raw:
            self.status_var.set("No name -- speak or type one, then press Enter.")
            return

        name = _best_match(raw, self._all_names)

        known = ASSET_NAMES.get(self.asset_type.get(), [])
        if name not in known:
            self.status_var.set(f"Unknown asset '{name}' -- not in registry for {self.asset_type.get()}")
            return

        # First Enter: show matched name as confirmation, wait for second Enter
        if not self._confirm_pending:
            self.name_var.set(name)
            if name != raw:
                self.status_var.set(f"Matched: {name}   -- Enter to save  |  Z to cancel")
            else:
                self.status_var.set(f"Confirm: {name}   -- Enter to save  |  Z to cancel")
            self._confirm_pending = True
            self.root.focus_set()
            return

        # Second Enter: commit
        self._confirm_pending = False

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
            "video_path": self.video_path.name,
            "frame_idx":  self.frame_idx,
            "frame_w":    self.frame_w,
            "frame_h":    self.frame_h,
            "asset_type": self.asset_type.get(),
            "asset_name": name,
            "bbox_xyxy":  [x0, y0, x1, y1],
        }, indent=2))
        self.saved_files.append((out_path, self.video_path.name, self.frame_idx))
        key = (self.video_path.name, self.frame_idx)
        self._label_index[key] = self._label_index.get(key, 0) + 1
        self.session_count += 1
        self.count_label.set(f"Session: {self.session_count} labels")
        self._update_info()

        matched = f"  (matched '{raw}')" if name != raw else ""
        self.status_var.set(f"Saved {out_path.name}{matched}   -- draw next box or [R] next frame")
        self.name_var.set("")
        self._clear_selection()
        self.root.focus_set()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _key_guard(self, fn):
        if isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox)):
            return
        fn()

    def _on_tab(self, e):
        if isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox)):
            return
        self._cycle_asset_type(1)
        return "break"

    def _on_shift_tab(self, e):
        if isinstance(self.root.focus_get(), (tk.Entry, ttk.Combobox)):
            return
        self._cycle_asset_type(-1)
        return "break"

    def _next_frame(self):
        self._load_pool_frame(self.pool_idx + 1)

    def _prev_frame(self):
        self._load_pool_frame(self.pool_idx - 1)

    def _reset_zoom(self):
        if self.frame is None:
            return
        self.view = [0.0, 0.0, float(self.frame_w), float(self.frame_h)]
        self._redraw()

    def _focus_name(self):
        self.name_combo.focus_set()

    def _undo(self):
        if self._confirm_pending:
            self._clear_selection()
            self.name_var.set("")
            self.status_var.set("Cancelled -- draw a new box")
            return
        if not self.saved_files:
            self.status_var.set("Nothing to undo.")
            return
        path, video_name, frame_idx = self.saved_files.pop()
        self.session_count = max(0, self.session_count - 1)
        self.count_label.set(f"Session: {self.session_count} labels")
        key = (video_name, frame_idx)
        self._label_index[key] = max(0, self._label_index.get(key, 0) - 1)
        self._update_info()
        try:
            path.unlink()
            sidecar = path.with_suffix(".json")
            if sidecar.exists():
                sidecar.unlink()
            self.status_var.set(f"Undone -- deleted {path.name}")
        except FileNotFoundError:
            self.status_var.set(f"Undo: {path.name} already gone")

    def _cycle_asset_type(self, direction):
        idx = (ASSET_TYPES.index(self.asset_type.get()) + direction) % len(ASSET_TYPES)
        self.asset_type.set(ASSET_TYPES[idx])
        self._on_asset_type_change()

    def _set_asset_type(self, atype):
        self.asset_type.set(atype)
        self._on_asset_type_change()

    # ── Autocomplete ──────────────────────────────────────────────────────────

    def _on_asset_type_change(self, _=None):
        self._confirm_pending = False
        self._all_names = _names_for_type(self.asset_type.get())
        typed = self.name_var.get().lower()
        self.name_combo["values"] = (
            [n for n in self._all_names if typed in n.lower()] if typed else self._all_names
        )
        self._update_info()

    def _on_name_key(self, e=None):
        if e and e.keysym in ("Up", "Down", "Left", "Right", "Return", "Escape", "Tab"):
            return
        self._confirm_pending = False
        typed = self.name_var.get().lower()
        self.name_combo["values"] = (
            [n for n in self._all_names if typed in n.lower()] if typed else self._all_names
        )


def run(args):
    videos = list_videos()
    if not videos:
        print("No footage found in gameplay_sources/gameplay_footage/")
        return

    if args.videos:
        selected = {}
        for v in args.videos:
            path = resolve_video(v)
            alias = next((k for k, p in videos.items() if p.resolve() == path.resolve()), path.stem)
            selected[str(path.resolve())] = alias
    else:
        selected = {str(p.resolve()): alias for alias, p in videos.items()}

    if not selected:
        print("No matching videos found.")
        return

    print(f"Sampling from {len(selected)} video(s): {', '.join(selected.values())}")
    print(f"Pool: {args.pool_size} random frames")
    print(f"Saving labels to: {OUTPUT_ROOT.resolve()}\n")

    video_paths = [Path(p) for p in selected]
    TemplateExtractor(video_paths, pool_size=args.pool_size,
                      video_aliases=selected,
                      whisper_model_name=args.whisper_model)


def _add_args(parser):
    parser.add_argument("videos", nargs="*",
                        help="Videos to sample from (BU aliases or paths). Omit to use all available.")
    parser.add_argument("--pool-size", type=int, default=300,
                        help="Number of random frames to pre-sample (default: 300)")
    parser.add_argument("--whisper-model", default="base",
                        help="Whisper model size: tiny/base/small (default: base)")


def main():
    parser = argparse.ArgumentParser(description="Label asset crops from gameplay footage")
    _add_args(parser)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
