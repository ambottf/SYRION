"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { group: "Workspace" },
  { id: "overview", label: "Overview", href: "/" },
  { id: "chat", label: "Chat", href: "/chat" },
  { id: "brain", label: "Brain", href: "/brain" },
  { id: "memory", label: "Memory", href: "/memory" },
  { id: "knowledge", label: "Knowledge", href: "/knowledge" },
  { id: "research", label: "Research", href: "/research" },
  { group: "Multimodal" },
  { id: "vision", label: "Vision", href: "/vision" },
  { id: "image-lab", label: "Image Lab", href: "/image-lab" },
  { id: "documents", label: "Documents", href: "/documents" },
  { id: "audio", label: "Audio", href: "/audio" },
  { group: "System" },
  { id: "agents", label: "Agents", href: "/agents" },
  { id: "tasks", label: "Tasks", href: "/tasks" },
  { id: "activity", label: "Activity", href: "/activity" },
  { id: "security", label: "Security", href: "/security" },
  { id: "system", label: "System", href: "/system" },
  { id: "settings", label: "Settings", href: "/settings" },
] as const;

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  return (
    <>
      {open && <div className="sidebar-overlay" onClick={onClose} aria-hidden />}
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Navigation">
        <div className="brand">
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-title">SYRION</div>
            <div className="brand-sub">Intelligence • Local-First</div>
          </div>
        </div>
        <nav className="nav">
          {NAV.map((item: any, i) =>
            item.group ? (
              <div key={i} className="nav-group">{item.group}</div>
            ) : (
              <Link
                key={item.id}
                href={item.href}
                onClick={onClose}
                className={`nav-item ${pathname === item.href ? "active" : ""}`}
              >
                <span className="nav-dot" />
                {item.label}
                {["vision","image-lab","audio","agents","knowledge"].includes(item.id) && (
                  <span className="badge soon" style={{ marginLeft: "auto", fontSize: 10 }}>soon</span>
                )}
              </Link>
            )
          )}
        </nav>
        <div className="sidebar-foot">
          <div className="mini-card">
            <div className="mini-label">Phase</div>
            <div className="mini-value">1 — Dashboard</div>
            <div style={{ fontSize: 12, color: "var(--sidebar-muted)", marginTop: 6 }}>Hot Reload aktiv • Next 14</div>
          </div>
          <div style={{ fontSize: 11, color: "var(--sidebar-muted)", textAlign: "center" }}>
            Local-First • Auditierbar
          </div>
        </div>
      </aside>
    </>
  );
}
