"""Small advisory ownership locks for local capture tools."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path


class OwnershipConflict(ValueError):
    """Another live invocation owns this output root."""


class OwnershipLock:
    """Hold a per-output-root OS lock and publish identifying metadata."""

    def __init__(self, root: Path, role: str, identity: dict):
        self.root = Path(root).resolve()
        self.path = self.root / f".{role}.owner.json"
        self.lock_path = self.root / f".{role}.lock"
        self.stream = None
        self.metadata_guard = threading.Lock()
        self.token = uuid.uuid4().hex
        self.identity = identity

    def acquire(self):
        self.root.mkdir(parents=True, exist_ok=True)
        self.stream = self.lock_path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.stream.seek(0)
                if not self.lock_path.stat().st_size:
                    self.stream.write(b" "); self.stream.flush()
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            try:
                details = self.path.read_text(encoding="utf-8")
            except OSError:
                details = "owner metadata unavailable"
            self.stream.close(); self.stream = None
            raise OwnershipConflict(f"output root is owned by another {self.path.name}: {details}") from exc
        record = {"pid": os.getpid(), "token": self.token, "role": self.path.name,
                  "started_monotonic": time.monotonic(), "identity": self.identity}
        try:
            self._write_record(record)
        except BaseException:
            self.stream.close(); self.stream = None
            raise
        return self

    def _write_record(self, record):
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as metadata:
                json.dump(record, metadata, sort_keys=True)
                metadata.write("\n")
                metadata.flush(); os.fsync(metadata.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)

    def update(self, **fields):
        with self.metadata_guard:
            if self.stream is None:
                raise RuntimeError("ownership lock is not held")
            record = json.loads(self.path.read_text(encoding="utf-8"))
            if record.get("token") != self.token:
                raise RuntimeError("ownership metadata changed while lock was held")
            record.update(fields)
            self._write_record(record)

    def close(self):
        if self.stream is None:
            return
        stream = self.stream
        try:
            record = json.loads(self.path.read_text(encoding="utf-8"))
            if record.get("pid") == os.getpid() and record.get("token") == self.token:
                self.path.unlink()
        except (OSError, ValueError):
            pass
        finally:
            self.stream = None
            stream.close()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.close()


def active_owner(root: Path, role: str):
    """Return metadata only when the corresponding OS lock is held."""
    root = Path(root).resolve()
    lock_path = root / f".{role}.lock"
    metadata_path = root / f".{role}.owner.json"
    if not lock_path.exists():
        return None
    with lock_path.open("a+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                if not lock_path.stat().st_size:
                    stream.write(b" "); stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            return None
        except (OSError, BlockingIOError):
            try:
                return json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {"metadata": "unavailable"}


def process_matches(pid: int, expected_args) -> bool:
    """Confirm the recorded PID still has the expected contiguous argv tokens."""
    if (type(pid) is not int or pid < 1 or not isinstance(expected_args, (list, tuple))
            or not expected_args or any(not isinstance(token, str) for token in expected_args)):
        return False
    if os.name == "nt":
        shell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
        if shell is None:
            return False
        script = (f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}'; "
                  "if ($p) { [Console]::Write($p.CommandLine) }")
        try:
            result = subprocess.run([shell, "-NoProfile", "-NonInteractive", "-Command", script],
                                    capture_output=True, text=True, timeout=5, check=True)
        except (OSError, subprocess.SubprocessError):
            return False
        command_line = result.stdout
    else:
        proc_cmdline = Path(f"/proc/{pid}/cmdline")
        try:
            if proc_cmdline.exists():
                command_line = proc_cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
            else:
                result = subprocess.run(["ps", "-p", str(pid), "-o", "command="],
                                        capture_output=True, text=True, timeout=5, check=True)
                command_line = result.stdout
        except (OSError, subprocess.SubprocessError):
            return False
    try:
        tokens = shlex.split(command_line, posix=os.name != "nt")
    except ValueError:
        return False
    # The interpreter executable is argv[0]. Require the expected module/script
    # entrypoint immediately after it, rather than accepting a matching substring
    # buried in an unrelated process's arguments.
    return tokens[1:1 + len(expected_args)] == list(expected_args)
