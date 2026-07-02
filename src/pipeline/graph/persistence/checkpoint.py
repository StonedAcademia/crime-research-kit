"""SQLite checkpointer for durable, resumable case-builder runs."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def case_checkpointer(case_dir: str):
    """Return a SqliteSaver persisted under <case_dir>/.runs/checkpoints.db."""
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise RuntimeError(
            "Checkpointing requires langgraph-checkpoint-sqlite. Install with `pip install -e '.[agentic]'`."
        ) from exc
    db_path = Path(case_dir) / ".runs" / "checkpoints.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), check_same_thread=False)
    connection.execute("PRAGMA user_version;")
    return SqliteSaver(connection)
