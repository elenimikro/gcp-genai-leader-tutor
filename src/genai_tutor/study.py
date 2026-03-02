"""Daily study session management."""

import json
from genai_tutor.db import get_connection
from genai_tutor.models import StudyDay, UserProgress


def get_study_day(day_number: int) -> StudyDay | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM study_days WHERE day_number=?", (day_number,)
        ).fetchone()
    if row is None:
        return None
    return StudyDay(
        id=row["id"],
        day_number=row["day_number"],
        domain_id=row["domain_id"],
        subtopic_ids=json.loads(row["subtopic_ids"]),
        reading_content=row["reading_content"],
    )


def get_current_day() -> int:
    """Return the next incomplete study day number."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT sd.day_number FROM study_days sd
            LEFT JOIN user_progress up ON sd.id = up.study_day_id
            WHERE up.id IS NULL OR (up.reading_complete=0 OR up.flashcard_complete=0 OR up.quiz_complete=0)
            ORDER BY sd.day_number ASC
            LIMIT 1
            """
        ).fetchone()
    return row["day_number"] if row else 1


def get_progress(study_day_id: int) -> UserProgress | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM user_progress WHERE study_day_id=?", (study_day_id,)
        ).fetchone()
    if row is None:
        return None
    return UserProgress(
        id=row["id"],
        study_day_id=row["study_day_id"],
        reading_complete=bool(row["reading_complete"]),
        flashcard_complete=bool(row["flashcard_complete"]),
        quiz_complete=bool(row["quiz_complete"]),
    )


def ensure_progress(study_day_id: int) -> UserProgress:
    p = get_progress(study_day_id)
    if p is None:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO user_progress (study_day_id) VALUES (?)",
                (study_day_id,),
            )
        p = get_progress(study_day_id)
    return p


def mark_reading_complete(study_day_id: int) -> None:
    ensure_progress(study_day_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE user_progress SET reading_complete=1 WHERE study_day_id=?",
            (study_day_id,),
        )


def mark_flashcards_complete(study_day_id: int) -> None:
    ensure_progress(study_day_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE user_progress SET flashcard_complete=1 WHERE study_day_id=?",
            (study_day_id,),
        )


def mark_quiz_complete(study_day_id: int) -> None:
    ensure_progress(study_day_id)
    with get_connection() as conn:
        conn.execute(
            "UPDATE user_progress SET quiz_complete=1 WHERE study_day_id=?",
            (study_day_id,),
        )


def get_completed_days() -> int:
    with get_connection() as conn:
        row = conn.execute(
            """SELECT COUNT(*) FROM user_progress
               WHERE reading_complete=1 AND flashcard_complete=1 AND quiz_complete=1"""
        ).fetchone()
    return row[0]


def get_total_days() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM study_days").fetchone()
    return row[0]


def reset_progress() -> None:
    from genai_tutor.seed import _seed_study_days
    with get_connection() as conn:
        conn.execute("DELETE FROM user_progress")
        conn.execute("DELETE FROM quiz_results")
        conn.execute("DELETE FROM flashcard_results")
        conn.execute("DELETE FROM study_days")
        conn.execute(
            "UPDATE flashcards SET ease_factor=2.5, interval=0, repetitions=0, next_review=NULL, last_reviewed=NULL"
        )
    _seed_study_days()
