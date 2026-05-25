import { useEffect, useState, useRef, useCallback } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Search,
  Zap,
  Circle,
  Diamond,
  Square,
  Network,
  Link2,
  Cpu,
  AlertTriangle,
  FileText,
  Hexagon,
} from "lucide-react";

interface KGNode {
  id: string;
  name: string;
  type: string;
  properties: Record<string, unknown>;
}

interface KGEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  weight: number;
}

interface GraphData {
  nodes: KGNode[];
  edges: KGEdge[];
}

interface KGStats {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  edge_types: Record<string, number>;
}

interface SimNode extends KGNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

const NODE_COLORS: Record<string, string> = {
  device: "#3b82f6",
  fault: "#ef4444",
  solution: "#22c55e",
  procedure: "#f59e0b",
  standard: "#8b5cf6",
};

const NODE_SIZES: Record<string, number> = {
  device: 24,
  fault: 18,
  solution: 18,
  procedure: 18,
  standard: 16,
};

const EDGE_COLORS: Record<string, string> = {
  has_fault: "#ef4444",
  solved_by: "#22c55e",
  related_to: "#6b7280",
  requires: "#f59e0b",
  complies_with: "#8b5cf6",
};

const EDGE_DASH: Record<string, boolean> = {
  has_fault: true,
  solved_by: false,
  related_to: false,
  requires: true,
  complies_with: true,
};

const TYPE_LABELS: Record<string, string> = {
  device: "设备",
  fault: "故障",
  solution: "解决方案",
  procedure: "操作流程",
  standard: "标准规范",
};

const RELATION_LABELS: Record<string, string> = {
  has_fault: "存在故障",
  solved_by: "解决方案",
  related_to: "相关",
  requires: "需要",
  complies_with: "符合",
};

function drawDiamond(ctx: CanvasRenderingContext2D, x: number, y: number, size: number) {
  ctx.beginPath();
  ctx.moveTo(x, y - size);
  ctx.lineTo(x + size, y);
  ctx.lineTo(x, y + size);
  ctx.lineTo(x - size, y);
  ctx.closePath();
}

function drawNode(
  ctx: CanvasRenderingContext2D,
  node: SimNode,
  isHighlighted: boolean,
  isDimmed: boolean,
  transform: { x: number; y: number; scale: number }
) {
  const sx = node.x * transform.scale + transform.x;
  const sy = node.y * transform.scale + transform.y;
  const size = (NODE_SIZES[node.type] || 16) * transform.scale;

  ctx.save();
  if (isDimmed) ctx.globalAlpha = 0.2;

  const color = NODE_COLORS[node.type] || "#9ca3af";

  if (isHighlighted) {
    ctx.shadowColor = color;
    ctx.shadowBlur = 20;
  }

  ctx.fillStyle = color;

  if (node.type === "device") {
    ctx.beginPath();
    ctx.arc(sx, sy, size, 0, Math.PI * 2);
    ctx.fill();
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  } else if (node.type === "fault") {
    drawDiamond(ctx, sx, sy, size);
    ctx.fill();
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  } else if (node.type === "procedure") {
    const r = size * 0.3;
    ctx.beginPath();
    ctx.moveTo(sx - size + r, sy - size);
    ctx.lineTo(sx + size - r, sy - size);
    ctx.quadraticCurveTo(sx + size, sy - size, sx + size, sy - size + r);
    ctx.lineTo(sx + size, sy + size - r);
    ctx.quadraticCurveTo(sx + size, sy + size, sx + size - r, sy + size);
    ctx.lineTo(sx - size + r, sy + size);
    ctx.quadraticCurveTo(sx - size, sy + size, sx - size, sy + size - r);
    ctx.lineTo(sx - size, sy - size + r);
    ctx.quadraticCurveTo(sx - size, sy - size, sx - size + r, sy - size);
    ctx.closePath();
    ctx.fill();
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  } else if (node.type === "standard") {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 6;
      const px = sx + size * Math.cos(angle);
      const py = sy + size * Math.sin(angle);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  } else {
    ctx.fillRect(sx - size, sy - size, size * 2, size * 2);
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.strokeRect(sx - size, sy - size, size * 2, size * 2);
    }
  }

  ctx.shadowBlur = 0;

  if (transform.scale > 0.5) {
    ctx.fillStyle = isDimmed ? "rgba(255,255,255,0.2)" : "#ffffff";
    ctx.font = `${Math.max(10, 12 * transform.scale)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.fillText(node.name, sx, sy + size + 4 * transform.scale);
  }

  ctx.restore();
}

function drawEdge(
  ctx: CanvasRenderingContext2D,
  edge: KGEdge,
  source: SimNode,
  target: SimNode,
  isHighlighted: boolean,
  isDimmed: boolean,
  transform: { x: number; y: number; scale: number }
) {
  const sx = source.x * transform.scale + transform.x;
  const sy = source.y * transform.scale + transform.y;
  const tx = target.x * transform.scale + transform.x;
  const ty = target.y * transform.scale + transform.y;

  ctx.save();
  if (isDimmed) ctx.globalAlpha = 0.1;

  const color = EDGE_COLORS[edge.relation] || "#6b7280";
  ctx.strokeStyle = isHighlighted ? color : `${color}88`;
  ctx.lineWidth = isHighlighted ? 2.5 : 1.2;

  if (EDGE_DASH[edge.relation]) {
    ctx.setLineDash([6, 4]);
  }

  ctx.beginPath();
  ctx.moveTo(sx, sy);
  ctx.lineTo(tx, ty);
  ctx.stroke();
  ctx.setLineDash([]);

  if (isHighlighted && transform.scale > 0.6) {
    const mx = (sx + tx) / 2;
    const my = (sy + ty) / 2;
    ctx.fillStyle = color;
    ctx.font = `${Math.max(9, 10 * transform.scale)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText(RELATION_LABELS[edge.relation] || edge.relation, mx, my - 4);
  }

  ctx.restore();
}

export default function KnowledgeGraphPage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";

  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [stats, setStats] = useState<KGStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<KGNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [nodeDetail, setNodeDetail] = useState<Record<string, unknown> | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractProgress, setExtractProgress] = useState(0);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const animFrameRef = useRef<number>(0);
  const transformRef = useRef({ x: 0, y: 0, scale: 1 });
  const dragRef = useRef<{
    nodeId: string | null;
    offsetX: number;
    offsetY: number;
    isPanning: boolean;
    lastX: number;
    lastY: number;
  }>({ nodeId: null, offsetX: 0, offsetY: 0, isPanning: false, lastX: 0, lastY: 0 });
  const graphDataRef = useRef<GraphData | null>(null);

  const fetchGraph = useCallback(async () => {
    try {
      const res = await api.get<GraphData>("/knowledge-graph/graph");
      setGraphData(res.data);
      graphDataRef.current = res.data;
    } catch {
      setGraphData(null);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get<KGStats>("/knowledge-graph/stats");
      setStats(res.data);
    } catch {
      setStats(null);
    }
  }, []);

  useEffect(() => {
    async function init() {
      setLoading(true);
      await Promise.all([fetchGraph(), fetchStats()]);
      setLoading(false);
    }
    init();
  }, [fetchGraph, fetchStats]);

  useEffect(() => {
    if (!graphData) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const w = canvas.parentElement?.clientWidth || 800;
    const h = canvas.parentElement?.clientHeight || 600;
    canvas.width = w * window.devicePixelRatio;
    canvas.height = h * window.devicePixelRatio;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    transformRef.current = {
      x: w / 2,
      y: h / 2,
      scale: 1,
    };

    simNodesRef.current = graphData.nodes.map((n) => ({
      ...n,
      x: (Math.random() - 0.5) * w * 0.6,
      y: (Math.random() - 0.5) * h * 0.6,
      vx: 0,
      vy: 0,
    }));

    const nodeMap = new Map(simNodesRef.current.map((n) => [n.id, n]));
    const edges = graphData.edges;

    const REPULSION = 8000;
    const SPRING_K = 0.005;
    const SPRING_LEN = 120;
    const DAMPING = 0.85;
    const CENTER_GRAVITY = 0.01;
    const ALPHA_DECAY = 0.998;
    let alpha = 1.0;

    function simulate() {
      const nodes = simNodesRef.current;
      if (!nodes.length) return;

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (REPULSION * alpha) / (dist * dist);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          nodes[i].vx -= fx;
          nodes[i].vy -= fy;
          nodes[j].vx += fx;
          nodes[j].vy += fy;
        }
      }

      for (const edge of edges) {
        const src = nodeMap.get(edge.source);
        const tgt = nodeMap.get(edge.target);
        if (!src || !tgt) continue;
        const dx = tgt.x - src.x;
        const dy = tgt.y - src.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = SPRING_K * (dist - SPRING_LEN) * alpha * edge.weight;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        src.vx += fx;
        src.vy += fy;
        tgt.vx -= fx;
        tgt.vy -= fy;
      }

      for (const node of nodes) {
        node.vx -= node.x * CENTER_GRAVITY * alpha;
        node.vy -= node.y * CENTER_GRAVITY * alpha;
        node.vx *= DAMPING;
        node.vy *= DAMPING;

        if (dragRef.current.nodeId !== node.id) {
          node.x += node.vx;
          node.y += node.vy;
        }
      }

      alpha *= ALPHA_DECAY;
      if (alpha < 0.001) alpha = 0.001;
    }

    function render() {
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
      ctx.clearRect(0, 0, w, h);

      ctx.fillStyle = "#0f172a";
      ctx.fillRect(0, 0, w, h);

      const gridStep = 40;
      ctx.strokeStyle = "rgba(51,65,85,0.3)";
      ctx.lineWidth = 0.5;
      const t = transformRef.current;
      const startX = (t.x % (gridStep * t.scale)) - gridStep * t.scale;
      const startY = (t.y % (gridStep * t.scale)) - gridStep * t.scale;
      for (let gx = startX; gx < w; gx += gridStep * t.scale) {
        ctx.beginPath();
        ctx.moveTo(gx, 0);
        ctx.lineTo(gx, h);
        ctx.stroke();
      }
      for (let gy = startY; gy < h; gy += gridStep * t.scale) {
        ctx.beginPath();
        ctx.moveTo(0, gy);
        ctx.lineTo(w, gy);
        ctx.stroke();
      }

      simulate();

      const highlightedIds = new Set<string>();
      const highlightedEdges = new Set<string>();
      if (selectedNode) {
        highlightedIds.add(selectedNode.id);
        for (const edge of edges) {
          if (edge.source === selectedNode.id || edge.target === selectedNode.id) {
            highlightedIds.add(edge.source);
            highlightedIds.add(edge.target);
            highlightedEdges.add(edge.id);
          }
        }
      }

      for (const edge of edges) {
        const src = nodeMap.get(edge.source);
        const tgt = nodeMap.get(edge.target);
        if (!src || !tgt) continue;
        const isHL = highlightedEdges.has(edge.id);
        const isDim = highlightedIds.size > 0 && !isHL;
        drawEdge(ctx, edge, src, tgt, isHL, isDim, t);
      }

      for (const node of simNodesRef.current) {
        const isHL = highlightedIds.has(node.id);
        const isDim = highlightedIds.size > 0 && !isHL;
        drawNode(ctx, node, isHL, isDim, t);
      }

      if (hoveredNode && !selectedNode) {
        const hx = hoveredNode.x * t.scale + t.x;
        const hy = hoveredNode.y * t.scale + t.y;
        ctx.save();
        ctx.fillStyle = "rgba(15,23,42,0.9)";
        ctx.strokeStyle = NODE_COLORS[hoveredNode.type] || "#9ca3af";
        ctx.lineWidth = 1;
        const label = `${hoveredNode.name} (${TYPE_LABELS[hoveredNode.type] || hoveredNode.type})`;
        ctx.font = "13px sans-serif";
        const tw = ctx.measureText(label).width;
        const px = 8;
        const py = 4;
        const bx = hx - tw / 2 - px;
        const by = hy - (NODE_SIZES[hoveredNode.type] || 16) * t.scale - 30;
        ctx.beginPath();
        ctx.roundRect(bx, by, tw + px * 2, 24, 4);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = "#e2e8f0";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, hx, by + 12);
        ctx.restore();
      }

      animFrameRef.current = requestAnimationFrame(render);
    }

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [graphData, selectedNode, hoveredNode]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const nodeMap = () => new Map(simNodesRef.current.map((n) => [n.id, n]));

    function getNodeAt(mx: number, my: number): SimNode | null {
      const t = transformRef.current;
      const nodes = simNodesRef.current;
      for (let i = nodes.length - 1; i >= 0; i--) {
        const n = nodes[i];
        const sx = n.x * t.scale + t.x;
        const sy = n.y * t.scale + t.y;
        const size = (NODE_SIZES[n.type] || 16) * t.scale;
        const dx = mx - sx;
        const dy = my - sy;
        if (n.type === "device") {
          if (dx * dx + dy * dy < size * size) return n;
        } else if (n.type === "fault") {
          if (Math.abs(dx) + Math.abs(dy) < size * 1.5) return n;
        } else if (n.type === "standard") {
          if (dx * dx + dy * dy < size * size) return n;
        } else {
          if (Math.abs(dx) < size && Math.abs(dy) < size) return n;
        }
      }
      return null;
    }

    function onMouseDown(e: MouseEvent) {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const node = getNodeAt(mx, my);
      if (node) {
        const t = transformRef.current;
        dragRef.current = {
          nodeId: node.id,
          offsetX: mx - node.x * t.scale - t.x,
          offsetY: my - node.y * t.scale - t.y,
          isPanning: false,
          lastX: mx,
          lastY: my,
        };
      } else {
        dragRef.current = {
          nodeId: null,
          offsetX: 0,
          offsetY: 0,
          isPanning: true,
          lastX: mx,
          lastY: my,
        };
        setSelectedNode(null);
      }
    }

    function onMouseMove(e: MouseEvent) {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      if (dragRef.current.nodeId) {
        const t = transformRef.current;
        const node = nodeMap().get(dragRef.current.nodeId);
        if (node) {
          node.x = (mx - dragRef.current.offsetX - t.x) / t.scale;
          node.y = (my - dragRef.current.offsetY - t.y) / t.scale;
          node.vx = 0;
          node.vy = 0;
        }
      } else if (dragRef.current.isPanning) {
        const dx = mx - dragRef.current.lastX;
        const dy = my - dragRef.current.lastY;
        transformRef.current.x += dx;
        transformRef.current.y += dy;
        dragRef.current.lastX = mx;
        dragRef.current.lastY = my;
      } else {
        const node = getNodeAt(mx, my);
        setHoveredNode(node);
        if (!canvas) return;
        canvas.style.cursor = node ? "pointer" : "grab";
      }
    }

    function onMouseUp() {
      if (!canvas) return;
      if (dragRef.current.nodeId) {
        const node = nodeMap().get(dragRef.current.nodeId);
        if (node) {
          setSelectedNode((prev) => (prev?.id === node.id ? null : node));
        }
      }
      dragRef.current = {
        nodeId: null,
        offsetX: 0,
        offsetY: 0,
        isPanning: false,
        lastX: 0,
        lastY: 0,
      };
      canvas.style.cursor = "grab";
    }

    function onWheel(e: WheelEvent) {
      e.preventDefault();
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const t = transformRef.current;
      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      const newScale = Math.max(0.1, Math.min(5, t.scale * factor));
      const ratio = newScale / t.scale;
      t.x = mx - (mx - t.x) * ratio;
      t.y = my - (my - t.y) * ratio;
      t.scale = newScale;
    }

    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("mouseleave", onMouseUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });

    return () => {
      canvas.removeEventListener("mousedown", onMouseDown);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("mouseleave", onMouseUp);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, []);

  useEffect(() => {
    if (!selectedNode) {
      setNodeDetail(null);
      return;
    }
    api
      .get(`/knowledge-graph/node/${selectedNode.id}`)
      .then((res) => setNodeDetail(res.data))
      .catch(() => setNodeDetail(null));
  }, [selectedNode]);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await api.get<KGNode[]>("/knowledge-graph/search", {
        params: { query: searchQuery },
      });
      setSearchResults(res.data || []);
    } catch {
      setSearchResults([]);
    }
  }, [searchQuery]);

  const [extractError, setExtractError] = useState<string | null>(null);
  const [extractSource, setExtractSource] = useState<"cases" | "documents">("cases");

  const handleExtractAll = useCallback(async () => {
    if (extracting) return;
    setExtracting(true);
    setExtractProgress(0);
    setExtractError(null);
    try {
      const progressInterval = setInterval(() => {
        setExtractProgress((p) => {
          if (p >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return p + 5;
        });
      }, 1000);

      const endpoint = extractSource === "documents"
        ? "/knowledge-graph/extract-documents"
        : "/knowledge-graph/extract-all";
      await api.post(endpoint);

      clearInterval(progressInterval);
      setExtractProgress(100);

      await Promise.all([fetchGraph(), fetchStats()]);
    } catch {
      setExtractError("实体抽取失败，请检查LLM服务是否可用");
    } finally {
      setTimeout(() => {
        setExtracting(false);
        setExtractProgress(0);
      }, 1500);
    }
  }, [extracting, extractSource, fetchGraph, fetchStats]);

  const focusNode = useCallback((nodeId: string) => {
    const node = simNodesRef.current.find((n) => n.id === nodeId);
    if (!node) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const w = canvas.parentElement?.clientWidth || 800;
    const h = canvas.parentElement?.clientHeight || 600;
    transformRef.current = {
      x: w / 2 - node.x,
      y: h / 2 - node.y,
      scale: 1.5,
    };
    setSelectedNode(node);
  }, []);

  const isEmpty = graphData && graphData.nodes.length === 0 && graphData.edges.length === 0

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">🕸️ 知识图谱</h1>
        <div className="h-96 animate-pulse rounded-lg bg-muted" />
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">🕸️ 知识图谱</h1>
        </div>
        <Card className="border-slate-700 bg-slate-900">
          <CardContent className="flex flex-col items-center justify-center py-20 gap-4">
            <Network className="h-16 w-16 text-slate-500" />
            <h2 className="text-xl font-semibold text-slate-300">知识图谱为空</h2>
            <p className="text-sm text-slate-400 max-w-md text-center">
              当前没有图谱数据。可以从已审核的检修案例或知识文档中抽取实体和关系来构建知识图谱。
            </p>
            {isAdmin ? (
              <div className="flex flex-col items-center gap-4 mt-2">
                <div className="flex items-center gap-2 rounded-lg border border-slate-600 bg-slate-800 p-1">
                  <button
                    onClick={() => setExtractSource("cases")}
                    className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
                      extractSource === "cases"
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <AlertTriangle className="h-3.5 w-3.5" />
                    从案例抽取
                  </button>
                  <button
                    onClick={() => setExtractSource("documents")}
                    className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
                      extractSource === "documents"
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <FileText className="h-3.5 w-3.5" />
                    从文档抽取
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  {extractSource === "cases"
                    ? "从已审核通过的检修案例中抽取设备、故障、解决方案等实体"
                    : "从已审核的知识文档中抽取设备、故障、操作流程、标准规范等实体"}
                </p>
                <Button
                  onClick={handleExtractAll}
                  disabled={extracting}
                  size="lg"
                  className="bg-indigo-600 hover:bg-indigo-700"
                >
                  <Zap className="mr-2 h-5 w-5" />
                  {extracting
                    ? "抽取中..."
                    : extractSource === "cases"
                    ? "从案例抽取实体"
                    : "从文档抽取实体"}
                </Button>
                {extracting && (
                  <div className="w-64 space-y-1">
                    <Progress value={extractProgress} className="h-2" />
                    <p className="text-xs text-slate-400 text-center">
                      {extractProgress >= 100 ? "抽取完成" : `正在抽取... ${Math.round(extractProgress)}%`}
                    </p>
                  </div>
                )}
                {extractError && (
                  <p className="text-xs text-red-400">{extractError}</p>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500">请联系管理员执行实体抽取操作</p>
            )}
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">🕸️ 知识图谱</h1>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Network className="h-4 w-4" />
          <span>力导向布局</span>
          <span className="text-slate-600">|</span>
          <span>滚轮缩放 · 拖拽节点 · 点击高亮</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card className="border-slate-700 bg-slate-900">
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium text-slate-400">节点总数</CardTitle>
            <Circle className="h-4 w-4 text-blue-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-400">
              {stats?.total_nodes ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-700 bg-slate-900">
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium text-slate-400">边总数</CardTitle>
            <Link2 className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-slate-200">
              {stats?.total_edges ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-700 bg-slate-900">
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium text-slate-400">设备数</CardTitle>
            <Cpu className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">
              {stats?.node_types?.device ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-700 bg-slate-900">
          <CardHeader className="flex flex-row items-center justify-between pb-1">
            <CardTitle className="text-xs font-medium text-slate-400">故障数</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-400">
              {stats?.node_types?.fault ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex min-h-0 flex-1 gap-4">
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-lg border border-slate-700 bg-slate-950">
          <canvas ref={canvasRef} className="h-full w-full" style={{ cursor: "grab" }} />

          <div className="absolute bottom-3 left-3 flex items-center gap-2 flex-wrap">
            <Badge variant="outline" className="border-blue-500 bg-blue-500/20 text-blue-300">
              <Circle className="mr-1 h-2.5 w-2.5" /> 设备
            </Badge>
            <Badge variant="outline" className="border-red-500 bg-red-500/20 text-red-300">
              <Diamond className="mr-1 h-2.5 w-2.5" /> 故障
            </Badge>
            <Badge variant="outline" className="border-green-500 bg-green-500/20 text-green-300">
              <Square className="mr-1 h-2.5 w-2.5" /> 解决方案
            </Badge>
            <Badge variant="outline" className="border-amber-500 bg-amber-500/20 text-amber-300">
              <Square className="mr-1 h-2.5 w-2.5 rounded-sm" /> 操作流程
            </Badge>
            <Badge variant="outline" className="border-purple-500 bg-purple-500/20 text-purple-300">
              <Hexagon className="mr-1 h-2.5 w-2.5" /> 标准规范
            </Badge>
          </div>

          {selectedNode && (
            <div className="absolute left-3 top-3 max-w-xs rounded-lg border border-slate-600 bg-slate-900/95 p-3 shadow-xl backdrop-blur">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-semibold text-slate-100">{selectedNode.name}</span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  ✕
                </button>
              </div>
              <Badge
                variant="outline"
                style={{
                  borderColor: NODE_COLORS[selectedNode.type],
                  backgroundColor: `${NODE_COLORS[selectedNode.type]}22`,
                  color: NODE_COLORS[selectedNode.type],
                }}
              >
                {TYPE_LABELS[selectedNode.type] || selectedNode.type}
              </Badge>
              {nodeDetail && (
                <div className="mt-2 space-y-1 text-xs text-slate-400">
                  {Object.entries(nodeDetail).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-2">
                      <span>{k}</span>
                      <span className="text-slate-300">{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex w-72 flex-shrink-0 flex-col gap-3">
          <Card className="border-slate-700 bg-slate-900">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">搜索节点</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex gap-2">
                <Input
                  placeholder="输入关键词..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="border-slate-600 bg-slate-800 text-slate-200 placeholder:text-slate-500"
                />
                <Button size="icon" onClick={handleSearch} variant="outline" className="border-slate-600 bg-slate-800 hover:bg-slate-700">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
              {searchResults.length > 0 && (
                <div className="max-h-48 space-y-1 overflow-y-auto">
                  {searchResults.map((node) => (
                    <button
                      key={node.id}
                      onClick={() => focusNode(node.id)}
                      className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-800"
                    >
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[node.type] || "#9ca3af" }}
                      />
                      <span className="text-slate-300">{node.name}</span>
                      <span className="ml-auto text-xs text-slate-500">
                        {TYPE_LABELS[node.type] || node.type}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {isAdmin && (
            <Card className="border-slate-700 bg-slate-900">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-300">实体抽取</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-1 rounded-md border border-slate-600 bg-slate-800 p-0.5">
                  <button
                    onClick={() => setExtractSource("cases")}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-sm px-2 py-1 text-xs transition-colors ${
                      extractSource === "cases"
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <AlertTriangle className="h-3 w-3" />
                    案例
                  </button>
                  <button
                    onClick={() => setExtractSource("documents")}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-sm px-2 py-1 text-xs transition-colors ${
                      extractSource === "documents"
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <FileText className="h-3 w-3" />
                    文档
                  </button>
                </div>
                <p className="text-xs text-slate-500">
                  {extractSource === "cases"
                    ? "从已审核案例抽取设备、故障、解决方案"
                    : "从已审核文档抽取设备、故障、流程、规范"}
                </p>
                <Button
                  onClick={handleExtractAll}
                  disabled={extracting}
                  className="w-full bg-indigo-600 hover:bg-indigo-700"
                >
                  <Zap className="mr-2 h-4 w-4" />
                  {extracting
                    ? "抽取中..."
                    : extractSource === "cases"
                    ? "从案例抽取"
                    : "从文档抽取"}
                </Button>
                {extracting && (
                  <div className="space-y-1">
                    <Progress value={extractProgress} className="h-2" />
                    <p className="text-xs text-slate-400">
                      {extractProgress >= 100
                        ? "抽取完成"
                        : `正在抽取... ${Math.round(extractProgress)}%`}
                    </p>
                  </div>
                )}
                {extractError && (
                  <p className="text-xs text-red-400">{extractError}</p>
                )}
              </CardContent>
            </Card>
          )}

          <Card className="border-slate-700 bg-slate-900">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">关系类型</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {stats?.edge_types &&
                Object.entries(stats.edge_types).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-6"
                        style={{
                          backgroundColor: EDGE_COLORS[type] || "#6b7280",
                          opacity: 0.7,
                          borderStyle: EDGE_DASH[type] ? "dashed" : "solid",
                          borderWidth: 2,
                          borderColor: EDGE_COLORS[type] || "#6b7280",
                        }}
                      />
                      <span className="text-slate-300">
                        {RELATION_LABELS[type] || type}
                      </span>
                    </div>
                    <span className="text-slate-500">{count}</span>
                  </div>
                ))}
            </CardContent>
          </Card>

          <Card className="border-slate-700 bg-slate-900">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-300">节点类型</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {stats?.node_types &&
                Object.entries(stats.node_types).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[type] || "#9ca3af" }}
                      />
                      <span className="text-slate-300">
                        {TYPE_LABELS[type] || type}
                      </span>
                    </div>
                    <span className="text-slate-500">{count}</span>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
