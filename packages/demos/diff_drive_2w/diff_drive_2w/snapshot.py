"""Atomic ROS2 telemetry snapshots for the Lappa desktop viewport."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


class SnapshotWriter:
    def __init__(self, package: str, interval: float = 0.1) -> None:
        self.package = package
        self.interval = max(0.05, interval)
        self.last_write = 0.0
        self.path = Path("/ws/src") / package / ".lappa_runtime" / "sim_snapshot.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, state: dict) -> None:
        now = time.monotonic()
        if now - self.last_write < self.interval:
            return
        self.last_write = now
        payload = {
            "source": "ros2",
            "package": self.package,
            "updated_at": time.time(),
            "state": state,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temporary, self.path)

