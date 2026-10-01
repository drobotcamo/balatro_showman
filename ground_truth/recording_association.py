"""Human-confirmed association of producer recording evidence with a run."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any

from run_bundle import BundleError, RunBundle


@dataclass(frozen=True)
class AssociationResult:
    status: str
    code: str
    diagnostic: str
    recording_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "code": self.code, "diagnostic": self.diagnostic,
                "recording_id": self.recording_id}


def associate_recording(
    bundle: RunBundle,
    run_id: str,
    *,
    confirmed: bool,
    marker: dict[str, Any] | None,
    observed_at_ns: int | None = None,
    max_age_ns: int | None = None,
    video_ref: str | None = None,
    confirmed_by: str = "human",
    interrupted: bool = False,
) -> AssociationResult:
    """Persist a recording marker only after an explicit human confirmation.

    The marker is producer evidence; this function deliberately does not claim
    that a video file exists. Provenance is additive, including after finalization.
    """
    if not isinstance(confirmed, bool):
        return AssociationResult("invalid", "confirmation_invalid", "confirmation must be boolean")
    if interrupted:
        return AssociationResult("interrupted", "coordination_interrupted", "coordination was interrupted")
    if not confirmed:
        return AssociationResult("declined", "confirmation_declined", "human confirmation was not granted")
    if marker is None:
        return AssociationResult("missing", "marker_missing", "recording marker is missing")
    if not isinstance(marker, dict):
        return AssociationResult("invalid", "marker_not_object", "recording marker is not an object")
    required = ("schema_version", "recording_id", "fps", "capture_timestamp_ns")
    if (marker.get("schema_version") != "producer/1.0.0"
            or not isinstance(marker.get("recording_id"), str)
            or not marker["recording_id"]
            or not isinstance(marker.get("fps"), (int, float))
            or isinstance(marker.get("fps"), bool)
            or marker["fps"] <= 0
            or not math.isfinite(marker["fps"])
            or not isinstance(marker.get("capture_timestamp_ns"), int)
            or isinstance(marker.get("capture_timestamp_ns"), bool)
            or marker["capture_timestamp_ns"] < 0):
        return AssociationResult("invalid", "marker_malformed", "recording marker is malformed")
    timestamp = marker["capture_timestamp_ns"]
    if max_age_ns is not None and (
        not isinstance(max_age_ns, int) or isinstance(max_age_ns, bool) or max_age_ns < 0
    ):
        return AssociationResult("invalid", "max_age_invalid", "maximum marker age is invalid", marker["recording_id"])
    if observed_at_ns is not None and (
        not isinstance(observed_at_ns, int) or isinstance(observed_at_ns, bool) or observed_at_ns < 0
    ):
        return AssociationResult("invalid", "observation_time_invalid", "observation time is invalid", marker["recording_id"])
    if max_age_ns is not None:
        if observed_at_ns is None or observed_at_ns < timestamp:
            return AssociationResult("stale", "marker_age_unknown", "marker age could not be verified", marker["recording_id"])
        if observed_at_ns - timestamp > max_age_ns:
            return AssociationResult("stale", "marker_stale", "recording marker is stale", marker["recording_id"])
    values = {
        "recording.association_status": "confirmed",
        "recording.recording_id": marker["recording_id"],
        "recording.marker_schema_version": marker["schema_version"],
        "recording.fps": marker["fps"],
        "recording.capture_timestamp_ns": timestamp,
        "recording.confirmed_by": confirmed_by,
        "recording.marker_json": json.dumps(marker, sort_keys=True, separators=(",", ":")),
    }
    if video_ref is not None:
        values["recording.video_ref"] = video_ref
    try:
        bundle.add_provenance(run_id, values)
    except BundleError:
        return AssociationResult("interrupted", "run_unavailable", "run disappeared during association", marker["recording_id"])
    return AssociationResult("confirmed", "association_confirmed", "recording marker associated", marker["recording_id"])


def confirm_interactive(prompt, notify, *, required: bool = False) -> bool:
    """Notify an operator of recording policy, then accept only explicit yes."""
    policy = "required" if required else "optional"
    notify(f"OBS recording is {policy}. OBS recording marker found. Confirm association? [y/N]")
    try:
        return prompt("y/N: ").strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        return False


def confirm_terminal(prompt=input) -> bool:
    """Terminal confirmation helper; EOF/interruption is never confirmation."""
    try:
        return prompt("OBS recording is required/optional. Confirm start? [y/N] ").strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        return False


def associate_after_confirmation(
    bundle: RunBundle,
    run_id: str,
    *,
    marker: dict[str, Any] | None,
    confirm,
    confirmed_by: str = "human",
    **kwargs: Any,
) -> AssociationResult:
    """Connect an operator confirmation callback to the association boundary."""
    try:
        confirmed = confirm() is True
    except (EOFError, KeyboardInterrupt):
        return associate_recording(
            bundle,
            run_id,
            confirmed=False,
            marker=marker,
            confirmed_by=confirmed_by,
            interrupted=True,
            **kwargs,
        )
    return associate_recording(
        bundle,
        run_id,
        confirmed=confirmed,
        marker=marker,
        confirmed_by=confirmed_by,
        **kwargs,
    )
