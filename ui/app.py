"""Streamlit student experience -- Screens A (Assignment Setup), B
(Understand This Assignment), C (Your Review), and D (Toughest Teacher).
See the Student Experience design proposal for the full recommended screen
set; Screen E (Reflection) is a future phase, not started yet.

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
    challenge_draft,
    create_assignment,
    present_assignment_understanding,
    present_other_issues,
    present_priority,
    present_revision_comparison,
    present_rubric_check,
    present_rubric_trajectory,
    present_strengths,
    present_success_criteria,
    present_toughest_teacher,
    record_priority_viewed,
    submit_draft,
)
from ammu_review.config import is_openai_api_key_configured
from ammu_review.pilot_access import check_access_code, get_pilot_access_code

st.set_page_config(page_title="Ammu's Assignment Coach", page_icon="🎓")

TRUST_CAPTION = "This is AI feedback, not your teacher's grade. Your teacher stays the final say."


def render_access_gate() -> bool:
    """Private pilot access gate -- must be called, and must block
    everything else, before any assignment/review functionality is
    reachable. Returns True once this browser session is authenticated.

    Fails closed: a missing access code is treated as "block everyone",
    never as "no gate configured". Never logs or persists the code the
    student enters -- it lives only in this browser session's in-memory
    Streamlit state, cleared immediately after a successful check.
    """
    if st.session_state.get("pilot_authenticated", False):
        return True

    expected_code = get_pilot_access_code()
    if not expected_code:
        st.error("This app isn't set up yet. Please check back later.")
        st.stop()

    st.title("Private Pilot")
    st.caption("Enter your access code to continue.")
    candidate = st.text_input("Access code", type="password", key="pilot_access_code_input")
    if st.button("Continue"):
        if check_access_code(candidate, expected_code):
            st.session_state.pilot_authenticated = True
            st.session_state.pop("pilot_access_code_input", None)
            st.rerun()
        else:
            st.error("That code isn't right. Try again.")
    return False


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
            st.session_state.show_toughest_teacher = False
            st.rerun()
    with right:
        if st.button("Start a different assignment"):
            st.session_state.assignment_id = None
            st.session_state.draft_id = None
            st.session_state.show_toughest_teacher = False
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

    st.divider()
    st.header("Ready to try the Toughest Teacher?")
    st.write(
        "Once you've worked on your priority above, you can put your revised work in front of "
        "the toughest teacher -- an extra, optional challenge, not something you have to do."
    )
    if st.button("Try the Toughest Teacher"):
        st.session_state.show_toughest_teacher = True
        st.rerun()

    st.divider()
    st.header("Revising your work?")
    st.caption("Your current draft is saved. Submit your revised version below when you're ready.")
    revision_text = st.text_area("Your revised draft", height=300, key="revision_text_input")
    if st.button("Submit my revision", disabled=not revision_text.strip()):
        with st.spinner("Reviewing your revised draft... this can take a minute."):
            new_draft = _run(submit_draft(store, assignment.id, revision_text))
        st.session_state.draft_id = new_draft.id
        st.session_state.show_toughest_teacher = False
        st.rerun()


def render_toughest_teacher_screen(store: SessionStore) -> None:
    session = store.load(st.session_state.assignment_id)
    assignment = session.assignment
    draft = next((d for d in session.drafts if d.id == st.session_state.draft_id), None)

    if draft is None:
        st.session_state.draft_id = None
        st.session_state.show_toughest_teacher = False
        st.rerun()
        return

    st.title("Toughest Teacher")
    st.caption(TRUST_CAPTION)

    if st.button("← Back to your review"):
        st.session_state.show_toughest_teacher = False
        st.rerun()

    if draft.toughest_teacher_review is None:
        st.header("Ready for the Toughest Teacher?")
        st.write(
            "This is the part where I challenge your revised work as if I were your toughest "
            "teacher. It's meant to be demanding -- that's the point, not a punishment."
        )
        if st.button("Challenge my work"):
            with st.spinner("Reviewing as your toughest teacher..."):
                _run(challenge_draft(store, assignment.id, draft.id))
            st.rerun()
        return

    review = present_toughest_teacher(draft.toughest_teacher_review)

    # --- Tier 1: the verdict ---------------------------------------------------
    st.header("The verdict")
    if review["had_previous_priority_to_check"]:
        st.markdown(f"**{review['verdict']}**")
    else:
        st.info(
            "There wasn't an earlier priority to check against for this draft, so the toughest "
            "teacher couldn't judge whether a previous challenge was resolved."
        )
    st.write(review["priority_status_explanation"])
    if review["overall_judgment"]:
        st.caption(review["overall_judgment"])

    st.divider()

    # --- Your progress (only shown when there's a genuine earlier draft) -------
    source_id = draft.priority_coach_checked_source_draft_id
    previous_draft = (
        next((d for d in session.drafts if d.id == source_id), None)
        if source_id and source_id != draft.id
        else None
    )
    comparison = present_revision_comparison(
        draft.rubric_trajectory, previous_draft.rubric_trajectory if previous_draft else None
    )
    if comparison["available"]:
        st.header("Your progress")
        if comparison["previous_grade"] and comparison["current_grade"]:
            st.write(
                f"Previous trajectory: **{comparison['previous_grade']}** → "
                f"Current trajectory: **{comparison['current_grade']}**"
            )
            st.caption("(AI estimate, not your teacher's grade)")
            if comparison["trajectory_changed"] is True:
                st.success("Your estimated trajectory moved.")
            elif comparison["trajectory_changed"] is False:
                st.info("Your estimated trajectory hasn't moved yet.")
        if review["trajectory_challenge"]:
            st.write(review["trajectory_challenge"])
        st.divider()

    # --- Tier 2: what the toughest teacher still sees ---------------------------
    if review["unresolved_issues"]:
        st.header("What the toughest teacher still sees")
        for issue in review["unresolved_issues"]:
            with st.expander(issue["category"]):
                st.write(issue["observation"])
                st.markdown("**Why this matters:**")
                st.write(issue["why_it_matters"])
                st.markdown("**The challenge:**")
                st.write(issue["teacher_challenge"])
                st.markdown("**Think about this:**")
                st.info(issue["student_question"])
        st.divider()

    if review["resolved_or_adequately_addressed"]:
        with st.expander("What's now resolved or adequately addressed"):
            for item in review["resolved_or_adequately_addressed"]:
                st.markdown(f"- {item}")
        st.divider()

    # --- Tier 3: what would change my mind ---------------------------------------
    if review["what_would_change_my_mind"]:
        st.header("What would change the toughest teacher's mind?")
        for item in review["what_would_change_my_mind"]:
            st.markdown(f"- {item}")
        st.divider()

    # --- Tier 4: final challenge ---------------------------------------------------
    st.header("Your final challenge")
    st.markdown("**Think about this:**")
    st.info(review["final_student_question"])
    st.markdown("**Your target:**")
    st.write(review["final_improvement_target"])

    if review["limitations"]:
        with st.expander("Things worth knowing"):
            for item in review["limitations"]:
                st.write(item)


def main() -> None:
    if not render_access_gate():
        return

    if not is_openai_api_key_configured():
        st.error("This app isn't set up yet. Please check back later.")
        st.stop()

    store = get_store()
    if "assignment_id" not in st.session_state:
        st.session_state.assignment_id = None
    if "draft_id" not in st.session_state:
        st.session_state.draft_id = None
    if "show_toughest_teacher" not in st.session_state:
        st.session_state.show_toughest_teacher = False

    if st.session_state.assignment_id is None:
        render_setup_screen(store)
    elif st.session_state.draft_id is None:
        render_understand_screen(store)
    elif st.session_state.show_toughest_teacher:
        render_toughest_teacher_screen(store)
    else:
        render_review_screen(store)


main()
