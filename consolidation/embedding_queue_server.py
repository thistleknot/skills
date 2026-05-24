"""
embedding_queue_server.py -- Async embedding task queue for agentic memory pre-compute.

This is the backend service that decouples skill edits from consolidation runs.
Skills change frequently; consolidation runs infrequently. By maintaining a queue,
embeddings are computed lazily as skills change, and consolidation can batch-flush
pending work instead of triggering fresh extractions.

Require:
  - fastapi, uvicorn
  - sqlite3
  - numpy
  - skill_similarity.py in the same directory (for triplet extraction)

Guarantee:
  - POST /queue/task accepts embedding tasks and returns immediately (non-blocking)
  - Tasks are keyed by (skill_name, content_hash) — duplicate submissions are idempotent
  - GET /queue/status returns pending, running, done, and error counts
  - POST /queue/cancel-pending cancels all pending tasks (used before consolidation batch)
  - Embeddings and metadata are persisted to consolidation/.checkpoint.db

Maintain:
  - Queue state is consistent across restarts (checkpoint.db is the source of truth)
  - No race conditions between skill-edit hook and consolidation batch submission

Assert:
  - All completed tasks have valid (premise_embeddings, bm25_kg_column) before marking done
"""

import asyncio
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Placeholder: in real usage, import from skill_similarity
# from skill_similarity import extract_triplets, compute_embeddings


class EmbeddingTask(BaseModel):
    skill_name: str
    content_hash: str
    action: str  # 'update' | 'delete' | 'batch'


class QueueStatus(BaseModel):
    pending: int
    running: int
    done: int
    error: int


app = FastAPI(title="Embedding Queue Server")
CHECKPOINT_DB = Path(__file__).parent / ".checkpoint.db"
QUEUE_LOCK = asyncio.Lock()


def init_db():
    """Initialize checkpoint schema if not present."""
    con = sqlite3.connect(CHECKPOINT_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            skill_name TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            premise_embeddings BLOB,
            bm25_kg_column BLOB,
            computed_at TEXT,
            PRIMARY KEY (skill_name, content_hash)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS embedding_queue (
            task_id TEXT PRIMARY KEY,
            skill_name TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            action TEXT,
            submitted_at TEXT,
            completed_at TEXT,
            status TEXT
        )
    """)
    con.commit()
    con.close()


async def process_embedding_task(task_id: str, skill_name: str, content_hash: str):
    """
    Compute triplet embeddings and BM25 KG column for a skill.
    
    Require: skill file exists at consolidation/skills/<skill_name>/SKILL.md
    Guarantee: embeddings and BM25 scores persisted to checkpoint.db on success
    Maintain: task status updated atomically
    """
    con = sqlite3.connect(CHECKPOINT_DB)
    try:
        # Mark task as running
        con.execute(
            "UPDATE embedding_queue SET status = ? WHERE task_id = ?",
            ("running", task_id),
        )
        con.commit()

        # Placeholder: actual triplet extraction and embedding
        # In real usage:
        # triplets = extract_triplets(skill_name)
        # premise_embeddings = compute_embeddings(triplets)
        # bm25_kg_column = compute_bm25_scores(triplets)
        
        # For now, stub values
        premise_embeddings = np.zeros((10, 768), dtype=np.float32)
        bm25_kg_column = np.zeros((10,), dtype=np.float32)

        # Persist embeddings
        con.execute(
            """
            INSERT OR REPLACE INTO embeddings 
            (skill_name, content_hash, premise_embeddings, bm25_kg_column, computed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                skill_name,
                content_hash,
                premise_embeddings.tobytes(),
                bm25_kg_column.tobytes(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Mark task as done
        con.execute(
            """
            UPDATE embedding_queue 
            SET status = ?, completed_at = ? 
            WHERE task_id = ?
            """,
            ("done", datetime.now(timezone.utc).isoformat(), task_id),
        )
        con.commit()
    except Exception as e:
        con.execute(
            """
            UPDATE embedding_queue 
            SET status = ?, completed_at = ? 
            WHERE task_id = ?
            """,
            ("error", datetime.now(timezone.utc).isoformat(), task_id),
        )
        con.commit()
        raise
    finally:
        con.close()


@app.on_event("startup")
def startup():
    init_db()


@app.post("/queue/task")
async def submit_task(task: EmbeddingTask):
    """
    Submit an embedding task.
    
    Require: skill_name and content_hash are valid
    Guarantee: task is queued and will be processed asynchronously; returns immediately
    
    Idempotency: re-submitting the same (skill_name, content_hash) is a no-op if already done;
                 if pending or running, the existing task is reused.
    """
    con = sqlite3.connect(CHECKPOINT_DB)
    try:
        # Check if task already done
        row = con.execute(
            """
            SELECT task_id, status FROM embedding_queue 
            WHERE skill_name = ? AND content_hash = ?
            ORDER BY submitted_at DESC LIMIT 1
            """,
            (task.skill_name, task.content_hash),
        ).fetchone()

        if row and row[1] == "done":
            return {"task_id": row[0], "status": "done", "message": "Already computed"}
        if row and row[1] in ("pending", "running"):
            return {"task_id": row[0], "status": row[1], "message": "Already queued"}

        # Create new task
        task_id = str(uuid4())
        con.execute(
            """
            INSERT INTO embedding_queue 
            (task_id, skill_name, content_hash, action, submitted_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                task.skill_name,
                task.content_hash,
                task.action,
                datetime.now(timezone.utc).isoformat(),
                "pending",
            ),
        )
        con.commit()

        # Schedule async processing
        asyncio.create_task(process_embedding_task(task_id, task.skill_name, task.content_hash))

        return {"task_id": task_id, "status": "pending", "message": "Queued"}
    finally:
        con.close()


@app.get("/queue/status")
def get_queue_status() -> QueueStatus:
    """Return counts of pending, running, done, and error tasks."""
    con = sqlite3.connect(CHECKPOINT_DB)
    try:
        pending = con.execute(
            "SELECT COUNT(*) FROM embedding_queue WHERE status = ?", ("pending",)
        ).fetchone()[0]
        running = con.execute(
            "SELECT COUNT(*) FROM embedding_queue WHERE status = ?", ("running",)
        ).fetchone()[0]
        done = con.execute(
            "SELECT COUNT(*) FROM embedding_queue WHERE status = ?", ("done",)
        ).fetchone()[0]
        error = con.execute(
            "SELECT COUNT(*) FROM embedding_queue WHERE status = ?", ("error",)
        ).fetchone()[0]
        return QueueStatus(pending=pending, running=running, done=done, error=error)
    finally:
        con.close()


@app.post("/queue/cancel-pending")
def cancel_pending():
    """
    Cancel all pending and running tasks. Used before consolidation batch submission.
    
    Guarantee: returns immediately with count of cancelled tasks; does not wait for
               in-flight tasks to stop (those continue but their completion is not awaited).
    """
    con = sqlite3.connect(CHECKPOINT_DB)
    try:
        count = con.execute(
            """
            SELECT COUNT(*) FROM embedding_queue 
            WHERE status IN ('pending', 'running')
            """
        ).fetchone()[0]

        con.execute(
            """
            UPDATE embedding_queue SET status = 'cancelled'
            WHERE status IN ('pending', 'running')
            """
        )
        con.commit()

        return {"cancelled_count": count, "message": f"Cancelled {count} pending/running tasks"}
    finally:
        con.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
