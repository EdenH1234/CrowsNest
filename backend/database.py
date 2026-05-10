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
                image_tag       TEXT NOT NULL DEFAULT '',
                last_seen       REAL NOT NULL,
                status          TEXT NOT NULL DEFAULT 'running',
                deleted_at      REAL DEFAULT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_logs_container_name
                ON logs(container_name, timestamp);
        """)
        try:
            conn.execute("ALTER TABLE containers ADD COLUMN image_tag TEXT NOT NULL DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE containers ADD COLUMN deleted_at REAL DEFAULT NULL")
        except Exception:
            pass


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
    image_tag: str = "",
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
                 image_tag, last_seen, status, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(container_name) DO UPDATE SET
                container_id    = excluded.container_id,
                compose_project = excluded.compose_project,
                compose_service = excluded.compose_service,
                image_tag       = excluded.image_tag,
                last_seen       = excluded.last_seen,
                status          = excluded.status,
                deleted_at      = CASE WHEN excluded.status = 'running' THEN NULL ELSE deleted_at END
            """,
            (container_name, container_id, compose_project, compose_service,
             image_tag, time.time(), status),
        )
        return is_restart


def get_containers(include_deleted: bool = False) -> list[dict]:
    with get_conn() as conn:
        where = "" if include_deleted else "WHERE deleted_at IS NULL"
        rows = conn.execute(
            f"SELECT * FROM containers {where} ORDER BY compose_project, container_name"
        ).fetchall()
        return [dict(r) for r in rows]


def get_deleted_containers() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM containers WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC"
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
    else:
        clauses.append(
            "container_name NOT IN (SELECT container_name FROM containers WHERE deleted_at IS NOT NULL)"
        )

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


def soft_delete_group(compose_project: str | None) -> int:
    """Marks all containers in a group as deleted. Returns number of containers marked."""
    with get_conn() as conn:
        if compose_project:
            cur = conn.execute(
                "UPDATE containers SET deleted_at = ? WHERE compose_project = ? AND deleted_at IS NULL",
                (time.time(), compose_project),
            )
        else:
            cur = conn.execute(
                "UPDATE containers SET deleted_at = ? WHERE compose_project IS NULL AND deleted_at IS NULL",
                (time.time(),),
            )
        return cur.rowcount


def recover_group(compose_project: str | None) -> int:
    """Clears deleted_at for all containers in a group. Returns number recovered."""
    with get_conn() as conn:
        if compose_project:
            cur = conn.execute(
                "UPDATE containers SET deleted_at = NULL WHERE compose_project = ? AND deleted_at IS NOT NULL",
                (compose_project,),
            )
        else:
            cur = conn.execute(
                "UPDATE containers SET deleted_at = NULL WHERE compose_project IS NULL AND deleted_at IS NOT NULL",
                (),
            )
        return cur.rowcount


def purge_deleted_containers(before: float) -> int:
    """Hard-deletes containers (and their logs) soft-deleted before the given timestamp."""
    with get_conn() as conn:
        names = conn.execute(
            "SELECT container_name FROM containers WHERE deleted_at IS NOT NULL AND deleted_at < ?",
            (before,),
        ).fetchall()
        if not names:
            return 0
        placeholders = ",".join("?" * len(names))
        name_list = [r["container_name"] for r in names]
        conn.execute(
            f"DELETE FROM logs WHERE container_name IN ({placeholders})", name_list
        )
        conn.execute("INSERT INTO logs_fts(logs_fts) VALUES('rebuild')")
        cur = conn.execute(
            f"DELETE FROM containers WHERE container_name IN ({placeholders})", name_list
        )
        return cur.rowcount


def delete_old_logs(retention_days: int) -> int:
    cutoff = time.time() - retention_days * 86400
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM logs WHERE timestamp < ?", (cutoff,))
        if cur.rowcount:
            conn.execute("INSERT INTO logs_fts(logs_fts) VALUES('rebuild')")
        return cur.rowcount
