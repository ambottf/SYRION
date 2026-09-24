export function StatCard({ label, value, sub, badge, children }: { label: string; value: string; sub?: string; badge?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="card">
      <div className="card-head">
        <div className="card-title">{label}</div>
        {badge}
      </div>
      <div className="kpi">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
      {children && <div style={{ marginTop: 12 }}>{children}</div>}
    </div>
  );
}
