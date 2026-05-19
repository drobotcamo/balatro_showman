"""
Download YouTube gameplay footage for Balatro Showman training data.

Saves to gameplay_sources/gameplay_footage/ at 1080p (falls back to best available).
Requires ffmpeg for merging audio/video. Uses Node.js if available for stable YouTube extraction.

Usage:
    python gameplay_sources/downloader.py <URL> [<URL> ...]
    python gameplay_sources/downloader.py <url1> <url2> <url3>   # batch

    --overwrite    Re-download even if the file already exists.
    --list-formats Show available formats without downloading.

Output is named by video title and saved as .mp4.
Skips if the file already exists (use --overwrite to force).
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yt_dlp

OUTPUT_DIR = Path(__file__).parent / "gameplay_footage"

# Fallback paths for tools that may not be on PATH in a freshly updated shell.
_FFMPEG_FALLBACKS = [
    Path.home() / "AppData/Local/Microsoft/WinGet/Links/ffmpeg.exe",
    Path("C:/ffmpeg/bin/ffmpeg.exe"),
    Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
]
_NODE_FALLBACKS = [
    Path("C:/Program Files/nodejs/node.exe"),
    Path("C:/Program Files (x86)/nodejs/node.exe"),
]


def _find_tool(name: str, fallbacks: list) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for p in fallbacks:
        if Path(p).exists():
            return str(p)
    return None


def _probe_video(path: Path, ffprobe: str) -> dict | None:
    """Return {width, height, fps, duration_sec} for the video stream, or None."""
    try:
        r = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        data = json.loads(r.stdout)
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                num, den = (int(x) for x in s.get("r_frame_rate", "1/1").split("/"))
                fps = num / den if den else 0
                duration = float(
                    s.get("duration")
                    or data.get("format", {}).get("duration")
                    or 0
                )
                return {
                    "width": s.get("width"),
                    "height": s.get("height"),
                    "fps": fps,
                    "duration_sec": duration,
                }
    except Exception:
        pass
    return None


def _next_number(prefix: str) -> int:
    pattern = re.compile(rf"{re.escape(prefix)}(\d+)\.mp4", re.IGNORECASE)
    nums = [int(m.group(1)) for f in OUTPUT_DIR.glob(f"{prefix}*.mp4") if (m := pattern.fullmatch(f.name))]
    return max(nums, default=0) + 1


def build_ydl_opts(ffmpeg_dir: str, node_path: str | None, overwrite: bool, out_stem: str) -> dict:
    opts = {
        # Priority: 1080p mp4+audio → best ≤1080p mp4+audio → best ≤1080p (pre-merged)
        "format": (
            "bestvideo[height=1080][ext=mp4]+bestaudio"
            "/bestvideo[height<=1080][ext=mp4]+bestaudio"
            "/best[height<=1080]"
        ),
        "outtmpl": str(OUTPUT_DIR / f"{out_stem}.%(ext)s"),
        "merge_output_format": "mp4",
        "ffmpeg_location": ffmpeg_dir,
        "noplaylist": True,
        "progress_hooks": [_progress_hook],
    }
    if not overwrite:
        opts["no_overwrites"] = True
    if node_path:
        opts["js_runtimes"] = {"node": {"path": node_path}}
        opts["remote_components"] = {"ejs:github"}
    return opts


def _progress_hook(d: dict):
    if d["status"] == "downloading":
        pct = d.get("_percent_str", "?%").strip()
        speed = d.get("_speed_str", "?").strip()
        eta = d.get("_eta_str", "?").strip()
        print(f"\r  {pct}  speed: {speed}  eta: {eta}    ", end="", flush=True)
    elif d["status"] == "finished":
        print(f"\r  Done: {Path(d['filename']).name}")


def download(urls: list, ffmpeg_path: str, node_path: str | None, overwrite: bool = False, prefix: str = "BU"):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ffmpeg_dir = str(Path(ffmpeg_path).parent)
    ffprobe = str(Path(ffmpeg_path).parent / "ffprobe.exe")
    if not Path(ffprobe).exists():
        ffprobe = shutil.which("ffprobe") or ffprobe

    next_n = _next_number(prefix)

    for url in urls:
        out_stem = f"{prefix}{next_n}"
        out_path = OUTPUT_DIR / f"{out_stem}.mp4"

        if out_path.exists() and not overwrite:
            print(f"\nSkipping {out_stem}: already exists")
            _report_resolution(out_path, ffprobe)
            next_n += 1
            continue

        opts = build_ydl_opts(ffmpeg_dir, node_path, overwrite, out_stem)
        with yt_dlp.YoutubeDL(opts) as ydl:
            print(f"\nFetching info: {url}")
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                print(f"  ERROR fetching info: {e}", file=sys.stderr)
                continue

            title = info.get("title", "unknown")
            duration = info.get("duration", 0)
            print(f"  Title:    {title}")
            print(f"  Duration: {duration // 60}m {duration % 60}s")
            print(f"  Saving as: {out_stem}.mp4")
            print("  Downloading...")
            try:
                ydl.download([url])
            except Exception as e:
                print(f"  ERROR during download: {e}", file=sys.stderr)
                continue

            if out_path.exists():
                _report_resolution(out_path, ffprobe)
                next_n += 1
            else:
                print(f"  WARNING: expected output not found at {out_path}")


def _report_resolution(path: Path, ffprobe: str):
    info = _probe_video(path, ffprobe)
    if not info:
        print(f"  Saved: {path.name} (resolution unknown — ffprobe unavailable)")
        return
    w, h, fps, dur = info["width"], info["height"], info["fps"], info["duration_sec"]
    mins = dur / 60
    res_tag = f"{h}p" if h else "?p"
    print(f"  {res_tag}  {w}x{h} @ {fps:.0f}fps  {mins:.1f}min  -> {path.name}")
    if h and h < 720:
        print(f"  WARNING: only {h}p — 1080p may not be available for this video.")


def list_formats(url: str, node_path: str | None):
    opts = {"listformats": True, "noplaylist": True}
    if node_path:
        opts["js_runtimes"] = {"node": {"path": node_path}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])


def run(args):
    # Windows console may use a legacy codepage (e.g. cp1252) that can't encode
    # non-ASCII video titles. Reconfigure to UTF-8 so yt-dlp output doesn't crash.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    ffmpeg_path = _find_tool("ffmpeg", _FFMPEG_FALLBACKS)
    if not ffmpeg_path:
        print(
            "ERROR: ffmpeg not found.\n"
            "Install with:  winget install Gyan.FFmpeg\n"
            "Then restart your terminal.",
            file=sys.stderr,
        )
        sys.exit(1)

    node_path = _find_tool("node", _NODE_FALLBACKS)
    print(f"ffmpeg: {ffmpeg_path}")
    print(f"node:   {node_path or 'not found (JS warning expected, downloads still work)'}")

    if args.list_formats:
        list_formats(args.urls[0], node_path)
        return

    download(args.urls, ffmpeg_path, node_path, args.overwrite, args.prefix)


def _add_args(parser):
    parser.add_argument("urls", nargs="+", help="YouTube URLs to download")
    parser.add_argument("--overwrite", action="store_true", help="Re-download if file already exists")
    parser.add_argument("--prefix", default="BU", metavar="PREFIX",
                        help="Filename prefix for numbered output files (default: BU → BU27.mp4, BU28.mp4, ...)")
    parser.add_argument("--list-formats", action="store_true", dest="list_formats",
                        help="Show available formats for the first URL without downloading")


def main():
    parser = argparse.ArgumentParser(description="Download Balatro YouTube footage at 1080p")
    _add_args(parser)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
