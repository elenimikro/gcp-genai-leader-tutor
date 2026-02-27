"""Readiness scoring and dashboard display."""

from genai_tutor.quiz import get_overall_accuracy, get_domain_scores, get_total_quizzes_taken
from genai_tutor.flashcards import get_flashcard_retention, get_total_flashcards_reviewed
from genai_tutor.study import get_completed_days, get_total_days


READINESS_THRESHOLDS = {
    "READY": 80.0,
    "LIKELY": 65.0,
    "NEEDS WORK": 50.0,
}


def compute_readiness_score() -> float:
    """
    Composite readiness score (0-100):
      Quiz accuracy        50%
      Flashcard retention  30%
      Study completion     20%
    """
    quiz_score = get_overall_accuracy()
    flashcard_score = get_flashcard_retention()
    total = get_total_days()
    study_score = (get_completed_days() / total * 100) if total > 0 else 0.0

    return (quiz_score * 0.50) + (flashcard_score * 0.30) + (study_score * 0.20)


def get_readiness_label(score: float) -> str:
    if score >= READINESS_THRESHOLDS["READY"]:
        return "READY"
    if score >= READINESS_THRESHOLDS["LIKELY"]:
        return "LIKELY"
    if score >= READINESS_THRESHOLDS["NEEDS WORK"]:
        return "NEEDS WORK"
    return "NOT READY"


def get_dashboard_data() -> dict:
    score = compute_readiness_score()
    domain_scores = get_domain_scores()
    completed = get_completed_days()
    total = get_total_days()

    return {
        "readiness_score": score,
        "readiness_label": get_readiness_label(score),
        "quiz_accuracy": get_overall_accuracy(),
        "flashcard_retention": get_flashcard_retention(),
        "study_completion_pct": (completed / total * 100) if total > 0 else 0.0,
        "days_completed": completed,
        "total_days": total,
        "total_quizzes": get_total_quizzes_taken(),
        "total_flashcards": get_total_flashcards_reviewed(),
        "domain_scores": domain_scores,
    }
