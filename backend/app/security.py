import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings


INSTANCE_DIR = Path(__file__).resolve().parents[1] / "instance"
KEY_FILE = INSTANCE_DIR / "identity.key"
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UserContext:
    username: str
    role: str


def _key() -> bytes:
    configured = os.getenv("IDENTITY_ENCRYPTION_KEY")
    if configured:
        return configured.encode()
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        KEY_FILE.write_bytes(Fernet.generate_key())
    return KEY_FILE.read_bytes().strip()


def _fernet() -> Fernet:
    return Fernet(_key())


def identity_hash(value: str) -> str:
    secret = hashlib.sha256(_key()).digest()
    return hmac.new(secret, value.strip().casefold().encode(), hashlib.sha256).hexdigest()


def pseudonym_for(value: str) -> str:
    digest = identity_hash(value)
    token = base64.b32encode(bytes.fromhex(digest[:10])).decode().rstrip("=")[:6]
    return f"Beneficiary {token}"


def encrypt_identity(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_identity(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def authenticate(username: str, password: str) -> UserContext | None:
    credentials = {"admin": (settings.admin_password, "org_admin"), "viewer": (settings.viewer_password, "viewer")}
    expected = credentials.get(username)
    if not expected or not hmac.compare_digest(password, expected[0]):
        return None
    return UserContext(username=username, role=expected[1])


def create_access_token(user: UserContext) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user.username, "role": user.role, "iat": now, "exp": now + timedelta(minutes=settings.jwt_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> UserContext:
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as error:
        raise HTTPException(401, "Invalid or expired access token") from error
    return UserContext(username=str(payload["sub"]), role=str(payload["role"]))


def require_org_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    if user.role != "org_admin":
        raise HTTPException(403, "org_admin access required")
    return user
