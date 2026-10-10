"""Local video/oracle debugging viewer. Sources are never modified."""

import argparse
import bisect
import hashlib
import json
import math
import os
import random
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from run_bundle.compatibility import read_oracle_run
from ground_truth.process_ownership import (OwnershipConflict, OwnershipLock, active_owner,
                                           process_matches)

ASSET = Path(__file__).with_name("qa_viewer.html")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def paths_overlap(left, right):
    left, right = Path(left).resolve(), Path(right).resolve()
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def probe(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=codec_name,width,height,avg_frame_rate,r_frame_rate,start_time:format=duration,start_time",
        "-of", "json", str(path),
    ], check=True, capture_output=True, text=True, timeout=60)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    data["codec_name"] = stream.get("codec_name")
    numerator, denominator = map(float, stream["avg_frame_rate"].split("/"))
    data["fps"] = numerator / denominator
    data["duration"] = float(data["format"]["duration"])
    if not all(math.isfinite(data[key]) and data[key] > 0 for key in ("fps", "duration")):
        raise ValueError("video duration and FPS must be finite and positive")
    packets = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_packets",
        "-show_entries", "packet=pts_time", "-of", "json", str(path),
    ], check=True, capture_output=True, text=True, timeout=120)
    recorded = json.loads(packets.stdout).get("packets")
    if not isinstance(recorded, list) or not recorded:
        raise ValueError("video contains no packets with presentation timestamps")
    timestamps = []
    for packet in recorded:
        raw = packet.get("pts_time") if isinstance(packet, dict) else None
        if raw is None:
            raise ValueError("video packet lacks a presentation timestamp")
        try:
            timestamp = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("video packet has an invalid presentation timestamp") from exc
        if not math.isfinite(timestamp):
            raise ValueError("video has non-finite presentation timestamps")
        timestamps.append(timestamp)
    timestamps.sort()
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("video has duplicate presentation timestamps")
    period = 1 / data["fps"]
    data["frame_count"] = len(timestamps)
    data["presentation_origin"] = timestamps[0]
    data["frame_timestamps"] = [timestamp - timestamps[0] for timestamp in timestamps]
    data["constant_fps"] = all(abs((right - left) - period) <= period * 0.05
                               for left, right in zip(timestamps, timestamps[1:]))
    return data


def run_ffmpeg(arguments):
    result = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-n", *arguments],
                            capture_output=True, text=True, timeout=600)
    if result.returncode:
        raise ValueError("ffmpeg failed: " + result.stderr[-2000:])


class Review:
    def __init__(self, video, runs, export_root, seed=None, start_ns=None, timing_evidence=None):
        self.video = Path(video).resolve(strict=True)
        self.export_root = Path(export_root).resolve()
        self.seed = seed or secrets.token_hex(8)
        self.rng = random.Random(self.seed)
        self.draw = 0
        self.startup_timings = {}
        if start_ns is not None and (type(start_ns) is not int or start_ns < 0 or not timing_evidence):
            raise ValueError("an override timestamp requires nonnegative integer ns and timing evidence")
        source_load_started = time.perf_counter()
        self.sources = []
        self.source_bytes = []
        for directory in runs:
            root = Path(directory).resolve(strict=True)
            record = read_oracle_run(root)
            json.dumps(record, allow_nan=False)
            if record["classification"] == "malformed" or not record["steps"]:
                raise ValueError(f"cannot review source {root}: {record['diagnostics']}")
            frozen = {name: (root / name).read_bytes() for name in ("session.json", "steps.ndjson")}
            if any(hashlib.sha256(data).hexdigest() != record["source"]["files"][name]["sha256"]
                   for name, data in frozen.items()):
                raise ValueError("oracle source changed while loading")
            if (json.loads(frozen["session.json"]) != record["session"] or
                    [json.loads(line) for line in frozen["steps.ndjson"].splitlines()] != record["steps"]):
                raise ValueError("oracle payload and hashed bytes disagree")
            # Restrict output to a separate tree: never beneath a source directory
            # or an ancestor containing source files or the original video.
            if paths_overlap(self.export_root, root):
                raise ValueError("export root overlaps an oracle source")
            self.sources.append(record)
            self.source_bytes.append(frozen)
        if not self.sources or len({r["run_id"] for r in self.sources}) != len(self.sources):
            raise ValueError("sources must be nonempty and have distinct run IDs")
        self.startup_timings["oracle_source_validation_s"] = time.perf_counter() - source_load_started
        if paths_overlap(self.video, self.export_root):
            raise ValueError("export root overlaps the source video")
        repository = Path(__file__).resolve().parent.parent
        if self.export_root.is_relative_to(repository):
            raise ValueError("generated exports must be outside the repository")
        if not self.export_root.parent.is_dir():
            raise ValueError("export parent must already exist")
        stage = time.perf_counter()
        self.video_hash = digest(self.video)
        self.startup_timings["video_hash_s"] = time.perf_counter() - stage
        stage = time.perf_counter()
        self.video_probe = probe(self.video)
        self.startup_timings["source_packet_probe_s"] = time.perf_counter() - stage
        if self.video_probe.get("codec_name") != "h264":
            raise ValueError("eligibility frame mapping currently supports H.264 video only")
        if not self.video_probe.get("constant_fps"):
            raise ValueError("eligibility review requires constant-FPS video")
        self.times = []
        self.timing = []
        for source in self.sources:
            marker = source["session"].get("recording") or {}
            original_ns = marker.get("capture_timestamp_ns") if isinstance(marker, dict) else None
            basis = start_ns if start_ns is not None else original_ns
            if type(basis) is not int:
                basis = None
            timing = {"original_marker": marker, "interpreted_start_ns": basis,
                      "evidence": timing_evidence if start_ns is not None else "source recording marker",
                      "alignment_status": "unverified", "diagnostics": []}
            if not marker:
                timing["diagnostics"].append("Original recording marker missing; no marker is copied into this source.")
            values = []
            for step in source["steps"]:
                timestamp = step.get("capture_timestamp_ns")
                if timestamp is None:
                    meta = step.get("meta")
                    timestamp = meta.get("capture_timestamp_ns") if isinstance(meta, dict) else None
                seconds = (timestamp - basis) / 1e9 if type(timestamp) is int and basis is not None else None
                if seconds is not None and not 0 <= seconds <= self.video_probe["duration"]:
                    seconds = None
                values.append(seconds)
            if any(t is None for t in values):
                timing["diagnostics"].append("Some timestamps are missing or outside video duration; those actions cannot seek.")
            self.times.append(values)
            self.timing.append(timing)
        self.media = None
        self.media_hash = None
        self.media_probe = None
        self.exports = {}
        self.selections = {}

    def prepare_media(self):
        """Reuse only a hash-verified derivative; never replace cached files."""
        cache = self.export_root / ".media"
        if cache.resolve() != cache:
            raise ValueError("browser cache must not redirect outside its export root")
        cache.mkdir(parents=True, exist_ok=True)
        destination = cache / (self.video_hash + ".mp4")
        metadata = destination.with_suffix(".json")
        stage = time.perf_counter()
        if destination.exists() or metadata.exists():
            if not destination.is_file() or not metadata.is_file():
                raise ValueError("incomplete browser cache; preserve it and choose a fresh export root")
            cached = json.loads(metadata.read_text())
            if cached.get("source_sha256") != self.video_hash or cached.get("media_sha256") != digest(destination):
                raise ValueError("browser cache hashes disagree; preserve it and choose a fresh export root")
            self.startup_timings["verified_cache_check_s"] = time.perf_counter() - stage
        else:
            remux_started = time.perf_counter()
            run_ffmpeg(["-i", str(self.video), "-map", "0:v:0", "-c:v", "copy", "-an",
                        "-movflags", "+faststart", str(destination)])
            self.startup_timings["cache_miss_remux_s"] = time.perf_counter() - remux_started
        stage = time.perf_counter()
        if digest(self.video) != self.video_hash:
            raise ValueError("source video changed while preparing browser media")
        self.startup_timings["source_recheck_hash_s"] = time.perf_counter() - stage
        stage = time.perf_counter()
        self.media_probe = probe(destination)
        self.startup_timings["remux_packet_probe_s"] = time.perf_counter() - stage
        # Oracle time is relative to video start. Reject remuxes that materially
        # change duration or leave a shifted presentation origin.
        origin = float(self.media_probe["streams"][0].get("start_time", 0))
        if abs(origin) > 1 / self.video_probe["fps"] or abs(self.media_probe["duration"] - self.video_probe["duration"]) > 0.1:
            raise ValueError("remux timeline differs from source; inspect media before using candidate times")
        source_times = self.video_probe["frame_timestamps"]
        media_times = self.media_probe["frame_timestamps"]
        if len(source_times) != len(media_times):
            raise ValueError("browser remux frame count differs from source; frame review is unavailable")
        maximum_frame_delta = max((abs(source - media) for source, media in zip(source_times, media_times)), default=0)
        if maximum_frame_delta > 0.5 / self.video_probe["fps"]:
            raise ValueError("browser remux frame timestamps do not map one-to-one to source frames")
        self.frame_mapping = {"status": "one_to_one_timestamps_confirmed", "frame_count": len(source_times),
                              "maximum_timestamp_delta_seconds": maximum_frame_delta}
        stage = time.perf_counter()
        self.media, self.media_hash = destination, digest(destination)
        self.startup_timings["prepared_media_hash_s"] = time.perf_counter() - stage
        if not metadata.exists():
            with metadata.open("x", encoding="utf-8") as stream:
                json.dump({"source_sha256": self.video_hash, "media_sha256": self.media_hash,
                           "probe": self.media_probe}, stream, allow_nan=False)

    def window(self, source=0, start=0, count=10, randomize=False):
        if type(count) is not int or not 1 <= count <= 200:
            raise ValueError("step count must be an integer from 1 to 200")
        if randomize:
            # Catalog order is stable by source ID; preserve caller order for Next.
            pool = [(i, j) for i in sorted(range(len(self.sources)), key=lambda i: self.sources[i]["run_id"])
                    for j in range(max(1, len(self.sources[i]["steps"]) - count + 1))]
            source, start = self.rng.choice(pool)
            self.draw += 1
        if type(source) is not int or not 0 <= source < len(self.sources):
            raise ValueError("invalid source index")
        original = self.sources[source]
        if type(start) is not int or not 0 <= start < len(original["steps"]):
            raise ValueError("invalid start index")
        stop = min(start + count, len(original["steps"]))
        rows = [{"index": index, "source_line": index + 1, "seconds": self.times[source][index],
                 "original": original["steps"][index]} for index in range(start, stop)]
        times = [row["seconds"] for row in rows]
        valid = all(t is not None for t in times) and all(a <= b for a, b in zip(times, times[1:]))
        following = self.times[source][stop] if stop < len(original["steps"]) else None
        beginning = max(0, times[0] - 0.75) if valid else None
        ending = min(self.video_probe["duration"], max(times[-1], following or times[-1]) + 0.75) if valid else None
        if stop < len(original["steps"]):
            next_window = {"source": source, "start": stop}
        elif source + 1 < len(self.sources):
            next_window = {"source": source + 1, "start": 0}
        else:
            next_window = None
        selection_id = secrets.token_urlsafe(12)
        self.selections[selection_id] = {"source": source, "start": start, "count": count, "draw": self.draw}
        return {"selection_id": selection_id, "source": source, "source_id": original["run_id"], "start": start, "stop": stop,
                "count": count, "rows": rows, "next": next_window, "clip_start": beginning,
                "clip_end": ending, "timing": self.timing[source], "diagnostics": original["diagnostics"],
                "seed": self.seed, "draw": self.draw, "sampling": "uniform-source-local-windows/v1"}

    def catalog(self, include_frame_timestamps=True):
        video_probe = dict(self.video_probe)
        if not include_frame_timestamps:
            video_probe.pop("frame_timestamps", None)
        return {"video": str(self.video), "video_sha256": self.video_hash, "probe": video_probe,
                "media_presentation_origin": self.media_probe.get("presentation_origin", 0) if self.media_probe else 0,
                "frame_mapping": self.frame_mapping if self.media_probe else {"status": "not_prepared"},
                "media": "/media", "seed": self.seed, "export_root": str(self.export_root),
                "sources": [{"id": source["run_id"], "steps": len(source["steps"]),
                             "source": source["source"], "timing": self.timing[i]}
                            for i, source in enumerate(self.sources)]}

    def export(self, source, start, count, notes, selection_id=None):
        if not isinstance(notes, str) or len(notes) > 100000:
            raise ValueError("notes must be text, maximum 100,000 characters")
        window = self.window(source, start, count)
        if selection_id is not None:
            selection = self.selections.get(selection_id)
            if selection is None or any(selection[key] != value for key, value in
                                        (("source", source), ("start", start), ("count", count))):
                raise ValueError("review selection does not match the displayed window")
            window["selection_id"] = selection_id
            window["draw"] = selection["draw"]
        if window["clip_start"] is None or window["clip_end"] <= window["clip_start"]:
            raise ValueError("window lacks ordered in-range timestamps; aligned clip export is unavailable")
        if self.media is None or digest(self.media) != self.media_hash or digest(self.video) != self.video_hash:
            raise ValueError("video evidence or browser derivative changed; reload viewer")
        self.check_sources()
        if self.export_root.resolve() != self.export_root:
            raise ValueError("export root was redirected; reload viewer")
        # UUID suffix avoids collisions; failed packages stay marked incomplete.
        folder = self.export_root / (datetime.now(timezone.utc).strftime("review-%Y%m%dT%H%M%SZ-") + secrets.token_hex(4))
        folder.mkdir()
        (folder / "INCOMPLETE.txt").write_text("Debug export did not finish. Source evidence is untouched.\n")
        clip = folder / "clip.mp4"
        arguments = ["-ss", str(window["clip_start"]), "-i", str(self.media), "-t",
                     str(window["clip_end"] - window["clip_start"]), "-map", "0:v:0", "-an",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-movflags", "+faststart", str(clip)]
        run_ffmpeg(arguments)
        # Verify again after extraction, and export the exact frozen source bytes
        # represented by the displayed payloads, never a later read of the file.
        self.check_sources()
        if digest(self.media) != self.media_hash or digest(self.video) != self.video_hash:
            raise ValueError("video changed during extraction; export remains incomplete")
        lines = self.source_bytes[source]["steps.ndjson"].splitlines(keepends=True)
        (folder / "actions.ndjson").write_bytes(b"".join(lines[window["start"]:window["stop"]]))
        (folder / "notes.txt").write_text(notes, encoding="utf-8")
        packet = {"schema_version": "oracle-video-qa-debug/1", "status": "unscored",
                   "window": window, "catalog": self.catalog(include_frame_timestamps=False), "notes": notes,
                  "clip_probe": probe(clip), "extraction": {"mode": "reencoded-video-only",
                  "timeline_note": "Clip seeks use requested clip_start as origin; frame quantization and rendered correspondence are unverified.",
                  "command": ["ffmpeg", "-nostdin", "-v", "error", "-n", *arguments],
                  "ffmpeg_version": subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True,
                                                   check=True).stdout.splitlines()[0]},
                  "files": {name: digest(folder / name) for name in ("clip.mp4", "actions.ndjson", "notes.txt")}}
        html = ASSET.read_text(encoding="utf-8").replace("<!--PACKET-->",
            '<script id="packet" type="application/json">' + json.dumps(packet, ensure_ascii=True,
                                                                          allow_nan=False).replace("<", "\\u003c") + '</script>')
        (folder / "index.html").write_text(html, encoding="utf-8")
        packet["files"]["index.html"] = digest(folder / "index.html")
        (folder / "manifest.json").write_text(json.dumps(packet, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        (folder / "INCOMPLETE.txt").unlink()
        self.exports[folder.name] = folder
        return {"folder": str(folder), "steps": len(window["rows"]), "manifest": str(folder / "manifest.json"),
                "url": f"/export/{folder.name}/index.html"}

    def check_sources(self):
        for original in self.sources:
            for name, metadata in original["source"]["files"].items():
                if digest(Path(original["source"]["directory"]) / name) != metadata["sha256"]:
                    raise ValueError("oracle source changed; reload viewer")

    def save_eligibility(self, data):
        """Preserve one human review observation outside the repository; never score it."""
        source = data.get("source")
        index = data.get("index")
        if type(source) is not int or not 0 <= source < len(self.sources):
            raise ValueError("invalid source index")
        if type(index) is not int or not 0 <= index < len(self.sources[source]["steps"]):
            raise ValueError("invalid step index")
        selection = self.selections.get(data.get("selection_id"))
        if (selection is None or selection["source"] != source or
                not selection["start"] <= index < min(selection["start"] + selection["count"],
                                                        len(self.sources[source]["steps"]))):
            raise ValueError("step is not part of a server-issued review window")
        stage = data.get("stage")
        if stage not in ("start", "small_blind_select", "small_blind_play", "cash_out", "first_shop"):
            raise ValueError("invalid stage")
        state = data.get("alignment")
        if state not in ("confirmed", "unverified", "failed", "disputed"):
            raise ValueError("invalid alignment disposition")
        frame = data.get("frame")
        if type(frame) is not int or frame < 0:
            raise ValueError("frame must be a nonnegative integer")
        if frame >= self.video_probe.get("frame_count", math.ceil(self.video_probe["duration"] * self.video_probe["fps"])):
            raise ValueError("frame is outside the video duration")
        offset = data.get("offset_frames")
        if offset is not None and (type(offset) is not int or abs(offset) > 100000):
            raise ValueError("invalid measured offset")
        if state == "confirmed" and (offset is None or abs(offset) > 3 or self.times[source][index] is None):
            raise ValueError("confirmation requires an in-range candidate and measured offset within ±3 frames")
        fields = ("evidence", "visual_observation", "missingness", "reviewer", "registry_audit")
        for field in fields:
            if not isinstance(data.get(field), str) or len(data[field]) > 10000:
                raise ValueError(f"{field} must be text of at most 10000 characters")
        if not data["evidence"].strip() or not data["reviewer"].strip():
            raise ValueError("reviewer and rendered-correspondence evidence are required")
        if self.export_root.resolve() != self.export_root:
            raise ValueError("export root was redirected")
        self.check_sources()
        if digest(self.video) != self.video_hash:
            raise ValueError("source video changed; reload viewer")
        folder = self.export_root / "eligibility-reviews"
        folder.mkdir(parents=True, exist_ok=True)
        if folder.resolve() != folder:
            raise ValueError("review folder was redirected")
        row = self.sources[source]["steps"][index]
        packet = {"schema": "first-slice-eligibility-review/1", "protocol": "FIRST_SLICE_PROTOCOL_V2",
                  "status": "unscored", "video_sha256": self.video_hash, "video": str(self.video),
                  "source_run_id": self.sources[source]["run_id"],
                  "oracle_files": self.sources[source]["source"]["files"],
                  "step_id": row.get("step_id"), "step_index": index,
                  "candidate_seconds": self.times[source][index], "fps": self.video_probe["fps"],
                  "marker": self.timing[source]["original_marker"],
                  "timing_evidence": self.timing[source]["evidence"],
                  "frame": frame, "frame_seconds": data.get("frame_seconds"),
                  "stage": stage, "alignment": state, "offset_frames": offset,
                  **{key: data[key] for key in fields}}
        if type(packet["frame_seconds"]) not in (int, float) or not math.isfinite(packet["frame_seconds"]) or not 0 <= packet["frame_seconds"] <= self.video_probe["duration"]:
            raise ValueError("invalid video time")
        frame_timestamps = self.video_probe["frame_timestamps"]
        expected_seconds = frame_timestamps[frame]
        if abs(packet["frame_seconds"] - expected_seconds) > 0.5 / self.video_probe["fps"]:
            raise ValueError("frame index and presented video time disagree with decoded frame timestamps")
        if state == "confirmed":
            candidate_index = bisect.bisect_left(frame_timestamps, packet["candidate_seconds"] or 0)
            if candidate_index and (candidate_index == len(frame_timestamps) or
                    abs(frame_timestamps[candidate_index - 1] - (packet["candidate_seconds"] or 0)) <
                    abs(frame_timestamps[candidate_index] - (packet["candidate_seconds"] or 0))):
                candidate_index -= 1
            expected_offset = frame - candidate_index
            if offset != expected_offset:
                raise ValueError("confirmed frame offset disagrees with the candidate and presented frame")
        packet["frame_index_basis"] = "zero-based presentation-frame index; timestamp checked against decoded constant-FPS cadence"
        destination = folder / (datetime.now(timezone.utc).strftime("review-%Y%m%dT%H%M%SZ-") + secrets.token_hex(8) + ".json")
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(packet, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        return {"file": str(destination), "status": "unscored"}


def byte_range(header, size):
    if not header:
        return 0, size - 1, False
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
    if not match or not any(match.groups()):
        raise ValueError("unsupported range")
    first, last = match.groups()
    if first:
        start = int(first)
        end = min(int(last), size - 1) if last else size - 1
    else:
        length = int(last)
        if length <= 0:
            raise ValueError("invalid suffix range")
        start, end = max(0, size - length), size - 1
    if start > end or start >= size:
        raise ValueError("unsatisfiable range")
    return start, end, True


def make_server(review, port=0, steps=10):
    token = secrets.token_urlsafe(24)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, *args):
            pass

        def valid_host(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

        def send(self, code, data, kind="application/json"):
            body = json.dumps(data, allow_nan=False).encode() if kind == "application/json" else data
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {"error": "invalid host"})
            route = urlsplit(self.path).path
            if route == "/":
                return self.send(200, ASSET.read_bytes(), "text/html; charset=utf-8")
            if route == "/api/init":
                return self.send(200, {"token": token, "catalog": review.catalog(), "window": review.window(count=steps)})
            path = review.media if route == "/media" else None
            if route.startswith("/export/"):
                pieces = route.split("/")
                folder = review.exports.get(pieces[2]) if len(pieces) == 4 else None
                if folder is not None and pieces[3] in ("index.html", "clip.mp4"):
                    path = folder / pieces[3]
                    if pieces[3] == "index.html":
                        return self.send(200, path.read_bytes(), "text/html; charset=utf-8")
            if path is None:
                return self.send(404, {"error": "not found"})
            size = path.stat().st_size
            try:
                start, end, partial = byte_range(self.headers.get("Range"), size)
            except ValueError:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                return self.end_headers()
            self.send_response(206 if partial else 200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if partial:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            if self.command == "HEAD":
                return
            try:
                with path.open("rb") as stream:
                    stream.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = stream.read(min(remaining, 1024 * 1024))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                pass

        def do_POST(self):
            origin = self.headers.get("Origin")
            if not self.valid_host() or origin not in (None, f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}") or self.headers.get("X-Review-Token") != token:
                return self.send(403, {"error": "invalid local request"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 200000:
                    raise ValueError("request size out of bounds")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("request must be a JSON object")
                with lock:
                    if self.path == "/api/window":
                        result = review.window(data.get("source", 0), data.get("start", 0),
                                               data.get("count", 10), data.get("random", False))
                    elif self.path == "/api/export":
                        result = review.export(data["source"], data["start"], data["count"], data.get("notes", ""),
                                               data["selection_id"])
                    elif self.path == "/api/eligibility":
                        result = review.save_eligibility(data)
                    else:
                        return self.send(404, {"error": "not found"})
                return self.send(200, result)
            except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
                return self.send(400, {"error": str(exc)})

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--run", required=True, action="append", type=Path,
                        help="ordered source directories for this explicitly selected video")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--seed")
    parser.add_argument("--recording-start-ns", type=int)
    parser.add_argument("--timing-evidence", help="required for diagnostic shared-marker override")
    parser.add_argument("--export-root", type=Path, default=Path("F:/OBS_RECORDINGS/qa_debug"))
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("ffmpeg and ffprobe must already be installed on PATH")
    identity = {
        "command": "ground_truth.qa_viewer", "video": str(args.video.resolve()),
        "command_args": ["-m", "ground_truth.qa_viewer"],
        "runs": [str(run.resolve()) for run in args.run],
        "export_root": str(args.export_root.resolve()), "steps": args.steps,
        "seed": args.seed,
    }
    ownership = OwnershipLock(args.export_root, "qa-viewer", identity)
    print("Checking viewer ownership and preparing media; HTTP readiness still unverified; "
          "deadline 120s.",
          file=sys.stderr, flush=True)
    stopped = threading.Event()
    def progress():
        elapsed = 0
        while not stopped.wait(15):
            elapsed += 15
            print(f"Viewer readiness still unverified after {elapsed}s; deadline 120s; pid={os.getpid()}; "
                  f"ownership/log path={args.export_root.resolve()}.", file=sys.stderr, flush=True)
    reporter = threading.Thread(target=progress, daemon=True)
    reporter.start()
    server = None
    server_thread = None
    try:
        ownership.acquire()
        print(f"Viewer preparation in progress; pid={os.getpid()} diagnostics=stderr.",
              file=sys.stderr, flush=True)
        stage = time.monotonic()
        review = Review(args.video, args.run, args.export_root, args.seed,
                        args.recording_start_ns, args.timing_evidence)
        print(f"Viewer source inspection/probe: {time.monotonic() - stage:.3f}s.",
              file=sys.stderr, flush=True)
        print("Viewer startup stages: " + json.dumps(review.startup_timings, sort_keys=True),
              file=sys.stderr, flush=True)
        stage = time.monotonic()
        review.window(count=args.steps)
        print("Preparing external browser media; original recording is unchanged.", flush=True)
        review.prepare_media()
        print(f"Viewer media preparation: {time.monotonic() - stage:.3f}s.",
              file=sys.stderr, flush=True)
        print("Viewer media stages: " + json.dumps(review.startup_timings, sort_keys=True),
              file=sys.stderr, flush=True)
        server = make_server(review, args.port, args.steps)
        url = f"http://127.0.0.1:{server.server_port}"
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url + "/", timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise ValueError("viewer HTTP readiness timed out after 120s")
        ownership.update(ready_url=url, ready_seed=review.seed)
    except OwnershipConflict as exc:
        stopped.set(); reporter.join()
        try:
            record = json.loads(ownership.path.read_text(encoding="utf-8"))
            ready_url = record.get("ready_url")
            if (record.get("identity") == identity and isinstance(record.get("pid"), int)
                    and isinstance(ready_url, str)
                    and process_matches(record["pid"], identity["command_args"])):
                with urllib.request.urlopen(ready_url + "/", timeout=1) as response:
                    current_owner = active_owner(args.export_root, "qa-viewer")
                    if (response.status == 200 and current_owner is not None
                            and current_owner.get("token") == record.get("token")):
                        print(json.dumps({"url": ready_url, "export_root": identity["export_root"],
                                          "seed": record.get("ready_seed", args.seed), "pid": record["pid"],
                                          "reused": True, "startup_ms": None}), flush=True)
                        print(f"Reusing healthy matching viewer: pid={record['pid']}; HTTP {ready_url}/; "
                              f"export_root={identity['export_root']}.", file=sys.stderr, flush=True)
                        return
        except (OSError, ValueError, urllib.error.URLError, TimeoutError):
            pass
        parser.error(f"viewer ownership conflict; existing process is mismatched or unhealthy: {exc}")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        stopped.set(); reporter.join()
        if server is not None and server_thread is not None:
            server.shutdown(); server.server_close()
        elif server is not None:
            server.server_close()
        ownership.close()
        parser.error(str(exc))
    except BaseException:
        stopped.set(); reporter.join()
        if server is not None and server_thread is not None:
            server.shutdown(); server.server_close()
        elif server is not None:
            server.server_close()
        ownership.close()
        raise
    stopped.set(); reporter.join()
    print(json.dumps({"url": url, "export_root": str(review.export_root), "seed": review.seed,
                      "pid": os.getpid(), "reused": False}), flush=True)
    print(f"Viewer ready: HTTP {url}/; pid={os.getpid()}; export_root={review.export_root}",
          file=sys.stderr, flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server_thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server_thread.join()
        server.server_close()
        ownership.close()


def launch_group():
    """Launch explicitly grouped videos from a UTF-8 JSON file or command line."""
    parser = argparse.ArgumentParser(description="Launch one local QA viewer per explicitly declared video/run group.")
    parser.add_argument("--config", type=Path, help="UTF-8 JSON configuration containing a viewers array")
    parser.add_argument("--video", action="append", type=Path, help="single video path (use --config for multiple videos)")
    parser.add_argument("--run", action="append", type=Path, help="ordered run directory for the single command-line video")
    parser.add_argument("--export-root", type=Path, help="base external export directory; each video gets a child")
    parser.add_argument("--seed", help="optional seed prefix for repeatable navigation")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--open", action="store_true", help="open every viewer in the default browser")
    args = parser.parse_args()
    try:
        if args.config:
            if args.video or args.run or args.export_root:
                raise ValueError("--config cannot be combined with command-line video/run/export arguments")
            config_path = args.config.resolve(strict=True)
            config = json.loads(config_path.read_text(encoding="utf-8"))
            viewers = config.get("viewers") if isinstance(config, dict) else None
            if not isinstance(viewers, list) or not viewers:
                raise ValueError("config must contain a nonempty viewers array")
            base = config_path.parent
            groups = []
            for item in viewers:
                if not isinstance(item, dict) or not item.get("video") or not item.get("runs"):
                    raise ValueError("each viewer requires video and a nonempty runs array")
                groups.append((Path(item["video"]), [Path(run) for run in item["runs"]], item.get("export_name")))
            if not config.get("export_root"):
                raise ValueError("config requires export_root")
            export_root = Path(config["export_root"])
            if not export_root.is_absolute():
                export_root = base / export_root
            export_root = export_root.resolve()
        else:
            if not args.video or not args.run or not args.export_root:
                raise ValueError("provide --config or --video/--run/--export-root")
            if len(args.video) != 1:
                raise ValueError("command-line launch accepts one --video; use --config to group multiple videos")
            groups = [(args.video[0], args.run, None)]
            export_root = args.export_root.resolve()
        if not export_root.parent.is_dir():
            raise ValueError("export root must be absolute or have an existing parent")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise ValueError("ffmpeg and ffprobe must already be installed on PATH")
        import sys
        import time
        repository = Path(__file__).resolve().parent.parent
        if export_root == repository or repository in export_root.parents or export_root in repository.parents:
            raise ValueError("launcher export root must remain outside the repository")
        names = [name or f"{ordinal:02d}-{re.sub(r'[^A-Za-z0-9._-]+', '-', Path(video).stem).strip('-')}"
                 for ordinal, (video, _, name) in enumerate(groups, 1)]
        if len(set(names)) != len(names) or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", name) for name in names):
            raise ValueError("export names must be unique, filesystem-safe single path components")
        resolved_groups = []
        for ordinal, (video, runs, _) in enumerate(groups, 1):
            name = names[ordinal - 1]
            resolved_video = (base / video if args.config and not video.is_absolute() else video).resolve(strict=True)
            resolved_runs = [(base / run if args.config and not run.is_absolute() else run).resolve(strict=True) for run in runs]
            if (paths_overlap(resolved_video, export_root) or
                    any(paths_overlap(export_root, root) for root in resolved_runs)):
                raise ValueError("export root overlaps source video or oracle evidence")
            resolved_groups.append((resolved_video, resolved_runs, name))
        children = []
        already_ready = []
        child_start_times = {}
        first_status_times = {}
        for ordinal, (video, resolved_runs, name) in enumerate(resolved_groups, 1):
            child_name = name
            child_export = export_root / child_name
            if (paths_overlap(video, child_export) or
                    any(paths_overlap(child_export, root) for root in resolved_runs)):
                raise ValueError("child export folder overlaps source video or oracle evidence")
            child_export.mkdir(parents=True, exist_ok=True)
            identity = {
                "command": "ground_truth.qa_viewer", "video": str(video),
                "command_args": ["-m", "ground_truth.qa_viewer"],
                "runs": [str(run) for run in resolved_runs],
                "export_root": str(child_export.resolve()), "steps": args.steps,
                "seed": f"{args.seed}-{ordinal}" if args.seed else None,
            }
            owner = active_owner(child_export, "qa-viewer")
            if owner is not None:
                ready_url = owner.get("ready_url")
                if owner.get("identity") != identity or not isinstance(ready_url, str):
                    raise ValueError(f"conflicting viewer owner for {child_name}: {owner}")
                if not process_matches(owner.get("pid"), identity["command_args"]):
                    raise ValueError(f"viewer owner PID/command mismatch for {child_name}: {owner}")
                reuse_started = time.monotonic()
                try:
                    with urllib.request.urlopen(ready_url + "/", timeout=1) as response:
                        if response.status != 200:
                            raise ValueError(f"matching viewer owner is not healthy for {child_name}")
                    current_owner = active_owner(child_export, "qa-viewer")
                    if (current_owner is None or current_owner.get("token") != owner.get("token")
                            or current_owner.get("pid") != owner.get("pid")):
                        raise ValueError(f"viewer ownership changed during health check for {child_name}")
                except (OSError, urllib.error.URLError, TimeoutError) as exc:
                    raise ValueError(f"matching viewer owner is not healthy for {child_name}: {exc}") from exc
                already_ready.append({"name": child_name, "url": ready_url,
                                      "export_root": identity["export_root"],
                                      "seed": owner.get("ready_seed", identity["seed"]),
                                      "pid": owner["pid"],
                                      "reused": True, "startup_ms": None,
                                      "reuse_check_ms": round((time.monotonic() - reuse_started) * 1000, 1)})
                print(f"Reusing healthy matching viewer {child_name}: pid={owner['pid']}; "
                      f"HTTP {ready_url}/; export_root={identity['export_root']}.",
                      file=sys.stderr, flush=True)
                continue
            command = [sys.executable, "-m", "ground_truth.qa_viewer", "--video", str(video),
                       "--export-root", str(child_export), "--steps", str(args.steps)]
            for run in resolved_runs:
                command.extend(("--run", str(run)))
            if args.seed:
                command.extend(("--seed", f"{args.seed}-{ordinal}"))
            if args.open:
                command.append("--open")
            log_base = export_root / (child_name + "-" + secrets.token_hex(4) + ".log")
            print(f"Starting viewer {ordinal}/{len(resolved_groups)} ({child_name}); "
                  f"readiness still unverified; deadline 120s; "
                  f"diagnostics: {log_base}.[out|err].txt",
                  file=sys.stderr, flush=True)
            stdout = log_base.with_suffix(log_base.suffix + ".out.txt").open("x", encoding="utf-8")
            stderr = log_base.with_suffix(log_base.suffix + ".err.txt").open("x", encoding="utf-8")
            try:
                child_started = time.monotonic()
                proc = subprocess.Popen(command, cwd=Path(__file__).resolve().parent.parent,
                                        stdout=stdout, stderr=stderr, text=True)
            except Exception:
                stdout.close()
                stderr.close()
                raise
            children.append((proc, stdout, stderr, child_name, log_base))
            child_start_times[proc.pid] = child_started
        deadline = time.monotonic() + 120
        last_progress = time.monotonic()
        if children:
            print("Viewers started; checking HTTP readiness (still unverified). "
                  "Owned PIDs/logs: " + "; ".join(
                      f"{name} pid={proc.pid} logs={log_base}.[out|err].txt"
                      for proc, _, _, name, log_base in children), file=sys.stderr, flush=True)
        else:
            print("All viewers are reused healthy matches; HTTP readiness verified.",
                  file=sys.stderr, flush=True)
        while time.monotonic() < deadline:
            failed = [child for child in children if child[0].poll() is not None]
            if failed:
                details = "; ".join(f"{name}: {err.with_suffix(err.suffix + '.err.txt').read_text(encoding='utf-8', errors='replace')}"
                                     for _, _, _, name, err in failed)
                raise ValueError("viewer startup failed: " + details)
            ready = list(already_ready)
            for proc, _, _, name, log_base in children:
                out = log_base.with_suffix(log_base.suffix + ".out.txt")
                text_out = out.read_text(encoding="utf-8", errors="replace") if out.exists() else ""
                err = log_base.with_suffix(log_base.suffix + ".err.txt")
                text_err = err.read_text(encoding="utf-8", errors="replace") if err.exists() else ""
                if "Checking viewer ownership and preparing media" in text_err:
                    first_status_times.setdefault(proc.pid, time.monotonic())
                for line in text_out.splitlines():
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if all(isinstance(record.get(key), str) for key in ("url", "export_root", "seed")):
                        if proc.poll() is not None:
                            continue
                        try:
                            with urllib.request.urlopen(record["url"] + "/", timeout=1) as response:
                                if response.status == 200:
                                    if proc.poll() is None:
                                        ready.append({"name": name, **record, "pid": proc.pid,
                                                      "reused": False,
                                                      "launch_to_first_status_observed_ms": (
                                                          round((first_status_times[proc.pid] -
                                                                 child_start_times[proc.pid]) * 1000, 1)
                                                          if proc.pid in first_status_times else None),
                                                      "startup_ms": round((time.monotonic() -
                                                                           child_start_times[proc.pid]) * 1000, 1)})
                                        break
                                    raise ValueError(f"{name} viewer exited during readiness probe")
                        except (OSError, urllib.error.URLError, TimeoutError):
                            continue
            if len(ready) == len(resolved_groups):
                if all(child[0].poll() is None for child in children):
                    print(json.dumps({"viewers": ready}, indent=2))
                    for child in children:
                        child[1].close()
                        child[2].close()
                    return
            now = time.monotonic()
            if now - last_progress >= 30:
                elapsed = int(now - (deadline - 120))
                print(f"Viewer readiness still unverified after {elapsed}s; "
                      f"deadline 120s; inspect the per-viewer logs above.",
                      file=sys.stderr, flush=True)
                last_progress = now
            time.sleep(0.25)
        raise ValueError("viewer startup timed out; inspect per-viewer .err.txt logs")
    except (ValueError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        for child in locals().get("children", []):
            proc = child[0]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            child[1].close()
            child[2].close()
        parser.error(str(exc))


if __name__ == "__main__":
    main()
