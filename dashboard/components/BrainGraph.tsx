"use client";
import { useEffect, useRef, useState, useMemo } from "react";
import * as d3 from "d3";
import { GraphData, GraphNode, GraphEdge, filterGraph } from "../lib/graphAdapter";
import { GraphEngine, EngineNode } from "../lib/graphEngine";

const STATUS_COLOR: Record<string, string> = {
  PENDING: "#f59e0b",
  APPROVED: "#f97316", // Orange wie echtes Gehirn
  REJECTED: "#ef4444",
  OUTDATED: "#64748b",
};

const TOPIC_COLOR: Record<string, string> = {
  "KI & Technologie": "#f97316", // Orange für alle - echtes Gehirn
  "Wissenschaft": "#fb923c",
  "Bildung": "#f97316",
  "Gesellschaft": "#fdba74",
  "Aktuelle Themen": "#f97316",
  "Web & Internet": "#fb923c",
  "SYRION": "#f59e0b",
};

export function BrainGraph({ data, onNodeClick, onEdgeClick }: { data: GraphData; onNodeClick?: (n: GraphNode) => void; onEdgeClick?: (e: GraphEdge) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<GraphEngine | null>(null);
  const transformRef = useRef(d3.zoomIdentity);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [hover, setHover] = useState<GraphNode | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [edgeSelected, setEdgeSelected] = useState<GraphEdge | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);

  const filtered = useMemo(() => filterGraph(data, search, statusFilter === "ALL" ? null : statusFilter), [data, search, statusFilter]);
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const rect = container.getBoundingClientRect();
    const w = rect.width, h = Math.max(420, rect.height || 500);
    canvas.width = w * window.devicePixelRatio;
    canvas.height = h * window.devicePixelRatio;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);

    const engine = new GraphEngine(w, h, () => draw());
    engineRef.current = engine;
    engine.setData(filtered);

    const zoom = d3.zoom<HTMLCanvasElement, unknown>().scaleExtent([0.15, 6]).on("zoom", (event) => {
      transformRef.current = event.transform;
      setZoomLevel(event.transform.k);
      draw();
    });
    d3.select(canvas).call(zoom as any);
    d3.select(canvas).on("dblclick.zoom", null);

    const ro = new ResizeObserver(() => {
      const r = container.getBoundingClientRect();
      engine.setSize(r.width, Math.max(520, r.height || 600));
      const c = canvasRef.current;
      if (!c) return;
      c.width = r.width * window.devicePixelRatio;
      c.height = Math.max(520, r.height || 600) * window.devicePixelRatio;
      c.style.width = r.width + "px";
      c.style.height = Math.max(520, r.height || 600) + "px";
      const cx = c.getContext("2d");
      if (cx) cx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
      draw();
    });
    ro.observe(container);

    let dragNode: EngineNode | null = null;
    const drag = d3.drag<HTMLCanvasElement, unknown>()
      .subject((event) => {
        const [mx, my] = d3.pointer(event, canvas);
        const t = transformRef.current;
        const x = (mx - t.x) / t.k, y = (my - t.y) / t.k;
        let closest: EngineNode | null = null, minD = Infinity;
        for (const n of engine.getNodes()) {
          const d = Math.hypot(n.x - x, n.y - y);
          if (d < 22 && d < minD) { minD = d; closest = n; }
        }
        dragNode = closest;
        if (closest) engine.dragStarted(closest);
        return closest as any;
      })
      .on("drag", (event) => {
        if (!dragNode) return;
        const [mx, my] = d3.pointer(event, canvas);
        const t = transformRef.current;
        engine.dragged(dragNode, (mx - t.x) / t.k, (my - t.y) / t.k);
      })
      .on("end", () => {
        if (dragNode) engine.dragEnded(dragNode);
        dragNode = null;
      });
    d3.select(canvas).call(drag as any);

    const handlePointer = (e: MouseEvent, click: boolean) => {
      const [mx, my] = d3.pointer(e, canvas);
      const t = transformRef.current;
      const x = (mx - t.x) / t.k, y = (my - t.y) / t.k;
      let hitEdge: GraphEdge | null = null, minEdgeD = 12;
      for (const ed of engine.getEdges()) {
        const s = ed.source as EngineNode, tt = ed.target as EngineNode;
        if (!s.x || !tt.x) continue;
        const d = distToSegment(x, y, s.x, s.y, tt.x, tt.y);
        if (d < minEdgeD) { minEdgeD = d; hitEdge = ed as any; }
      }
      let hitNode: GraphNode | null = null, minD = 18;
      for (const n of engine.getNodes()) {
        const d = Math.hypot(n.x - x, n.y - y);
        if (d < minD) { minD = d; hitNode = n as any; }
      }
      if (click) {
        if (hitNode) { setSelected(hitNode); setEdgeSelected(null); onNodeClick?.(hitNode); }
        else if (hitEdge) { setEdgeSelected(hitEdge); setSelected(null); onEdgeClick?.(hitEdge); }
        else { setSelected(null); setEdgeSelected(null); }
      } else {
        setHover(hitNode);
        canvas.style.cursor = hitNode || hitEdge ? "pointer" : "grab";
      }
    };
    const onMove = (e: MouseEvent) => handlePointer(e, false);
    const onClick = (e: MouseEvent) => handlePointer(e, true);
    canvas.addEventListener("mousemove", onMove as any);
    canvas.addEventListener("click", onClick as any);

    function distToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number) {
      const l2 = (x2 - x1) ** 2 + (y2 - y1) ** 2;
      if (l2 === 0) return Math.hypot(px - x1, py - y1);
      let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
      t = Math.max(0, Math.min(1, t));
      const lx = x1 + t * (x2 - x1), ly = y1 + t * (y2 - y1);
      return Math.hypot(px - lx, py - ly);
    }

    function draw() {
      const c = canvasRef.current;
      if (!ctx || !engineRef.current || !c) return;
      const eng = engineRef.current;
      const nodes = eng.getNodes();
      const edges = eng.getEdges();
      const t = transformRef.current;
      ctx.save();
      ctx.clearRect(0, 0, c.width, c.height);
      // Dark space background
      ctx.fillStyle = "#020617";
      ctx.fillRect(0, 0, c.width, c.height);
      // Subtle starfield
      ctx.fillStyle = "rgba(148,163,184,.15)";
      for (let i = 0; i < 80; i++) {
        const x = (Math.sin(i * 12.9898) * 43758.5453) % 1 * c.width;
        const y = (Math.cos(i * 78.233) * 23421.6789) % 1 * c.height;
        ctx.beginPath();
        ctx.arc((x + t.x) % c.width, (y + t.y) % c.height, 0.7, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.translate(t.x, t.y);
      ctx.scale(t.k, t.k);

      // Cluster halos (subtle)
      const clusters: Record<string, { x: number; y: number; count: number; color: string }> = {};
      for (const n of nodes) {
        const topic = n.topic || "SYRION";
        if (!clusters[topic]) clusters[topic] = { x: 0, y: 0, count: 0, color: TOPIC_COLOR[topic] || "#64748b" };
        clusters[topic].x += n.x;
        clusters[topic].y += n.y;
        clusters[topic].count++;
      }
      for (const [topic, cl] of Object.entries(clusters)) {
        if (cl.count < 2) continue;
        cl.x /= cl.count; cl.y /= cl.count;
        ctx.beginPath();
        ctx.arc(cl.x, cl.y, 90, 0, Math.PI * 2);
        ctx.fillStyle = (TOPIC_COLOR[topic] || "#64748b") + "12";
        ctx.fill();
        ctx.strokeStyle = (TOPIC_COLOR[topic] || "#64748b") + "22";
        ctx.lineWidth = 1 / t.k;
        ctx.stroke();
        ctx.fillStyle = TOPIC_COLOR[topic] || "#94a3b8";
        ctx.font = `700 ${10 / t.k}px Inter`;
        ctx.textAlign = "center";
        ctx.fillText(topic, cl.x, cl.y - 95);
      }

      // Edges
      for (const e of edges) {
        const s = e.source as EngineNode, tt = e.target as EngineNode;
        if (s.x == null || tt.x == null) continue;
        const isSel = edgeSelected && (edgeSelected as any).id === (e as any).id;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(tt.x, tt.y);
        ctx.strokeStyle = isSel ? "#06b6d4" : "rgba(148,163,184,.28)";
        ctx.lineWidth = isSel ? 2.2 / t.k : 0.9 / t.k;
        ctx.stroke();
        const ang = Math.atan2(tt.y - s.y, tt.x - s.x);
        const r = 13;
        const ax = tt.x - Math.cos(ang) * r, ay = tt.y - Math.sin(ang) * r;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(ax - Math.cos(ang - 0.5) * 5, ay - Math.sin(ang - 0.5) * 5);
        ctx.lineTo(ax - Math.cos(ang + 0.5) * 5, ay - Math.sin(ang + 0.5) * 5);
        ctx.closePath();
        ctx.fillStyle = isSel ? "#06b6d4" : "rgba(148,163,184,.55)";
        ctx.fill();
      }

      // Nodes - KLEINER, professioneller
      for (const n of nodes) {
        const isHov = hover && (hover as any).id === n.id;
        const isSel = selected && (selected as any).id === n.id;
        const isCentral = n.id === "SYRION" || n.label.includes("SYRION");
        const col = TOPIC_COLOR[n.topic] || STATUS_COLOR[n.status] || "#64748b";
        const r = isCentral ? 16 : isSel ? 10 : isHov ? 8 : 5.5;
        // Glow for central
        if (isCentral) {
          const grad = ctx.createRadialGradient(n.x, n.y, r, n.x, n.y, r + 18);
          grad.addColorStop(0, col + "55");
          grad.addColorStop(1, "transparent");
          ctx.beginPath();
          ctx.arc(n.x, n.y, r + 18, 0, Math.PI * 2);
          ctx.fillStyle = grad;
          ctx.fill();
        }
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = col;
        ctx.fill();
        ctx.strokeStyle = isSel ? "#ffffff" : "rgba(255,255,255,.85)";
        ctx.lineWidth = isSel ? 2.2 / t.k : 1.2 / t.k;
        ctx.stroke();
        // Inner
        ctx.beginPath();
        ctx.arc(n.x, n.y, r * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,.92)";
        ctx.fill();
        ctx.fillStyle = isCentral ? "#0f172a" : col;
        ctx.font = `700 ${isCentral ? 10 : 7}px Inter`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("S", n.x, n.y);
        // Label
        ctx.fillStyle = "rgba(226,232,240,.9)";
        ctx.font = `${isSel ? "700" : "500"} ${10 / t.k}px Inter`;
        ctx.textAlign = "center";
        const label = n.label.slice(0, 16);
        ctx.fillText(label, n.x, n.y + r + 10 / t.k);
        // Status dot
        ctx.beginPath();
        ctx.arc(n.x + r * 0.7, n.y - r * 0.7, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = STATUS_COLOR[n.status] || "#64748b";
        ctx.fill();
        ctx.strokeStyle = "rgba(15,23,42,.9)";
        ctx.lineWidth = 1 / t.k;
        ctx.stroke();
      }
      ctx.restore();
    }

    // Initial draw
    draw();
    return () => {
      ro.disconnect();
      engine.stop();
      canvas.removeEventListener("mousemove", onMove as any);
      canvas.removeEventListener("click", onClick as any);
    };
  }, []);

  useEffect(() => { if (engineRef.current) engineRef.current.setData(filtered); }, [filtered]);

  const resetView = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const t = d3.zoomIdentity;
    transformRef.current = t;
    d3.select(canvas).call(d3.zoom().transform as any, t);
    setZoomLevel(1);
  };
  const fitGraph = () => {
    const eng = engineRef.current;
    if (!eng || eng.getNodes().length === 0) return;
    const nodes = eng.getNodes();
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const n of nodes) { minX = Math.min(minX, n.x); minY = Math.min(minY, n.y); maxX = Math.max(maxX, n.x); maxY = Math.max(maxY, n.y); }
    const w = eng.width, h = eng.height;
    const pad = 80;
    const bw = maxX - minX || 200, bh = maxY - minY || 200;
    const scale = Math.min((w - pad * 2) / bw, (h - pad * 2) / bh, 1.4);
    const tx = w / 2 - (minX + bw / 2) * scale, ty = h / 2 - (minY + bh / 2) * scale;
    const t = d3.zoomIdentity.translate(tx, ty).scale(scale);
    transformRef.current = t;
    const canvas = canvasRef.current;
    if (canvas) d3.select(canvas).call(d3.zoom().transform as any, t);
    setZoomLevel(scale);
  };

  return (
    <div style={{ border: "1px solid #1e293b", borderRadius: 14, overflow: "hidden", background: "#020617" }}>
      <div style={{ display: "flex", gap: 8, padding: 10, borderBottom: "1px solid #1e293b", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", background: "rgba(15,23,42,.6)" }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Suche ID/Titel/Tags…" style={{ padding: "6px 10px", borderRadius: 8, border: "1px solid #334155", background: "#0f172a", color: "#e2e8f0", fontSize: 12, minWidth: 200 }} />
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} style={{ padding: "6px 8px", borderRadius: 8, border: "1px solid #334155", background: "#0f172a", color: "#e2e8f0", fontSize: 12 }}>
            <option value="ALL">Alle Status</option>
            <option value="PENDING">PENDING</option>
            <option value="APPROVED">APPROVED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="OUTDATED">OUTDATED</option>
          </select>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span className="mono" style={{ fontSize: 11, color: "#94a3b8" }}>{filtered.nodes.length} Knoten • {filtered.edges.length} Kanten • {(zoomLevel * 100).toFixed(0)}%</span>
          <button onClick={resetView} className="btn" style={{ padding: "6px 10px", fontSize: 11, background: "#1e293b", color: "#e2e8f0", borderColor: "#334155" }}>Reset</button>
          <button onClick={fitGraph} className="btn primary" style={{ padding: "6px 10px", fontSize: 11 }}>Fit</button>
        </div>
      </div>
      <div ref={containerRef} style={{ position: "relative", height: 380, background: "radial-gradient(700px 320px at 50% 0%, rgba(6,182,214,.07), transparent), #020617" }}>
        <canvas ref={canvasRef} style={{ display: "block", cursor: "grab" }} />
        {hover && (
          <div style={{ position: "absolute", left: 10, bottom: 10, background: "#0f172a", border: "1px solid #334155", borderRadius: 8, padding: "6px 8px", fontSize: 11, color: "#e2e8f0", boxShadow: "0 8px 24px rgba(0,0,0,.4)", maxWidth: 240 }}>
            <div style={{ fontWeight: 700, fontSize: 11 }}>{hover.label}</div>
            <div className="mono" style={{ color: "#94a3b8", fontSize: 9 }}>{hover.id} • {hover.status} • {hover.type}</div>
          </div>
        )}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0, borderTop: "1px solid #1e293b", background: "#0f172a" }}>
        <div style={{ padding: 12, borderRight: "1px solid #1e293b", minHeight: 150 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, color: "#e2e8f0" }}>Node Details {selected ? `• ${selected.id.slice(0, 8)}` : "(klicken)"}</div>
          {selected ? (
            <div style={{ fontSize: 12, lineHeight: 1.5, color: "#cbd5e1" }}>
              <div><strong>ID:</strong> <span className="mono">{selected.id}</span></div>
              <div><strong>Titel:</strong> {selected.title}</div>
              <div><strong>Typ:</strong> {selected.type} • <span style={{ color: STATUS_COLOR[selected.status] || "#94a3b8", fontWeight: 700 }}>{selected.status}</span></div>
              <div><strong>Thema:</strong> {selected.topic} • <strong>Tags:</strong> {selected.tags.join(", ") || "—"}</div>
              <div className="mono" style={{ color: "#64748b", fontSize: 10 }}>{new Date(selected.timestamp).toLocaleString()} • Quelle: {selected.source}</div>
              {selected.url && <div className="mono" style={{ fontSize: 10, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}><a href={selected.url} target="_blank" rel="noreferrer" style={{ color: "#38bdf8" }}>{selected.url}</a></div>}
            </div>
          ) : <div className="mono" style={{ color: "#64748b", fontSize: 12 }}>Kein Node ausgewählt — klicke einen Knoten im Graph.</div>}
        </div>
        <div style={{ padding: 12, minHeight: 150 }}>
          <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8, color: "#e2e8f0" }}>Relationship Details {edgeSelected ? `• ${edgeSelected.id.slice(0, 8)}` : "(Kante klicken)"}</div>
          {edgeSelected ? (
            <div style={{ fontSize: 12, lineHeight: 1.5, color: "#cbd5e1" }}>
              <div><strong>ID:</strong> <span className="mono">{edgeSelected.id}</span></div>
              <div><strong>Quelle:</strong> {String(edgeSelected.source as any).slice(0, 8)} → <strong>Ziel:</strong> {String(edgeSelected.target as any).slice(0, 8)}</div>
              <div><strong>Typ:</strong> {edgeSelected.type}</div>
              {edgeSelected.createdAt && <div className="mono" style={{ color: "#64748b", fontSize: 10 }}>{new Date(edgeSelected.createdAt).toLocaleString()}</div>}
            </div>
          ) : <div className="mono" style={{ color: "#64748b", fontSize: 12 }}>Keine Kante ausgewählt — klicke eine Linie zwischen zwei Nodes.</div>}
        </div>
      </div>
    </div>
  );
}
