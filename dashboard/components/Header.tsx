"use client";
import { useEffect, useState } from "react";

export function Header({ onMenu }: { onMenu: () => void }) {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [q, setQ] = useState("");

  useEffect(() => {
    const saved = (localStorage.getItem("syrion-theme") as any) || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setTheme(saved);
    document.documentElement.setAttribute("data-theme", saved);
  }, []);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("syrion-theme", next);
  };

  return (
    <header className="header">
      <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1 }}>
        <button className="icon-btn mobile-toggle" onClick={onMenu} aria-label="Menu">≡</button>
        <div className="search">
          <span style={{ color: "var(--text-3)" }}>⌕</span>
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Suchen — Chat, Memory, Dokumente…" aria-label="Suche" />
          <span className="mono" style={{ color: "var(--text-3)", fontSize: 11 }}>⌘K</span>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="badge ok" title="System ok">● Live</span>
        <button className="icon-btn" onClick={toggle} aria-label="Theme umschalten" title="Dark/Light">
          {theme === "dark" ? "☾" : "☀"}
        </button>
        <div style={{ width: 36, height: 36, borderRadius: 999, background: "linear-gradient(135deg, var(--accent), var(--accent-2))", display: "grid", placeItems: "center", color: "white", fontWeight: 800 }}>A</div>
      </div>
    </header>
  );
}
