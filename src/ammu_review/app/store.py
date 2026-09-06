"""Session persistence: one JSON file per assignment session.

Flat files are deliberately the simplest thing that works at pilot scale (see
the Student Experience design proposal, sections 13/16) -- no database
engineering ahead of an actual need. The base directory is configurable via
the ``AMMU_SESSIONS_DIR`` environment variable, never hardcoded, matching the
pattern already used for model configuration in ``config.py``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .models import AssignmentSession

DEFAULT_SESSIONS_DIR = Path(__file__).resolve().parents[3] / "data" / "sessions"


class SessionStore:
    """Reads and writes AssignmentSession objects as JSON files on disk."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(os.getenv("AMMU_SESSIONS_DIR", str(DEFAULT_SESSIONS_DIR)))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, assignment_id: str) -> Path:
        return self.base_dir / f"{assignment_id}.json"

    def save(self, session: AssignmentSession) -> None:
        self._path(session.assignment.id).write_text(session.model_dump_json(indent=2))

    def load(self, assignment_id: str) -> AssignmentSession:
        path = self._path(assignment_id)
        if not path.exists():
            raise FileNotFoundError(f"No session found for assignment id '{assignment_id}'.")
        return AssignmentSession.model_validate_json(path.read_text())

    def exists(self, assignment_id: str) -> bool:
        return self._path(assignment_id).exists()

    def list_assignment_ids(self) -> list[str]:
        return sorted(p.stem for p in self.base_dir.glob("*.json"))
