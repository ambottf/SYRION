-- SYRION Phase 0 — leeres Schema, keine Geschäftslogik
-- Nur technische Tabellen für spätere Phasen vorbereitet, aber leer.
-- SYRION_ARCHITEKTUR.md Kap. 3

-- Audit-Log Spiegel (append-only wird primär in Datei geführt, hier optional Index)
CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    prev_hash CHAR(64),
    entry_hash CHAR(64) NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB
);

-- Scheduler Jobs (APScheduler, SYRION_ARCHITEKTUR.md:11)
CREATE TABLE IF NOT EXISTS apscheduler_jobs (
    id TEXT PRIMARY KEY,
    next_run_time TIMESTAMPTZ,
    job_state BYTEA
);

-- Platzhalter-Schemas werden erst in Phase 1+ befüllt (keine Tabellen für Memory/Graph/Projekte jetzt)
