# SYRION — Gesamtarchitektur v1.0
### Persönliche Intelligence-Plattform — Local-First | Auditierbar | Erweiterbar

**Status:** Architektur-Entwurf | **Datum:** 24.09.2026 | **Autor:** Leitende Architektur (Muse Spark)
**Prinzipien:** Local-First, Zero-Trust intern, Immutability der Sicherheitsregeln, Memory-Isolation

---

## 0. Leitprinzipien & Unveränderliche Leitplanken

Diese Regeln sind architektonisch hart verdrahtet und technisch erzwungen:

1.  **Kein Self-Modifying Model:** SYRION darf Gewichte/LoRA/Configs seiner lokalen KI-Modelle nicht schreiben. Modell-Updates nur durch `Mensch (Admin)` via signierten Release-Prozess.
2.  **Kein Self-Modifying Security:** `SecurityPolicy.yaml` und `RBAC` sind read-only zur Laufzeit. Änderungen nur offline, signiert, mit Audit-Log und 4-Augen-Freigabe (auch bei Single-User: explizite Bestätigung + Backup).
3.  **Kein Privilege Escalation:** Agenten/Tools laufen mit Capability-Tokens (zeitlich begrenzt, minimal). `Kernel` prüft jeden Call gegen `PolicyEngine`. Verstoß = Block + Audit-Eintrag.
4.  **Externes Memory zuerst:** Neues Wissen landet IMMER zuerst in `Quarantäne-Memory` (extern, versioniert, freigabepflichtig) bevor es in `Wissensdatenbank` oder `Wissensgraph` überführt wird.
5.  **Offline-fähig:** Alle Kernfunktionen ohne Internet lauffähig. Web-Recherche ist optionales, isoliertes Tool.

---

## 1. Module — Schichtenarchitektur

SYRION ist vertikal in 7 Schichten und horizontal in Domänen-Module gegliedert. Kommunikation nur über **API-Gateway** und **Event-Bus**, niemals direkt.

```
┌─────────────────────────────────────────────────────────────────┐
│ SCHICHT 7: PRESENTATION                                         │
│  Dashboard (Web) | Brain-Visualizer | Mobile Companion App      │
├─────────────────────────────────────────────────────────────────┤
│ SCHICHT 6: ORCHESTRATION                                        │
│  Agent-System | Aufgabenplanung (Scheduler) | Tool-Orchestrator │
├─────────────────────────────────────────────────────────────────┤
│ SCHICHT 5: INTELLIGENCE                                         │
│  LLM-Orchestrator | Vision | Audio | Bildgenerierung | RAG     │
├─────────────────────────────────────────────────────────────────┤
│ SCHICHT 4: MEMORY & KNOWLEDGE                                   │
│  STM | LTM | Wissensdatenbank | Wissensgraph | Vector-Store    │
├─────────────────────────────────────────────────────────────────┤
│ SCHICHT 3: TOOL & EXECUTION                                     │
│  Tool-System | Codeanalyse | Projektverwaltung | Web-Recherche  │
├─────────────────────────────────────────────────────────────────┤
│ SCHICHT 2: INFRASTRUCTURE                                       │
│  24/7-Hintergrundagent | Systemüberwachung | Audit-Log | Storage│
├─────────────────────────────────────────────────────────────────┤
│ SCHICHT 1: SECURITY KERNEL (querschneidend)                     │
│  Sicherheitscenter | PolicyEngine | PermissionService | Sandbox  │
└─────────────────────────────────────────────────────────────────┘
```

### Modul-Katalog (22 Module)

| ID | Modul | Aufgabe | Technologie-Hinweis |
|---|---|---|---|
| **P1** | Dashboard | Zentrales Cockpit, Widgets, Chat, File-Drop | Next.js 14 + Tailwind + shadcn |
| **P2** | Brain | Interaktiver Wissensgraph, Memory-Inspector | React Flow / Cytoscape.js, 3D mit Three.js |
| **O1** | Agent-System | Multi-Agent-Orchestrierung, Planner-Executor-Critic | LangGraph-ähnlich, eigen implementiert |
| **O2** | Scheduler | Cron + ereignisbasierte Aufgaben, 24/7 | APScheduler + Systemd/Windows Service |
| **O3** | Tool-Orchestrator | Tool-Routing, Capability-Checks | - |
| **I1** | SYRION Model | Eigenes SYRION Modell (Tokenizer/Vocab/Transformer) | `core/app/syrion_model/` |
| **I2** | Vision | Bildanalyse, OCR, Objekterkennung | LLaVA / Moondream / Florence-2 |
| **I3** | ImageGen | Lokale Bildgenerierung | Stable Diffusion XL + ComfyUI API |
| **I4** | Audio | STT, Speaker-ID, Audio-Analyse | Whisper large-v3 (faster-whisper), pyannote |
| **I5** | TTS | Optionale Sprachausgabe | Piper TTS (lokal, <100ms) |
| **I6** | RAG-Pipeline | Chunking, Embedding, Retrieval | - |
| **M1** | Kurzzeitgedächtnis (STM) | Kontextfenster, Session-Memory | Redis |
| **M2** | Langzeitgedächtnis (LTM) | Episodisch + Semantisch, konsolidiert | Postgres + Qdrant |
| **M3** | Wissensdatenbank | Dokumente, PDFs, Notizen (versioniert) | Postgres + S3-kompatibel (MinIO) |
| **M4** | Wissensgraph | Entitäten, Relationen, Provenienz | Neo4j oder FalkorDB / Kuzu (leichtgewichtig) |
| **T1** | Tool-System | Registry aller Tools, JSON-Schema | - |
| **T2** | Codeanalyse | Repo-Index, AST, Symbol-Suche | Tree-sitter + LSP |
| **T3** | Projektverwaltung | Projekte, Tasks, Dateien | - |
| **T4** | Web-Recherche | Gekapseltes Search+Scrape+FactCheck | SearXNG (lokal) + Trafilatura + Cross-Encoder |
| **F1** | Systemüberwachung | Metriken, Health, Ressourcen | Prometheus + Grafana (embedded) |
| **F2** | Audit-Log | Unveränderliches Log aller Aktionen | Append-only SQLite + Hash-Chain |
| **S1** | Sicherheitscenter | Policy, Freigaben, Quarantäne | OPA-ähnliche PolicyEngine |

> **Isolationsregel:** Jedes Modul hat eigene DB-Schema / eigenen Ordner. Kein Modul greift direkt auf die DB eines anderen zu.

---

## 2. Datenflüsse

### A) Ingestion-Flow (Neues Wissen -> Quarantäne)
```
[PDF/Bild/Audio/Web] -> Ingestion-Gateway -> Preprocessing
-> I2/I4 (Vision/Audio -> Text) -> I6 (Chunk+Embed)
-> M3_Quarantäne (Status: PENDING_REVIEW) -> Benachrichtigung an User
-> Freigabesystem -> bei APPROVED -> M3_Approved + M4 (Graph-Extraktion) + M2 (Vektor)
-> bei REJECTED -> bleibt isoliert, wird nicht für RAG genutzt
```

### B) Query-Flow (User fragt)
```
User (Chat/Sprache) -> P1 -> I4 (STT falls Audio) -> O1 (Agent-Planner)
-> O1 entscheidet: RAG? Tool? Vision? 
-> M1 (STM laden) + M2/M3/M4 (Retrieval via I6)
-> I1 (LLM generiert Antwort mit Kontext + Quellen)
-> PolicyEngine prüft Antwort (PII-Leak, Halluzination?)
-> P1 (Antwort + Quellenkarten + Graph-Highlight)
```

### C) Agent-Loop (24/7 Aufgabe)
```
Scheduler (O2) triggert Task -> O1 spawnt Agent
-> Agent hat Capability-Token (z.B. "read:projects, tool:web_search")
-> Tool-Orchestrator (O3) prüft Token bei jedem Tool-Call
-> Ergebnis -> Quarantäne-Memory (nie direkt ins Wissen)
-> Audit-Log (F2) + Mobile Push bei Bedarf
-> User-Freigabe erforderlich für persistente Änderungen
```

### D) Lern-Flow (Kontrolliertes Lernen)
```
Neues Wissen (approved) --/nicht automatisch/--> kein Fine-Tuning
Stattdessen: Retrieval-Learning (RAG) + Graph-Learning
Fine-Tuning nur manuell: Admin exportiert kuratiertes Dataset -> Offline-Training -> signiertes Modell-Release
```

**Event-Bus:** Alle Flüsse publizieren Events auf `SYRION-Bus` (NATS oder Redis Streams). Module subscriben nur ihre Events.

---

## 3. Datenbanken — Polyglot Persistence

SYRION nutzt nicht EINE, sondern 5 spezialisierte Datenbanken. Grund: Jede hat andere Zugriffsmuster.

| Datenbank | Zweck | Technologie | Warum |
|---|---|---|---|
| **Primary DB** | User, Projekte, Tasks, Freigaben, Scheduler-Jobs, Config | **PostgreSQL 16** (oder SQLite für v1 Solo-Setup) | ACID, Relationen, JSONB |
| **Vector DB** | Embeddings für RAG, semantische Suche | **Qdrant** (empfohlen, Rust, schnell, lokal) Alternative: Chroma | Cosine-Search, Filter, Payload |
| **Graph DB** | Wissensgraph, Entitäten, Provenienz | **Kuzu** (embedded, leicht) oder **Neo4j 5** (mächtiger) | Traversierung, Inferenz |
| **Cache / STM** | Kurzzeitgedächtnis, Sessions, Queues | **Redis 7** | TTL, Pub/Sub, schnell |
| **Object Store** | PDFs, Bilder, Audio, generierte Bilder | **MinIO** (S3-lokal) oder direkt Filesystem | Versionierung |

**Trennung:**
- `knowledge_quarantine` (Schema in Postgres + Qdrant Collection `_quarantine`) vs. `knowledge_approved`
- `audit_log` ist **append-only**, hash-verkettet (wie Git): `hash(n) = SHA256(hash(n-1) + entry(n))` — Manipulation erkennbar.
- Backups: Täglich verschlüsselt (age) nach `B:/SYRION_BACKUP` oder extern.

---

## 4. Lokale KI-Modelle — SYRION Eigenes Modell (kein Ollama)

SYRION verwendet **kein externes LLM (Llama/Qwen/Mistral) als Kern**. Stattdessen eigenes **SYRION-Modell** (Kap. 2 neues Brain).

| Schicht | Komponente | Status | Technologie |
|---|---|---|---|
| **Tokenizer** | `SyrionTokenizer` | Interface + `SimpleTokenizer` (Tests) | Eigene Vocab (`vocabulary.py`) |
| **Vocabulary** | `Vocabulary` | Versioniert, special tokens | JSON, `vocab.json` |
| **Embeddings** | `SyrionEmbeddings` | `d_model=64` (Tests), später 512+ | Sinusoidal pos. |
| **Transformer** | `SyrionTransformer` | `2 layers` (Tests), später 12/24 | Eigene Attention/FFN |
| **Model** | `SyrionModel` | `syrion-0.1.0-base` (64 dim) | `model.py` |
| **Training** | `TrainingPipeline` | Dry-run + Checkpoint | `training.py` |
| **Dataset** | `DatasetVersion` | Dedupe, hash | `dataset.py` |
| **Checkpoint** | `CheckpointManager` | versioniert, signierbar | `checkpoints/` |
| **Evaluation** | `Evaluator` | Perplexity/Accuracy | `evaluation.py` |
| **Inference** | `InferenceEngine` | Streaming, Timeout | `inference.py` |
| **Registry** | `SyrionModelRegistry` | Semver, active | `registry.py` |

**Architektur (neu, Brain-getrennt):**
```
SYRION MODEL (eigen, lokal)
        ↓
SYRION CORE (Orchestrierung)
        ↓
MEMORY (unabhängig, PENDING→APPROVED)
        ↓
KNOWLEDGE BASE (nur APPROVED)
        ↓
KNOWLEDGE GRAPH (Beziehungen)
```

**Regel:** `models/syrion/` ist versioniert, Gewichte nur via signiertem Checkpoint-Release. Kein Self-Modifying zur Laufzeit. Training nur offline, freigegeben.

---

## 5. APIs zwischen internen Modulen

Interne APIs sind versioniert (`/api/v1/...`), authentifiziert (mTLS intern + JWT mit Capability) und über ein Gateway gebündelt.

### 5.1 API-Gateway (Kern)
- **Einziger Einstiegspunkt.** Alle UI/Mobile/Agent-Calls gehen durch `Gateway :8080`.
- Verantwortlich für: Auth, Rate-Limit, Policy-Check, Routing, Audit-Logging.

### 5.2 Modul-APIs (REST + Events)

| Von -> Nach | Endpoint / Event | Beschreibung |
|---|---|---|
| Dashboard -> Gateway | `POST /api/v1/chat` | Chat mit Streaming (SSE) |
| Dashboard -> Gateway | `POST /api/v1/ingest` | Dokument/Bild hochladen -> Quarantäne |
| Agent -> Tool-Orchestrator | `POST /internal/v1/tools/:tool/execute` | Tool-Call (mit Capability-Token) |
| RAG -> VectorDB | `POST /internal/v1/retrieval/search` | Vektor-Suche |
| Memory -> Graph | `POST /internal/v1/graph/extract` | Entitäten aus Text extrahieren |
| Scheduler -> Agent | `Event: task.due` | Task fällig |
| Any -> Audit | `Event: audit.entry` | Audit-Eintrag schreiben |
| Security -> Any | `POST /internal/v1/policy/check` | Darf X das Y? |

**Kontrakt-Beispiel (Tool-Call):**
```json
POST /internal/v1/tools/web_search/execute
Headers: Authorization: Bearer <capability-token: agent-123, ttl:60s, scopes:[web_search]>
Body: { "query": "SYRION Architektur", "max_results": 5 }
-> PolicyEngine prüft: hat Agent web_search? Ja -> Ausführung in Sandbox -> Ergebnis zurück
```

**Event-Bus Topics (NATS):**
`ingest.new`, `memory.quarantine.new`, `memory.approved`, `agent.task.started`, `audit.*`, `system.health`

---

## 6. Sicherheitsgrenzen — Zonenmodell

SYRION hat 4 Sicherheitszonen. Daten dürfen nur nach außen fließen wenn die Regel es erlaubt.

```
Zone 0: KERNEL (höchste Privilegien)
  SecurityCenter, PolicyEngine, Audit-Log, KeyStore
  -> Niemals direkt von Agenten erreichbar
  -> Code ist signiert, unveränderlich zur Laufzeit

Zone 1: TRUSTED CORE
  Memory (approved), LLM-Gateway, Scheduler
  -> Nur via Gateway erreichbar, braucht Auth

Zone 2: SANDBOX (unsicher)
  Agent-System, Tool-System, Web-Recherche, Codeanalyse
  -> Läuft in Docker/gVisor Sandbox, kein direkter FS-Zugriff
  -> Nur via Capability-Tokens, Netzwerk nur via Proxy

Zone 3: QUARANTÄNE (untrusted)
  Ingestion, Web-Scrape-Ergebnisse, unbestätigtes Wissen
  -> Physikalisch getrennt (eigene DB/Collection)
  -> Kann niemals automatisch in Zone 1 gelangen

Zone 4: EXTERN
  Internet, Mobile Push Provider
  -> Nur via explizitem, geloggtem Egress-Proxy
```

**Technische Durchsetzung:**
- Filesystem: Zone 1/0 = read-only für Zone 2 (via Docker Volumes `:ro`)
- Netzwerk: Zone 2 hat `network_mode: isolated`, Egress nur über `egress-proxy :3128` (geloggt)
- Code: `import security_kernel` ist in Zone 2 geblockt (Linter + Laufzeit-Check)

---

## 7. Berechtigungen — RBAC + Capabilities + Freigabesystem

### 7.1 Rollen (RBAC)
| Rolle | Rechte |
|---|---|
| `Admin (Mensch)` | Alles, inkl. Policy-Änderung (offline signiert), Modell-Updates |
| `User` | Chat, Dokumente hochladen, Freigaben erteilen/ablehnen |
| `Agent-Background` | Nur was Scheduler ihm explizit gibt (z.B. `read:calendar`, `tool:notify`) |
| `Agent-Interactive` | Temporär für einen Chat (erbt User-Rechte minus kritische) |
| `Tool` | Minimal (z.B. `web_search` darf nur lesen, nicht schreiben) |

### 7.2 Capability-Tokens (für Agenten/Tools)
- Kurzlebig (60s - 24h), scop-spezifisch, nicht verlängerbar.
- Beispiel: `cap_abc123 {sub: agent-7, scopes: ["memory:read:approved", "tool:code_search"], exp: 60s}`
- Vergabe nur durch `Orchestrator` nach `PolicyEngine.check()`.

### 7.3 Benutzer-Freigabesystem (Kern-Feature)
Jede **schreibende** Aktion eines Agenten braucht Freigabe, es sei denn sie ist explizit als `auto_approved` in Policy markiert (z.B. `notify`).

**Zustände:** `PENDING` -> `APPROVED` | `REJECTED` | `EXPIRED`

**Flow:**
1. Agent will `wissensgraph.add_node` -> stattdessen `freigabe.create(type: graph_write, payload: ...)`
2. User sieht im Dashboard + Mobile: Karte mit Diff, Quelle, Risiko
3. User: Approve/Reject/Approve+Edit
4. Erst dann schreibt `Kernel` in approved Memory + Audit-Log

**Kategorien:**
- `memory_promote` (Quarantäne -> Approved) — immer Freigabe
- `file_write` / `project_change`
- `external_send` (Web, Push)
- `system_config` (nur Admin)

---

## 8. Speicherstruktur

Vorschlag für Single-Machine Setup (Windows, erweiterbar auf Linux-Server):

```
C:/SYRION/                          # Root (oder D:/SYRION)
├── config/
│   ├── SecurityPolicy.yaml         # IMMUTABLE, signiert
│   ├── models.yaml                 # Modell-Registry
│   └── dap-permissions.yaml
├── models/                         # READ-ONLY für SYRION
│   ├── llm/                        # GGUF / safetensors
│   ├── embeddings/
│   ├── vision/
│   └── tts/
├── data/
│   ├── primary.db                  # Postgres Data (oder sqlite)
│   ├── qdrant_storage/
│   ├── kuzu_db/
│   ├── redis_dump.rdb
│   ├── object_store/               # MinIO oder plain
│   │   ├── quarantine/             # Untrusted
│   │   ├── approved/
│   │   └── generated/              # Bilder
│   └── audit/
│       └── audit.log               # Hash-Chain, append-only
├── memory/
│   ├── stm/                        # Redis snapshots
│   ├── ltm/
│   └── quarantine/                 # JSON + Vektoren pending
├── projects/                       # User-Projekte (git-repos)
├── logs/
├── backups/                        # verschlüsselt, rotiert
└── sandbox/                        # Temp für Agent-Tool Ausführung
    └── workdir-*                   # ephemer, wird gelöscht
```

**Backup-Strategie:** Nightly `pg_dump` + `qdrant snapshot` + `audit.log` -> verschlüsselt (age) -> lokales NAS + optional verschlüsselter Cloud-Mirror.

---

## 9. UI — Modernes Dashboard & Brain

**Stack:** Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + Zustand + SSE für Streaming. Keine externe KI-API im Frontend.

### Dashboard-Layout
```
┌─ Sidebar ─┬─ Hauptbereich (Chat + Kontext) ─┬─ Inspector ─┐
│ SYRION ●  │  Chat (LLM)                      │ Quellen     │
│ Dashboard │  [Datei hierher ziehen ->        │ [PDF S.3]   │
│ Brain     │   Quarantäne-Vorschau]           │ [Graph-Node]│
│ Projekte  │  Antwort mit Zitationen          │ Freigaben   │
│ Aufgaben  │  ─────────────────               │ (3 pending) │
│ Freigaben │  Tool-Calls (aufklappbar)        │ Health      │
│ Audit     │                                  │             │
│ Settings  │  [🎤 Spracheingabe] [🔊 TTS]     │             │
└───────────┴──────────────────────────────────┴─────────────┘
```

**Kern-Seiten:**
1.  **Dashboard:** Health-Widgets (Model-Status, Memory-Füllstand, Agent-Tasks), Schnell-Chat, Pending Freigaben.
2.  **Brain (USP):** Interaktiver Wissensgraph (React Flow). Nodes: Dokumente, Entitäten, Konzepte. Kanten: `belegt_durch`, `widerspricht`, `abgeleitet_von`. Klick auf Node -> Inspector mit Provenienz + Vektor-Suche. Zeit-Slider für Memory-Evolution.
3.  **Projekte:** File-Tree + Code-Suche + Agent-Chat pro Projekt (Repo-aware).
4.  **Freigaben:** Inbox-Prinzip wie GitHub PRs. Diff-Ansicht, Approve/Reject, Bulk.
5.  **Audit & Sicherheit:** Unveränderliches Log, Filter nach Agent/Tool, Policy-Viewer (read-only).
6.  **System:** Modell-Manager (nur Anzeige, kein Self-Update), Storage-Nutzung, Logs.

**Design-Prinzipien:** Dunkles, ruhiges Theme (slate/zinc + akzent cyan/violet), viel Whitespace, Monospace für Code/Logs, keine bunten Spielereien. Fühlt sich an wie Linear + Obsidian.

---

## 10. Mobile Architektur — Companion App

**Ziel:** Kein zweites SYRION auf dem Handy, sondern sichere Fernbedienung + Notifier.

**Variante A (empfohlen für v1, lokal-first):**
- **PWA** oder **Tauri/Capacitor** Wrapper um Dashboard (gleiche Next.js App, responsive)
- Push via **ntfy.sh (self-hosted)** oder **UnifiedPush**. Kein Firebase-Zwang.
- Verbindung via **WireGuard VPN** oder **Tailscale** nach Hause (SYRION ist nie öffentlich im Netz). Alternativ Cloudflare Tunnel mit mTLS.
- Features: Freigaben approve/reject, Chat, Spracheingabe (Whisper on-device), Task-Status, Push bei `task.completed` / `quarantine.new` / `alert`.

**Variante B (später, voll nativ):**
- Flutter / React Native App, teilt `API-Gateway` mit Dashboard. Offline-Cache für letzte Antworten.

**Sicherheit Mobile:**
- Biometrie-Pflicht, JWT kurzlebig (15min) + Refresh, Device-Binding.
- Kein direkter DB-Zugriff, alles via Gateway + PolicyEngine.

```
[Handy] --WireGuard--> [Heimnetz: SYRION Gateway :8080] --mTLS--> [Core]
   |                         |
   +-- ntfy (self-hosted) <--+-- Push: "3 Freigaben pending"
```

---

## 11. 24/7-Hintergrundagent & Aufgabenplanung

**Kein Dauer-LLM-Loop!** Das wäre teuer und instabil. Stattdessen ereignisgesteuert + Scheduler.

**Komponenten:**
- **Scheduler (O2):** APScheduler im Core-Prozess. Persistiert Jobs in Postgres (`apscheduler_jobs`). Unterstützt Cron, Intervall, Einmalig, Event-Trigger (`on: ingest.new`).
- **Hintergrund-Dienst:** Läuft als `Windows Service` / `systemd service` / Docker `restart: always`. Health-Check alle 30s. Bei Crash: Auto-Restart + Audit-Eintrag. Watchdog prüft alle 5min ob Scheduler lebt.
- **Agent-Worker-Pool:** Max 2-3 parallele Agenten, Queue (Redis Stream). Jeder Agent hat Timeout (z.B. 10min) und Budget (max Tool-Calls).
- **Ressourcenwächter:** Pausiert Agenten wenn CPU>90% oder RAM knapp oder Nutzer aktiv chattet (Priorität: interaktiv).

**Beispiel-Tasks:**
- `08:00 Täglich: Web-Recherche zu "KI News" -> Quarantäne -> Push "Zum Review bereit"`
- `Bei neuem PDF in projects/X: Auto-Chunk+Embed -> Quarantäne`
- `Stündlich: System-Health prüfen -> bei Fehler Push + Audit`

**Stromausfall:** Jobs sind persistent. Nach Reboot holt Scheduler verpasste Jobs nach (mit `misfire_grace_time`).

---

## 12. Entwicklungsphasen — Roadmap (inkrementell, jede Phase lieferfähig)

### Phase 0 — Fundament (2-3 Wochen)
- Repo + Monorepo-Setup (`/core`, `/dashboard`, `/models`, `/infra`)
- API-Gateway + Postgres + Redis + Qdrant via Docker Compose
- SecurityKernel Stub (PolicyEngine read-only) + Audit-Log (append-only)
- Health-Endpoint + Docker Setup für Windows/Linux

### Phase 1 — Kern-Chat & Memory (4-6 Wochen) — *Erster nutzbarer SYRION*
- LLM-Gateway (Ollama) + STT (Whisper) + TTS (Piper)
- STM (Redis) + LTM (Qdrant) + RAG-Pipeline (Chunk, Embed, Retrieve, Rerank)
- Dashboard Chat (Streaming) + Quellenanzeige
- Ingestion (PDF -> Markdown -> Quarantäne)

### Phase 2 — Wissen & Brain (4-5 Wochen)
- Wissensdatenbank (approved/quarantine) + Freigabesystem (Inbox)
- Wissensgraph (Kuzu) + Graph-Extraktion (LLM)
- Brain-Visualizer (React Flow) + Inspector
- Bildanalyse (LLaVA/Moondream)

### Phase 3 — Agenten & Tools (5-6 Wochen)
- Tool-System (Registry, JSON-Schema, Sandbox)
- Agent-System (Planner-Executor, LangGraph-light)
- Codeanalyse + Projektverwaltung
- Web-Recherche (SearXNG, isoliert, Quellenprüfung via Cross-Encoder)
- Aufgabenplanung (Scheduler)

### Phase 4 — Härtung & 24/7 (3-4 Wochen)
- 24/7-Dienst (Windows Service/systemd) + Watchdog + Ressourcenwächter
- Systemüberwachung (Prometheus/Grafana embedded) + Backup-Verschlüsselung
- Mobile PWA + ntfy Push + WireGuard-Anleitung
- Audit-Log Hash-Chain + Penetration-Test der Zonen

### Phase 5 — Bildgenerierung & Multimodal (3 Wochen)
- ComfyUI Integration (lokal, Queue)
- Audioanalyse (Speaker-ID, Keyword-Spotting)
- Multimodale RAG (Bild+Text gemeinsam)

### Phase 6 — Polish & Skalierung (laufend)
- Performance-Tuning (vLLM, Quantisierung), Evaluations-Suite (RAGAS)
- Wissens-Konsolidierung (Duplikat-Erkennung, Widerspruchs-Auflösung)
- Plugin-System für Community-Tools (signiert, sandboxed)
- Optional: Multi-User / Familien-Modus (echtes RBAC)

**Jede Phase endet mit:** Demo, Audit-Log Review, Backup-Test, Security-Policy Review (menschlich).

---

## Anhang A — Technologie-Entscheidungen (begründet)

| Entscheidung | Gewählt | Alternative | Grund |
|---|---|---|---|
| Vector DB | Qdrant | Chroma, Milvus | Rust, geringer RAM, gute Filter, lokal einfach |
| Graph DB | Kuzu (v1) -> Neo4j (skaliert) | - | Kuzu embedded = kein extra Server in v1 |
| LLM Server | SYRION eigenes Modell | Ollama/vLLM (entfernt) | Eigenes `syrion-0.1.0-base`, lokal, kein externes LLM als Kern |
| Primary DB | Postgres (prod) / SQLite (dev) | - | Postgres für Skalierung, SQLite für Solo-Start |
| Event Bus | Redis Streams (v1) -> NATS (prod) | Kafka | Redis schon da, leicht |
| Frontend | Next.js | SvelteKit | Ökosystem, shadcn, Streaming |

## Anhang B — Was SYRION explizit NICHT tut (Guardrails)

- Kein automatisches Fine-Tuning / LoRA-Training aus User-Daten
- Kein Schreiben in `SecurityPolicy.yaml` zur Laufzeit (auch nicht für Admin-Token)
- Kein direkter Internet-Egress außer via `egress-proxy` (geloggt, gefiltert)
- Kein Tool darf ohne Capability-Token schreibend agieren
- Keine Cloud-KI-API im Standardpfad (nur optional, explizit opt-in, geloggt)

---

**Nächster Schritt (empfohlen):** Phase 0 starten — `docker-compose.yml` + `SecurityPolicy.yaml` (leer, signiert) + `audit` + `gateway` Stub. Auf Wunsch generiere ich das Grundgerüst (ohne große Logik) als nächsten Schritt.

