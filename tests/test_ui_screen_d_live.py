"""Live integration test for Screen D ("Toughest Teacher") and the Screen C
revision entry, driving the real Streamlit app end-to-end (Screen A -> B ->
C -> submit a revision -> C again -> D) with Ammu's actual Hannah Clarke
assignment/rubric/draft and real model calls.

Deliberately ONE test covering the whole path rather than several smaller
ones, to keep live model calls to a single run: Stage 1+2 (create
assignment), Stage 3+Trajectory+4 for draft 1, the same three again for
draft 2 (the "revision" -- reusing the same draft text is a deliberate
simplification purely to exercise the pipeline wiring, not a claim about
what a real revision would say), and Stage 5 for the Toughest Teacher
challenge -- nine calls total. Skipped automatically without
OPENAI_API_KEY, like every other *_live.py file in this suite.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import streamlit as st
from dotenv import load_dotenv
from streamlit.testing.v1 import AppTest

# Other *_live.py files rely on an earlier-collected test module having
# already imported ammu_review.config (which calls load_dotenv()) -- that's
# order-dependent, so this file loads .env itself to run correctly standalone.
load_dotenv()

pytestmark = pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="requires OPENAI_API_KEY")

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "app.py"


@pytest.fixture(autouse=True)
def _reset_streamlit_resource_cache():
    st.cache_resource.clear()
    yield


@pytest.fixture
def isolated_sessions_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(tmp_path / "sessions"))
    yield tmp_path / "sessions"


def test_hannah_clarke_revision_and_toughest_teacher_flow(isolated_sessions_dir):
    assignment_text = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric_text = (DATA_DIR / "hannah_clarke_rubric.md").read_text()
    student_work_text = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.run(timeout=120)

    # Screen A -> Stage 1 + 2 -> Screen B
    at.text_input[0].input("Hannah Clarke Case Study")
    at.text_area[0].input(assignment_text)
    at.text_area[1].input(rubric_text)
    at.run(timeout=120)
    at.button[0].click()
    at.run(timeout=120)
    assert not at.exception

    # Screen B -> submit draft 1 -> Stage 3 -> Trajectory -> Stage 4 -> Screen C
    draft_text_area = next(t for t in at.text_area if t.key == "draft_text_input")
    draft_text_area.input(student_work_text)
    at.run(timeout=180)
    next(b for b in at.button if b.label == "Get my review").click()
    at.run(timeout=180)
    assert not at.exception
    assert [t.value for t in at.title] == ["Your review"]

    # Screen C -> submit a revision -> a fresh Stage 3 -> Trajectory -> Stage 4 -> Screen C again
    revision_text_area = next(t for t in at.text_area if t.key == "revision_text_input")
    revision_text_area.input(student_work_text)
    at.run(timeout=180)
    next(b for b in at.button if b.label == "Submit my revision").click()
    at.run(timeout=180)
    assert not at.exception
    assert [t.value for t in at.title] == ["Your review"]

    # Screen C -> "Try the Toughest Teacher" -> Screen D intro
    next(b for b in at.button if b.label == "Try the Toughest Teacher").click()
    at.run(timeout=60)
    assert not at.exception
    assert [t.value for t in at.title] == ["Toughest Teacher"]
    assert "Ready for the Toughest Teacher?" in [h.value for h in at.header]

    # Opt in -> real Stage 5 call -> Screen D results
    next(b for b in at.button if b.label == "Challenge my work").click()
    at.run(timeout=180)

    assert not at.exception
    assert "The verdict" in [h.value for h in at.header]
    assert "Your final challenge" in [h.value for h in at.header]

    rendered = "\n".join(str(m.value) for m in at.markdown) + "\n".join(str(i.value) for i in at.info)
    assert "S3-ISSUE" not in rendered  # never a raw issue id
    assert student_work_text.strip() not in rendered  # never the raw draft echoed back
