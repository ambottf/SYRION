"use client";
import { useEffect, useState } from "react";

const CORE = "http://127.0.0.1:8080";

type Task = { id: string; topic: string; urls: string[]; interval_s: number; priority: number; status: string; enabled: boolean; run_count: number; error_count: number; last_run?: string };

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [status, setStatus] = useState("stopped");
  const [topic, setTopic] = useState("SYRION");
  const [urls, setUrls] = useState("https://example.com");
  const [interval, setIntervalVal] = useState(120);

  const load = async () => {
    const r = await fetch(`${CORE}/api/v1/scheduler`);
    const j = await r.json();
    setTasks(j.tasks || []);
    setStatus(j.status);
  };
  useEffect(() => { load(); const id = setInterval(load, 4000); return () => clearInterval(id); }, []);

  const create = async () => {
    await fetch(`${CORE}/api/v1/scheduler`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ topic, urls: urls.split("\n").map(s => s.trim()).filter(Boolean), interval_s: interval, priority: 5 }) });
    load();
  };
  const act = async (path: string) => { await fetch(`${CORE}/api/v1/scheduler/${path}`, { method: "POST" }); load(); };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.02em" }}>Scheduler — 24/7 Research</h1>
          <p className="mono" style={{ color: "var(--text-3)", fontSize: 11, marginTop: 4 }}>Status: {status} • {tasks.length} Tasks • max_parallel 3 • Timeout & Pause/Stop</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={() => act("start")} className="btn primary" style={{ padding: "6px 10px", fontSize: 12 }}>Start</button>
          <button onClick={() => act("pause")} className="btn" style={{ padding: "6px 10px", fontSize: 12 }}>Pause</button>
          <button onClick={() => act("stop")} className="btn ghost" style={{ padding: "6px 10px", fontSize: 12 }}>Stop</button>
          <button onClick={() => act("tick")} className="btn" style={{ padding: "6px 10px", fontSize: 12 }}>Tick (Test)</button>
        </div>
      </div>
      <div className="card">
        <div className="card-title" style={{ marginBottom: 8 }}>Neuer Task</div>
        <div className="grid" style={{ gap: 8 }}>
          <input value={topic} onChange={e => setTopic(e.target.value)} placeholder="Thema" style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)" }} />
          <textarea value={urls} onChange={e => setUrls(e.target.value)} rows={2} placeholder="URLs, eine pro Zeile" style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)", fontSize: 12, fontFamily: "monospace" }} />
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <label className="mono" style={{ fontSize: 11 }}>Intervall (s)</label>
            <input type="number" value={interval} onChange={e => setIntervalVal(parseInt(e.target.value) || 60)} style={{ width: 100, padding: "6px 8px", borderRadius: 8, border: "1px solid var(--border)" }} />
            <button onClick={create} className="btn primary">Erstellen</button>
          </div>
        </div>
      </div>
      <div className="grid" style={{ gap: 8 }}>
        {tasks.length === 0 ? <div className="empty">Keine Tasks — erstelle einen für Tests (z.B. alle 120s).</div> : tasks.map(t => (
          <div key={t.id} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 12, background: "var(--surface)", display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13 }}>{t.topic} <span className={`badge ${t.enabled ? "ok" : "warn"}`}>{t.enabled ? "enabled" : "paused"}</span> <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>{t.status} • alle {t.interval_s}s • Prio {t.priority}</span></div>
              <div className="mono" style={{ fontSize: 11, color: "var(--text-3)", marginTop: 4 }}>{t.urls.join(", ").slice(0, 80)} • runs {t.run_count} • errors {t.error_count} • {t.last_run?.slice(11, 19) ?? "nie"}</div>
            </div>
            <div style={{ display: "flex", gap: 6, alignItems: "start" }}>
              <button onClick={async () => { await fetch(`${CORE}/api/v1/scheduler/${t.id}/pause`, { method: "POST" }); load(); }} className="btn" style={{ padding: "4px 8px", fontSize: 11 }}>Pause</button>
              <button onClick={async () => { await fetch(`${CORE}/api/v1/scheduler/${t.id}/resume`, { method: "POST" }); load(); }} className="btn" style={{ padding: "4px 8px", fontSize: 11 }}>Resume</button>
              <button onClick={async () => { await fetch(`${CORE}/api/v1/scheduler/${t.id}`, { method: "DELETE" }); load(); }} className="btn ghost" style={{ padding: "4px 8px", fontSize: 11 }}>Löschen</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
