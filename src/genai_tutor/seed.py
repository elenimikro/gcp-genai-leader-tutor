"""Seed the database with initial content from JSON files."""

import json
from importlib.resources import files
from datetime import date

from genai_tutor.db import get_connection


def _load(filename: str) -> list:
    data = files("genai_tutor.content").joinpath(filename).read_text(encoding="utf-8")
    return json.loads(data)


def is_seeded() -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM domains").fetchone()
        return row[0] > 0


def seed_all() -> None:
    if is_seeded():
        return
    _seed_domains()
    _seed_questions()
    _seed_flashcards()
    _seed_study_days()


def _seed_domains() -> None:
    domains = _load("domains.json")
    with get_connection() as conn:
        for d in domains:
            conn.execute(
                "INSERT OR IGNORE INTO domains (id, name, section_number, exam_weight, description) VALUES (?,?,?,?,?)",
                (d["id"], d["name"], d["section_number"], d["exam_weight"], d["description"]),
            )
            for st in d.get("subtopics", []):
                conn.execute(
                    "INSERT OR IGNORE INTO subtopics (id, name, domain_id, description) VALUES (?,?,?,?)",
                    (st["id"], st["name"], d["id"], st["description"]),
                )


def _seed_questions() -> None:
    questions = _load("questions.json")
    with get_connection() as conn:
        for q in questions:
            conn.execute(
                """INSERT OR IGNORE INTO quiz_questions
                   (id, domain_id, subtopic_id, stem, choice_a, choice_b, choice_c, choice_d, correct_answer, explanation)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    q["id"], q["domain_id"], q["subtopic_id"], q["stem"],
                    q["choice_a"], q["choice_b"], q["choice_c"], q["choice_d"],
                    q["correct_answer"], q["explanation"],
                ),
            )


def _seed_flashcards() -> None:
    cards = _load("flashcards.json")
    with get_connection() as conn:
        for c in cards:
            conn.execute(
                """INSERT OR IGNORE INTO flashcards
                   (id, subtopic_id, front, back, source)
                   VALUES (?,?,?,?,?)""",
                (c["id"], c["subtopic_id"], c["front"], c["back"], c.get("source", "")),
            )


def _seed_study_days() -> None:
    reading = _load("reading.json")
    reading_map: dict[tuple[int, int], str] = {
        (r["domain_id"], r["subtopic_id"]): r["content"] for r in reading
    }
    domains = _load("domains.json")

    # Build ordered list of (domain_id, subtopic_id) pairs
    # 31 subtopic days + 8 weighted review days (D2=3, D1=2, D3=2, D4=1)
    schedule: list[tuple[int, list[int]]] = []
    for domain in domains:
        for st in domain.get("subtopics", []):
            schedule.append((domain["id"], [st["id"]]))

    # Add 8 review days distributed by exam weight
    review_extra = [(2, [7]), (2, [8]), (2, [9]),   # D2 x3 (35%)
                    (1, [1]), (1, [3]),               # D1 x2 (30%)
                    (3, [13]), (3, [14]),              # D3 x2 (20%)
                    (4, [17])]                        # D4 x1 (15%)
    schedule.extend(review_extra)

    with get_connection() as conn:
        for day_num, (domain_id, subtopic_ids) in enumerate(schedule, start=1):
            st_id = subtopic_ids[0]
            content = reading_map.get(
                (domain_id, st_id),
                f"Study reading for Domain {domain_id}, Subtopic {st_id}.\n\nReview the official exam guide and Google Cloud documentation for this topic.",
            )
            conn.execute(
                """INSERT OR IGNORE INTO study_days (day_number, domain_id, subtopic_ids, reading_content)
                   VALUES (?,?,?,?)""",
                (day_num, domain_id, json.dumps(subtopic_ids), content),
            )
