"""Telemetry: a lightweight, append-only observer of the application layer.

Captures the student journey (assignment created, draft submitted, review
completed, priority identified, revision submitted, priority challenged) as
structured events for later pilot analysis -- see .ai/TELEMETRY.md. This
package never imports from the review engine (Stages 1-5) and is never
imported by it; only ``ammu_review.app.orchestration`` calls it.
"""

from .models import EventType, TelemetryEvent
from .recorder import TelemetryRecorder
from .store import TelemetryStore

__all__ = ["EventType", "TelemetryEvent", "TelemetryRecorder", "TelemetryStore"]
