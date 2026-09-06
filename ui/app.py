"""Streamlit student experience -- Screens A (Assignment Setup), B
(Understand This Assignment), and C (Your Review). See the Student
Experience design proposal for the full recommended screen set; Screens D
(Toughest Teacher Challenge) and E (Reflection) are future phases, not
started yet.

This is a thin presentation shell only:
- All orchestration goes through ``ammu_review.app`` (the application/
  session layer) -- this file never calls a Stage 1-5 function directly and
  never touches the review engine's internals. It makes no AI calls itself.
- Everything shown to the student is filtered through
  ``ammu_review.app.presentation`` first -- no raw field name, model name,
  issue id, or AI vocabulary should leak into this file's rendering code.
"""

from __future__ import annotations

import asyncio

import streamlit as st

from ammu_review.app import (
    SessionStore,
    create_assignment,
    present_assignment_understanding,
    present_other_issues,
    present_priority,
    present_rubric_check,
    present_rubric_trajectory,
    present_strengths,
    present_success_criteria,
    record_priority_viewed,
    submit_draft,
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
    st.header("Ready for feedback on your draft?")
    st.caption("Paste what you've written so far to get your review.")
    draft_text = st.text_area("Your draft", height=300, key="draft_text_input")
    if st.button("Get my review", disabled=not draft_text.strip()):
        with st.spinner("Reviewing your draft... this can take a minute."):
            draft = _run(submit_draft(store, assignment.id, draft_text))
        st.session_state.draft_id = draft.id
        st.rerun()


def render_review_screen(store: SessionStore) -> None:
    session = store.load(st.session_state.assignment_id)
    assignment = session.assignment
    draft = next((d for d in session.drafts if d.id == st.session_state.draft_id), None)

    if draft is None:
        # Stale state (e.g. a draft id from a since-cleared session) -- fall
        # back to the understand screen rather than crashing.
        st.session_state.draft_id = None
        st.rerun()
        return

    st.title("Your review")
    st.caption(TRUST_CAPTION)

    left, right = st.columns(2)
    with left:
        if st.button("← Back to assignment overview"):
            st.session_state.draft_id = None
            st.rerun()
    with right:
        if st.button("Start a different assignment"):
            st.session_state.assignment_id = None
            st.session_state.draft_id = None
            st.rerun()

    if draft.student_work_review is None:
        st.info("Still reviewing your draft...")
        return

    # --- Tier 1: your biggest opportunity ------------------------------------
    priority = present_priority(draft.priority_coach)
    st.header("🎯 Your biggest opportunity")
    if priority["available"]:
        viewed_key = f"priority_viewed::{draft.id}"
        if not st.session_state.get(viewed_key, False):
            record_priority_viewed(
                assignment_id=assignment.id,
                draft_id=draft.id,
                priority_issue_id=draft.priority_coach.priority_issue_id,
                priority_category=draft.priority_coach.priority_category,
            )
            st.session_state[viewed_key] = True

        st.markdown(f"**{priority['priority_statement']}**")
        st.markdown("**Why this matters:**")
        st.write(priority["why_it_matters"])
        criterion_name = priority["criterion"]["name"]
        if criterion_name:
            label = (
                f"{priority['criterion']['code']} — {criterion_name}"
                if priority["criterion"]["code"]
                else criterion_name
            )
            st.caption(f"Connected to: {label}")
        st.markdown("**Think about this:**")
        st.info(priority["student_question"])
    else:
        st.info("We couldn't identify a clear priority for this draft.")

    st.divider()

    # --- Tier 2: where you stand ----------------------------------------------
    trajectory = present_rubric_trajectory(draft.rubric_trajectory)
    st.header("📍 Where you stand")
    if not trajectory["available"]:
        st.warning(trajectory["message"])
    else:
        if trajectory["overall_estimated_grade"]:
            st.markdown(
                f"**Your current trajectory: {trajectory['overall_estimated_grade']}** "
                "_(AI estimate, not your teacher's grade)_"
            )
        if trajectory["biggest_opportunity"]:
            st.write(trajectory["biggest_opportunity"])
        for criterion in trajectory["criteria"]:
            label = f"{criterion['code']} — {criterion['name']}" if criterion["code"] else criterion["name"]
            with st.expander(label):
                if criterion["estimated_grade"]:
                    st.write(f"AI estimate: **{criterion['estimated_grade']}**")
                elif criterion["limitation"]:
                    st.write(criterion["limitation"])
                if criterion["rationale"]:
                    st.caption(criterion["rationale"])
        if trajectory["next_boundary_requirements"]:
            st.markdown("**Your next opportunity:**")
            for item in trajectory["next_boundary_requirements"]:
                st.markdown(f"- {item}")

    st.divider()

    # --- Strengths --------------------------------------------------------------
    strengths = present_strengths(draft.student_work_review)
    if strengths:
        st.header("✅ What you're doing well")
        for item in strengths:
            st.markdown(f"- {item}")
        st.divider()

    # --- Tier 3: rubric check ----------------------------------------------------
    rubric_check = present_rubric_check(draft.student_work_review)
    if rubric_check["available"]:
        st.header("📋 Rubric check")
        for criterion in rubric_check["criteria"]:
            label = f"{criterion['code']} — {criterion['name']}" if criterion["code"] else criterion["name"]
            with st.expander(label):
                st.write(f"Current level: **{criterion['current_level']}**")
                if criterion["whats_working"]:
                    st.markdown("**What's working:**")
                    for item in criterion["whats_working"]:
                        st.markdown(f"- {item}")
                if criterion["whats_missing"]:
                    st.markdown("**What's missing:**")
                    for item in criterion["whats_missing"]:
                        st.markdown(f"- {item}")
        st.divider()

    # --- Tier 4: other things noticed (collapsed, secondary) ---------------------
    priority_issue_id = draft.priority_coach.priority_issue_id if draft.priority_coach else None
    other_issues = present_other_issues(draft.student_work_review, priority_issue_id)
    if other_issues:
        with st.expander(f"Other things I noticed ({len(other_issues)})"):
            for issue in other_issues:
                st.markdown(f"**{issue['category']}**")
                st.write(issue["observation"])
                st.caption(issue["why_it_matters"])
                st.markdown("---")

    if draft.student_work_review.limitations:
        with st.expander("Things worth knowing"):
            for item in draft.student_work_review.limitations:
                st.write(item)


def main() -> None:
    store = get_store()
    if "assignment_id" not in st.session_state:
        st.session_state.assignment_id = None
    if "draft_id" not in st.session_state:
        st.session_state.draft_id = None

    if st.session_state.assignment_id is None:
        render_setup_screen(store)
    elif st.session_state.draft_id is None:
        render_understand_screen(store)
    else:
        render_review_screen(store)


main()
