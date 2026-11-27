# Production Readiness — Nexgile WealthAgent

Post Phase-1 hardening. Status values are honest: **READY** means the control exists in this repository and is enforced. External systems are marked **REQUIRES_EXTERNAL_DEPENDENCY**.

| Area | Status | Notes |
|---|---|---|
| Architecture | PARTIAL | Web + FastAPI + worker + Postgres + Redis. Native mobile not built. |
| Security | PARTIAL | Headers, CORS allow-list, error envelope, upload allow-list, no secrets in source. TLS and WAF sit at the edge. |
| Authentication | READY | Argon2/bcrypt hashes, 15-minute access JWT, rotating refresh tokens, lockout, login rate limit. Demo users disabled when `ALLOW_DEMO_SEED=false`. |
| Authorization | READY | RBAC + household relationship checks. IDOR tests cover reports, search, advisor routes, approvals. |
| Database | READY | PostgreSQL required in production. Pooling, pre-ping, recycle. Alembic `001_initial`. SQLite only if `ALLOW_SQLITE=true` in development/test. |
| Redis | READY | Required in production. Cache, rate limit, pub/sub heartbeat. Memory fallback only with explicit `ALLOW_MEMORY_CACHE`. |
| Async jobs | PARTIAL | JobRun + idempotency + backoff + dead-letter. Jobs are read-only scans; they do not book trades. Scheduler is a loop, not Celery/SQS. |
| AI | PARTIAL | Authz-first retrieval, prompt/model version fields, disclaimer. Live LLM **REQUIRES_EXTERNAL_DEPENDENCY** (`GROQ_API_KEY` on the API server only). RAG uses JSON cosine embeddings. |
| Audit | READY | Append-only via API (no update/delete). Captures actor, role, action, entity, request_id, before/after, result. |
| Lineage | READY | source, provider, as_of, received_at, updated_at, version, data_quality_status, realtime flag. UI must use `lineage.display`. |
| Integrations | REQUIRES_EXTERNAL_DEPENDENCY | Adapter contract (timeout, retry, idempotency, error mapping) with **mock** providers only. |
| Testing | PARTIAL | Backend auth/IDOR/calc/approval/audit/health tests. Frontend error envelope, error boundary, role nav. Not a full E2E suite. |
| Docker | PARTIAL | Compose with healthchecks, env files, non-root backend/worker, prod nginx frontend. Secrets must come from `.env` / secret manager. |
| Observability | PARTIAL | JSON logs, request IDs, live/ready. No bundled APM/metrics exporter. |
| Deployment | NOT_READY | CI runs tests/build/migrations. No cloud deploy pipeline, no TLS cert automation, no secret manager integration. |
| Documents | PARTIAL | Type/size/name validation, local disk, S3 interface. S3 **REQUIRES_EXTERNAL_DEPENDENCY**. |
| Calculation engine | READY | Unchanged math; metadata includes fees/taxes/uncertainty; scenarios do not mutate the book. |

## Must be supplied outside this repo before go-live

- Managed PostgreSQL and Redis
- `JWT_SECRET` from a secret manager
- TLS terminating proxy
- Object storage credentials if not using local disk
- Custodian/CRM/recordkeeper credentials
- Optional LLM API key
- Production IdP/SSO (adapter stub only)

## Local development (explicit SQLite opt-in)

```
ENVIRONMENT=development
JWT_SECRET=<32+ chars>
DATABASE_URL=sqlite:///./wealthagent.db
ALLOW_SQLITE=true
ALLOW_MEMORY_CACHE=true
ALLOW_DEMO_SEED=true
ALLOW_CREATE_ALL=true
```

Production must not set those `ALLOW_*` flags to true.
