"use client";
import { useEffect, useState, useMemo } from "react";
import { BrainGraph } from "../../components/BrainGraph";
import { ErrorBoundary } from "../../components/ErrorBoundary";
import { knowledgeToGraph } from "../../lib/graphAdapter";

const CORE = "http://127.0.0.1:8080";

type BrainSnapshot = {
  nodes: any[];
  counts: { facts: number; pending: number; approved: number; total: number; relations: number; sources: number };
  topics: { tag: string; count: number }[];
  sources: { source: string; url: string | null; count: number }[];
  growth: { date: string; count: number }[];
  recent: any[];
  timestamp: string;
};

export default function BrainPage() {
  const [snap, setSnap] = useState<BrainSnapshot | null>(null);
  const [graphRaw, setGraphRaw] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [htRunning, setHtRunning] = useState(false);

  const load = async () => {
    try {
      const [s, g] = await Promise.all([
        fetch(`${CORE}/api/v1/brain?limit=100`).then(r => {
          if (!r.ok) throw new Error(`Brain ${r.status}`);
          return r.json();
        }),
        fetch(`${CORE}/api/v1/brain/graph?limit=200`).then(r => {
          if (!r.ok) throw new Error(`Graph ${r.status}`);
          return r.json();
        }),
      ]);
      // Handle error field from API (nie Crash)
      if ((s as any).error) throw new Error((s as any).error);
      if ((g as any).error) throw new Error((g as any).error);
      setSnap(s);
      setGraphRaw(g);
      setError(null);
    } catch (e: any) {
      // Nicht crashen, nur Fehler anzeigen, aber Seite bleibt stabil
      setError(e.message || "Unbekannter Fehler");
      // Behalte altes snap, falls vorhanden, für Stabilität
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 3000);
    let es: EventSource | null = null;
    try {
      es = new EventSource(`${CORE}/api/v1/activity/stream`);
      es.onmessage = () => load();
    } catch {}
    return () => {
      clearInterval(id);
      es?.close();
    };
  }, []);

  const graphData = useMemo(() => {
    if (!snap) return { nodes: [], edges: [] };
    const knowledgeNodes = snap.nodes?.length ? snap.nodes : [];
    if (knowledgeNodes.length > 0) {
      return knowledgeToGraph(knowledgeNodes);
    }
    if (graphRaw) {
      return {
        nodes: (graphRaw.nodes || []).map((n: any) => ({
          id: n.id,
          label: n.label,
          title: n.label,
          type: n.type,
          status: n.status,
          topic: n.tags?.[0] || n.type,
          timestamp: "",
          tags: n.tags || [],
          source: "",
        })),
        edges: (graphRaw.edges || []).map((e: any) => ({
          id: `${e.source}::${e.target}`,
          source: e.source,
          target: e.target,
          type: e.type || "related",
        })),
      };
    }
    return { nodes: [], edges: [] };
  }, [snap, graphRaw]);

  const toggleHt = async () => {
    const url = `http://127.0.0.1:8080/api/v1/brain/high-throughput/${htRunning ? "stop" : "start"}`;
    await fetch(url, { method: "POST" });
    const s = await fetch("http://127.0.0.1:8080/api/v1/brain/high-throughput/status").then(r => r.json());
    setHtRunning(s.running);
  };
  useEffect(() => {
    fetch("http://127.0.0.1:8080/api/v1/brain/high-throughput/status").then(r => r.json()).then(j => setHtRunning(j.running)).catch(() => {});
  }, []);

  if (loading) return <div className="grid" style={{ gap: 12 }}><div className="skeleton" style={{ height: 120 }} /><div className="skeleton" style={{ height: 520 }} /></div>;
  if (error) return <div className="card" style={{ borderColor: "var(--danger)" }}><strong>Fehler:</strong> {error}</div>;
  if (!snap) return <div className="empty">Keine Daten</div>;

  return (
    <div className="grid" style={{ gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.02em" }}>SYRION Brain</h1>
          <p className="mono" style={{ color: "var(--text-3)", fontSize: 11, marginTop: 4 }}>Live • {snap.timestamp.slice(0, 19)} • {snap.counts.total} Knoten • {snap.counts.relations} Beziehungen • 500/min {htRunning ? "● läuft" : "○ pausiert"}</p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button onClick={toggleHt} className={`btn ${htRunning ? "" : "primary"}`} style={{ padding: "6px 12px", fontSize: 12 }}>{htRunning ? "■ Stop" : "▶ Start 500/min"}</button>
          <span className="badge ok">● Live</span>
        </div>
      </div>

      <div className="grid grid-4" style={{ gap: 10 }}>
        <div className="card" style={{ padding: "12px 14px" }}><div className="card-title" style={{ fontSize: 11 }}>Fakten</div><div className="kpi" style={{ fontSize: 22 }}>{snap.counts.facts}</div><div className="kpi-sub" style={{ fontSize: 11 }}>approved</div></div>
        <div className="card" style={{ padding: "12px 14px" }}><div className="card-title" style={{ fontSize: 11 }}>Quellen</div><div className="kpi" style={{ fontSize: 22 }}>{snap.counts.sources}</div><div className="kpi-sub" style={{ fontSize: 11 }}>eindeutige URLs</div></div>
        <div className="card" style={{ padding: "12px 14px" }}><div className="card-title" style={{ fontSize: 11 }}>Beziehungen</div><div className="kpi" style={{ fontSize: 22 }}>{snap.counts.relations}</div><div className="kpi-sub" style={{ fontSize: 11 }}>Kanten</div></div>
        <div className="card" style={{ padding: "12px 14px" }}><div className="card-title" style={{ fontSize: 11 }}>Pending</div><div className="kpi" style={{ fontSize: 22 }}>{snap.counts.pending}</div><div className="kpi-sub" style={{ fontSize: 11 }}>zur Prüfung</div></div>
      </div>

      {/* ECHTER INTERAKTIVER GRAPH - KOMPAKT & STILL */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(15,23,42,.04)" }}>
          <div className="card-title" style={{ margin: 0, fontSize: 12 }}>Wissensgraph — Still & Kategorisiert</div>
          <span className="mono" style={{ color: "var(--text-3)", fontSize: 10 }}>{graphData.nodes.length} Knoten • {graphData.edges.length} Kanten • Still</span>
        </div>
        <ErrorBoundary>
          {graphData.nodes.length > 0 ? (
            <BrainGraph
              data={graphData}
              onNodeClick={(n) => setSelectedNode(n)}
              onEdgeClick={(e) => console.log("edge", e)}
            />
          ) : (
            <div className="empty" style={{ margin: 12, padding: 16, fontSize: 12 }}>Noch keine Knoten — starte Einspeisung mit ▶ Start 500/min oben.</div>
          )}
        </ErrorBoundary>
        <div className="mono" style={{ color: "var(--text-3)", fontSize: 10, padding: "6px 14px", borderTop: "1px solid var(--border)", background: "var(--bg-soft)", display: "flex", justifyContent: "space-between" }}>
          <span>Still • Kategorisiert (6 Cluster) • 10k+ fähig (Canvas)</span>
          <span>500/min graduell (9/sec), Start/Stop steuerbar</span>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-head"><div className="card-title">Themen</div></div>
          {snap.topics.length ? snap.topics.map(t => (
            <div key={t.tag} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 13 }}>
              <span>#{t.tag}</span><span className="badge soon">{t.count}</span>
            </div>
          )) : <div className="mono" style={{ color: "var(--text-3)" }}>Keine Themen</div>}
        </div>
        <div className="card">
          <div className="card-head"><div className="card-title">Quellen</div></div>
          {snap.sources.length ? snap.sources.slice(0, 8).map((s, i) => (
            <div key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
              <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.source}</div>
              {s.url && <div className="mono" style={{ color: "var(--text-3)", fontSize: 10, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.url}</div>}
              <span className="badge soon" style={{ fontSize: 10 }}>{s.count}</span>
            </div>
          )) : <div className="mono" style={{ color: "var(--text-3)" }}>Keine Quellen</div>}
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-head"><div className="card-title">Wachstum (Zeitverlauf)</div></div>
          {snap.growth.length ? (
            <div style={{ display: "flex", alignItems: "end", gap: 4, height: 80 }}>
              {snap.growth.map(g => (
                <div key={g.date} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <div style={{ width: "100%", background: "linear-gradient(180deg, var(--accent), var(--accent-2))", borderRadius: 4, height: Math.max(4, g.count * 12) }} />
                  <span className="mono" style={{ fontSize: 9, color: "var(--text-3)" }}>{g.date.slice(5)}</span>
                </div>
              ))}
            </div>
          ) : <div className="empty" style={{ padding: 12 }}>Noch kein Wachstum — warte auf APPROVED.</div>}
          <div className="mono" style={{ color: "var(--text-3)", fontSize: 11, marginTop: 8 }}>{snap.counts.approved} approved • {snap.counts.total} gesamt</div>
        </div>
        <div className="card">
          <div className="card-head"><div className="card-title">Letzte Aktivitäten (Memory)</div></div>
          {snap.recent.length ? snap.recent.map((r: any) => (
            <div key={r.id} style={{ display: "flex", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
              <span className={`badge ${r.trust_status === "APPROVED" ? "ok" : r.trust_status === "PENDING" ? "warn" : "soon"}`} style={{ height: 20 }}>{r.trust_status}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.content.slice(0, 80)}</div>
                <div className="mono" style={{ color: "var(--text-3)", fontSize: 10 }}>{r.source} • {r.timestamp.slice(11, 19)} • {r.tags.join(", ")}</div>
              </div>
            </div>
          )) : <div className="empty">Keine Aktivitäten</div>}
        </div>
      </div>

      {selectedNode && (
        <div className="card" style={{ borderColor: "var(--accent)", background: "rgba(6,182,214,.04)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>Ausgewählter Node: {selectedNode.id}</div>
            <button onClick={() => setSelectedNode(null)} className="btn" style={{ padding: "4px 8px", fontSize: 11 }}>Schließen</button>
          </div>
          <div className="mono" style={{ fontSize: 11, marginTop: 6, lineHeight: 1.6 }}>
            Titel: {selectedNode.title}<br />Typ: {selectedNode.type} • Status: {selectedNode.status} • Thema: {selectedNode.topic}<br />ID: {selectedNode.id} • Tags: {selectedNode.tags.join(", ")}
          </div>
        </div>
      )}
    </div>
  );
}
