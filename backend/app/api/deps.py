from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.entities import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise AppError("UNAUTHORIZED", "Not authenticated.", 401)
    try:
        payload = decode_token(creds.credentials, "access")
    except ValueError:
        raise AppError("UNAUTHORIZED", "Invalid or expired token.", 401)
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise AppError("UNAUTHORIZED", "Invalid or expired token.", 401)
    request.state.actor = user.email
    request.state.actor_role = user.role
    return user


def get_optional_user(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    if creds is None or not creds.credentials:
        return None
    try:
        payload = decode_token(creds.credentials, "access")
    except ValueError:
        return None
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        return None
    request.state.actor = user.email
    request.state.actor_role = user.role
    return user


def require_roles(*roles: str):
    def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles and user.role != "ADMIN":
            raise AppError("FORBIDDEN", "You do not have permission to perform this action.", 403)
        return user

    return _inner
