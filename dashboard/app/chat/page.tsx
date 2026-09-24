"use client";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Role = "user" | "assistant";
type Msg = { id: string; role: Role; content: string; ts: number; model?: string; error?: string };

const CORE = "http://127.0.0.1:8080";
const STORAGE_KEY = "syrion-chat-v1";

function uid() { return Math.random().toString(36).slice(2, 9); }

function CodeBlock({ children, className }: any) {
  const text = String(children).replace(/\n$/, "");
  const isBlock = className?.startsWith("language-");
  const [copied, setCopied] = useState(false);
  if (!isBlock) return <code className="mono" style={{ background: "var(--bg-soft)", padding: "2px 6px", borderRadius: 6, fontSize: 13 }}>{children}</code>;
  return (
    <div style={{ position: "relative", margin: "10px 0", border: "1px solid var(--border)", borderRadius: 10, overflow: "hidden", background: "#0b1220" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px", background: "#0f172a", color: "#94a3b8", fontSize: 11 }} className="mono">
        <span>{(className || "code").replace("language-", "")}</span>
        <button onClick={async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1200); }} className="btn" style={{ padding: "4px 8px", fontSize: 11, background: "white", color: "#0f172a" }}>{copied ? "Kopiert" : "Kopieren"}</button>
      </div>
      <pre style={{ margin: 0, padding: 12, overflowX: "auto", color: "#e2e8f0", fontSize: 13, lineHeight: 1.5 }}><code>{text}</code></pre>
    </div>
  );
}

export default function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState<{ active: string; state: string; message: string } | null>(null);
  const [session, setSession] = useState<string>(() => `sess_${Date.now().toString(36)}`);
  const listRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load history + model
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) { const p = JSON.parse(raw); if (Array.isArray(p.msgs)) setMsgs(p.msgs); if (p.session) setSession(p.session); }
    } catch {}
    fetch(`${CORE}/api/v1/models/status`).then(r => r.json()).then(j => setModel({ active: j.active_model, state: j.state, message: j.message })).catch(() => setModel({ active: "syrion-0.1.0-base", state: "offline", message: "Core offline" }));
  }, []);
  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify({ msgs, session })); }, [msgs, session]);
  useEffect(() => { listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" }); }, [msgs, streaming]);

  const newChat = () => { abortRef.current?.abort(); setMsgs([]); setError(null); setSession(`sess_${Date.now().toString(36)}`); localStorage.removeItem(STORAGE_KEY); };
  const clearChat = () => { if (confirm("Chatverlauf löschen?")) newChat(); };
  const copyMsg = async (t: string) => { await navigator.clipboard.writeText(t); };

  const send = async (text = input, opts?: { regen?: boolean }) => {
    const content = text.trim();
    if (!content || streaming) return;
    setError(null);
    const userMsg: Msg = { id: uid(), role: "user", content, ts: Date.now() };
    setMsgs(m => [...m, userMsg]);
    setInput("");
    setStreaming(true);

    const assistantId = uid();
    setMsgs(m => [...m, { id: assistantId, role: "assistant", content: "", ts: Date.now(), model: model?.active }]);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch(`${CORE}/api/v1/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content, session_id: session, stream: true, timeout_ms: 60000, model: model?.active }),
        signal: ctrl.signal,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ message: `HTTP ${res.status}` }));
        throw new Error(err.message || `Fehler ${res.status}: ${err.code || ""}`);
      }
      const reader = res.body?.getReader();
      if (!reader) throw new Error("Kein Stream");
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          const jsonStr = line.slice(5).trim();
          if (!jsonStr) continue;
          try {
            const obj = JSON.parse(jsonStr);
            if (obj.error) throw new Error(obj.error.message || obj.error.code);
            if (obj.content) {
              setMsgs(m => m.map(x => x.id === assistantId ? { ...x, content: x.content + obj.content } : x));
            }
            if (obj.done) break;
          } catch (e: any) {
            if (e.message && !e.message.includes("Unexpected")) throw e;
          }
        }
      }
    } catch (e: any) {
      if (e.name === "AbortError") {
        setMsgs(m => m.map(x => x.id === assistantId ? { ...x, content: x.content + "\n\n*(abgebrochen)*" } : x));
      } else {
        const msg = e.message || "Unbekannter Fehler";
        setError(msg);
        setMsgs(m => m.map(x => x.id === assistantId ? { ...x, error: msg, content: x.content || "" } : x));
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  };

  const stop = () => abortRef.current?.abort();
  const regenerate = () => {
    const lastUser = [...msgs].reverse().find(m => m.role === "user");
    if (lastUser && !streaming) {
      // entferne letzte assistant antwort
      setMsgs(m => {
        const idx = m.findLastIndex(x => x.role === "assistant");
        return idx >= 0 ? m.slice(0, idx) : m;
      });
      setTimeout(() => send(lastUser.content), 50);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 64px - 32px)", minHeight: 520 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginBottom: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.02em" }}>Chat</h1>
          <div className="mono" style={{ color: "var(--text-3)", fontSize: 11, marginTop: 4 }}>
            Modell: <strong style={{ color: "var(--text)" }}>{model?.active ?? "lädt…"}</strong> • {model?.state ?? ""} • Session {session.slice(0, 8)}
            {model?.state === "degraded" && <span style={{ color: "var(--warning)", marginLeft: 8 }}>• {model.message.slice(0, 80)}</span>}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={newChat} className="btn" title="Neue Unterhaltung">+ Neu</button>
          <button onClick={regenerate} disabled={streaming || msgs.length === 0} className="btn" title="Letzte Antwort neu generieren">↻ Regenerate</button>
          <button onClick={clearChat} disabled={msgs.length === 0} className="btn ghost" title="Verlauf löschen">Löschen</button>
        </div>
      </div>

      {/* Fehler */}
      {error && (
        <div style={{ padding: "10px 12px", borderRadius: 12, border: "1px solid rgba(239,68,68,.3)", background: "rgba(239,68,68,.08)", color: "#b91c1c", marginBottom: 12, display: "flex", justifyContent: "space-between", gap: 12 }}>
          <span><strong>Fehler:</strong> {error}</span>
          <button onClick={() => setError(null)} className="btn" style={{ padding: "4px 8px" }}>×</button>
        </div>
      )}
      {model?.state === "degraded" && msgs.length === 0 && (
        <div style={{ padding: "10px 12px", borderRadius: 12, border: "1px solid rgba(245,158,11,.3)", background: "rgba(245,158,11,.08)", marginBottom: 12, fontSize: 13 }}>
          <strong>SYRION Modell:</strong> {model.message} — Basis-Modell aktiv, Training für große Version folgt.
        </div>
      )}

      {/* Verlauf */}
      <div ref={listRef} style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, padding: "4px 2px 12px", scrollBehavior: "smooth" }}>
        {msgs.length === 0 && (
          <div className="empty" style={{ marginTop: 24 }}>
            <div style={{ fontWeight: 700 }}>Starte eine Unterhaltung</div>
            <div style={{ marginTop: 6, fontSize: 13, color: "var(--text-2)" }}>Kurze oder lange Anfragen, Streaming, Abbruch und Fehlerbehandlung werden getestet. Markdown & Codeblöcke werden gerendert.</div>
            <div style={{ marginTop: 12, display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
              {["Erkläre SYRION in 3 Sätzen", "Schreibe eine Python-Funktion für Fibonacci mit Codeblock", "Was ist ein Wissensgraph? Antworte mit Markdown-Tabelle"].map(ex => (
                <button key={ex} onClick={() => send(ex)} className="btn" style={{ fontSize: 12 }}>{ex.slice(0, 32)}…</button>
              ))}
            </div>
          </div>
        )}
        {msgs.map(m => (
          <div key={m.id} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{
              maxWidth: "min(78%, 760px)", width: "fit-content",
              background: m.role === "user" ? "var(--text)" : "var(--surface)",
              color: m.role === "user" ? "var(--bg)" : "var(--text)",
              border: `1px solid ${m.role === "user" ? "var(--text)" : "var(--border)"}`,
              borderRadius: 14, padding: "10px 12px", boxShadow: "var(--shadow)",
              overflow: "hidden"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 6, fontSize: 11, opacity: .7 }} className="mono">
                <span>{m.role === "user" ? "Du" : `SYRION ${m.model ? "• " + m.model : ""}`}</span>
                <span>{new Date(m.ts).toLocaleTimeString()}</span>
              </div>
              {m.role === "assistant" ? (
                m.content ? (
                  <div style={{ fontSize: 14, lineHeight: 1.6, overflowWrap: "anywhere" }}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: CodeBlock }}>{m.content}</ReactMarkdown>
                  </div>
                ) : m.error ? null : (
                  <div className="skeleton" style={{ height: 14, width: 120 }} />
                )
              ) : (
                <div style={{ whiteSpace: "pre-wrap", fontSize: 14, lineHeight: 1.5 }}>{m.content}</div>
              )}
              {m.error && <div style={{ marginTop: 8, padding: "8px 10px", borderRadius: 8, background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)", color: "#991b1b", fontSize: 13 }}>Fehler: {m.error}</div>}
              <div style={{ display: "flex", gap: 6, marginTop: 8, justifyContent: "flex-end" }}>
                <button onClick={() => copyMsg(m.content)} className="btn" style={{ padding: "4px 8px", fontSize: 11 }}>Kopieren</button>
                {m.role === "assistant" && <button onClick={regenerate} className="btn ghost" style={{ padding: "4px 8px", fontSize: 11 }} disabled={streaming}>↻</button>}
              </div>
            </div>
          </div>
        ))}
        {streaming && <div className="mono" style={{ color: "var(--text-3)", fontSize: 11, paddingLeft: 4 }}>● Streamt…</div>}
      </div>

      {/* Input */}
      <div style={{ position: "sticky", bottom: 0, background: "var(--bg)", paddingTop: 12, borderTop: "1px solid var(--border)", marginTop: 8 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder={streaming ? "Streamt…" : "Nachricht eingeben — Enter senden, Shift+Enter neue Zeile"}
            disabled={streaming}
            rows={1}
            style={{
              flex: 1, resize: "none", minHeight: 44, maxHeight: 140, padding: "10px 12px",
              borderRadius: 12, border: "1px solid var(--border)", background: "var(--surface)", color: "var(--text)", fontSize: 14, outline: "none"
            }}
            onInput={e => { const t = e.target as HTMLTextAreaElement; t.style.height = "auto"; t.style.height = Math.min(t.scrollHeight, 140) + "px"; }}
          />
          {streaming ? (
            <button onClick={stop} className="btn" style={{ background: "var(--danger)", color: "white", borderColor: "var(--danger)", height: 44, padding: "0 18px" }}>Stop</button>
          ) : (
            <button onClick={() => send()} disabled={!input.trim()} className="btn primary" style={{ height: 44, padding: "0 18px", opacity: input.trim() ? 1 : .5 }}>Senden</button>
          )}
        </div>
        <div className="mono" style={{ color: "var(--text-3)", fontSize: 10, marginTop: 6, display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <span>Enter senden • Shift+Enter Zeilenumbruch • Modell: {model?.active ?? "—"}</span>
          <span>{msgs.length} Nachrichten • Session {session.slice(0, 8)}</span>
        </div>
      </div>
    </div>
  );
}
