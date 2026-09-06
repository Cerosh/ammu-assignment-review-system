"""Tests for the telemetry event schema."""

from __future__ import annotations

from ammu_review.telemetry.models import EventType, TelemetryEvent


def test_event_gets_a_default_unique_id_and_timestamp():
    e1 = TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a1", assignment_id="a1")
    e2 = TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a1", assignment_id="a1")

    assert e1.event_id != e2.event_id
    assert e1.event_id
    assert e1.timestamp is not None


def test_metadata_defaults_to_empty_dict():
    event = TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a1", assignment_id="a1")
    assert event.metadata == {}


def test_draft_id_defaults_to_none():
    event = TelemetryEvent(event_type=EventType.ASSIGNMENT_CREATED, session_id="a1", assignment_id="a1")
    assert event.draft_id is None


def test_event_round_trips_through_json():
    event = TelemetryEvent(
        event_type=EventType.DRAFT_SUBMITTED,
        session_id="a1",
        assignment_id="a1",
        draft_id="d1",
        metadata={"draft_number": 1, "word_count": 250},
    )

    restored = TelemetryEvent.model_validate_json(event.model_dump_json())

    assert restored.event_id == event.event_id
    assert restored.event_type == EventType.DRAFT_SUBMITTED
    assert restored.draft_id == "d1"
    assert restored.metadata == {"draft_number": 1, "word_count": 250}


def test_event_type_serializes_as_plain_string():
    event = TelemetryEvent(event_type=EventType.REVIEW_COMPLETED, session_id="a1", assignment_id="a1")
    assert "REVIEW_COMPLETED" in event.model_dump_json()
