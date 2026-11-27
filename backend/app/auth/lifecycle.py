"""Registration, email verification, and password reset on the existing User/JWT model."""
from __future__ import annotations

import logging
import re
import secrets
from datetime import timedelta

from fastapi import Request
from sqlalchemy.orm import Session

from app.auth.email import dispatch_auth_email
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.redis import incr_with_ttl
from app.core.security import (
    generate_otp,
    hash_password,
    hash_token,
    utcnow,
    validate_registration_password,
)
from app.models import entities as m
from app.services.audit import record_audit

log = logging.getLogger("wealthagent.auth.lifecycle")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GENERIC_RESET = "If an account exists for that email, we sent reset instructions."
GENERIC_VERIFY = "If an account needs verification, we sent instructions."


def _ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "") or ""


def _rate_limit(request: Request, key: str, limit: int, window: int, message: str) -> None:
    ip = _ip(request)
    count = incr_with_ttl(f"rl:{key}:{ip}", window)
    if count > limit:
        raise AppError("RATE_LIMITED", message, 429)


def _initials(first: str, last: str) -> str:
    a = (first or "").strip()[:1]
    b = (last or "").strip()[:1]
    return ((a + b) or "NA").upper()


def _issue_challenge(db: Session, user: m.User, purpose: str, minutes: int, request_id: str) -> tuple[str, str, m.AuthToken]:
    db.query(m.AuthToken).filter(
        m.AuthToken.user_id == user.id,
        m.AuthToken.purpose == purpose,
        m.AuthToken.used_at.is_(None),
    ).update({m.AuthToken.used_at: utcnow()})
    raw = secrets.token_urlsafe(32)
    otp = generate_otp(6)
    row = m.AuthToken(
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_token(raw),
        otp_hash=hash_token(otp),
        expires_at=utcnow() + timedelta(minutes=minutes),
        request_id=request_id,
    )
    db.add(row)
    db.flush()
    return raw, otp, row


def _consume_token(db: Session, purpose: str, raw: str | None = None, otp: str | None = None) -> m.AuthToken:
    if not raw and not otp:
        raise AppError("UNAUTHORIZED", "This link is invalid or has expired.", 401)
    hashed = hash_token(raw) if raw else hash_token(otp)
    q = db.query(m.AuthToken).filter(m.AuthToken.purpose == purpose)
    if raw:
        row = q.filter(m.AuthToken.token_hash == hashed).first()
    else:
        row = q.filter(m.AuthToken.otp_hash == hashed).first()
    if not row or row.used_at is not None:
        raise AppError("UNAUTHORIZED", "This link is invalid or has expired.", 401)
    if row.expires_at < utcnow():
        raise AppError("UNAUTHORIZED", "This link has expired. Request a new one.", 401)
    row.used_at = utcnow()
    db.add(row)
    db.query(m.AuthToken).filter(
        m.AuthToken.user_id == row.user_id,
        m.AuthToken.purpose == purpose,
        m.AuthToken.used_at.is_(None),
        m.AuthToken.id != row.id,
    ).update({m.AuthToken.used_at: utcnow()})
    return row


def revoke_all_sessions(db: Session, user_id: int) -> None:
    db.query(m.RefreshToken).filter(m.RefreshToken.user_id == user_id, m.RefreshToken.revoked_at.is_(None)).update(
        {m.RefreshToken.revoked_at: utcnow()}
    )


def register(db: Session, request: Request, payload) -> dict:
    settings = get_settings()
    _rate_limit(
        request,
        "signup",
        settings.signup_rate_limit,
        settings.signup_rate_window_seconds,
        "Too many attempts. Please wait before trying again.",
    )
    email = (payload.email or "").strip().lower()
    first = (payload.first_name or "").strip()
    last = (payload.last_name or "").strip()
    if not first or not last:
        raise AppError("VALIDATION_ERROR", "First name and last name are required.", 422)
    if not EMAIL_RE.match(email):
        raise AppError("VALIDATION_ERROR", "Enter a valid email address.", 422)
    if not payload.accept_terms:
        raise AppError("VALIDATION_ERROR", "You must accept the Terms and Privacy Policy.", 422)
    if payload.password != payload.confirm_password:
        raise AppError("VALIDATION_ERROR", "Passwords do not match.", 422)
    failures = validate_registration_password(payload.password)
    if failures:
        raise AppError("VALIDATION_ERROR", "Password does not meet the requirements: " + "; ".join(failures) + ".", 422)
    existing = db.query(m.User).filter(m.User.email == email).first()
    if existing:
        raise AppError("CONFLICT", "An account with this email already exists.", 409)
    full_name = f"{first} {last}".strip()
    household = m.Household(
        name=f"{last} Household",
        primary_client_name=full_name,
        domicile="India",
        tax_filing_status="",
        risk_profile="Moderate Growth",
    )
    db.add(household)
    db.flush()
    user = m.User(
        email=email,
        full_name=full_name,
        first_name=first,
        last_name=last,
        hashed_password=hash_password(payload.password),
        role="CLIENT",
        title="Client",
        phone=(payload.phone or "").strip(),
        avatar_initials=_initials(first, last),
        household_id=household.id,
        is_active=True,
        email_verified=False,
        terms_accepted_at=utcnow(),
    )
    db.add(user)
    db.flush()
    raw, otp, _token = _issue_challenge(db, user, "email_verify", settings.verification_token_minutes, _rid(request))
    url = f"{settings.public_app_url.rstrip('/')}/verify-email?token={raw}"
    mail = dispatch_auth_email(
        purpose="email_verify",
        to_email=user.email,
        subject="Verify your Nexgile WealthAgent email",
        url=url,
        request_id=_rid(request),
    )
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="user_registered",
        entity_type="User",
        entity_id=str(user.id),
        result="success",
        ip_address=_ip(request),
        request_id=_rid(request),
    )
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="email_verification_requested",
        entity_type="User",
        entity_id=str(user.id),
        result="success",
        ip_address=_ip(request),
        request_id=_rid(request),
    )
    log.info("user_registered user_id=%s", user.id)
    body = {
        "status": "pending_verification",
        "message": "Check your email to verify your account before signing in.",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.role,
            "email_verified": False,
        },
    }
    if not settings.is_production:
        body["development"] = {
            "verification_url": mail.get("development_url"),
            "otp": otp,
            "note": mail.get("development_note"),
        }
    return body


def verify_email(db: Session, request: Request, token: str = "", otp: str = "") -> dict:
    row = _consume_token(db, "email_verify", raw=token or None, otp=otp or None)
    user = db.query(m.User).filter(m.User.id == row.user_id).first()
    if not user:
        raise AppError("UNAUTHORIZED", "This link is invalid or has expired.", 401)
    user.email_verified = True
    user.email_verified_at = utcnow()
    db.add(user)
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="email_verified",
        entity_type="User",
        entity_id=str(user.id),
        result="success",
        ip_address=_ip(request),
        request_id=_rid(request),
    )
    return {"status": "verified", "message": "Your email is verified. You can now sign in."}


def resend_verification(db: Session, request: Request, email: str) -> dict:
    settings = get_settings()
    _rate_limit(
        request,
        "verify",
        settings.auth_email_rate_limit,
        settings.auth_email_rate_window_seconds,
        "Too many attempts. Please wait before trying again.",
    )
    user = db.query(m.User).filter(m.User.email == (email or "").strip().lower()).first()
    body = {"status": "ok", "message": GENERIC_VERIFY}
    if user and user.is_active and not user.email_verified:
        raw, otp, _token = _issue_challenge(db, user, "email_verify", settings.verification_token_minutes, _rid(request))
        url = f"{settings.public_app_url.rstrip('/')}/verify-email?token={raw}"
        mail = dispatch_auth_email(
            purpose="email_verify",
            to_email=user.email,
            subject="Verify your Nexgile WealthAgent email",
            url=url,
            request_id=_rid(request),
        )
        record_audit(
            db,
            actor=user.email,
            actor_role=user.role,
            action="email_verification_requested",
            entity_type="User",
            entity_id=str(user.id),
            result="success",
            ip_address=_ip(request),
            request_id=_rid(request),
        )
        if not settings.is_production:
            body["development"] = {"verification_url": mail.get("development_url"), "otp": otp}
    return body


def forgot_password(db: Session, request: Request, email: str) -> dict:
    settings = get_settings()
    _rate_limit(
        request,
        "forgot",
        settings.auth_email_rate_limit,
        settings.auth_email_rate_window_seconds,
        "Too many attempts. Please wait before trying again.",
    )
    user = db.query(m.User).filter(m.User.email == (email or "").strip().lower()).first()
    body = {"status": "ok", "message": GENERIC_RESET}
    if user and user.is_active:
        raw, otp, _token = _issue_challenge(db, user, "password_reset", settings.reset_token_minutes, _rid(request))
        url = f"{settings.public_app_url.rstrip('/')}/reset-password?token={raw}"
        mail = dispatch_auth_email(
            purpose="password_reset",
            to_email=user.email,
            subject="Reset your Nexgile WealthAgent password",
            url=url,
            request_id=_rid(request),
        )
        record_audit(
            db,
            actor=user.email,
            actor_role=user.role,
            action="password_reset_requested",
            entity_type="User",
            entity_id=str(user.id),
            result="success",
            ip_address=_ip(request),
            request_id=_rid(request),
        )
        if not settings.is_production:
            body["development"] = {"reset_url": mail.get("development_url"), "otp": otp}
    return body


def reset_password(db: Session, request: Request, token: str, password: str, confirm: str) -> dict:
    if password != confirm:
        raise AppError("VALIDATION_ERROR", "Passwords do not match.", 422)
    failures = validate_registration_password(password)
    if failures:
        raise AppError("VALIDATION_ERROR", "Password does not meet the requirements: " + "; ".join(failures) + ".", 422)
    row = _consume_token(db, "password_reset", raw=token or None)
    user = db.query(m.User).filter(m.User.id == row.user_id).first()
    if not user:
        raise AppError("UNAUTHORIZED", "This link is invalid or has expired.", 401)
    user.hashed_password = hash_password(password)
    user.password_changed_at = utcnow()
    user.failed_login_count = 0
    user.locked_until = None
    db.add(user)
    revoke_all_sessions(db, user.id)
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="password_reset_completed",
        entity_type="User",
        entity_id=str(user.id),
        result="success",
        ip_address=_ip(request),
        request_id=_rid(request),
    )
    return {"status": "reset", "message": "Your password was updated. Sign in with your new password."}


def list_sessions(db: Session, user: m.User) -> dict:
    rows = (
        db.query(m.RefreshToken)
        .filter(m.RefreshToken.user_id == user.id)
        .order_by(m.RefreshToken.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "sessions": [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "revoked": r.revoked_at is not None,
                "ip_address": r.ip_address,
                "user_agent": r.user_agent,
            }
            for r in rows
        ]
    }


def revoke_session(db: Session, user: m.User, session_id: int) -> dict:
    row = db.query(m.RefreshToken).filter(m.RefreshToken.id == session_id, m.RefreshToken.user_id == user.id).first()
    if not row:
        raise AppError("RESOURCE_NOT_FOUND", "Session was not found.", 404)
    row.revoked_at = utcnow()
    db.add(row)
    return {"status": "ok"}
