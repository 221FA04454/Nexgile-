# Nexgile WealthAgent Architecture

```
Users
  → React Web Frontend (+ future native mobile)
    → API Gateway / Authentication (FastAPI JWT)
      → Python FastAPI Backend
        → Redis / Realtime + Async Jobs + AI Engine
          → Business / Calculation Engine
            → Data Layer (SQLAlchemy, PostgreSQL-ready, SQLite fallback)
              → Integration Layer (adapter stubs)
```

Sensitive actions (rebalance, harvest, distribution, beneficiary change) write
Approval + AuditEvent rows and do not mutate the book of record from a preview.
