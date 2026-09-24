import Link from "next/link";
export default function NotFound() {
  return (
    <div className="empty">
      <div style={{ fontWeight: 800, fontSize: 18 }}>404 — Nicht gefunden</div>
      <p style={{ color: "var(--text-2)" }}>Diese Seite existiert noch nicht. Zurück zur Übersicht.</p>
      <Link href="/" className="btn primary" style={{ display: "inline-block", marginTop: 12, textDecoration: "none" }}>Zur Overview</Link>
    </div>
  );
}
