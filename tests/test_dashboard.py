"""Tests for dashboard readiness scoring."""

from genai_tutor.dashboard import compute_readiness_score, get_readiness_label


def test_readiness_label_ready():
    assert get_readiness_label(82.0) == "READY"


def test_readiness_label_likely():
    assert get_readiness_label(70.0) == "LIKELY"


def test_readiness_label_needs_work():
    assert get_readiness_label(55.0) == "NEEDS WORK"


def test_readiness_label_not_ready():
    assert get_readiness_label(40.0) == "NOT READY"


def test_readiness_score_weighted():
    from unittest.mock import patch
    with (
        patch("genai_tutor.dashboard.get_overall_accuracy", return_value=80.0),
        patch("genai_tutor.dashboard.get_flashcard_retention", return_value=60.0),
        patch("genai_tutor.dashboard.get_completed_days", return_value=14),
        patch("genai_tutor.dashboard.get_total_days", return_value=28),
    ):
        score = compute_readiness_score()
    # 80*0.5 + 60*0.3 + 50*0.2 = 40 + 18 + 10 = 68
    assert abs(score - 68.0) < 0.01
