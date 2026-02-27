"""Tests that content JSON files are valid and well-formed."""

import json
import pytest
from importlib.resources import files


def _load(filename):
    return json.loads(
        files("genai_tutor.content").joinpath(filename).read_text(encoding="utf-8")
    )


def test_domains_structure():
    domains = _load("domains.json")
    assert len(domains) == 4
    for d in domains:
        assert "id" in d
        assert "name" in d
        assert "exam_weight" in d
        assert "subtopics" in d
        assert len(d["subtopics"]) > 0


def test_exam_weights_sum_to_100():
    domains = _load("domains.json")
    total = sum(d["exam_weight"] for d in domains)
    assert abs(total - 100.0) < 0.1


def test_questions_have_required_fields():
    questions = _load("questions.json")
    assert len(questions) >= 80
    required = {"id", "domain_id", "subtopic_id", "stem", "choice_a", "choice_b", "choice_c", "choice_d", "correct_answer", "explanation"}
    for q in questions:
        assert required.issubset(q.keys()), f"Question {q.get('id')} missing fields"
        assert q["correct_answer"] in ("a", "b", "c", "d"), f"Question {q.get('id')} has invalid answer"


def test_flashcards_have_required_fields():
    cards = _load("flashcards.json")
    assert len(cards) >= 50
    for c in cards:
        assert "id" in c
        assert "subtopic_id" in c
        assert "front" in c and c["front"]
        assert "back" in c and c["back"]


def test_reading_has_content():
    reading = _load("reading.json")
    assert len(reading) >= 10
    for r in reading:
        assert "domain_id" in r
        assert "content" in r and len(r["content"]) > 50
