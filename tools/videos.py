from pathlib import Path
import sys

FOOTAGE_DIR = Path("gameplay_sources/gameplay_footage")


def list_videos():
    """Return {BU1: Path, BU2: Path, ...} sorted by mtime ascending (oldest = BU1)."""
    files = sorted(FOOTAGE_DIR.glob("*.mp4"), key=lambda f: f.stat().st_mtime)
    return {f"BU{i + 1}": f for i, f in enumerate(files)}


def resolve_video(arg):
    """Resolve BU1/BU2/etc. to a Path, or return Path(arg) unchanged."""
    upper = str(arg).upper()
    if upper.startswith("BU") and upper[2:].isdigit():
        videos = list_videos()
        if upper not in videos:
            available = ", ".join(videos) or "none"
            sys.exit(f"error: '{arg}' not found. Available: {available}")
        path = videos[upper]
        print(f"  {upper} → {path.name}")
        return path
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
