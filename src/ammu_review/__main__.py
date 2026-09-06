"""Run Stages 1-3 from the command line.

Usage:
    uv run python -m ammu_review
    uv run python -m ammu_review path/to/assignment.md path/to/rubric.md path/to/student_work.md
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

from .assignment_understanding import review_assignment
from .rubric_success_criteria import review_rubric_success_criteria
from .priority_coach import review_priority_coach
from .student_work_review import review_rubric_trajectory, review_student_work
from .toughest_teacher import review_toughest_teacher

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DEFAULT_ASSIGNMENT = DATA_DIR / "sample_assignment.md"
DEFAULT_RUBRIC = DATA_DIR / "sample_rubric.md"
DEFAULT_STUDENT_WORK = DATA_DIR / "sample_student_work.md"


async def _run(assignment_path: Path, rubric_path: Optional[Path], student_work_path: Optional[Path]) -> None:
    assignment = assignment_path.read_text()
    rubric = rubric_path.read_text() if rubric_path and rubric_path.exists() else None

    understanding = await review_assignment(assignment=assignment, rubric=rubric)
    print("# Stage 1: Assignment Understanding")
    print(understanding.model_dump_json(indent=2))

    success_criteria = await review_rubric_success_criteria(
        assignment=assignment,
        rubric=rubric,
        assignment_understanding=understanding,
    )
    print("\n# Stage 2: Rubric / Success Criteria")
    print(success_criteria.model_dump_json(indent=2))

    if student_work_path and student_work_path.exists():
        student_work = student_work_path.read_text()
        work_review = await review_student_work(
            assignment=assignment,
            student_work=student_work,
            rubric=rubric,
            assignment_understanding=understanding,
            success_criteria=success_criteria,
        )
        print("\n# Stage 3: Student Work Review")
        print(work_review.model_dump_json(indent=2))

        trajectory = await review_rubric_trajectory(
            assignment=assignment,
            student_work=student_work,
            rubric=rubric,
            assignment_understanding=understanding,
            success_criteria=success_criteria,
        )
        print("\n# Stage 3: Rubric Trajectory")
        print(trajectory.model_dump_json(indent=2))

        priority = await review_priority_coach(
            assignment=assignment,
            student_work=student_work,
            rubric=rubric,
            assignment_understanding=understanding,
            success_criteria=success_criteria,
            student_work_review=work_review,
            rubric_trajectory=trajectory,
        )
        print("\n# Stage 4: Priority Coach")
        print(priority.model_dump_json(indent=2))

        toughest_teacher = await review_toughest_teacher(
            assignment=assignment,
            student_work=student_work,
            rubric=rubric,
            assignment_understanding=understanding,
            success_criteria=success_criteria,
            student_work_review=work_review,
            rubric_trajectory=trajectory,
            priority_coach=priority,
        )
        print("\n# Stage 5: Toughest Teacher Review")
        print(toughest_teacher.model_dump_json(indent=2))


def main() -> None:
    args = sys.argv[1:]
    assignment_path = Path(args[0]) if len(args) > 0 else DEFAULT_ASSIGNMENT
    rubric_path = Path(args[1]) if len(args) > 1 else DEFAULT_RUBRIC
    student_work_path = Path(args[2]) if len(args) > 2 else DEFAULT_STUDENT_WORK
    asyncio.run(_run(assignment_path, rubric_path, student_work_path))


if __name__ == "__main__":
    main()
