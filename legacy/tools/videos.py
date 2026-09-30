import re
from pathlib import Path
import sys

FOOTAGE_DIR = Path("gameplay_sources/gameplay_footage")


def list_videos():
    """Return {stem: Path} for all <prefix><N>.mp4 files, sorted by prefix then number."""
    numbered = []
    for f in FOOTAGE_DIR.glob("*.mp4"):
        m = re.fullmatch(r"([A-Za-z]+)(\d+)\.mp4", f.name)
        if m:
            numbered.append((m.group(1).upper(), int(m.group(2)), f))
    return {f.stem: f for _, _, f in sorted(numbered, key=lambda x: (x[0], x[1]))}


def resolve_video(arg):
    """Resolve a numbered alias (BU1, FOO3, etc.) to a Path, or return Path(arg) unchanged."""
    videos = list_videos()
    upper = str(arg).upper()
    if upper in videos:
        path = videos[upper]
        print(f"  {upper} -> {path.name}")
        return path
    if re.fullmatch(r"[A-Za-z]+\d+", arg):
        available = ", ".join(videos) or "none"
        sys.exit(f"error: '{arg}' not found. Available: {available}")
    return Path(arg)


def video_completer(prefix, **kwargs):
    return list(list_videos().keys())


def cmd_videos():
    videos = list_videos()
    if not videos:
        print("No footage in gameplay_sources/gameplay_footage/")
        return
    for alias, path in videos.items():
        size = path.stat().st_size / 1e9
        print(f"  {alias}  {size:.1f} GB  {path.name}")
