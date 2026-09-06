"""TelemetryRecorder: the failure-safe API the application layer uses to
emit events.

Telemetry is observational, not authoritative -- a telemetry failure must
never break an assignment review (see .ai/TELEMETRY.md "Failure
isolation"). This covers BOTH failure points:

- Construction-time: if the default ``TelemetryStore()`` can't be built
  (e.g. its directory can't be created -- a bad ``AMMU_TELEMETRY_DIR``,
  a permissions error), that's caught here and ``self.store`` is left
  ``None`` rather than letting the exception propagate. Every
  ``orchestration.py`` function builds its recorder via the bare
  ``recorder or TelemetryRecorder()`` default, so a failure at this stage
  used to crash the caller (e.g. ``submit_draft``) even though it was
  telemetry, not the review, that failed.
- Write-time: any exception from an already-constructed store's
  ``append()`` is caught and logged, never raised, so
  ``orchestration.py`` can call ``record()`` unconditionally without
  wrapping every call in its own try/except.

An explicitly supplied ``store`` (e.g. a test double) is trusted as-is and
never wrapped -- only the default construction path needs this, since a
caller supplying its own store is responsible for it.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .models import EventType, TelemetryEvent
from .store import TelemetryStore

logger = logging.getLogger(__name__)


class TelemetryRecorder:
    def __init__(self, store: Optional[TelemetryStore] = None):
        if store is not None:
            self.store: Optional[TelemetryStore] = store
            return
        try:
            self.store = TelemetryStore()
        except Exception:
            logger.warning(
                "Could not initialise telemetry storage -- telemetry will be disabled for this session.",
                exc_info=True,
            )
            self.store = None

    def record(
        self,
        event_type: EventType,
        assignment_id: str,
        draft_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> None:
        if self.store is None:
            return
        event = TelemetryEvent(
            event_type=event_type,
            session_id=session_id or assignment_id,
            assignment_id=assignment_id,
            draft_id=draft_id,
            metadata=metadata or {},
        )
        try:
            self.store.append(event)
        except Exception:
            logger.warning(
                "Telemetry write failed for event %s (%s) -- continuing without it.",
                event.event_id,
                event_type,
                exc_info=True,
            )
