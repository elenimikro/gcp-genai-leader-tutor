"""Tests for the SM-2 spaced repetition algorithm."""

import pytest
from genai_tutor.sm2 import sm2_update


def test_perfect_recall_first_repetition():
    interval, ef, reps = sm2_update(quality=5, repetitions=0, ease_factor=2.5, interval=0)
    assert interval == 1
    assert reps == 1
    assert ef > 2.5  # quality 5 increases ease factor


def test_perfect_recall_second_repetition():
    interval, ef, reps = sm2_update(quality=5, repetitions=1, ease_factor=2.5, interval=1)
    assert interval == 6
    assert reps == 2


def test_perfect_recall_third_repetition():
    interval, ef, reps = sm2_update(quality=5, repetitions=2, ease_factor=2.5, interval=6)
    assert interval == round(6 * 2.5)
    assert reps == 3


def test_blackout_resets_repetitions():
    interval, ef, reps = sm2_update(quality=0, repetitions=5, ease_factor=2.5, interval=30)
    assert reps == 0
    assert interval == 1


def test_poor_recall_resets():
    interval, ef, reps = sm2_update(quality=2, repetitions=3, ease_factor=2.5, interval=15)
    assert reps == 0
    assert interval == 1


def test_ease_factor_never_below_minimum():
    _, ef, _ = sm2_update(quality=0, repetitions=0, ease_factor=1.4, interval=0)
    assert ef >= 1.3


def test_correct_with_difficulty_continues():
    interval, ef, reps = sm2_update(quality=3, repetitions=1, ease_factor=2.5, interval=1)
    assert reps == 2
    assert interval == 6


def test_quality_4_increases_reps():
    interval, ef, reps = sm2_update(quality=4, repetitions=0, ease_factor=2.5, interval=0)
    assert reps == 1
    assert interval == 1
