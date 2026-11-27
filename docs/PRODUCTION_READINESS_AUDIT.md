# Production Readiness Audit — Nexgile WealthAgent

Inspected: `frontend/`, `backend/`, `worker/`, `ai/`, `database/`, `integrations/`, `docker-compose.yml`.

This audit describes the MVP **before** the Phase 1 hardening in this change set. Status values below are **pre-change**.

| Area | Current implementation | Risk | Required change | Status (pre-change) |
|---|---|---|---|---|
| Database | SQLAlchemy + **SQLite default** (`sqlite:///./wealthagent.db`). `create_all` on startup. No Alembic. No pool settings. Postgres image exists only in Compose. | Data loss, no concurrent writes, schema drift, silent SQLite in “prod”. | PostgreSQL required in production; pooling; Alembic; fail closed if misconfigured. | NOT_READY |
| Redis | Optional ping; **silent in-memory fallback** on any failure. | Split-brain cache, no rate-limit/job coordination in prod. | Redis required in production; explicit `ALLOW_MEMORY_CACHE` only in dev/test. | NOT_READY |
| Secrets / config | Hard-coded `secret_key`, SQLite URL, CORS defaults in `config.py`. Compose embeds `wealthagent/wealthagent`. Demo password `demo123` in seed. | Credential leak, token forgery. | Env-only secrets; `.env.example`; production startup validation; no demo users in production. | NOT_READY |
| Authentication | bcrypt + HS256 JWT, **8-hour** access token, no refresh, no revocation, no lockout, no login rate limit. Tokens in `localStorage`. | Stolen long-lived JWT; brute force; XSS token theft. | Short-lived access + refresh rotation; lockout; rate limit; no token logging. | NOT_READY |
| Authorization | Role check only on advisor/audit routes. `household_for_user` falls back to **first household** / hardcoded Morgan Family. Search lists **all households**. `portfolio_id` OR-query can load another book. `report_id` not scoped. Approvals listed globally. Participant fallback to `participants[0]`. | **IDOR/BOLA** — Client A can read Client B. | RBAC + relationship scope on every query; tests for IDOR. | NOT_READY |
| API structure | Single `router.py`; mixed auth. | Hard to reason about permissions. | Keep routes; add deps, request IDs, consistent errors. | PARTIAL |
| Models | Broad wealth domain; FKs present; missing lockout/refresh/job/idempotency; `datetime.utcnow`; incomplete lineage. | Weak audit/job/token persistence. | Additive columns/tables; UTC; indexes. | PARTIAL |
| Services | `wealth.py` + `ai_engine.py` assemble payloads from DB. | Scope bugs as above. | Authorize before load; empty-but-valid payloads when out of scope. | PARTIAL |
| Calculations | Functional; expose as_of/method/assumptions/limitations. Scenarios isolated. | Missing fees/taxes/uncertainty fields. | Extend metadata; do not change formulas. | PARTIAL |
| Worker | Loop + print; `create_all` + seed; no retries/idempotency/history. | Duplicate financial jobs on retry. | JobRun model; backoff; dead-letter; structured logs. | NOT_READY |
| AI | Keyword engine + optional OpenAI. Uses same `household_for_user` (leaky). | Cross-client context; unversioned prompts. | Authz-first retrieval; prompt/model version fields; no advice claim. | PARTIAL |
| Docker | Compose with hardcoded DB password; frontend runs **Vite dev**; root containers; no backend healthcheck. | Secrets in compose; non-prod image. | env files; healthchecks; non-root; prod frontend nginx. | NOT_READY |
| Environment | Partial `.env.example`; defaults in code. | Prod can boot with MVP secrets. | Fail if production vars missing. | NOT_READY |
| Tests | **None** in repo. | Regressions and IDOR undetected. | Auth, IDOR, calc, approval, audit, API, frontend unit tests. | NOT_READY |
| Audit log | `AuditEvent` exists; mutable via normal ORM; no request_id/role; `/api/audit` is read-only for advisor. | Weak forensics; no immutability policy. | Richer fields; no update/delete API; write on sensitive actions. | PARTIAL |
| Lineage | Static “as of / 5 minutes ago”. | Stale data presented as live. | Quality statuses; never label delayed data real-time. | PARTIAL |
| Error handling | Raw FastAPI `detail`; stack traces possible in debug. | Info leak. | Envelope `{error:{code,message,request_id}}`; no internals in prod. | NOT_READY |
| Observability | Uvicorn access logs only. Health does not check Postgres. | Blind incidents; false “ok”. | JSON logs; live/ready; duration; correlation ID. | NOT_READY |
| Documents | Local filesystem; weak type/size checks; path stored. | Malicious upload; path leak. | Validation; storage ABC; S3-ready; audit. | NOT_READY |
| Integrations | Stub `fetch()` only. | Fake “connected” impression. | Adapter contract: timeout/retry/idempotency/error mapping; mocks for test. | PARTIAL |
| Frontend | Working SPA; `localStorage` tokens; no error boundary; demo roles always shown. | XSS persistence; blank crash; prod demo login. | Memory/session token handling; refresh; error envelope; hide demo in prod. | PARTIAL |
| CI/CD | Absent. | Broken main undetected. | GitHub Actions: lint, tests, build, alembic check. | NOT_READY |

## Highest-severity findings (must fix in this phase)

1. **IDOR:** household fallback, global search, unscoped reports/portfolios/approvals/participants.
2. **SQLite as default runtime** and `create_all` as schema management.
3. **Hard-coded JWT secret** and demo password in seed used for all environments.
4. **Redis failures swallowed** — production would look healthy without cache/rate-limits.
5. **No automated tests** for authorization or calculations.

Implementation follows this document; it does not stop at documentation.
