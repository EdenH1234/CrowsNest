import time

import database


def test_login_success(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "testpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["expires_at"] > time.time()


def test_login_bad_credentials(client):
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_containers_requires_auth(client):
    resp = client.get("/api/containers")
    assert resp.status_code in (401, 403)


def test_containers_returns_list(client, auth_token):
    resp = client.get("/api/containers", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_logs_requires_auth(client):
    resp = client.get("/api/logs")
    assert resp.status_code in (401, 403)


def test_logs_returns_list(client, auth_token):
    resp = client.get("/api/logs", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_logs_search(client, auth_token):
    database.insert_logs([{
        "container_id": "abc",
        "container_name": "web",
        "compose_project": None,
        "compose_service": None,
        "timestamp": time.time(),
        "stream": "stdout",
        "message": "uniquecanarytoken",
    }])
    resp = client.get(
        "/api/logs?q=uniquecanarytoken",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert "uniquecanarytoken" in results[0]["message"]
