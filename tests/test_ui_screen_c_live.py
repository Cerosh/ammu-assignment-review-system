"""Live integration test for Screen C ("Your Review"), driving the real
Streamlit app end-to-end (Screen A -> B -> C) with Ammu's actual Hannah
Clarke assignment/rubric/draft and real model calls (Stage 1, 2, 3, Rubric
Trajectory, Stage 4 -- five calls). Skipped automatically without
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


def test_hannah_clarke_full_flow_through_screen_c(isolated_sessions_dir):
    assignment_text = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric_text = (DATA_DIR / "hannah_clarke_rubric.md").read_text()
    student_work_text = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.run(timeout=120)

    at.text_input[0].input("Hannah Clarke Case Study")
    at.text_area[0].input(assignment_text)
    at.text_area[1].input(rubric_text)
    at.run(timeout=120)
    at.button[0].click()
    at.run(timeout=120)  # Screen A -> Stage 1 + 2 -> Screen B

    assert not at.exception

    draft_text_area = next(t for t in at.text_area if t.key == "draft_text_input")
    draft_text_area.input(student_work_text)
    at.run(timeout=180)
    get_review_button = next(b for b in at.button if b.label == "Get my review")
    get_review_button.click()
    at.run(timeout=180)  # Stage 3 -> Rubric Trajectory -> Stage 4 -> Screen C

    assert not at.exception
    assert [t.value for t in at.title] == ["Your review"]
    assert "🎯 Your biggest opportunity" in [h.value for h in at.header]
    assert "📍 Where you stand" in [h.value for h in at.header]

    rendered = "\n".join(str(m.value) for m in at.markdown) + "\n".join(str(i.value) for i in at.info)
    assert "S3-ISSUE" not in rendered  # never a raw issue id
    assert student_work_text.strip() not in rendered  # never the raw draft echoed back as a "review"
