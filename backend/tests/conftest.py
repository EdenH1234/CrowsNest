import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import auth
import database


@pytest.fixture(autouse=True)
def setup_auth():
    saved = {k: os.environ.get(k) for k in ("SECRET_KEY", "ADMIN_USER", "ADMIN_PASSWORD")}
    os.environ.update({
        "SECRET_KEY": "test-secret-key",
        "ADMIN_USER": "admin",
        "ADMIN_PASSWORD": "testpass",
    })
    auth.init_auth()
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture
def tmp_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    database.set_db_path(db_file)
    database.init_db()
    return db_file


@pytest.fixture
def client(tmp_path):
    os.environ["DB_PATH"] = str(tmp_path / "test.db")
    with (
        patch("collector.start_collector", new_callable=AsyncMock),
        patch("collector.stop_collector", new_callable=AsyncMock),
        patch("retention.run_retention_loop", new_callable=AsyncMock),
    ):
        import main
        with TestClient(main.app) as c:
            yield c
    os.environ.pop("DB_PATH", None)


@pytest.fixture
def auth_token(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "testpass"})
    assert resp.status_code == 200
    return resp.json()["token"]
