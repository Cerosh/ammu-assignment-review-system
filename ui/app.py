"""Streamlit student experience -- Screens A (Assignment Setup) and B
(Understand This Assignment). See the Student Experience design proposal for
the full recommended screen set; only A and B are built so far (Phase B).
Screen C (Your Review) is a separate future phase, not started yet.

This is a thin presentation shell only:
- All orchestration goes through ``ammu_review.app`` (the application/
  session layer built in Phase A) -- this file never calls a Stage 1-5
  function directly and never touches the review engine's internals.
- Everything shown to the student is filtered through
  ``ammu_review.app.presentation`` first -- no raw field name, model name,
  or AI vocabulary should leak into this file's rendering code.
"""

from __future__ import annotations

import asyncio

import streamlit as st

from ammu_review.app import (
    SessionStore,
    create_assignment,
    present_assignment_understanding,
    present_success_criteria,
)

st.set_page_config(page_title="Ammu's Assignment Coach", page_icon="🎓")

TRUST_CAPTION = "This is AI feedback, not your teacher's grade. Your teacher stays the final say."


@st.cache_resource
def get_store() -> SessionStore:
    return SessionStore()


def _run(coro):
    return asyncio.run(coro)


def render_setup_screen(store: SessionStore) -> None:
    st.title("Start a new assignment")
    st.caption(TRUST_CAPTION)

    existing_ids = store.list_assignment_ids()
    if existing_ids:
        with st.sidebar:
            st.subheader("Resume an assignment")
            chosen = st.selectbox(
                "Pick an assignment you've already started",
                ["-- new assignment --"] + existing_ids,
            )
            if chosen != "-- new assignment --":
                st.session_state.assignment_id = chosen
                st.rerun()

    title = st.text_input("Give this assignment a short name (optional)")
    assignment_text = st.text_area("Paste the assignment / task sheet", height=200)
    rubric_text = st.text_area("Paste the marking rubric (optional, but recommended)", height=200)
    teacher_instructions_text = st.text_area("Any extra teacher instructions? (optional)", height=100)

    if st.button("Start reviewing my assignment", disabled=not assignment_text.strip()):
        with st.spinner("Reading your task and rubric..."):
            session = _run(
                create_assignment(
                    store,
                    assignment_text=assignment_text,
                    rubric_text=rubric_text or None,
                    teacher_instructions_text=teacher_instructions_text or None,
                    title=title or None,
                )
            )
        st.session_state.assignment_id = session.assignment.id
        st.rerun()


def render_understand_screen(store: SessionStore) -> None:
    session = store.load(st.session_state.assignment_id)
    assignment = session.assignment

    st.title(assignment.title or "Understand this assignment")
    st.caption(TRUST_CAPTION)

    if st.button("← Start a different assignment"):
        st.session_state.assignment_id = None
        st.rerun()

    if assignment.assignment_understanding is None:
        st.info("Still working this out...")
        return

    understanding = present_assignment_understanding(assignment.assignment_understanding)

    st.header("What you're being asked to do")
    st.write(understanding["what_youre_being_asked_to_do"])

    if understanding["requirements"]:
        st.subheader("What your response needs to include")
        for item in understanding["requirements"]:
            st.markdown(f"- {item}")

    if understanding["watch_out_for"]:
        st.subheader("Easy to miss")
        for item in understanding["watch_out_for"]:
            st.markdown(f"- {item}")

    if understanding["key_words_to_notice"]:
        st.subheader("Key words in the task")
        for item in understanding["key_words_to_notice"]:
            st.markdown(f"- {item}")

    if understanding["checklist"]:
        st.subheader("Before you start writing, check:")
        for i, item in enumerate(understanding["checklist"]):
            st.checkbox(item, key=f"task-checklist-{i}")

    st.divider()

    if assignment.success_criteria is None:
        st.info("Still working out what top marks need...")
        return

    success = present_success_criteria(assignment.success_criteria)

    st.header("What top marks need")
    if not success["rubric_provided"]:
        st.warning(success["message"])
    else:
        if success["overview"]:
            st.write(success["overview"])
        for criterion in success["criteria"]:
            label = f"{criterion['code']} — {criterion['name']}" if criterion["code"] else criterion["name"]
            with st.expander(label):
                st.write(criterion["what_it_means"])
                st.markdown("**What top marks need:**")
                for item in criterion["what_top_marks_need"]:
                    st.markdown(f"- {item}")
                st.markdown("**Good vs. outstanding:**")
                st.write(criterion["good_vs_outstanding"])
                if criterion["common_mistakes"]:
                    st.markdown("**Common mistakes to avoid:**")
                    for item in criterion["common_mistakes"]:
                        st.markdown(f"- {item}")

    if success["checklist"]:
        st.subheader("Success checklist")
        for i, item in enumerate(success["checklist"]):
            st.checkbox(item, key=f"success-checklist-{i}")

    if success["limitations"]:
        with st.expander("Things worth knowing"):
            for item in success["limitations"]:
                st.write(item)

    st.divider()
    st.info("Submitting a draft for review isn't built yet — coming in the next phase.")


def main() -> None:
    store = get_store()
    if "assignment_id" not in st.session_state:
        st.session_state.assignment_id = None

    if st.session_state.assignment_id is None:
        render_setup_screen(store)
    else:
        render_understand_screen(store)


main()
