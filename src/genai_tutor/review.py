"""Weak area identification for targeted review sessions."""

from genai_tutor.db import get_connection


def get_weak_domains(threshold: float = 70.0) -> list[dict]:
    """Return domains where quiz accuracy is below the threshold, worst first."""
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
            HAVING (CAST(SUM(r.is_correct) AS REAL) / COUNT(r.id)) * 100 < ?
            ORDER BY (CAST(SUM(r.is_correct) AS REAL) / COUNT(r.id)) ASC
            """,
            (threshold,),
        ).fetchall()
    return [
        {
            "domain_id": r["domain_id"],
            "name": r["name"],
            "accuracy": (r["correct"] or 0) / r["total"] * 100 if r["total"] > 0 else 0.0,
            "total": r["total"],
        }
        for r in rows
    ]


def get_weak_subtopics(threshold: float = 70.0) -> list[dict]:
    """Return subtopics where quiz accuracy is below the threshold, worst first."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT q.subtopic_id, s.name, d.name as domain_name,
                   COUNT(r.id) as total,
                   SUM(r.is_correct) as correct
            FROM quiz_results r
            JOIN quiz_questions q ON r.question_id = q.id
            JOIN subtopics s ON q.subtopic_id = s.id
            JOIN domains d ON s.domain_id = d.id
            GROUP BY q.subtopic_id
            HAVING (CAST(SUM(r.is_correct) AS REAL) / COUNT(r.id)) * 100 < ?
            ORDER BY (CAST(SUM(r.is_correct) AS REAL) / COUNT(r.id)) ASC
            """,
            (threshold,),
        ).fetchall()
    return [
        {
            "subtopic_id": r["subtopic_id"],
            "name": r["name"],
            "domain_name": r["domain_name"],
            "accuracy": (r["correct"] or 0) / r["total"] * 100 if r["total"] > 0 else 0.0,
            "total": r["total"],
        }
        for r in rows
    ]


def get_all_domains() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, section_number, exam_weight FROM domains ORDER BY section_number"
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_subtopics() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT s.id, s.name, s.domain_id, d.name as domain_name
               FROM subtopics s JOIN domains d ON s.domain_id = d.id
               ORDER BY s.domain_id, s.id"""
        ).fetchall()
    return [dict(r) for r in rows]
