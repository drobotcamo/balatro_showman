# PYTHON_ARGCOMPLETE_OK
"""
Balatro Showman — unified CLI entry point.

    python main.py videos                           list footage with BU aliases
    python main.py download <url> [url ...]         download YouTube footage
    python main.py extract  <video|BU#> [options]   label assets in footage (GUI)
    python main.py dataset  build [options]         build YOLO dataset from labeled sidecars
    python main.py train    [options]               train YOLOv8 on the built dataset
    python main.py detect   <video|BU#> [options]   run YOLO asset detection (--model, --asset-type)
    python main.py assets   stats  [type]           print asset coverage
    python main.py assets   browse [type]           open thumbnail grid browser

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
            "Video arguments accept BU aliases (BU1, BU2, ...) or full paths.\n"
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

    # ── extract ───────────────────────────────────────────────────────────────
    p_extract = sub.add_parser("extract", help="Label assets in footage (GUI, writes sidecar JSONs)")
    from tools.extract_templates import _add_args as _extract_args
    _extract_args(p_extract)
    _attach_video_completer(p_extract)

    # ── dataset ───────────────────────────────────────────────────────────────
    p_dataset = sub.add_parser("dataset", help="Manage YOLO training dataset")
    ds_sub = p_dataset.add_subparsers(dest="cmd", metavar="action")
    ds_sub.required = True

    p_build = ds_sub.add_parser("build", help="Build YOLO dataset from labeled sidecar JSONs")
    from tools.build_dataset import _add_args as _build_args
    _build_args(p_build)

    p_synth = ds_sub.add_parser("synthetic", help="Build synthetic dataset from wiki sprites")
    from tools.build_synthetic_dataset import _add_args as _synth_args
    _synth_args(p_synth)

    # ── train ─────────────────────────────────────────────────────────────────
    p_train = sub.add_parser("train", help="Train YOLOv8 on the built dataset")
    from tools.train import _add_args as _train_args
    _train_args(p_train)

    # ── detect ────────────────────────────────────────────────────────────────
    p_detect = sub.add_parser("detect", help="Run YOLO asset detection on footage")
    from test_harness import _add_args as _detect_args
    _detect_args(p_detect)
    _attach_video_completer(p_detect)

    # ── assets ────────────────────────────────────────────────────────────────
    p_assets = sub.add_parser("assets", help="Inspect labeled asset crops")
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

    elif args.command == "extract":
        from tools.extract_templates import run
        run(args)

    elif args.command == "dataset":
        if args.cmd == "build":
            from tools.build_dataset import run
            run(args)
        elif args.cmd == "synthetic":
            from tools.build_synthetic_dataset import run
            run(args)

    elif args.command == "train":
        from tools.train import run
        run(args)

    elif args.command == "detect":
        from test_harness import run
        run(args)

    elif args.command == "assets":
        from tools.assets import run
        run(args)


if __name__ == "__main__":
    main()
