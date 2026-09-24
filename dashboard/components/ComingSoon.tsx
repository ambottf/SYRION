export function ComingSoon({ title, desc, eta = "Phase 1â€“3" }: { title: string; desc: string; eta?: string }) {
  return (
    <div className="card" style={{ padding: 28 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <span className="badge soon">Coming Soon</span>
        <span className="mono" style={{ color: "var(--text-3)" }}>{eta}</span>
      </div>
      <h2 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.02em" }}>{title}</h2>
      <p style={{ color: "var(--text-2)", marginTop: 8, lineHeight: 1.6 }}>{desc}</p>
      <div className="empty" style={{ marginTop: 18 }}>
        <div style={{ fontWeight: 700 }}>Noch nicht implementiert</div>
        <div style={{ marginTop: 6, fontSize: 13 }}>UI ist vorbereitet, Logik folgt per Freigabe. Status wird im Audit-Log gefÃ¼hrt.</div>
      </div>
    </div>
  );
}

