"use client";
import { useEffect, useState, useRef } from "react";

const CORE = "http://127.0.0.1:8080";

type Ev = { ts: string; time: string; message: string; topic?: string; level?: string };

export default function ActivityPage() {
  const [events, setEvents] = useState<Ev[]>([]);
  const [connected, setConnected] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let es: EventSource | null = null;
    let cancelled = false;
    async function init() {
      try {
        const r = await fetch(`${CORE}/api/v1/activity`);
        const j = await r.json();
        if (!cancelled) setEvents(j.events || []);
      } catch {}
      try {
        es = new EventSource(`${CORE}/api/v1/activity/stream`);
        es.onopen = () => setConnected(true);
        es.onerror = () => setConnected(false);
        es.onmessage = (e) => {
          try {
            const obj = JSON.parse(e.data);
            setEvents(prev => [...prev.slice(-150), obj]);
          } catch {}
        };
      } catch {}
    }
    init();
    return () => { cancelled = true; es?.close(); };
  }, []);

  useEffect(() => { listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" }); }, [events]);

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.02em" }}>Live Activity Stream</h1>
          <p className="mono" style={{ color: "var(--text-3)", fontSize: 11, marginTop: 4 }}>SSE • automatisch aktualisiert • {connected ? "verbunden" : "getrennt"}</p>
        </div>
        <span className={`badge ${connected ? "ok" : "warn"}`}>{connected ? "● Live" : "● Offline"}</span>
      </div>
      <div ref={listRef} style={{ background: "#0b1220", color: "#e2e8f0", borderRadius: 12, border: "1px solid #1e293b", padding: 12, height: 480, overflowY: "auto", fontFamily: "ui-monospace, monospace", fontSize: 12, lineHeight: 1.6 }}>
        {events.length === 0 ? <div style={{ color: "#64748b" }}>Warte auf Ereignisse…</div> : events.map((e, i) => (
          <div key={i} style={{ display: "flex", gap: 8, padding: "2px 0", borderBottom: "1px solid rgba(255,255,255,.06)" }}>
            <span style={{ color: "#38bdf8" }}>[{e.time || e.ts.slice(11, 19)}]</span>
            <span style={{ color: e.level === "warning" ? "#f59e0b" : "#94a3b8" }}>{e.message}</span>
            {e.topic && <span style={{ color: "#a78bfa" }}>• {e.topic}</span>}
          </div>
        ))}
      </div>
      <div className="card">
        <div className="card-title">Beispiel-Stream</div>
        <div className="mono" style={{ color: "var(--text-2)", fontSize: 12, marginTop: 6, lineHeight: 1.8 }}>
          [19:42:03] Research gestartet<br />[19:42:07] Quelle gefunden<br />[19:42:09] Inhalt analysiert<br />[19:42:12] neue Information erkannt<br />[19:42:13] Quelle gespeichert<br />[19:42:15] neue Beziehung erkannt<br />[19:42:16] Knowledge Graph aktualisiert
        </div>
      </div>
    </div>
  );
}
