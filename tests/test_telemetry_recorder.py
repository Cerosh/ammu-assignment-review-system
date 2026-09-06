"""Tests for TelemetryRecorder -- specifically that it never lets a
telemetry failure escape and break the caller, per .ai/TELEMETRY.md
"Failure isolation"."""

from __future__ import annotations

import logging

from ammu_review.telemetry.models import EventType
from ammu_review.telemetry.recorder import TelemetryRecorder
from ammu_review.telemetry.store import TelemetryStore


def test_record_writes_an_event(tmp_path):
    recorder = TelemetryRecorder(store=TelemetryStore(base_dir=tmp_path))

    recorder.record(EventType.ASSIGNMENT_CREATED, assignment_id="a1")

    events = recorder.store.read_events("a1")
    assert len(events) == 1
    assert events[0].event_type == EventType.ASSIGNMENT_CREATED
    assert events[0].assignment_id == "a1"
    assert events[0].session_id == "a1"  # defaults to assignment_id


def test_record_passes_through_draft_id_and_metadata(tmp_path):
    recorder = TelemetryRecorder(store=TelemetryStore(base_dir=tmp_path))

    recorder.record(
        EventType.DRAFT_SUBMITTED,
        assignment_id="a1",
        draft_id="d1",
        metadata={"draft_number": 1, "word_count": 42},
    )

    event = recorder.store.read_events("a1")[0]
    assert event.draft_id == "d1"
    assert event.metadata == {"draft_number": 1, "word_count": 42}


class _BrokenStore:
    """A store whose append() always raises -- simulates disk-full, a
    permissions error, or any other telemetry-storage failure."""

    def append(self, event):
        raise OSError("simulated telemetry storage failure")


def test_record_does_not_raise_when_the_store_fails(caplog):
    recorder = TelemetryRecorder(store=_BrokenStore())

    with caplog.at_level(logging.WARNING):
        recorder.record(EventType.ASSIGNMENT_CREATED, assignment_id="a1")  # must not raise

    assert any("Telemetry write failed" in message for message in caplog.messages)


def test_construction_does_not_raise_when_the_default_store_cannot_be_created(tmp_path, monkeypatch, caplog):
    """The directory-creation failure this closes: TelemetryStore()'s
    mkdir() used to happen outside any try/except, so a broken
    AMMU_TELEMETRY_DIR crashed TelemetryRecorder() itself -- and every
    orchestration.py function builds its recorder via the bare
    `recorder or TelemetryRecorder()` default, so this used to crash the
    caller (e.g. submit_draft), not just fail to log telemetry."""
    blocking_file = tmp_path / "not_a_directory"
    blocking_file.write_text("this is a file, not a directory")
    monkeypatch.setenv("AMMU_TELEMETRY_DIR", str(blocking_file / "telemetry"))

    with caplog.at_level(logging.WARNING):
        recorder = TelemetryRecorder()  # must not raise

    assert recorder.store is None
    assert any("Could not initialise telemetry storage" in message for message in caplog.messages)


def test_record_is_a_safe_no_op_when_the_default_store_could_not_be_created(tmp_path, monkeypatch):
    blocking_file = tmp_path / "not_a_directory"
    blocking_file.write_text("this is a file, not a directory")
    monkeypatch.setenv("AMMU_TELEMETRY_DIR", str(blocking_file / "telemetry"))

    recorder = TelemetryRecorder()
    recorder.record(EventType.ASSIGNMENT_CREATED, assignment_id="a1")  # must not raise


def test_explicitly_supplied_store_is_never_wrapped_even_if_it_could_raise_on_construction():
    """An explicitly supplied store is trusted as-is -- only the default
    construction path is defended, since a caller supplying its own store
    is responsible for it."""
    store = TelemetryStore.__new__(TelemetryStore)  # constructed without running __init__
    recorder = TelemetryRecorder(store=store)
    assert recorder.store is store
