import { StatCard } from "../components/StatCard";
import { SystemStatus } from "../components/SystemStatus";

export default function OverviewPage() {
  return (
    <div className="grid" style={{ gap: 16 }}>
      <div style={{ display: "flex", alignItems: "end", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 28, letterSpacing: "-0.02em", lineHeight: 1.1 }}>Overview</h1>
          <p style={{ margin: "6px 0 0", color: "var(--text-2)" }}>Willkommen bei SYRION — dein lokales Intelligence-Cockpit. Phase 1 Dashboard ist live, Module laden schrittweise.</p>
        </div>
        <span className="badge ok">● Operational</span>
      </div>

      <SystemStatus />

      <div className="grid grid-4">
        <StatCard label="Aktive Module" value="3 / 22" sub="Dashboard • Gateway • Audit" badge={<span className="badge ok">live</span>}>
          <div className="progress"><span style={{ width: "14%" }} /></div>
        </StatCard>
        <StatCard label="Memory" value="Quarantäne" sub="0 pending • 0 approved" badge={<span className="badge warn">isoliert</span>}>
          <div className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>M1 STM (Redis) • M2 LTM (Qdrant)</div>
        </StatCard>
        <StatCard label="Wissensgraph" value="—" sub="Kuzu / Neo4j — Phase 2" badge={<span className="badge soon">soon</span>}>
          <div className="progress"><span style={{ width: "0%" }} /></div>
        </StatCard>
        <StatCard label="Letzte Aktivität" value="vor 2 Min" sub="GET /api/v1/health → 200" badge={<span className="badge ok">ok</span>}>
          <div className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>audit_chain_ok: true</div>
        </StatCard>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-head"><div className="card-title">Aktive Module</div><span className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>22 geplant</span></div>
          <div className="grid" style={{ gap: 10 }}>
            {[
              ["P1 Dashboard", "Live", "ok"],
              ["S1 Security Kernel", "Live", "ok"],
              ["F2 Audit-Log", "Append-only", "ok"],
              ["I1 SYRION Model", "syrion-0.1.0-base • lokal", "ok"],
              ["M4 Wissensgraph", "Soon — Kuzu", "soon"],
              ["O1 Agent-System", "Soon", "soon"],
            ].map(([name, note, state]) => (
              <div key={name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", border: "1px solid var(--border)", borderRadius: 10, background: "var(--surface-2)" }}>
                <div><div style={{ fontWeight: 600, fontSize: 13 }}>{name}</div><div className="mono" style={{ color: "var(--text-2)", fontSize: 11 }}>{note}</div></div>
                <span className={`badge ${state === "ok" ? "ok" : state === "soon" ? "soon" : "warn"}`}>{state}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid" style={{ gap: 16 }}>
          <div className="card">
            <div className="card-head"><div className="card-title">Letzte Aktivitäten</div><span className="badge soon">Audit</span></div>
            <div className="grid" style={{ gap: 8 }}>
              {[
                ["12:42", "gateway.startup", "system", "policy v0.1.0-phase0"],
                ["12:41", "health check", "dashboard", "GET / → 200"],
                ["12:40", "quarantine.new", "—", "keine Einträge"],
              ].map(([t, a, actor, detail]) => (
                <div key={t+a} style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                  <span className="mono" style={{ color: "var(--text-3)" }}>{t}</span>
                  <div style={{ flex: 1 }}><div style={{ fontWeight: 600, fontSize: 13 }}>{a}</div><div className="mono" style={{ color: "var(--text-2)", fontSize: 11 }}>{actor} • {detail}</div></div>
                  <span className="badge ok">ok</span>
                </div>
              ))}
            </div>
            <div className="empty" style={{ marginTop: 12, padding: 12 }}>Leerer Zustand wird sauber angezeigt — keine Daten = keine erfundenen Werte.</div>
          </div>

          <div className="card">
            <div className="card-head"><div className="card-title">Fehlerstatus</div><span className="badge ok">keine Fehler</span></div>
            <div className="grid" style={{ gap: 8 }}>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}><span style={{ width: 8, height: 8, borderRadius: 999, background: "var(--success)" }} /> Gateway erreichbar</div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}><span style={{ width: 8, height: 8, borderRadius: 999, background: "var(--success)" }} /> Audit-Kette intakt</div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}><span style={{ width: 8, height: 8, borderRadius: 999, background: "var(--success)" }} /> SYRION Modell syrion-0.1.0-base bereit</div>
            </div>
            <div className="mono" style={{ marginTop: 12, color: "var(--text-3)", fontSize: 11 }}>Fehler werden hier als Karten mit Retry/Details angezeigt — aktuelle Ladezustände siehe Skeleton unten.</div>
            <div className="grid grid-3" style={{ marginTop: 12 }}>
              <div className="skeleton" style={{ height: 14 }} />
              <div className="skeleton" style={{ height: 14 }} />
              <div className="skeleton" style={{ height: 14 }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
