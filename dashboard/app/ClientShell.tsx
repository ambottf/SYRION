"use client";
import { useState } from "react";
import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";

export default function ClientShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="shell">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="main">
        <Header onMenu={() => setOpen(v => !v)} />
        <div className="content">{children}</div>
        <footer style={{ padding: "16px 24px", borderTop: "1px solid var(--border)", color: "var(--text-3)", fontSize: 12, display: "flex", justifyContent: "space-between" }}>
          <span>© SYRION — Local-First • v0.1 Phase 1 Dashboard</span>
          <span className="mono">SYRION_ARCHITEKTUR.md • 24/7 ready</span>
        </footer>
      </div>
    </div>
  );
}
