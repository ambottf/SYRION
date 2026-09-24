"use client";
import { useState } from "react";

const CORE = "http://127.0.0.1:8080";

export default function ResearchPage() {
  const [topic, setTopic] = useState("SYRION");
  const [urls, setUrls] = useState("https://example.com\nhttps://httpbin.org/html");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true); setError(null); setResult(null);
    try {
      const r = await fetch(`${CORE}/api/v1/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, urls: urls.split("\n").map(s => s.trim()).filter(Boolean), tags: [topic.toLowerCase()], engine: "chromium" }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.message || JSON.stringify(j));
      setResult(j);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.02em" }}>Research Engine</h1>
        <p className="mono" style={{ color: "var(--text-3)", fontSize: 11, marginTop: 4 }}>Kontrolliert • PENDING • Quellenpflicht • kein ungeprüftes Übernehmen</p>
      </div>
      <div className="card">
        <div className="grid" style={{ gap: 12 }}>
          <div>
            <label className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>Thema</label>
            <input value={topic} onChange={e => setTopic(e.target.value)} style={{ width: "100%", marginTop: 4, padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)" }} />
          </div>
          <div>
            <label className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>URLs (eine pro Zeile, nur http/https, kein localhost)</label>
            <textarea value={urls} onChange={e => setUrls(e.target.value)} rows={3} style={{ width: "100%", marginTop: 4, padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)", fontFamily: "monospace", fontSize: 12 }} />
          </div>
          <button onClick={run} disabled={loading} className="btn primary" style={{ width: "fit-content" }}>{loading ? "Recherchiert…" : "Recherche starten"}</button>
        </div>
      </div>
      {error && <div style={{ padding: 12, borderRadius: 10, border: "1px solid rgba(239,68,68,.3)", background: "rgba(239,68,68,.08)", color: "#991b1b" }}>Fehler: {error}</div>}
      {result && (
        <div className="grid" style={{ gap: 12 }}>
          <div className="card">
            <div className="card-head"><div className="card-title">Ergebnis</div><span className="badge ok">{result.created} neu • {result.deduped} Duplikate • {result.contradictions} Widersprüche</span></div>
            <div className="mono" style={{ fontSize: 11, color: "var(--text-3)" }}>Task {result.task_id} • {result.fetched} Quellen geholt • {result.sources.length} Quellen</div>
            <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
              {result.entries.map((e: any) => (
                <div key={e.id} style={{ padding: 10, border: "1px solid var(--border)", borderRadius: 10, background: "var(--surface-2)" }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{e.content.slice(0, 120)}</div>
                  <div className="mono" style={{ color: "var(--text-3)", fontSize: 10, marginTop: 4 }}>{e.id} • {e.trust_status} • {e.source} • {e.url?.slice(0, 60)}</div>
                  <div style={{ marginTop: 4 }}><span className="badge warn">PENDING</span> <span className="mono" style={{ fontSize: 10, color: "var(--text-3)" }}>{e.tags.join(", ")}</span></div>
                </div>
              ))}
              {result.entries.length === 0 && <div className="empty">Keine neuen Fakten — Duplikate oder nicht relevant.</div>}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Quellen</div>
            {result.sources.map((s: any, i: number) => (
              <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                <div style={{ fontWeight: 600 }}>{s.url}</div>
                {s.title && <div className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>{s.title}</div>}
                {s.error && <div style={{ color: "var(--danger)", fontSize: 11 }}>Fehler: {s.error}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
