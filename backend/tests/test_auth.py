import time

import auth


def test_correct_credentials_accepted():
    assert auth.verify_credentials("admin", "testpass") is True


def test_wrong_password_rejected():
    assert auth.verify_credentials("admin", "wrongpassword") is False


def test_wrong_username_rejected():
    assert auth.verify_credentials("notadmin", "testpass") is False


def test_token_is_valid_jwt():
    resp = auth.create_token()
    assert resp.token
    assert resp.expires_at > time.time() + 3600


def test_token_roundtrip():
    token = auth.create_token().token
    from jose import jwt
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "admin"
