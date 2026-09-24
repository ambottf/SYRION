"use client";
import { useEffect, useState } from "react";

type ModelStatus = {
  state: "ok" | "degraded" | "unavailable";
  message: string;
  active_model: string;
  configured_default: string | null;
  reachable: boolean;
  available: boolean;
  ollama_url?: string;
  engine?: string;
  resources: { ram_available_mb?: number | null; disk_free_gb?: number; sufficient_for_7b?: boolean | null; sufficient_for_syrion_base?: boolean | null };
};

export function SystemStatus() {
  const [ram, setRam] = useState<number | null>(null);
  const [model, setModel] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const anyNav = performance as any;
    if (anyNav?.memory?.usedJSHeapSize) {
      const tick = () => setRam(Math.round(anyNav.memory.usedJSHeapSize / 1024 / 1024));
      tick();
      const id = setInterval(tick, 3000);
      return () => clearInterval(id);
    } else {
      setRam(412);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function fetchStatus() {
      try {
        const r = await fetch("http://127.0.0.1:8080/api/v1/models/status", { cache: "no-store" });
        if (!r.ok) throw new Error(String(r.status));
        const j = (await r.json()) as ModelStatus;
        if (!cancelled) setModel(j);
      } catch {
        if (!cancelled) setModel(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchStatus();
    const id = setInterval(fetchStatus, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const badge =
    loading ? <span className="badge soon">lädt…</span> :
    !model ? <span className="badge warn">Core offline</span> :
    model.state === "ok" ? <span className="badge ok">● {model.active_model}</span> :
    <span className="badge warn">● {model.state}</span>;

  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">Systemstatus</div>
        {badge}
      </div>

      {!model && !loading && (
        <div className="empty" style={{ padding: 14, marginBottom: 12 }}>
          <div style={{ fontWeight: 700 }}>Core nicht erreichbar</div>
          <div className="mono" style={{ color: "var(--text-2)", marginTop: 6 }}>SYRION Gateway :8080 offline — Dashboard läuft, LLM-Anbindung degraded. Core starten: <span className="mono">uvicorn app.gateway.main:app --port 8080</span></div>
        </div>
      )}

      {model && (
        <div style={{ marginBottom: 12, padding: "10px 12px", borderRadius: 10, border: `1px solid ${model.state === "ok" ? "rgba(16,185,129,.2)" : "rgba(245,158,11,.25)"}`, background: model.state === "ok" ? "rgba(16,185,129,.08)" : "rgba(245,158,11,.08)" }}>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{model.state === "ok" ? "SYRION Modell bereit" : "SYRION Basis aktiv"}</div>
          <div className="mono" style={{ color: "var(--text-2)", marginTop: 4, lineHeight: 1.4 }}>{model.message}</div>
          <div className="mono" style={{ color: "var(--text-3)", marginTop: 6, fontSize: 11 }}>Aktiv: {model.active_model} {model.configured_default ? `• Konfiguriert: ${model.configured_default}` : ""} • Engine: {model.engine ?? "syrion"} — erreichbar: {String(model.reachable)} • verfügbar: {String(model.available)}</div>
        </div>
      )}

      <div className="grid grid-3" style={{ gap: 12 }}>
        <div>
          <div className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>CPU</div>
          <div style={{ fontWeight: 800, marginTop: 4 }}>12% <span style={{ fontWeight: 400, color: "var(--text-2)", fontSize: 12 }}>idle</span></div>
          <div className="progress" style={{ marginTop: 8 }}><span style={{ width: "12%" }} /></div>
        </div>
        <div>
          <div className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>RAM</div>
          <div style={{ fontWeight: 800, marginTop: 4 }}>{ram ?? "—"} MB <span style={{ fontWeight: 400, color: "var(--text-2)", fontSize: 12 }}>/ 16 GB</span></div>
          <div className="progress" style={{ marginTop: 8 }}><span style={{ width: ram ? `${Math.min(90, Math.round((ram/16000)*100))}%` : "24%" }} /></div>
          {model?.resources && <div className="mono" style={{ color: "var(--text-3)", fontSize: 10, marginTop: 4 }}>Frei: {model.resources.ram_available_mb ?? "—"} MB • 7B ok: {String(model.resources.sufficient_for_7b)}</div>}
        </div>
        <div>
          <div className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>Storage</div>
          <div style={{ fontWeight: 800, marginTop: 4 }}>{model?.resources.disk_free_gb ?? 38} GB frei</div>
          <div className="progress" style={{ marginTop: 8 }}><span style={{ width: "38%" }} /></div>
        </div>
      </div>
      <div className="mono" style={{ marginTop: 12, color: "var(--text-3)", fontSize: 11 }}>Gateway :8080 • Models: {model?.active_model ?? "mock-echo"} — {loading ? "prüfe…" : model ? model.message : "Core offline, Mock aktiv"}</div>
    </div>
  );
}
