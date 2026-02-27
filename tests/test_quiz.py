"""Tests for the quiz engine."""

import pytest
from unittest.mock import patch, MagicMock
from genai_tutor import quiz as quiz_engine


def _make_question(id=1, domain_id=1, subtopic_id=1, correct_answer="b"):
    return MagicMock(
        id=id,
        domain_id=domain_id,
        subtopic_id=subtopic_id,
        correct_answer=correct_answer,
    )


def test_record_answer_correct():
    with patch("genai_tutor.quiz.get_connection") as mock_conn:
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        result = quiz_engine.record_answer(1, "b", "b")
    assert result is True


def test_record_answer_incorrect():
    with patch("genai_tutor.quiz.get_connection") as mock_conn:
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        result = quiz_engine.record_answer(1, "a", "b")
    assert result is False


def test_record_answer_case_insensitive():
    with patch("genai_tutor.quiz.get_connection") as mock_conn:
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        result = quiz_engine.record_answer(1, "B", "b")
    assert result is True
