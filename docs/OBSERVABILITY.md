# Observability

## Logging
Backend and worker emit JSON lines to stdout: timestamp, level, service, message, request_id, path, method, status_code, duration_ms, environment.

Ship these to your log aggregator (CloudWatch, Datadog, ELK). Never log passwords, tokens, or raw PII account numbers.

## Metrics
No in-process Prometheus exporter is bundled. Scrape:

- request rate/latency from logs or an ingress mesh
- `/api/health/ready` as a synthetic check (fails when PostgreSQL or Redis is down)
- worker `job_runs` table for success/fail/dead_letter counts

## Health checks
- `GET /api/health` — liveness-ish plus redis status (does not fail the process)
- `GET /api/health/live` — process is up
- `GET /api/health/ready` — PostgreSQL + Redis required; 503 if either is missing in production configuration

## Tracing
Send `X-Request-ID` and `X-Correlation-ID`. The API echoes `X-Request-ID` on every response and stores it on audit events.
