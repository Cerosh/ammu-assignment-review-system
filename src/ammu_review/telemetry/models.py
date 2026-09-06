"""Telemetry event schema.

Structured, privacy-conscious facts about the student journey through the
application layer -- never the review engine's frozen internals, and never
raw student content. See .ai/TELEMETRY.md for the full design rationale,
including which event types are emitted today vs. reserved for Screen C/E.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    # -- Assignment lifecycle (app.orchestration.create_assignment) --
    ASSIGNMENT_CREATED = "ASSIGNMENT_CREATED"
    ASSIGNMENT_UNDERSTOOD = "ASSIGNMENT_UNDERSTOOD"

    # -- Draft / review lifecycle (app.orchestration.submit_draft) --
    DRAFT_SUBMITTED = "DRAFT_SUBMITTED"
    REVISION_SUBMITTED = "REVISION_SUBMITTED"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    PRIORITY_SELECTED = "PRIORITY_SELECTED"

    # -- Toughest Teacher challenge lifecycle (app.orchestration.challenge_draft) --
    PRIORITY_CHALLENGE_STARTED = "PRIORITY_CHALLENGE_STARTED"
    PRIORITY_CHALLENGE_COMPLETED = "PRIORITY_CHALLENGE_COMPLETED"

    # -- Reserved for future student-interaction instrumentation (Screen C/E).
    # Not emitted anywhere yet -- there is no UI event capture and no
    # reflection persistence in the application layer today. Defined now so
    # the event vocabulary is stable once those screens exist; see
    # .ai/TELEMETRY.md "Deferred to Screen C/E".
    PRIORITY_VIEWED = "PRIORITY_VIEWED"
    REFLECTION_SAVED = "REFLECTION_SAVED"
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_COMPLETED = "SESSION_COMPLETED"


def _new_event_id() -> str:
    return uuid.uuid4().hex[:16]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryEvent(BaseModel):
    """One fact about the student journey.

    ``session_id`` currently always equals ``assignment_id`` -- an
    AssignmentSession is 1:1 with an Assignment in this architecture, so
    there is no separate session concept to track yet. Kept as its own
    field for forward compatibility. ``metadata`` holds only structured,
    non-identifying, non-content data (ids, counts, categories, durations,
    booleans) -- never raw assignment/student-work text and never personal
    information.
    """

    event_id: str = Field(default_factory=_new_event_id)
    event_type: EventType
    timestamp: datetime = Field(default_factory=_now)
    session_id: str
    assignment_id: str
    draft_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
