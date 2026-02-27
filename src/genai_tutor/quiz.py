"""Quiz engine — question retrieval and result recording."""

from datetime import datetime, timezone
from genai_tutor.db import get_connection
from genai_tutor.models import QuizQuestion


def _row_to_question(row) -> QuizQuestion:
    return QuizQuestion(
        id=row["id"],
        domain_id=row["domain_id"],
        subtopic_id=row["subtopic_id"],
        stem=row["stem"],
        choice_a=row["choice_a"],
        choice_b=row["choice_b"],
        choice_c=row["choice_c"],
        choice_d=row["choice_d"],
        correct_answer=row["correct_answer"],
        explanation=row["explanation"],
    )


def get_random_questions(count: int = 10) -> list[QuizQuestion]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM quiz_questions ORDER BY RANDOM() LIMIT ?", (count,)
        ).fetchall()
    return [_row_to_question(r) for r in rows]


def get_questions_by_domain(domain_id: int, count: int = 10) -> list[QuizQuestion]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM quiz_questions WHERE domain_id=? ORDER BY RANDOM() LIMIT ?",
            (domain_id, count),
        ).fetchall()
    return [_row_to_question(r) for r in rows]


def get_questions_by_subtopic(subtopic_id: int, count: int = 10) -> list[QuizQuestion]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM quiz_questions WHERE subtopic_id=? ORDER BY RANDOM() LIMIT ?",
            (subtopic_id, count),
        ).fetchall()
    return [_row_to_question(r) for r in rows]


def record_answer(question_id: int, user_answer: str, correct_answer: str) -> bool:
    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO quiz_results (question_id, user_answer, is_correct, answered_at) VALUES (?,?,?,?)",
            (question_id, user_answer, int(is_correct), now),
        )
    return is_correct


def get_overall_accuracy() -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as total, SUM(is_correct) as correct FROM quiz_results"
        ).fetchone()
    total = row["total"] or 0
    correct = row["correct"] or 0
    return (correct / total * 100) if total > 0 else 0.0


def get_domain_scores() -> dict[int, dict]:
    """Returns per-domain quiz accuracy stats."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT q.domain_id, d.name,
                   COUNT(r.id) as total,
                   SUM(r.is_correct) as correct
            FROM quiz_results r
            JOIN quiz_questions q ON r.question_id = q.id
            JOIN domains d ON q.domain_id = d.id
            GROUP BY q.domain_id
            """
        ).fetchall()
    return {
        r["domain_id"]: {
            "name": r["name"],
            "total": r["total"],
            "correct": r["correct"] or 0,
            "accuracy": (r["correct"] or 0) / r["total"] * 100 if r["total"] > 0 else 0.0,
        }
        for r in rows
    }


def get_total_quizzes_taken() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM quiz_results").fetchone()
    return row[0]
