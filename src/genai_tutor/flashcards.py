"""Flashcard retrieval and SM-2 spaced repetition management."""

from datetime import datetime, date, timezone, timedelta
from genai_tutor.db import get_connection
from genai_tutor.models import Flashcard
from genai_tutor.sm2 import sm2_update


def _row_to_card(row) -> Flashcard:
    return Flashcard(
        id=row["id"],
        subtopic_id=row["subtopic_id"],
        front=row["front"],
        back=row["back"],
        source=row["source"] or "",
        ease_factor=row["ease_factor"],
        interval=row["interval"],
        repetitions=row["repetitions"],
        next_review=date.fromisoformat(row["next_review"]) if row["next_review"] else None,
        last_reviewed=date.fromisoformat(row["last_reviewed"]) if row["last_reviewed"] else None,
    )


def get_due_cards(limit: int = 15) -> list[Flashcard]:
    """Return cards due for review today (never reviewed first, then by next_review date)."""
    today = date.today().isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM flashcards
            WHERE next_review IS NULL OR next_review <= ?
            ORDER BY (next_review IS NULL) DESC, next_review ASC
            LIMIT ?
            """,
            (today, limit),
        ).fetchall()
    return [_row_to_card(r) for r in rows]


def get_cards_for_domain(domain_id: int, limit: int = 15) -> list[Flashcard]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT f.* FROM flashcards f
            JOIN subtopics s ON f.subtopic_id = s.id
            WHERE s.domain_id = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (domain_id, limit),
        ).fetchall()
    return [_row_to_card(r) for r in rows]


def record_flashcard_result(card: Flashcard, quality: int) -> None:
    """Update SM-2 parameters and persist flashcard result."""
    new_interval, new_ef, new_reps = sm2_update(
        quality, card.repetitions, card.ease_factor, card.interval
    )
    today = date.today()
    next_review = today + timedelta(days=new_interval)
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """UPDATE flashcards
               SET ease_factor=?, interval=?, repetitions=?, next_review=?, last_reviewed=?
               WHERE id=?""",
            (new_ef, new_interval, new_reps, next_review.isoformat(), today.isoformat(), card.id),
        )
        conn.execute(
            "INSERT INTO flashcard_results (flashcard_id, quality, reviewed_at) VALUES (?,?,?)",
            (card.id, quality, now),
        )


def get_flashcard_retention() -> float:
    """Average quality score (0-5) as a percentage of max (5)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT AVG(quality) as avg_q FROM flashcard_results"
        ).fetchone()
    avg = row["avg_q"]
    if avg is None:
        return 0.0
    return (avg / 5.0) * 100


def get_total_flashcards_reviewed() -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(DISTINCT flashcard_id) FROM flashcard_results").fetchone()
    return row[0]
