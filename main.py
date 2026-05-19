# PYTHON_ARGCOMPLETE_OK
"""
Balatro Showman — unified CLI entry point.

    python main.py videos                          list footage with BU aliases
    python main.py download <url> [url ...]        download YouTube footage
    python main.py detect   <video|BU#> [options]  run skip tag detection
    python main.py extract  <video|BU#> [options]  extract template crops (GUI)
    python main.py assets   stats  [type]          print asset coverage
    python main.py assets   browse [type]          open thumbnail grid browser

Tab completion (run once):
    echo 'eval "$(register-python-argcomplete main.py)"' >> ~/.bashrc
"""

import argparse
import sys

import argcomplete

from tools.videos import list_videos, resolve_video, video_completer, cmd_videos


def _attach_video_completer(parser):
    for action in parser._actions:
        if action.dest == "video":
            action.completer = video_completer


def main():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Balatro Showman toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Video arguments accept BU aliases (BU1, BU2, …) or full paths.\n"
            "Run 'python main.py videos' to see the current alias mapping."
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # ── videos ────────────────────────────────────────────────────────────────
    sub.add_parser("videos", help="List downloaded footage with BU aliases")

    # ── download ──────────────────────────────────────────────────────────────
    p_dl = sub.add_parser("download", help="Download YouTube footage at 1080p")
    from gameplay_sources.downloader import _add_args as _dl_args
    _dl_args(p_dl)

    # ── detect ────────────────────────────────────────────────────────────────
    p_detect = sub.add_parser("detect", help="Run skip tag detection on footage")
    from test_harness import _add_args as _detect_args
    _detect_args(p_detect)
    _attach_video_completer(p_detect)

    # ── extract ───────────────────────────────────────────────────────────────
    p_extract = sub.add_parser("extract", help="Extract template crops (GUI)")
    from tools.extract_templates import _add_args as _extract_args
    _extract_args(p_extract)
    _attach_video_completer(p_extract)

    # ── assets ────────────────────────────────────────────────────────────────
    p_assets = sub.add_parser("assets", help="Inspect recorded asset crops")
    assets_sub = p_assets.add_subparsers(dest="cmd", metavar="action")
    assets_sub.required = True

    from tools.assets import ASSET_TYPE_TO_DIR
    type_choices = list(ASSET_TYPE_TO_DIR.keys())

    p_stats = assets_sub.add_parser("stats", help="Print coverage statistics")
    p_stats.add_argument("type", nargs="?", choices=type_choices, help="Asset type (omit for all)")

    p_browse = assets_sub.add_parser("browse", help="Open thumbnail grid browser")
    p_browse.add_argument("type", nargs="?", choices=type_choices, help="Asset type (omit for all)")

    # ── completion + parse ────────────────────────────────────────────────────
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Resolve BU aliases for any command that takes a video argument
    if hasattr(args, "video"):
        args.video = str(resolve_video(args.video))

    # ── dispatch ──────────────────────────────────────────────────────────────
    if args.command == "videos":
        cmd_videos()

    elif args.command == "download":
        from gameplay_sources.downloader import run
        run(args)

    elif args.command == "detect":
        from test_harness import run
        run(args)

    elif args.command == "extract":
        from tools.extract_templates import run
        run(args)

    elif args.command == "assets":
        from tools.assets import run
        run(args)


if __name__ == "__main__":
    main()
