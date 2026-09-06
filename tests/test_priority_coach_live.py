"""Live-model checks for Stage 4's priority-selection and coaching behaviour.

These call a real model, unlike test_priority_coach.py (which is fully
offline via a fake model). What they verify -- that the model actually
selects a foundational analytical issue over a superficial one, respects the
accuracy exception, phrases challenges as questions rather than answers, and
grounds its grade-boundary framing in Python-computed facts rather than
inventing its own -- is a property of real model reasoning, not of the
code's wiring.

Skipped automatically when no OPENAI_API_KEY is available, so the rest of
the suite stays runnable offline in any environment, including CI.
"""

import os
from pathlib import Path

import pytest

from ammu_review.assignment_understanding import review_assignment
from ammu_review.priority_coach import next_grade_up, review_priority_coach
from ammu_review.rubric_success_criteria import review_rubric_success_criteria
from ammu_review.student_work_review import review_rubric_trajectory, review_student_work

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="requires a live OPENAI_API_KEY",
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
async def real_pipeline():
    """Runs the full Stage 1 -> 2 -> 3 -> Rubric Trajectory -> Stage 4
    pipeline on the real Hannah Clarke case ONCE, shared across this
    module's tests -- these are real, billed model calls, and this is
    already the most expensive test file (5 chained calls per run)."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()
    student_work = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    understanding = await review_assignment(assignment=assignment, rubric=rubric)
    success_criteria = await review_rubric_success_criteria(
        assignment=assignment, rubric=rubric, assignment_understanding=understanding
    )
    work_review = await review_student_work(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
    )
    trajectory = await review_rubric_trajectory(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
    )
    coach = await review_priority_coach(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
        student_work_review=work_review,
        rubric_trajectory=trajectory,
    )
    return {
        "work_review": work_review,
        "trajectory": trajectory,
        "coach": coach,
    }


async def test_priority_is_analytical_or_rubric_not_grammar(real_pipeline):
    """Hannah Clarke validation: the real draft has both grammar nits and a
    significant analytical gap (whether justice was served, depth of legal
    analysis). Stage 4 must not default to the superficial one."""
    coach = real_pipeline["coach"]
    assert coach.priority_category != "grammar"
    assert coach.priority_category in {"analysis", "rubric", "content", "accuracy", "evidence"}


async def test_priority_issue_id_if_set_is_a_real_stage3_id(real_pipeline):
    coach = real_pipeline["coach"]
    work_review = real_pipeline["work_review"]

    if coach.priority_issue_id is not None:
        known_ids = {issue.id for issue in work_review.issues}
        assert coach.priority_issue_id in known_ids


async def test_student_question_is_a_genuine_question_not_a_conclusion(real_pipeline):
    coach = real_pipeline["coach"]

    assert coach.student_question.strip().endswith("?")

    # Heuristic guardrail: the specific completed-conclusion shapes flagged
    # as bad in the approved design should not appear.
    lowered = coach.student_question.lower()
    bad_patterns = ["demonstrates that", "shows that the law", "proves that"]
    assert not any(pattern in lowered for pattern in bad_patterns)


async def test_improvement_target_describes_quality_not_content(real_pipeline):
    coach = real_pipeline["coach"]
    lowered = coach.improvement_target.lower()

    # Heuristic guardrail against the specific "X, so Y failed" causal-
    # conclusion shape the design flagged as answer-leakage.
    assert ", so the law failed" not in lowered
    assert ", so it failed" not in lowered
    assert coach.improvement_target.strip()


async def test_current_and_target_grade_match_independent_recomputation(real_pipeline):
    """Proves the grade-boundary framing really is Python's, not the
    model's -- same style of check used for Rubric Trajectory."""
    coach = real_pipeline["coach"]
    trajectory = real_pipeline["trajectory"]

    assert coach.current_grade == trajectory.estimated_grade
    assert coach.target_grade == next_grade_up(trajectory.estimated_grade, trajectory.grade_boundaries_used)


async def test_trajectory_connection_uses_hedged_language(real_pipeline):
    coach = real_pipeline["coach"]
    lowered = coach.trajectory_connection.lower()

    # Must not manufacture a specific point/percentage claim.
    import re

    assert not re.search(r"\bincrease.{0,20}\d+%|\bby \d+%|\bwill (raise|increase|boost)\b", lowered)


async def test_output_stays_focused_on_one_priority(real_pipeline):
    """Guardrail against reproducing Stage 3: Stage 4's deferred-issues
    acknowledgement must not become a full re-review."""
    coach = real_pipeline["coach"]
    work_review = real_pipeline["work_review"]

    assert len(coach.other_issues_deferred) <= len(work_review.issues)
    # A one-line-each acknowledgement should be far shorter than Stage 3's
    # own detailed issue write-ups.
    deferred_total_length = sum(len(item) for item in coach.other_issues_deferred)
    stage3_total_length = sum(len(issue.observation) + len(issue.why_it_matters) for issue in work_review.issues)
    assert deferred_total_length < stage3_total_length


async def test_no_rubric_trajectory_supplied_states_limitation_not_invented_claim():
    """Foundational analytical issue vs superficial: run Stage 3 without
    trajectory context and confirm Stage 4 still works and is honest about
    the missing framing rather than inventing a grade claim."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()
    student_work = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    understanding = await review_assignment(assignment=assignment, rubric=rubric)
    work_review = await review_student_work(
        assignment=assignment, student_work=student_work, rubric=rubric, assignment_understanding=understanding
    )
    coach = await review_priority_coach(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        student_work_review=work_review,
        rubric_trajectory=None,
    )

    assert coach.current_grade is None
    assert coach.target_grade is None
    assert coach.trajectory_connection == (
        "Trajectory framing is not available because no Rubric Trajectory context was supplied."
    )


async def test_accuracy_issue_can_take_priority_over_analytical_weakness():
    """The accuracy exception: an accuracy issue that could invalidate the
    argument should be eligible to outrank an analytical weakness, when
    that accuracy issue is the only thing Stage 3 flagged as high-severity."""
    assignment = (
        "# Task\n\nWrite a short report on the founding of Acme Robotics and evaluate its "
        "impact on the robotics industry. The company was founded in 1990 by two engineers "
        "in Sydney.\n"
    )
    student_work = (
        "Acme Robotics was founded in 1995 by two engineers in Sydney. Because the company "
        "was founded so early, it became the first mover in the robotics industry and this "
        "gave it a lasting competitive advantage that shaped the whole sector."
    )

    understanding = await review_assignment(assignment=assignment)
    work_review = await review_student_work(
        assignment=assignment, student_work=student_work, assignment_understanding=understanding
    )
    coach = await review_priority_coach(
        assignment=assignment,
        student_work=student_work,
        assignment_understanding=understanding,
        student_work_review=work_review,
    )

    # The entire "first mover advantage" argument rests on the (wrong) 1995
    # founding date -- an accuracy issue here is eligible to be the priority.
    accuracy_issue_ids = {issue.id for issue in work_review.issues if issue.category == "accuracy"}
    if accuracy_issue_ids and coach.priority_issue_id in accuracy_issue_ids:
        assert coach.priority_category == "accuracy"
    # If the model chose something else instead, that's an acceptable
    # judgement call (see design doc section 14) -- this test only checks
    # that WHEN accuracy is chosen, it's handled consistently, not that it
    # must always win.
