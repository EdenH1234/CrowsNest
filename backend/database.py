import sqlite3
import time
from contextlib import contextmanager
from typing import Generator

DB_PATH: str = "/data/logs.db"


def set_db_path(path: str) -> None:
    global DB_PATH
    DB_PATH = path


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;

            CREATE TABLE IF NOT EXISTS logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                container_id    TEXT    NOT NULL,
                container_name  TEXT    NOT NULL,
                compose_project TEXT,
                compose_service TEXT,
                timestamp       REAL    NOT NULL,
                stream          TEXT    NOT NULL,
                message         TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_logs_container_ts
                ON logs(container_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp
                ON logs(timestamp);

            CREATE VIRTUAL TABLE IF NOT EXISTS logs_fts USING fts5(
                message,
                content=logs,
                content_rowid=id
            );

            CREATE TABLE IF NOT EXISTS containers (
                container_name  TEXT PRIMARY KEY,
                container_id    TEXT NOT NULL,
                compose_project TEXT,
                compose_service TEXT,
                last_seen       REAL NOT NULL,
                status          TEXT NOT NULL DEFAULT 'running'
            );

            CREATE INDEX IF NOT EXISTS idx_logs_container_name
                ON logs(container_name, timestamp);
        """)


def insert_logs(rows: list[dict]) -> None:
    if not rows:
        return
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO logs
                (container_id, container_name, compose_project, compose_service,
                 timestamp, stream, message)
            VALUES
                (:container_id, :container_name, :compose_project, :compose_service,
                 :timestamp, :stream, :message)
            """,
            rows,
        )
        # Keep FTS in sync
        conn.execute("INSERT INTO logs_fts(logs_fts) VALUES('rebuild')")


def upsert_container(
    container_id: str,
    container_name: str,
    compose_project: str | None,
    compose_service: str | None,
    status: str = "running",
) -> bool:
    """Returns True if this is a restart (same name, different container_id)."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT container_id FROM containers WHERE container_name = ?",
            (container_name,),
        ).fetchone()
        is_restart = (
            existing is not None
            and existing["container_id"] != container_id
            and status == "running"
        )
        conn.execute(
            """
            INSERT INTO containers
                (container_name, container_id, compose_project, compose_service,
                 last_seen, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(container_name) DO UPDATE SET
                container_id    = excluded.container_id,
                compose_project = excluded.compose_project,
                compose_service = excluded.compose_service,
                last_seen       = excluded.last_seen,
                status          = excluded.status
            """,
            (container_name, container_id, compose_project, compose_service,
             time.time(), status),
        )
        return is_restart


def get_containers() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM containers ORDER BY compose_project, container_name"
        ).fetchall()
        return [dict(r) for r in rows]


def query_logs(
    container_name: str | None = None,
    since: float | None = None,
    until: float | None = None,
    q: str | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[dict]:
    clauses: list[str] = []
    params: list = []

    if q:
        clauses.append(
            "id IN (SELECT rowid FROM logs_fts WHERE logs_fts MATCH ?)"
        )
        params.append(q)

    if container_name:
        clauses.append("container_name = ?")
        params.append(container_name)

    if since is not None:
        clauses.append("timestamp >= ?")
        params.append(since)

    if until is not None:
        clauses.append("timestamp <= ?")
        params.append(until)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params += [limit, offset]

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM logs {where} ORDER BY timestamp ASC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def delete_old_logs(retention_days: int) -> int:
    cutoff = time.time() - retention_days * 86400
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
        if cur.rowcount:
            conn.execute("INSERT INTO logs_fts(logs_fts) VALUES('rebuild')")
        return cur.rowcount
