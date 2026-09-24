# SYRION Core — Gateway Stub (Phase 0)

> Nur Health + Policy Stub + Audit Stub. Keine Chat/RAG/Agent-Logik.

## Struktur
```
core/
  app/
    gateway/main.py      # FastAPI: GET /api/v1/health|ready|policy
    security/policy_engine.py  # read-only Stub
    audit/audit_log.py         # append-only hash-chain
  tests/                 # pytest (reale Tests für Stubs)
  requirements.txt
  pyproject.toml
  Dockerfile
```

## Lokal starten (ohne Docker)
```powershell
cd core
pip install -r requirements.txt
$env:SECURITY_POLICY_PATH="../config/SecurityPolicy.yaml"
$env:AUDIT_LOG_PATH="../data/audit/audit.log"
uvicorn app.gateway.main:app --host 127.0.0.1 --port 8080 --reload
curl http://127.0.0.1:8080/api/v1/health
```

## Via Docker (Phase-0 Compose)
```powershell
docker compose up -d --build
curl http://localhost:8080/api/v1/health
```

## Tests
```powershell
cd core
pip install -e ".[dev]"
pytest -q
```

## Leitplanken
- `config/SecurityPolicy.yaml` ist `immutable: true`, im Container `:ro`
- `models/` ist `:ro` gemountet
- Audit-Log ist append-only, hash-verkettet
