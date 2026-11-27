from datetime import date

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_user, require_roles
from app.auth import service as auth_service
from app.auth import lifecycle as auth_lifecycle
from app.auth.access import assigned_household_ids, can_access_household
from app.calculations import engine as calc
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.redis import cache_delete_prefix, cache_get, cache_set, publish, redis_ready, redis_status
from app.core.security import PASSWORD_POLICY, utcnow
from app.db.session import database_status, get_db
from app.documents.storage import get_storage, validate_upload
from app.models import entities as m
from app.schemas.common import (
    ApprovalCreate,
    ApprovalDecide,
    ChatRequest,
    EmailRequest,
    LoginRequest,
    RebalanceRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyEmailRequest,
)
from app.services import wealth
from app.services.audit import record_audit

router = APIRouter()
REFRESH_COOKIE = "wa_refresh"


def _set_refresh_cookie(response: Response, token: str, remember_me: bool = True) -> None:
    settings = get_settings()
    kwargs = dict(
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )
    if remember_me:
        kwargs["max_age"] = settings.refresh_token_expire_days * 86400
    response.set_cookie(REFRESH_COOKIE, token, **kwargs)


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


def _user_payload(user: m.User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "role": user.role,
        "title": user.title,
        "initials": user.avatar_initials,
        "household_id": user.household_id,
        "phone": user.phone or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "email_verified": bool(user.email_verified),
        "mfa_enabled": bool(user.mfa_enabled),
    }


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "")


@router.get("/health")
def health():
    settings = get_settings()
    db = database_status()
    rd = redis_status()
    overall = "ok" if db.get("available") and (rd.get("available") or rd.get("backend") == "memory_fallback") else "degraded"
    return {
        "status": overall,
        "service": "Nexgile WealthAgent API",
        "environment": settings.environment,
        "as_of": settings.as_of_date,
        "demo_login_enabled": settings.demo_login_enabled,
        "database": db,
        "redis": rd,
    }


@router.get("/health/live")
def health_live():
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready():
    db = database_status()
    rd = redis_status()
    db_ok = bool(db.get("available"))
    rd_ok = redis_ready()
    if not db_ok or not rd_ok:
        raise AppError("SERVICE_UNAVAILABLE", "Required dependencies are unavailable.", 503)
    return {
        "status": "ready",
        "database": db,
        "redis": rd,
        "postgres": db_ok,
    }


@router.get("/auth/public-config")
def public_config():
    settings = get_settings()
    return {
        "environment": settings.environment,
        "demo_login_enabled": settings.demo_login_enabled,
        "as_of": settings.as_of_date,
        "password_policy": PASSWORD_POLICY,
        "currency": settings.default_currency,
        "locale": settings.default_locale,
    }


@router.post("/auth/signup", tags=["auth"])
def signup(payload: SignupRequest, request: Request, db: Session = Depends(get_db)):
    return auth_lifecycle.register(db, request, payload)


@router.post("/auth/verify-email", tags=["auth"])
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    return auth_lifecycle.verify_email(db, request, token=payload.token, otp=payload.otp)


@router.post("/auth/resend-verification", tags=["auth"])
def resend_verification(payload: EmailRequest, request: Request, db: Session = Depends(get_db)):
    return auth_lifecycle.resend_verification(db, request, payload.email)


@router.post("/auth/forgot-password", tags=["auth"])
def forgot_password(payload: EmailRequest, request: Request, db: Session = Depends(get_db)):
    return auth_lifecycle.forgot_password(db, request, payload.email)


@router.post("/auth/reset-password", tags=["auth"])
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    return auth_lifecycle.reset_password(db, request, payload.token, payload.password, payload.confirm_password)


@router.post("/auth/login")
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user, access, refresh = auth_service.authenticate(db, request, payload.email, payload.password)
    _set_refresh_cookie(response, refresh, remember_me=payload.remember_me)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": get_settings().access_token_expire_minutes * 60,
        "user": _user_payload(user),
    }


@router.post("/auth/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(REFRESH_COOKIE) or (request.headers.get("x-refresh-token") or "")
    user, access, new_raw = auth_service.rotate_refresh(db, request, raw)
    _set_refresh_cookie(response, new_raw)
    return {
        "access_token": access,
        "refresh_token": new_raw,
        "token_type": "bearer",
        "expires_in": get_settings().access_token_expire_minutes * 60,
        "user": _user_payload(user),
    }


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db), user: m.User | None = Depends(get_optional_user)):
    raw = request.cookies.get(REFRESH_COOKIE) or (request.headers.get("x-refresh-token") or "")
    if user is None and raw:
        from app.core.security import hash_token

        rec = db.query(m.RefreshToken).filter(m.RefreshToken.token_hash == hash_token(raw)).first()
        if rec:
            user = db.query(m.User).filter(m.User.id == rec.user_id).first()
    auth_service.revoke_refresh(db, request, raw, user)
    _clear_refresh_cookie(response)
    return {"status": "ok"}


@router.get("/auth/me")
def me(user: m.User = Depends(get_current_user)):
    return _user_payload(user)


@router.get("/auth/sessions")
def auth_sessions(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return auth_lifecycle.list_sessions(db, user)


@router.post("/auth/sessions/{session_id}/revoke")
def revoke_auth_session(session_id: int, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return auth_lifecycle.revoke_session(db, user, session_id)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    cached = cache_get(f"dash:{user.id}")
    if cached:
        cached["cache"] = "hit"
        return cached
    data = wealth.dashboard(db, user)
    cache_set(f"dash:{user.id}", data, 20)
    data["cache"] = "miss"
    return data


@router.get("/accounts")
def accounts(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.accounts_payload(db, user)


@router.get("/portfolios")
def portfolios(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.portfolio_payload(db, user)


@router.get("/portfolios/{portfolio_id}")
def portfolio_detail(portfolio_id: int, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.portfolio_payload(db, user, portfolio_id)


@router.get("/holdings")
def holdings(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    data = wealth.portfolio_payload(db, user)
    return {"holdings": data["summary"]["holdings"], "lineage": data["lineage"]}


@router.get("/goals")
def goals(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.goals_payload(db, user)


@router.get("/tax/opportunities")
def tax_opportunities(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.tax_payload(db, user)


@router.get("/estate")
def estate(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.estate_payload(db, user)


@router.get("/philanthropy")
def philanthropy(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.philanthropy_payload(db, user)


@router.get("/retirement")
def retirement(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.retirement_payload(db, user)


@router.get("/documents")
def documents(request: Request, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="document_list",
        entity_type="Document",
        request_id=_rid(request),
    )
    return wealth.documents_payload(db, user)


@router.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: m.User = Depends(get_current_user),
):
    hh = wealth.household_for_user(db, user)
    if not hh:
        raise AppError("FORBIDDEN", "No authorized household is available for this account.", 403)
    raw = await file.read()
    key = validate_upload(file.filename or "document", file.content_type or "", len(raw))
    stored = get_storage().put(key, raw, file.content_type or "application/octet-stream")
    classification = wealth.classify_document(file.filename or "document")
    category = "Tax" if "tax" in classification else "Estate" if "estate" in classification or "will" in classification else "Other"
    doc = m.Document(
        household_id=hh.id,
        name=file.filename,
        category=category,
        doc_type=(file.content_type or "file").split("/")[-1].upper()[:8],
        uploaded_on=date.today(),
        version="1.0",
        owner=user.full_name,
        status="current",
        ai_classification=classification,
        file_path=key,
    )
    db.add(doc)
    db.flush()
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="document_upload",
        entity_type="Document",
        entity_id=str(doc.id),
        after={"classification": classification, "storage": get_settings().object_storage_backend},
        request_id=_rid(request),
    )
    cache_delete_prefix(f"dash:{user.id}")
    from app.ai.rag.ingest import ingest_document

    ingest_document(db, doc, raw=raw, content_type=file.content_type or "")
    return {"id": doc.id, "name": doc.name, "ai_classification": classification, "status": "stored", "key": key}


@router.get("/messages")
def messages(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.messages_payload(db, user)


@router.get("/advisors/clients")
def advisor_clients(db: Session = Depends(get_db), user: m.User = Depends(require_roles("ADVISOR", "ADMIN"))):
    return wealth.advisor_clients(db, user)


@router.get("/advisors/clients/{household_id}")
def client_360(
    household_id: int,
    db: Session = Depends(get_db),
    user: m.User = Depends(require_roles("ADVISOR", "ADMIN")),
):
    return wealth.client_360(db, user, household_id)


@router.get("/reports")
def reports(request: Request, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    record_audit(db, actor=user.email, actor_role=user.role, action="report_list", entity_type="Report", request_id=_rid(request))
    return wealth.reports_payload(db, user)


@router.get("/reports/{report_id}")
def report_detail(report_id: int, request: Request, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="report_preview",
        entity_type="Report",
        entity_id=str(report_id),
        request_id=_rid(request),
    )
    return wealth.report_preview(db, user, report_id)


@router.post("/ai/chat")
def ai_chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    from app.ai.orchestrator import AIOrchestrator

    return AIOrchestrator(db, user, request_id=_rid(request)).chat(payload.message)


@router.get("/ai/status")
def ai_status(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    from app.ai.orchestrator import AIOrchestrator

    return AIOrchestrator(db, user).status()


@router.get("/ai/sources")
def ai_sources(q: str = Query(""), db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    from app.ai.orchestrator import AIOrchestrator

    return AIOrchestrator(db, user).sources(q)


@router.post("/ai/search")
def ai_search(payload: ChatRequest, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    from app.ai.orchestrator import AIOrchestrator

    return AIOrchestrator(db, user).sources(payload.message)


@router.post("/rebalance/preview")
def rebalance_preview(
    payload: RebalanceRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: m.User = Depends(get_current_user),
):
    idem = request.headers.get("idempotency-key")
    if idem:
        existing = db.query(m.IdempotencyKey).filter(m.IdempotencyKey.key == idem, m.IdempotencyKey.user_id == user.id).first()
        if existing:
            return existing.response_json
    port = wealth.portfolio_payload(db, user, payload.portfolio_id)
    if not port["portfolio"].get("id"):
        raise AppError("FORBIDDEN", "No authorized portfolio is available.", 403)
    preview = calc.rebalance_preview(port["summary"], port["targets"])
    rec = m.Rebalance(
        portfolio_id=port["portfolio"]["id"],
        status="preview",
        estimated_gains=preview["estimated_capital_gains"],
        estimated_tax=preview["estimated_tax_impact"],
        approval_required=True,
        payload=preview,
    )
    db.add(rec)
    db.flush()
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="rebalance_preview",
        entity_type="Portfolio",
        entity_id=str(port["portfolio"]["id"]),
        after={"book_of_record_modified": False, "rebalance_id": rec.id},
        request_id=_rid(request),
    )
    preview["rebalance_id"] = rec.id
    preview["book_of_record_modified"] = False
    if idem:
        db.add(
            m.IdempotencyKey(
                key=idem,
                user_id=user.id,
                method="POST",
                path="/api/rebalance/preview",
                response_json=preview,
                status_code=200,
            )
        )
    return preview


@router.get("/approvals")
def list_approvals(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    q = db.query(m.Approval)
    if user.role != "ADMIN":
        ids = assigned_household_ids(db, user) or {-1}
        q = q.filter((m.Approval.household_id.in_(ids)) | (m.Approval.requested_by_user_id == user.id))
    rows = q.order_by(m.Approval.created_at.desc()).all()
    return {
        "approvals": [
            {
                "id": a.id,
                "requested_by": a.requested_by,
                "role": a.role,
                "action": a.action,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "old_value": a.old_value,
                "new_value": a.new_value,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "notes": a.notes,
                "version": a.version,
            }
            for a in rows
        ]
    }


@router.post("/approvals")
def create_approval(
    payload: ApprovalCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: m.User = Depends(get_current_user),
):
    hh = wealth.household_for_user(db, user)
    idem = request.headers.get("idempotency-key")
    if idem:
        existing = db.query(m.Approval).filter(m.Approval.idempotency_key == idem).first()
        if existing:
            return {"id": existing.id, "status": existing.status, "idempotent": True}
    a = m.Approval(
        household_id=hh.id if hh else None,
        requested_by=user.full_name,
        requested_by_user_id=user.id,
        role=user.role,
        action=payload.action,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        new_value=payload.new_value,
        notes=payload.notes,
        status="pending",
        idempotency_key=idem,
    )
    db.add(a)
    db.flush()
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action="approval_request",
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        after=payload.new_value,
        request_id=_rid(request),
    )
    return {"id": a.id, "status": a.status}


@router.post("/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: int,
    payload: ApprovalDecide,
    request: Request,
    db: Session = Depends(get_db),
    user: m.User = Depends(require_roles("ADVISOR", "ADMIN", "CLIENT")),
):
    a = db.query(m.Approval).filter(m.Approval.id == approval_id).first()
    if not a:
        raise AppError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    if a.household_id and not can_access_household(db, user, a.household_id):
        raise AppError("FORBIDDEN", "You are not authorized to decide this approval.", 403)
    if a.status != "pending":
        raise AppError("CONFLICT", "This approval has already been decided.", 409)
    if payload.status not in {"approved", "rejected"}:
        raise AppError("BAD_REQUEST", "status must be approved or rejected.", 400)
    expected_version = a.version or 1
    a.status = payload.status
    a.decided_by = user.full_name
    a.decided_at = utcnow()
    a.notes = (a.notes or "") + f" | {payload.notes}"
    a.version = expected_version + 1
    record_audit(
        db,
        actor=user.email,
        actor_role=user.role,
        action=f"approval_{payload.status}",
        entity_type="Approval",
        entity_id=str(a.id),
        before={"status": "pending", "version": expected_version},
        after={"status": payload.status, "version": a.version},
        request_id=_rid(request),
    )
    cache_delete_prefix(f"dash:{user.id}")
    return {"id": a.id, "status": a.status, "book_of_record_modified": False, "version": a.version}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.notifications_payload(db, user)


@router.get("/search")
def search(q: str = Query(""), db: Session = Depends(get_db), user: m.User = Depends(get_current_user)):
    return wealth.search_payload(db, user, q)


@router.get("/audit")
def audit(db: Session = Depends(get_db), user: m.User = Depends(require_roles("ADVISOR", "ADMIN"))):
    q = db.query(m.AuditEvent)
    if user.role != "ADMIN":
        q = q.filter(m.AuditEvent.user == user.email)
    rows = q.order_by(m.AuditEvent.timestamp.desc()).limit(100).all()
    return {
        "events": [
            {
                "id": e.id,
                "user": e.user,
                "actor_role": e.actor_role,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "old_value": e.old_value,
                "new_value": e.new_value,
                "status": e.status,
                "result": e.result,
                "request_id": e.request_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in rows
        ]
    }


@router.get("/events/stream")
def events_foundation():
    publish("wealthagent.notifications", {"type": "heartbeat"})
    return {
        "channel": "wealthagent.notifications",
        "transport": "redis_pubsub",
        "redis": redis_status(),
        "note": "Subscribe via Redis pub/sub. Provider adapters remain mocked until credentials are supplied.",
    }


@router.get("/integrations")
def integrations_catalog(db: Session = Depends(get_db), user: m.User = Depends(require_roles("ADVISOR", "ADMIN"))):
    from app.integrations.service import list_integrations

    return list_integrations(db)


@router.get("/integrations/status")
def integrations_status(db: Session = Depends(get_db), user: m.User = Depends(require_roles("ADVISOR", "ADMIN"))):
    from app.integrations.service import status_summary

    return status_summary(db)


@router.get("/integrations/reconciliation")
def integrations_reconciliation(db: Session = Depends(get_db), user: m.User = Depends(require_roles("ADVISOR", "ADMIN"))):
    from app.integrations.service import reconciliation_queue

    return reconciliation_queue(db)


@router.get("/integrations/{provider}/health")
def integration_health(provider: str, db: Session = Depends(get_db), user: m.User = Depends(require_roles("ADVISOR", "ADMIN"))):
    from app.integrations.service import provider_health

    body = provider_health(db, provider)
    if body is None:
        raise AppError("NOT_FOUND", "Unknown integration provider.", 404)
    return body


@router.post("/integrations/{provider}/sync")
def integration_sync(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
    user: m.User = Depends(require_roles("ADVISOR", "ADMIN")),
):
    from app.integrations.service import trigger_sync

    body = trigger_sync(db, provider, actor=user.email, actor_role=user.role, request_id=_rid(request))
    if body is None:
        raise AppError("NOT_FOUND", "Unknown integration provider.", 404)
    return body


@router.get("/integrations/{provider}/sync-history")
def integration_sync_history(provider: str, db: Session = Depends(get_db), user: m.User = Depends(require_roles("ADVISOR", "ADMIN"))):
    from app.integrations.registry import get_provider
    from app.integrations.service import sync_history

    if not get_provider(provider):
        raise AppError("NOT_FOUND", "Unknown integration provider.", 404)
    return sync_history(db, provider)
