// Graph Data Adapter — Knowledge Data → Graph Data
// Trennung: Knowledge Data (API) → Adapter → Graph Engine → UI
export type KnowledgeNode = {
  id: string;
  content: string;
  type: string;
  source: string;
  url?: string | null;
  timestamp: string;
  freshness?: string;
  tags: string[];
  relations: string[];
  trust_status: string;
  history: any[];
};

export type GraphNode = {
  id: string;
  label: string; // Kurzbezeichnung (content slice)
  title: string; // Voller Inhalt für tooltip
  type: string;
  status: string; // PENDING/APPROVED/REJECTED/OUTDATED
  topic: string; // erstes Tag
  timestamp: string;
  tags: string[];
  source: string;
  url?: string | null;
  // Physik
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
};

export type GraphEdge = {
  id: string;
  source: string; // node id
  target: string;
  type: string;
  createdAt?: string;
  sourceEntry?: KnowledgeNode;
  targetEntry?: KnowledgeNode;
};

export type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export function knowledgeToGraph(nodes: KnowledgeNode[]): GraphData {
  const graphNodes: GraphNode[] = nodes.map(n => ({
    id: n.id,
    label: n.content.slice(0, 28) + (n.content.length > 28 ? "…" : ""),
    title: n.content,
    type: n.type,
    status: n.trust_status,
    topic: n.tags[0] || n.type,
    timestamp: n.timestamp,
    tags: n.tags,
    source: n.source,
    url: n.url,
  }));

  const edgeMap = new Map<string, GraphEdge>();
  for (const n of nodes) {
    for (const rel of n.relations) {
      const a = n.id, b = rel;
      const key = [a, b].sort().join("::");
      if (edgeMap.has(key)) continue;
      // Prüfe ob Ziel existiert
      const targetExists = nodes.some(x => x.id === b);
      if (!targetExists) continue;
      edgeMap.set(key, {
        id: key,
        source: a,
        target: b,
        type: "related",
        createdAt: n.timestamp,
        sourceEntry: n as any,
        targetEntry: nodes.find(x => x.id === b) as any,
      });
    }
  }

  return { nodes: graphNodes, edges: Array.from(edgeMap.values()) };
}

export function filterGraph(data: GraphData, query: string, status: string | null): GraphData {
  const q = query.trim().toLowerCase();
  let nodes = data.nodes;
  if (q) {
    nodes = nodes.filter(n =>
      n.label.toLowerCase().includes(q) ||
      n.title.toLowerCase().includes(q) ||
      n.topic.toLowerCase().includes(q) ||
      n.tags.some(t => t.toLowerCase().includes(q)) ||
      n.id.toLowerCase().includes(q)
    );
  }
  if (status && status !== "ALL") {
    nodes = nodes.filter(n => n.status === status);
  }
  const idSet = new Set(nodes.map(n => n.id));
  const edges = data.edges.filter(e => idSet.has(e.source) && idSet.has(e.target));
  return { nodes, edges };
}
