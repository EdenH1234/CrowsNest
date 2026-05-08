import os
import time

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

_bearer = HTTPBearer()

SECRET_KEY: str = ""
ADMIN_USER: str = ""
_admin_password_hash: str = ""

TOKEN_EXPIRE_SECONDS = 8 * 3600  # 8 hours
ALGORITHM = "HS256"


def init_auth() -> None:
    global SECRET_KEY, ADMIN_USER, _admin_password_hash
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
    raw_password = os.environ.get("ADMIN_PASSWORD", "admin")
    _admin_password_hash = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt())


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    expires_at: float


def create_token() -> TokenResponse:
    exp = time.time() + TOKEN_EXPIRE_SECONDS
    payload = {"sub": ADMIN_USER, "exp": exp}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return TokenResponse(token=token, expires_at=exp)


def verify_credentials(username: str, password: str) -> bool:
    if username != ADMIN_USER:
        return False
    return bcrypt.checkpw(password.encode(), _admin_password_hash)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
