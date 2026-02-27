"""Tests for database initialization and seeding."""

import pytest
import tempfile
import os
from unittest.mock import patch


def test_init_db_creates_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        with (
            patch("genai_tutor.db.DB_DIR", __import__("pathlib").Path(tmpdir)),
            patch("genai_tutor.db.DB_PATH", __import__("pathlib").Path(db_path)),
        ):
            from genai_tutor.db import get_connection, init_db
            init_db()
            with get_connection() as conn:
                tables = {
                    r[0]
                    for r in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
    expected = {
        "domains", "subtopics", "flashcards", "quiz_questions",
        "study_days", "user_progress", "quiz_results", "flashcard_results",
        "user_settings",
    }
    assert expected.issubset(tables)
