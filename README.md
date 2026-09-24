# SYRION — Phase 0 Grundgerüst

> Stand: `0.1.0-phase0` | Architektur: `SYRION_ARCHITEKTUR.md` | Keine Anwendungslogik

## Was ist enthalten (nur Skelett)
- `docker-compose.yml` — Postgres 16 + Redis 7 + Qdrant + Gateway-Stub
- `config/SecurityPolicy.yaml` — immutable Stub, read-only
- `config/models.yaml` — alle Modelle `enabled: false`
- `config/permissions.yaml` — Scope-Definitionen, default deny
- `core/app/security/policy_engine.py` — read-only Stub, kein `save()`
- `core/app/audit/audit_log.py` — append-only JSONL + SHA256 Hash-Kette
- `core/app/gateway/main.py` — nur `GET /api/v1/health|ready|policy`

## Was ist NICHT enthalten
Kein Chat, kein RAG, keine Agenten/Tools, keine Vector/Graph Writes, keine Bild/Audio-Pipelines. Wartet auf Freigabe Phase 1.

## Start
```powershell
Copy-Item .env.example .env
docker compose up -d --build
curl http://localhost:8080/api/v1/health
```

## Leitplanken (hart)
- `SecurityPolicy.yaml` ist `immutable: true` — Änderungen nur offline, signiert
- `models/` ist im Container `:ro` gemountet
- Audit-Log ist append-only, hash-verkettet (`prev_hash` → `entry_hash`)

## Verifikation
- `GET /api/v1/health` → `audit_chain_ok: true`
- `docker compose ps` → postgres/redis/qdrant healthy
