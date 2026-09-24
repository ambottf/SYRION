"use client";
export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="card" style={{ borderColor: "var(--danger)" }}>
      <h2 style={{ margin: 0, color: "var(--danger)" }}>Fehler</h2>
      <p className="mono" style={{ color: "var(--text-2)", marginTop: 8 }}>{error.message || "Unbekannter Fehler"}</p>
      <button className="btn primary" style={{ marginTop: 12 }} onClick={() => reset()}>Erneut versuchen</button>
    </div>
  );
}
