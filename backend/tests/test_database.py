import time

import database


def _log(container_name="web", message="hello", stream="stdout", ts=None):
    return {
        "container_id": "abc123",
        "container_name": container_name,
        "compose_project": None,
        "compose_service": None,
        "timestamp": ts if ts is not None else time.time(),
        "stream": stream,
        "message": message,
    }


def test_insert_and_query(tmp_db):
    database.insert_logs([_log(message="hello world")])
    rows = database.query_logs()
    assert len(rows) == 1
    assert rows[0]["message"] == "hello world"


def test_query_filter_by_container(tmp_db):
    database.insert_logs([
        _log(container_name="web", message="web log"),
        _log(container_name="db", message="db log"),
    ])
    rows = database.query_logs(container_name="web")
    assert len(rows) == 1
    assert rows[0]["message"] == "web log"


def test_query_time_range(tmp_db):
    now = time.time()
    database.insert_logs([
        _log(message="old", ts=now - 200),
        _log(message="recent", ts=now),
    ])
    rows = database.query_logs(since=now - 10)
    assert len(rows) == 1
    assert rows[0]["message"] == "recent"


def test_fts_search(tmp_db):
    database.insert_logs([
        _log(message="connection refused"),
        _log(message="server started"),
    ])
    rows = database.query_logs(q="refused")
    assert len(rows) == 1
    assert "refused" in rows[0]["message"]


def test_upsert_container_and_get(tmp_db):
    database.upsert_container("id1", "web", "myapp", "web", "running")
    containers = database.get_containers()
    assert len(containers) == 1
    assert containers[0]["container_name"] == "web"
    assert containers[0]["status"] == "running"


def test_upsert_container_detects_restart(tmp_db):
    database.upsert_container("id1", "web", None, None, "running")
    is_restart = database.upsert_container("id2", "web", None, None, "running")
    assert is_restart is True


def test_delete_old_logs_respects_retention(tmp_db):
    now = time.time()
    database.insert_logs([
        _log(message="stale", ts=now - 40 * 86400),
        _log(message="fresh", ts=now),
    ])
    deleted = database.delete_old_logs(retention_days=30)
    assert deleted == 1
    remaining = database.query_logs()
    assert len(remaining) == 1
    assert remaining[0]["message"] == "fresh"
