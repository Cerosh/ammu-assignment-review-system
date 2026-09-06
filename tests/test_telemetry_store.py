"""Tests for TelemetryStore: JSON-Lines append persistence, one file per
assignment. All tests use tmp_path -- never the real data/telemetry/
directory."""

from __future__ import annotations

from ammu_review.telemetry.models import EventType, TelemetryEvent
from ammu_review.telemetry.store import TelemetryStore


def test_append_then_read_events_round_trips(tmp_path):
    store = TelemetryStore(base_dir=tmp_path)
    event = TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a1", assignment_id="a1")

    store.append(event)
    events = store.read_events("a1")

    assert len(events) == 1
    assert events[0].event_id == event.event_id
    assert events[0].event_type == EventType.ASSIGNMENT_CREATED


def test_multiple_events_append_as_separate_lines(tmp_path):
    store = TelemetryStore(base_dir=tmp_path)
    store.append(TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a1", assignment_id="a1"))
    store.append(TelemetryEvent(event_type=EventType.ASSIGNMENT_UNDERSTOOD, session_id="a1", assignment_id="a1"))
    store.append(TelemetryEvent(event_type=EventType.DRAFT_SUBMITTED, session_id="a1", assignment_id="a1", draft_id="d1"))

    events = store.read_events("a1")

    assert [e.event_type for e in events] == [
        EventType.ASSIGNMENT_CREATED,
        EventType.ASSIGNMENT_UNDERSTOOD,
        EventType.DRAFT_SUBMITTED,
    ]

    path = tmp_path / "a1.jsonl"
    lines = path.read_text().splitlines()
    assert len(lines) == 3


def test_events_are_partitioned_per_assignment(tmp_path):
    store = TelemetryStore(base_dir=tmp_path)
    store.append(TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a1", assignment_id="a1"))
    store.append(TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a2", assignment_id="a2"))

    assert len(store.read_events("a1")) == 1
    assert len(store.read_events("a2")) == 1


def test_read_events_for_unknown_assignment_returns_empty_list(tmp_path):
    store = TelemetryStore(base_dir=tmp_path)
    assert store.read_events("does-not-exist") == []


def test_base_dir_is_created_if_missing(tmp_path):
    base_dir = tmp_path / "nested" / "telemetry"
    assert not base_dir.exists()
    TelemetryStore(base_dir=base_dir)
    assert base_dir.exists()


def test_base_dir_defaults_from_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("AMMU_TELEMETRY_DIR", str(tmp_path / "from_env"))
    store = TelemetryStore()
    assert store.base_dir == tmp_path / "from_env"
    assert store.base_dir.exists()
