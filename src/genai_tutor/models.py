"""Data models for the GCP Generative AI Leader Tutor."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Domain:
    id: int
    name: str
    section_number: int
    exam_weight: float  # percentage, e.g. 30.0
    description: str


@dataclass
class Subtopic:
    id: int
    name: str
    domain_id: int
    description: str


@dataclass
class Flashcard:
    id: int
    subtopic_id: int
    front: str
    back: str
    source: str = ""
    ease_factor: float = 2.5
    interval: int = 0
    repetitions: int = 0
    next_review: Optional[date] = None
    last_reviewed: Optional[date] = None


@dataclass
class QuizQuestion:
    id: int
    domain_id: int
    subtopic_id: int
    stem: str
    choice_a: str
    choice_b: str
    choice_c: str
    choice_d: str
    correct_answer: str   # 'a', 'b', 'c', or 'd'
    explanation: str


@dataclass
class StudyDay:
    id: int
    day_number: int
    domain_id: int
    subtopic_ids: list[int]
    reading_content: str


@dataclass
class UserProgress:
    id: int
    study_day_id: int
    reading_complete: bool = False
    flashcard_complete: bool = False
    quiz_complete: bool = False
