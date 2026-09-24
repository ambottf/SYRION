"use client";
import { useEffect, useState } from "react";
const CORE = "http://127.0.0.1:8080";
export default function KnowledgePage() {
  const [entries, setEntries] = useState<any[]>([]);
  useEffect(() => { fetch(`${CORE}/api/v1/memory?status=APPROVED`).then(r => r.json()).then(j => setEntries(j.entries || [])); }, []);
  return (
    <div className="grid" style={{ gap: 16 }}>
      <div>
        <h1 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.02em" }}>Knowledge Base</h1>
        <p className="mono" style={{ color: "var(--text-3)", fontSize: 11, marginTop: 4 }}>Nur APPROVED • getrennt vom Modell • kein PENDING hier</p>
      </div>
      {entries.length === 0 ? <div className="empty">Keine bestätigten Fakten — approviere Einträge in Memory.</div> : (
        <div className="grid" style={{ gap: 8 }}>
          {entries.map((e: any) => (
            <div key={e.id} style={{ padding: 12, border: "1px solid var(--border)", borderRadius: 12, background: "var(--surface)" }}>
              <div style={{ fontWeight: 600, fontSize: 13 }}>{e.content}</div>
              <div className="mono" style={{ fontSize: 10, color: "var(--text-3)", marginTop: 4 }}>{e.id} • {e.source} • {e.tags.join(", ")} • {new Date(e.timestamp).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
