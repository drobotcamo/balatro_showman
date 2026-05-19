"""
Download YouTube gameplay footage for use as training data.

Saves to gameplay_sources/gameplay_footage/ at 1080p (falls back to best available).

Usage:
    python gameplay_sources/downloader.py <URL> [<URL> ...]

Examples:
    python gameplay_sources/downloader.py https://www.youtube.com/watch?v=...
    python gameplay_sources/downloader.py <url1> <url2> <url3>

Output files are named by video title, sanitized for the filesystem.
Skips downloads if the file already exists (yt-dlp --no-overwrites).
"""

import argparse
import sys
from pathlib import Path

import yt_dlp

OUTPUT_DIR = Path(__file__).parent / "gameplay_footage"


def build_ydl_opts():
    return {
        # Prefer 1080p mp4 video + best audio; fall back to best available up to 1080p
        "format": "bestvideo[height=1080][ext=mp4]+bestaudio/bestvideo[height<=1080][ext=mp4]+bestaudio/best[height<=1080]",
        "outtmpl": str(OUTPUT_DIR / "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
        "no_overwrites": True,
        "noplaylist": True,          # single video only, ignore playlist context
        "progress_hooks": [_progress_hook],
    }


def _progress_hook(d):
    if d["status"] == "downloading":
        pct = d.get("_percent_str", "?%").strip()
        speed = d.get("_speed_str", "?").strip()
        eta = d.get("_eta_str", "?").strip()
        print(f"\r  {pct}  speed: {speed}  eta: {eta}    ", end="", flush=True)
    elif d["status"] == "finished":
        print(f"\r  Done: {d['filename']}")


def download(urls):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    opts = build_ydl_opts()

    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            print(f"\nFetching info: {url}")
            info = ydl.extract_info(url, download=False)
            print(f"  Title:    {info.get('title')}")
            print(f"  Duration: {info.get('duration', 0) // 60}m {info.get('duration', 0) % 60}s")
            print(f"  Downloading...")
            ydl.download([url])


def main():
    parser = argparse.ArgumentParser(description="Download YouTube gameplay footage at 1080p")
    parser.add_argument("urls", nargs="+", help="YouTube URLs to download")
    args = parser.parse_args()
    download(args.urls)


if __name__ == "__main__":
    main()
