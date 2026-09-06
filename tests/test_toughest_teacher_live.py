"""Live-model checks for Stage 5's final-review behaviour.

These call a real model, unlike test_toughest_teacher.py (which is fully
offline via a fake model). What they verify -- that the model actually
grounds its judgement in the supplied rubric/work, genuinely checks whether
Stage 4's priority was addressed, avoids getting distracted by grammar when
substantive issues remain, and never invents a percentage -- is a property
of real model reasoning, not of the code's wiring.

Skipped automatically when no OPENAI_API_KEY is available, so the rest of
the suite stays runnable offline in any environment, including CI.
"""

import os
import re
from pathlib import Path

import pytest

from ammu_review.assignment_understanding import review_assignment
from ammu_review.priority_coach import review_priority_coach
from ammu_review.rubric_success_criteria import review_rubric_success_criteria
from ammu_review.student_work_review import review_rubric_trajectory, review_student_work
from ammu_review.toughest_teacher import review_toughest_teacher

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="requires a live OPENAI_API_KEY",
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

_PERCENT_PATTERN = re.compile(r"\d+(\.\d+)?\s*%")


@pytest.fixture(scope="module")
async def real_pipeline():
    """Runs the full Stage 1 -> 2 -> 3 -> Rubric Trajectory -> 4 -> 5
    pipeline on the real Hannah Clarke case ONCE, shared across this
    module's tests -- this is now the most expensive test file (6 chained
    model calls per file run, not per test)."""
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
    priority = await review_priority_coach(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
        student_work_review=work_review,
        rubric_trajectory=trajectory,
    )
    toughest = await review_toughest_teacher(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
        student_work_review=work_review,
        rubric_trajectory=trajectory,
        priority_coach=priority,
    )
    return {
        "work_review": work_review,
        "trajectory": trajectory,
        "priority": priority,
        "toughest": toughest,
    }


async def test_grounded_in_supplied_rubric_criteria(real_pipeline):
    """Any rubric criteria referenced must actually come from the real
    Hannah Clarke rubric's 3 outcome codes -- never invented."""
    toughest = real_pipeline["toughest"]
    codes_used = {
        ref.criterion_code
        for challenge in toughest.unresolved_issues
        for ref in challenge.related_criteria
        if ref.criterion_code is not None
    }
    assert codes_used <= {"5.3", "5.8", "5.9"}
    assert not any(
        "does not match any criterion in the supplied Stage 2 success map" in limitation
        for limitation in toughest.limitations
    )


async def test_stage4_priority_is_explicitly_checked(real_pipeline):
    """Stage 5 must record a judgement on whether Stage 4's specific
    priority was addressed -- not leave it unset when a priority WAS
    supplied."""
    toughest = real_pipeline["toughest"]
    priority = real_pipeline["priority"]

    if priority.priority_issue_id is not None:
        assert toughest.priority_coach_issue_id == priority.priority_issue_id
        assert toughest.priority_status in {"resolved", "partially_resolved", "unresolved"}
        assert toughest.priority_status_explanation.strip()


async def test_unresolved_priority_is_challenged_not_ignored(real_pipeline):
    """If Stage 4's priority was judged unresolved, it should show up
    among the remaining challenges (or at least be clearly explained),
    not silently dropped."""
    toughest = real_pipeline["toughest"]
    priority = real_pipeline["priority"]

    if toughest.priority_status == "unresolved" and priority.priority_issue_id is not None:
        referenced_ids = {c.issue_id for c in toughest.unresolved_issues if c.issue_id is not None}
        # Either the same issue is directly challenged again, or the
        # explanation substantively engages with why it's still unresolved.
        assert priority.priority_issue_id in referenced_ids or len(toughest.priority_status_explanation) > 20


async def test_final_challenge_is_substantive_not_grammar_only(real_pipeline):
    """The real draft has both a grammar nit and a significant analytical
    gap. The strongest remaining challenge must not be grammar while a
    substantive issue remains unaddressed."""
    toughest = real_pipeline["toughest"]

    if toughest.unresolved_issues:
        top_ranked = min(toughest.unresolved_issues, key=lambda c: c.rank)
        non_grammar_exists = any(c.category != "grammar" for c in toughest.unresolved_issues)
        if non_grammar_exists:
            assert top_ranked.category != "grammar"


async def test_student_questions_are_genuine_questions(real_pipeline):
    toughest = real_pipeline["toughest"]

    assert toughest.final_student_question.strip().endswith("?")
    assert not any(
        "final_student_question" in limitation and "did not end with" in limitation
        for limitation in toughest.limitations
    )
    for challenge in toughest.unresolved_issues:
        assert challenge.student_question.strip().endswith("?")


async def test_no_answer_or_rewrite_leakage(real_pipeline):
    """Heuristic guardrail: the specific replacement-text shapes flagged as
    bad in the approved design should not appear anywhere in the judgement
    prose."""
    toughest = real_pipeline["toughest"]
    bad_patterns = [
        "instead, write",
        "change this sentence to",
        "use this sentence",
        "your paragraph could say",
        "here is a better version",
    ]
    all_text = " ".join(
        [
            toughest.overall_judgment,
            toughest.trajectory_challenge,
            toughest.final_improvement_target,
            *(c.teacher_challenge for c in toughest.unresolved_issues),
        ]
    ).lower()
    assert not any(pattern in all_text for pattern in bad_patterns)


async def test_trajectory_challenged_without_inventing_a_percentage(real_pipeline):
    toughest = real_pipeline["toughest"]
    trajectory = real_pipeline["trajectory"]

    assert not _PERCENT_PATTERN.search(toughest.trajectory_challenge)
    assert not any(
        "trajectory_challenge" in limitation and "percentage" in limitation for limitation in toughest.limitations
    )
    # Grade context is echoed from Rubric Trajectory, never recomputed.
    assert toughest.current_grade == trajectory.estimated_grade


async def test_hannah_clarke_end_to_end_is_coherent(real_pipeline):
    """Overall sanity: the full pipeline produced a coherent Stage 5 result
    that doesn't just repeat Stage 3's full issue list."""
    toughest = real_pipeline["toughest"]
    work_review = real_pipeline["work_review"]

    assert toughest.overall_judgment.strip()
    assert len(toughest.unresolved_issues) <= 3
    assert len(toughest.unresolved_issues) <= len(work_review.issues)
    assert toughest.confidence in {"low", "medium", "high"}


async def test_missing_upstream_context_states_limitations_not_invented_claims():
    """Run Stage 5 with only the bare assignment/rubric/work -- no Stage
    3/4/Trajectory context at all -- and confirm it degrades gracefully."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()
    student_work = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    toughest = await review_toughest_teacher(assignment=assignment, student_work=student_work, rubric=rubric)

    assert toughest.current_grade is None
    assert toughest.priority_coach_issue_id is None
    assert toughest.priority_status is None
    assert toughest.limitations
    assert toughest.trajectory_challenge == (
        "Trajectory framing is not available because no Rubric Trajectory context was supplied."
    )
