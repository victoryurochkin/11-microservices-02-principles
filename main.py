from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Security service", version="1.0.0")

JWT_SECRET = os.getenv("JWT_SECRET", "secret")
JWT_ALGORITHM = "HS256"
JWT_TTL_MINUTES = int(os.getenv("JWT_TTL_MINUTES", "60"))


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# In-memory storage is intentionally used only for a local homework demo.
users: dict[str, str] = {
    "bob": hash_password("qwe123"),
}


class Credentials(BaseModel):
    login: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def unauthorized(detail: str = "invalid or missing bearer token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise unauthorized()
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        raise unauthorized()
    return token


def decode_token(authorization: str | None) -> str:
    token = extract_bearer_token(authorization)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise unauthorized("token validation failed") from exc

    login = payload.get("sub")
    if not isinstance(login, str) or login not in users:
        raise unauthorized("unknown token subject")
    return login


def current_user(authorization: Annotated[str | None, Header()] = None) -> str:
    return decode_token(authorization)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "security"}


@app.post("/v1/user", status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials) -> dict[str, str]:
    if credentials.login in users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="user already exists")
    users[credentials.login] = hash_password(credentials.password)
    return {"login": credentials.login, "status": "registered"}


@app.get("/v1/user")
def get_user(login: Annotated[str, Depends(current_user)]) -> dict[str, str]:
    return {"login": login}


@app.post("/v1/token", response_model=TokenResponse)
def issue_token(credentials: Credentials) -> TokenResponse:
    stored_hash = users.get(credentials.login)
    supplied_hash = hash_password(credentials.password)
    if stored_hash is None or not hmac.compare_digest(stored_hash, supplied_hash):
        raise unauthorized("invalid login or password")

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=JWT_TTL_MINUTES)
    token = jwt.encode(
        {
            "sub": credentials.login,
            "iat": int(now.timestamp()),
            "exp": int(expires.timestamp()),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return TokenResponse(
        access_token=token,
        expires_in=JWT_TTL_MINUTES * 60,
    )


@app.get("/v1/token/validation")
@app.get("/v1/token/validation/", include_in_schema=False)
def validate_token(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, str | bool]:
    login = decode_token(authorization)
    return {"valid": True, "login": login}
