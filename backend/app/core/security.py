from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import hmac
import secrets
import re

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

PASSWORD_PATTERN = re.compile(r".{8,}")
PRODUCTION_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{12,}$")
REGISTRATION_SPECIAL = re.compile(r"[^A-Za-z0-9]")

PASSWORD_POLICY = {
    "min_length": 10,
    "uppercase": True,
    "lowercase": True,
    "number": True,
    "special": True,
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def utcnow_aware() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def validate_password(password: str, production: bool = False) -> None:
    if production:
        if not PRODUCTION_PASSWORD_PATTERN.match(password or ""):
            raise ValueError("Password must be at least 12 characters and include upper, lower, and a digit.")
        return
    if not PASSWORD_PATTERN.match(password or ""):
        raise ValueError("Password must be at least 8 characters.")


def validate_registration_password(password: str) -> list[str]:
    """Return human-readable requirement failures. Empty list means the password is acceptable."""
    failures: list[str] = []
    value = password or ""
    if len(value) < PASSWORD_POLICY["min_length"]:
        failures.append(f"At least {PASSWORD_POLICY['min_length']} characters")
    if not re.search(r"[A-Z]", value):
        failures.append("One uppercase letter")
    if not re.search(r"[a-z]", value):
        failures.append("One lowercase letter")
    if not re.search(r"\d", value):
        failures.append("One number")
    if not REGISTRATION_SPECIAL.search(value):
        failures.append("One special character")
    return failures


def generate_otp(digits: int = 6) -> str:
    n = secrets.randbelow(10**digits)
    return str(n).zfill(digits)


def _secret() -> str:
    secret = get_settings().jwt_secret
    if not secret:
        raise RuntimeError("JWT_SECRET is not configured")
    return secret


def create_access_token(subject: str, role: str, extra: Optional[dict] = None) -> str:
    settings = get_settings()
    expire = utcnow_aware() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": utcnow_aware(),
        "jti": secrets.token_urlsafe(16),
        "typ": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _secret(), algorithm=settings.algorithm)


def create_refresh_token_pair() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    secret = _secret().encode()
    return hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()


def decode_token(token: str, token_type: str = "access") -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, _secret(), algorithms=[settings.algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
    if payload.get("typ", "access") != token_type:
        raise ValueError("Invalid token type")
    return payload
