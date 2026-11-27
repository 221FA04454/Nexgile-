-- Nexgile WealthAgent — PostgreSQL schema foundation
-- SQLAlchemy creates tables at startup. This file documents the intended production DDL.

CREATE TABLE IF NOT EXISTS households (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    primary_client_name VARCHAR(255),
    risk_profile VARCHAR(64),
    domicile VARCHAR(128),
    tax_filing_status VARCHAR(64)
);

-- Remaining tables are created by SQLAlchemy metadata (see backend/app/models/entities.py).
-- Apply via: alembic upgrade head (production) or app startup create_all (MVP).
