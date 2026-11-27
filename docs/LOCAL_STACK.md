# Local PostgreSQL + Redis demo

The supported local architecture is:

```
Browser → React (Vite :5173)
       → FastAPI (:8000)
       → PostgreSQL
       → Redis
Worker → PostgreSQL + Redis
```

SQLite and in-memory Redis are **not** used for this demo. Tests may still use them.

## Start from a clean machine

```bash
copy .env.example .env
# Set POSTGRES_PASSWORD and JWT_SECRET in .env

docker compose down -v
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs
- Ready: http://localhost:8000/api/health/ready

Demo password `demo123` works only when `ALLOW_DEMO_SEED=true`.

## Inspect PostgreSQL

```bash
docker compose exec postgres psql -U wealthagent -d wealthagent
```

```sql
\dt
SELECT id, email, role, household_id FROM users ORDER BY id;
SELECT id, name, advisor_id FROM households;
SELECT id, household_id, name, account_type, market_value FROM accounts ORDER BY household_id, id;
SELECT h.id, h.symbol, h.quantity, h.price, a.name
  FROM holdings h JOIN accounts a ON a.id = h.account_id
  ORDER BY a.household_id, h.symbol;
SELECT id, household_id, name, category, current_amount, target_amount FROM goals;
SELECT id, household_id, title, estimated_benefit FROM tax_opportunities;
SELECT id, action, entity_type, result, timestamp FROM audit_events ORDER BY id DESC LIMIT 20;
SELECT id, job_name, status, attempt, started_at, finished_at FROM job_runs;
```

There is no public SQL endpoint.

## Validate seed integrity

```bash
docker compose exec backend python -m app.db.validate_demo
```

From the host (Postgres published on 5432):

```bash
python scripts/validate_demo_data.py
```

## Redis

```bash
docker compose exec redis redis-cli ping
docker compose exec redis redis-cli keys '*'
```

## Worker jobs

The worker writes `job_runs` rows for `daily_tlh_scan`, `rmd_monitor`, `data_reconciliation`, and `notifications`. Jobs do not book trades.
