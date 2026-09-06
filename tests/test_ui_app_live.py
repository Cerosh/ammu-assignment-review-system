"""Live integration test for Screens A + B of the Streamlit student
experience, using Ammu's real Hannah Clarke assignment/rubric -- this is
the Hannah Clarke validation step for Phase B (Student Experience design
proposal). It drives the actual ui/app.py script via Streamlit's AppTest,
not a mock, and makes two real model calls (Stage 1 + Stage 2).

Skipped automatically without OPENAI_API_KEY, like every other *_live.py
test in this suite.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from streamlit.testing.v1 import AppTest

# Other *_live.py files rely on an earlier-collected test module having
# already imported ammu_review.config (which calls load_dotenv()) -- that's
# order-dependent, so this file loads .env itself to run correctly standalone.
load_dotenv()

pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "app.py"


@pytest.fixture
def isolated_sessions_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(tmp_path / "sessions"))
    yield tmp_path / "sessions"


def test_hannah_clarke_setup_and_understand_screens(isolated_sessions_dir):
    assignment_text = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric_text = (DATA_DIR / "hannah_clarke_rubric.md").read_text()

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.run(timeout=120)

    assert not at.exception
    assert at.title[0].value == "Start a new assignment"

    at.text_input[0].input("Hannah Clarke Case Study")
    at.text_area[0].input(assignment_text)
    at.text_area[1].input(rubric_text)
    at.run(timeout=120)  # re-run so the submit button's disabled state updates

    at.button[0].click()
    at.run(timeout=120)

    assert not at.exception, [e.value for e in at.exception]
    assert at.title[0].value == "Hannah Clarke Case Study"

    header_texts = [h.value for h in at.header]
    assert "What you're being asked to do" in header_texts
    assert "What top marks need" in header_texts

    info_texts = [i.value for i in at.info]
    assert not any("Still working" in text for text in info_texts)

    warning_texts = [w.value for w in at.warning]
    assert not any("No marking rubric" in text for text in warning_texts)
