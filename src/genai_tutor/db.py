"""Database connection and schema management."""

import sqlite3
from pathlib import Path

DB_DIR = Path.home() / ".genai_tutor"
DB_PATH = DB_DIR / "tutor.db"


def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS domains (
            id              INTEGER PRIMARY KEY,
            name            TEXT NOT NULL,
            section_number  INTEGER NOT NULL,
            exam_weight     REAL NOT NULL,
            description     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subtopics (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            domain_id   INTEGER NOT NULL REFERENCES domains(id),
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS flashcards (
            id            INTEGER PRIMARY KEY,
            subtopic_id   INTEGER NOT NULL REFERENCES subtopics(id),
            front         TEXT NOT NULL,
            back          TEXT NOT NULL,
            source        TEXT DEFAULT '',
            ease_factor   REAL DEFAULT 2.5,
            interval      INTEGER DEFAULT 0,
            repetitions   INTEGER DEFAULT 0,
            next_review   TEXT,
            last_reviewed TEXT
        );

        CREATE TABLE IF NOT EXISTS quiz_questions (
            id             INTEGER PRIMARY KEY,
            domain_id      INTEGER NOT NULL REFERENCES domains(id),
            subtopic_id    INTEGER NOT NULL REFERENCES subtopics(id),
            stem           TEXT NOT NULL,
            choice_a       TEXT NOT NULL,
            choice_b       TEXT NOT NULL,
            choice_c       TEXT NOT NULL,
            choice_d       TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS study_days (
            id              INTEGER PRIMARY KEY,
            day_number      INTEGER NOT NULL UNIQUE,
            domain_id       INTEGER NOT NULL REFERENCES domains(id),
            subtopic_ids    TEXT NOT NULL,
            reading_content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_progress (
            id                INTEGER PRIMARY KEY,
            study_day_id      INTEGER NOT NULL UNIQUE REFERENCES study_days(id),
            reading_complete  INTEGER DEFAULT 0,
            flashcard_complete INTEGER DEFAULT 0,
            quiz_complete     INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS quiz_results (
            id              INTEGER PRIMARY KEY,
            question_id     INTEGER NOT NULL REFERENCES quiz_questions(id),
            user_answer     TEXT NOT NULL,
            is_correct      INTEGER NOT NULL,
            answered_at     TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS flashcard_results (
            id           INTEGER PRIMARY KEY,
            flashcard_id INTEGER NOT NULL REFERENCES flashcards(id),
            quality      INTEGER NOT NULL,
            reviewed_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS imported_content (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            source_ref  TEXT    NOT NULL,
            domain_id   INTEGER NOT NULL REFERENCES domains(id),
            subtopic_id INTEGER NOT NULL REFERENCES subtopics(id),
            content     TEXT    NOT NULL,
            imported_at TEXT    NOT NULL
        );
        """)
