"""Telemetry persistence: append-only JSON Lines, one file per assignment.

Mirrors ``ammu_review.app.store.SessionStore``'s configuration pattern
(a base directory read from an environment variable, never hardcoded) and
its one-file-per-assignment convention, so a pilot student's whole journey
is one file, readable top to bottom in emission order.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .models import TelemetryEvent

DEFAULT_TELEMETRY_DIR = Path(__file__).resolve().parents[3] / "data" / "telemetry"


class TelemetryStore:
    """Appends TelemetryEvent rows to ``<base_dir>/<assignment_id>.jsonl``."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(os.getenv("AMMU_TELEMETRY_DIR", str(DEFAULT_TELEMETRY_DIR)))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, assignment_id: str) -> Path:
        return self.base_dir / f"{assignment_id}.jsonl"

    def append(self, event: TelemetryEvent) -> None:
        with self._path(event.assignment_id).open("a") as f:
            f.write(event.model_dump_json())
            f.write("\n")

    def read_events(self, assignment_id: str) -> list[TelemetryEvent]:
        path = self._path(assignment_id)
        if not path.exists():
            return []
        return [
            TelemetryEvent.model_validate_json(line)
            for line in path.read_text().splitlines()
            if line.strip()
        ]
