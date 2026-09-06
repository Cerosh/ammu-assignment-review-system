"""TelemetryRecorder: the failure-safe API the application layer uses to
emit events.

Telemetry is observational, not authoritative -- a telemetry failure must
never break an assignment review (see .ai/TELEMETRY.md "Failure
isolation"). Any exception from the underlying store is caught and logged,
never raised, so ``orchestration.py`` can call ``record()`` unconditionally
without wrapping every call in its own try/except.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .models import EventType, TelemetryEvent
from .store import TelemetryStore

logger = logging.getLogger(__name__)


class TelemetryRecorder:
    def __init__(self, store: Optional[TelemetryStore] = None):
        self.store = store or TelemetryStore()

    def record(
        self,
        event_type: EventType,
        assignment_id: str,
        draft_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> None:
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
