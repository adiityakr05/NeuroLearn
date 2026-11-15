
"""
SQLite database infrastructure for NeuroLearn.

Stores real learner review events independently from synthetic
training datasets.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Iterator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATABASE_DIR / "neurolearn.db"



def initialize_database() -> None:
    """Create the database and required tables if they do not exist."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS review_schedules (
                schedule_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                topic_id TEXT NOT NULL,
                predicted_retention_prob REAL NOT NULL,
                recommended_interval_days INTEGER NOT NULL,
                next_review_at TEXT NOT NULL,
                is_review_due INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, topic_id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_review_schedules_user_due
            ON review_schedules (user_id, next_review_at)
            """
        )

        # NEW: Study session completion history
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS study_session_completions (
                completion_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_date TEXT NOT NULL,
                planned_minutes INTEGER NOT NULL,
                actual_minutes INTEGER NOT NULL,
                topics_planned TEXT NOT NULL,
                topics_completed TEXT NOT NULL,
                completion_rate REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )



@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Provide a database connection with automatic cleanup."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
