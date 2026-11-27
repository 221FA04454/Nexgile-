from datetime import timedelta
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.redis import incr_with_ttl
from app.core.security import (
    create_access_token,
    create_refresh_token_pair,
    hash_token,
    utcnow,
    verify_password,
)
from app.models import entities as m
from app.services.audit import record_audit


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def _rate_limit_login(request: Request, email: str) -> None:
    settings = get_settings()
    ip = _client_ip(request)
    key = f"rl:login:{ip}:{email.lower()}"
    count = incr_with_ttl(key, settings.login_rate_window_seconds)
    if count > settings.login_rate_limit:
        raise AppError("RATE_LIMITED", "Too many attempts. Please wait before trying again.", 429)


def issue_tokens(user: m.User, db: Session, request: Request) -> tuple[str, str]:
    settings = get_settings()
    extra = {"uid": user.id, "name": user.full_name, "household_id": user.household_id}
    access = create_access_token(user.email, user.role, extra)
    raw, hashed = create_refresh_token_pair()
    rec = m.RefreshToken(
        user_id=user.id,
        token_hash=hashed,
        jti=hash_token(raw + ":jti")[:32],
        expires_at=utcnow() + timedelta(days=settings.refresh_token_expire_days),
        ip_address=_client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:255],
    )
    db.add(rec)
    db.flush()
    return access, raw


def authenticate(db: Session, request: Request, email: str, password: str) -> tuple[m.User, str, str]:
    settings = get_settings()
    _rate_limit_login(request, email)
    user = db.query(m.User).filter(m.User.email == email.lower()).first()
    dummy = False
    if not user or not user.is_active:
        dummy = True
    if user and user.locked_until and user.locked_until > utcnow():
        record_audit(
            db,
            actor=email,
            actor_role=getattr(user, "role", ""),
            action="login_locked",
            entity_type="User",
            result="denied",
            ip_address=_client_ip(request),
            request_id=getattr(request.state, "request_id", ""),
        )
        db.commit()
        raise AppError("UNAUTHORIZED", "Your account is temporarily locked. Please try again later.", 401)
    ok = False if dummy else verify_password(password, user.hashed_password)
    if not ok:
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.max_failed_logins:
                user.locked_until = utcnow() + timedelta(minutes=settings.lockout_minutes)
            db.add(user)
        record_audit(
            db,
            actor=email,
            actor_role=getattr(user, "role", "") if user else "",
            action="login_failed",
            entity_type="User",
            result="denied",
            ip_address=_client_ip(request),
            request_id=getattr(request.state, "request_id", ""),
        )
        db.commit()
        raise AppError("UNAUTHORIZED", "Invalid email or password.", 401)
    if not user.email_verified:
        record_audit(
            db,
            actor=user.email,
            actor_role=user.role,
            action="login_failed",
            entity_type="User",
            entity_id=str(user.id),
            result="denied",
            reason="email_unverified",
            ip_address=_client_ip(request),
            request_id=getattr(request.state, "request_id", ""),
        )
        db.commit()
        raise AppError("EMAIL_UNVERIFIED", "Please verify your email address before signing in.", 403)
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    db.add(user)
    access, refresh = issue_tokens(user, db, request)
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="login",
        entity_type="User",
        entity_id=str(user.id),
        result="success",
        ip_address=_client_ip(request),
        request_id=getattr(request.state, "request_id", ""),
    )
    return user, access, refresh


def rotate_refresh(db: Session, request: Request, raw: str) -> tuple[m.User, str, str]:
    if not raw:
        raise AppError("UNAUTHORIZED", "Not authenticated.", 401)
    hashed = hash_token(raw)
    rec = db.query(m.RefreshToken).filter(m.RefreshToken.token_hash == hashed).first()
    if not rec or rec.revoked_at is not None or rec.expires_at < utcnow():
        if rec and rec.revoked_at is not None:
            db.query(m.RefreshToken).filter(m.RefreshToken.user_id == rec.user_id, m.RefreshToken.revoked_at.is_(None)).update(
                {m.RefreshToken.revoked_at: utcnow()}
            )
        raise AppError("UNAUTHORIZED", "Invalid or expired token.", 401)
    rec.revoked_at = utcnow()
    user = db.query(m.User).filter(m.User.id == rec.user_id, m.User.is_active.is_(True)).first()
    if not user:
        raise AppError("UNAUTHORIZED", "Invalid or expired token.", 401)
    access, new_raw = issue_tokens(user, db, request)
    rec.replaced_by_hash = hash_token(new_raw)
    db.add(rec)
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="token_refresh",
        entity_type="User",
        entity_id=str(user.id),
        result="success",
        ip_address=_client_ip(request),
        request_id=getattr(request.state, "request_id", ""),
    )
    return user, access, new_raw


def revoke_refresh(db: Session, request: Request, raw: str, user: m.User | None) -> None:
    if raw:
        hashed = hash_token(raw)
        rec = db.query(m.RefreshToken).filter(m.RefreshToken.token_hash == hashed).first()
        if rec:
            rec.revoked_at = utcnow()
            db.add(rec)
    if user:
        record_audit(
            db,
            actor=user.email,
            actor_role=user.role,
            action="logout",
            entity_type="User",
            entity_id=str(user.id),
            result="success",
            ip_address=_client_ip(request),
            request_id=getattr(request.state, "request_id", ""),
        )
