// Graph Engine — STILL, KATEGORISIERT, kein Jiggle
// Für 10k+ Nodes: statisches Grid pro Kategorie, kein Force-Simulation
import type { GraphData, GraphNode, GraphEdge } from "./graphAdapter";

export type EngineNode = GraphNode & { x: number; y: number; vx: number; vy: number; fx?: number | null; fy?: number | null };
export type EngineEdge = GraphEdge & { source: EngineNode | string; target: EngineNode | string };

export class GraphEngine {
  nodes: EngineNode[] = [];
  edges: EngineEdge[] = [];
  width = 800;
  height = 400;
  private onTick: (() => void) | null = null;

  constructor(width: number, height: number, onTick?: () => void) {
    this.width = width;
    this.height = height;
    this.onTick = onTick || null;
  }

  setSize(w: number, h: number) {
    this.width = w;
    this.height = h;
    this.layout(); // neu anordnen bei Resize
    if (this.onTick) this.onTick();
  }

  setData(data: GraphData) {
    // Behalte Positionen für bestehende Nodes (kein Springen)
    const posMap = new Map(this.nodes.map(n => [n.id, { x: n.x, y: n.y }]));
    this.nodes = data.nodes.map(n => {
      const prev = posMap.get(n.id);
      if (prev) {
        return { ...n, x: prev.x, y: prev.y, vx: 0, vy: 0 } as EngineNode;
      }
      // Neue Nodes: platziere deterministisch im Cluster-Grid (still)
      return { ...n, x: 0, y: 0, vx: 0, vy: 0 } as EngineNode;
    });
    this.edges = data.edges.map(e => ({ ...e })) as unknown as EngineEdge[];
    this.layout();
    if (this.onTick) this.onTick();
  }

  private layout() {
    if (this.nodes.length === 0) return;

    // 6 feste Cluster-Zentren (wie im Bild) - absolut still, nicht force-basiert
    const centers: Record<string, { x: number; y: number }> = {
      "KI & Technologie": { x: this.width * 0.28, y: this.height * 0.30 },
      "Wissenschaft": { x: this.width * 0.72, y: this.height * 0.30 },
      "Bildung": { x: this.width * 0.22, y: this.height * 0.65 },
      "Gesellschaft": { x: this.width * 0.38, y: this.height * 0.85 },
      "Aktuelle Themen": { x: this.width * 0.72, y: this.height * 0.82 },
      "Web & Internet": { x: this.width * 0.78, y: this.height * 0.58 },
      "SYRION": { x: this.width / 2, y: this.height / 2 },
    };

    // Gruppiere Nodes nach Topic
    const groups = new Map<string, EngineNode[]>();
    for (const n of this.nodes) {
      const key = n.topic || "SYRION";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(n);
    }

    // Für jede Gruppe: Grid-Layout um Zentrum - WEITER AUSEINANDER wie echtes Gehirn, flüssig
    for (const [topic, group] of groups.entries()) {
      const center = centers[topic] || centers["SYRION"];
      const isCentral = topic === "SYRION";
      if (isCentral && group.length === 1) {
        group[0].x = center.x;
        group[0].y = center.y;
        continue;
      }
      // Größerer Radius und mehr Abstand für 10k+ und für "weiter auseinander wie echtes Gehirn"
      const radius = group.length > 50 ? 140 : group.length > 20 ? 110 : group.length > 8 ? 85 : 65;
      const cols = Math.ceil(Math.sqrt(group.length));
      for (let i = 0; i < group.length; i++) {
        const n = group[i];
        if (n.x !== 0 || n.y !== 0) {
          const dx = n.x - center.x, dy = n.y - center.y;
          if (Math.hypot(dx, dy) < radius * 1.3) continue;
        }
        const row = Math.floor(i / cols);
        const col = i % cols;
        const gridW = (cols - 1) * 42; // weiter auseinander (32→42)
        const gridH = (Math.ceil(group.length / cols) - 1) * 38; // 28→38
        n.x = center.x - gridW / 2 + col * 42 + (row % 2 ? 21 : 0);
        n.y = center.y - gridH / 2 + row * 38;
        const hash = Array.from(n.id).reduce((a, c) => a + c.charCodeAt(0), 0);
        n.x += ((hash % 7) - 3) * 1.5;
        n.y += ((hash % 11) - 5) * 1.5;
      }
    }

    // SYRION Zentral-Node immer exakt Mitte, falls vorhanden
    const central = this.nodes.find(n => n.id === "SYRION" || n.label === "SYRION");
    if (central) {
      central.x = this.width / 2;
      central.y = this.height / 2;
    }
  }

  getNodes(): EngineNode[] { return this.nodes; }
  getEdges(): EngineEdge[] { return this.edges; }

  dragStarted(node: EngineNode) {
    node.fx = node.x;
    node.fy = node.y;
  }
  dragged(node: EngineNode, x: number, y: number) {
    node.fx = x;
    node.fy = y;
    node.x = x;
    node.y = y;
    if (this.onTick) this.onTick();
  }
  dragEnded(node: EngineNode) {
    node.fx = null;
    node.fy = null;
  }

  stop() {}
}
