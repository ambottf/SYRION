# SYRION — Root Dockerfile für Render / Fly.io / Railway
# Baut das SYRION Gateway (Python FastAPI) — dashboard wird separat als Static Site deployed
# Kontext: SYRION/ (root), nicht core/
FROM python:3.11-slim

WORKDIR /app

# Core-Abhängigkeiten
COPY core/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Core-Code
COPY core/app ./app
# Config (für Modelle, SecurityPolicy)
COPY config ./config

# Daten-Verzeichnisse (werden als Volumes gemountet, hier nur leere Struktur)
RUN mkdir -p /app/data/memory /app/data/model /app/checkpoints

EXPOSE 8080

CMD ["uvicorn", "app.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
