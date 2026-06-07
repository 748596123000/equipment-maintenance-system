import { useEffect, useState, useRef, useCallback } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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
  Download,
  Maximize2,
  Minimize2,
  Plus,
  Trash2,
  Edit3,
  Save,
  RefreshCw,
  GitBranch,
  Atom,
  Sparkles,
  ChevronRight,
  Loader2,
  TreePine,
  CheckSquare,
  ListChecks,
} from "lucide-react";
import { useTheme, COLORS } from '@/hooks/useTheme'
import { GradientText } from '@/components/ui/gradient-text'

const LOCAL_COLORS = COLORS

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

interface AvailableDoc {
  id: string;
  filename: string;
  category: string;
  status: string;
  created_at: string;
  file_size?: number;
  chunk_count?: number;
  extracted?: boolean;
  node_count?: number;
  edge_count?: number;
}

interface AvailableCase {
  id: string;
  title: string;
  fault_type: string;
  device_model: string;
  status: string;
  created_at: string;
  extracted?: boolean;
  node_count?: number;
  edge_count?: number;
}

interface GraphSource {
  id: string;
  type: "case" | "document";
  name: string;
  detail: string;
  node_count: number;
  edge_count: number;
}

interface ExtractionTaskProgress {
  status: string;
  source: string;
  total: number;
  current: number;
  progress: number;
  success_count: number;
  fail_count: number;
  results: Array<Record<string, unknown>>;
  current_doc?: string;
  error?: string;
}

// Note: CYBER_* constants are now defined in COLORS object above
// NODE_COLORS, EDGE_COLORS will be set dynamically based on theme

const NODE_SIZES: Record<string, number> = {
  device: 22,
  fault: 16,
  solution: 16,
  procedure: 16,
  standard: 14,
  person: 13,
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
  person: "人员",  // v23: 补上
};

const RELATION_LABELS: Record<string, string> = {
  has_fault: "存在故障",
  solved_by: "解决方案",
  related_to: "相关",
  requires: "需要",
  complies_with: "符合",
};

// 兼容旧浏览器：roundRect polyfill
function safeRoundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number
) {
  if (typeof ctx.roundRect === 'function') {
    ctx.roundRect(x, y, w, h, r);
    return;
  }
  // 手动绘制圆角矩形
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

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
  transform: { x: number; y: number; scale: number },
  NODE_COLORS: Record<string, string>
) {
  const sx = node.x * transform.scale + transform.x;
  const sy = node.y * transform.scale + transform.y;
  const size = (NODE_SIZES[node.type] || 16) * transform.scale;

  ctx.save();
  if (isDimmed) ctx.globalAlpha = 0.2;

  const color = NODE_COLORS[node.type] || "#9ca3af";

  if (isHighlighted) {
    ctx.shadowColor = color;
    ctx.shadowBlur = 25;
  }

  ctx.fillStyle = color;

  if (node.type === "device") {
    ctx.beginPath();
    ctx.arc(sx, sy, size, 0, Math.PI * 2);
    ctx.fill();
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }
  } else if (node.type === "fault") {
    drawDiamond(ctx, sx, sy, size);
    ctx.fill();
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2.5;
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
      ctx.lineWidth = 2.5;
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
      ctx.lineWidth = 2.5;
      ctx.stroke();
    }
  } else {
    ctx.fillRect(sx - size, sy - size, size * 2, size * 2);
    if (isHighlighted) {
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2.5;
      ctx.strokeRect(sx - size, sy - size, size * 2, size * 2);
    }
  }

  ctx.shadowBlur = 0;

  if (transform.scale > 0.5) {
    const fontSize = Math.max(9, 11 * transform.scale);
    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";

    // 白色背景描边，让黑色文字在任何颜色节点上都清晰可读
    const textY = sy + size + 5 * transform.scale;
    const textWidth = ctx.measureText(node.name).width;
    const padding = 3 * transform.scale;
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    safeRoundRect(ctx, sx - textWidth / 2 - padding, textY - 1, textWidth + padding * 2, fontSize + 2, 3);
    ctx.fill();

    ctx.fillStyle = isDimmed ? "rgba(0,0,0,0.35)" : "#000000";
    ctx.fillText(node.name, sx, textY);
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
  transform: { x: number; y: number; scale: number },
  EDGE_COLORS: Record<string, string>
) {
  const sx = source.x * transform.scale + transform.x;
  const sy = source.y * transform.scale + transform.y;
  const tx = target.x * transform.scale + transform.x;
  const ty = target.y * transform.scale + transform.y;

  ctx.save();
  if (isDimmed) ctx.globalAlpha = 0.1;

  const color = EDGE_COLORS[edge.relation] || "#6b7280";
  ctx.strokeStyle = isHighlighted ? color : `${color}88`;
  ctx.lineWidth = isHighlighted ? 3 : 1.5;

  if (EDGE_DASH[edge.relation]) {
    ctx.setLineDash([8, 5]);
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
    ctx.font = `bold ${Math.max(10, 11 * transform.scale)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText(RELATION_LABELS[edge.relation] || edge.relation, mx, my - 5);
  }

  ctx.restore();
}

export default function KnowledgeGraphPage() {
  const user = useAuthStore((s) => s.user);
  const { theme } = useTheme()
  const isLight = theme === 'light'
  const colors = isLight ? COLORS.light : COLORS.dark
  
  const isAdmin = user?.role === "admin";
  const [mounted, setMounted] = useState(false);
  
  // Dynamic node and edge colors based on theme
  const NODE_COLORS: Record<string, string> = {
    device: colors.CYBER_CYAN,
    fault: colors.CYBER_RED,
    solution: colors.CYBER_GREEN,
    procedure: colors.CYBER_YELLOW,
    standard: colors.CYBER_BLUE,
    person: "#a78bfa",  // v23: 补上
  };
  
  const EDGE_COLORS: Record<string, string> = {
    has_fault: colors.CYBER_RED,
    solved_by: colors.CYBER_GREEN,
    related_to: colors.textSecondary,
    requires: colors.CYBER_YELLOW,
    complies_with: colors.CYBER_BLUE,
  };
  
  const CYBER_CYAN = colors.CYBER_CYAN
  const CYBER_BLUE = colors.CYBER_BLUE
  const CYBER_PURPLE = colors.CYBER_PURPLE
  const CYBER_GREEN = colors.CYBER_GREEN
  const CYBER_RED = colors.CYBER_RED
  const CYBER_YELLOW = colors.CYBER_YELLOW

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
  const [extractError, setExtractError] = useState<string | null>(null);
  const [extractSource, setExtractSource] = useState<"cases" | "documents">("cases");
  const [availableDocs, setAvailableDocs] = useState<AvailableDoc[]>([]);
  const [availableCases, setAvailableCases] = useState<AvailableCase[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<Set<string>>(new Set());
  const [selectedCaseIds, setSelectedCaseIds] = useState<Set<string>>(new Set());
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskProgress, setTaskProgress] = useState<ExtractionTaskProgress | null>(null);
  const [sources, setSources] = useState<GraphSource[]>([]);
  const [activeSource, setActiveSource] = useState<GraphSource | null>(null);

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editNode, setEditNode] = useState<{ id: string; name: string; type: string } | null>(null);
  const [newNodeName, setNewNodeName] = useState("");
  const [newNodeType, setNewNodeType] = useState("device");
  const [zoomLevel, setZoomLevel] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [pathSourceId, setPathSourceId] = useState("");
  const [pathTargetId, setPathTargetId] = useState("");
  const [pathResult, setPathResult] = useState<string[] | null>(null);
  const [pathEdges, setPathEdges] = useState<string[] | null>(null);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const animFrameRef = useRef<number>(0);
  const transformRef = useRef({ x: 0, y: 0, scale: 1 });
  // v23 新增：避免 useEffect 因 selectedNode/hoveredNode 变化重启而重置 simNodesRef
  const selectedNodeRef = useRef<KGNode | null>(null);
  const hoveredNodeRef = useRef<KGNode | null>(null);
  const dragRef = useRef<{
    nodeId: string | null;
    offsetX: number;
    offsetY: number;
    isPanning: boolean;
    lastX: number;
    lastY: number;
  }>({ nodeId: null, offsetX: 0, offsetY: 0, isPanning: false, lastX: 0, lastY: 0 });
  const graphDataRef = useRef<GraphData | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    function onChange() {
      setIsFullscreen(!!document.fullscreenElement);
    }
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);

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

  const fetchAvailableDocs = useCallback(async () => {
    try {
      const res = await api.get<AvailableDoc[]>("/knowledge-graph/available-documents");
      setAvailableDocs(res.data || []);
    } catch {
      setAvailableDocs([]);
    }
  }, []);

  const fetchAvailableCases = useCallback(async () => {
    try {
      const res = await api.get<AvailableCase[]>("/knowledge-graph/available-cases");
      setAvailableCases(res.data || []);
    } catch {
      setAvailableCases([]);
    }
  }, []);

  const fetchSources = useCallback(async () => {
    try {
      const res = await api.get<GraphSource[]>("/knowledge-graph/sources");
      setSources(res.data || []);
    } catch {
      setSources([]);
    }
  }, []);

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

  const searchPath = useCallback(() => {
    if (!pathSourceId || !pathTargetId || !graphDataRef.current) {
      setPathResult(null);
      setPathEdges(null);
      return;
    }
    const data = graphDataRef.current;
    const adj = new Map<string, string[]>();
    const edgeMap = new Map<string, { source: string; target: string; id: string }>();
    for (const edge of data.edges) {
      if (!adj.has(edge.source)) adj.set(edge.source, []);
      if (!adj.has(edge.target)) adj.set(edge.target, []);
      adj.get(edge.source)!.push(edge.target);
      adj.get(edge.target)!.push(edge.source);
      edgeMap.set(`${edge.source}-${edge.target}`, edge);
      edgeMap.set(`${edge.target}-${edge.source}`, edge);
    }

    const visited = new Set<string>();
    const prev = new Map<string, string | null>();
    const queue: string[] = [pathSourceId];
    visited.add(pathSourceId);
    prev.set(pathSourceId, null);

    while (queue.length > 0) {
      const cur = queue.shift()!;
      if (cur === pathTargetId) break;
      const neighbors = adj.get(cur) || [];
      for (const nb of neighbors) {
        if (!visited.has(nb)) {
          visited.add(nb);
          prev.set(nb, cur);
          queue.push(nb);
        }
      }
    }

    if (!visited.has(pathTargetId)) {
      setPathResult([]);
      setPathEdges(null);
      return;
    }

    const path: string[] = [];
    const pathEdgeIds: string[] = [];
    let step: string | null = pathTargetId;
    while (step) {
      path.unshift(step);
      const p = prev.get(step);
      if (p) {
        const edge = edgeMap.get(`${p}-${step}`) || edgeMap.get(`${step}-${p}`);
        if (edge) pathEdgeIds.unshift(edge.id);
      }
      step = p;
    }
    setPathResult(path);
    setPathEdges(pathEdgeIds);

    const startNode = simNodesRef.current.find(n => n.id === pathSourceId);
    if (startNode) {
      setSelectedNode(startNode);
      focusNode(pathSourceId);
    }
  }, [pathSourceId, pathTargetId, focusNode]);

  const exportGraphImage = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = 'knowledge-graph.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, []);

  const relayoutGraph = useCallback(() => {
    const nodes = simNodesRef.current;
    if (!nodes.length) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const w = canvas.parentElement?.clientWidth || 800;
    const h = canvas.parentElement?.clientHeight || 600;
    for (const node of nodes) {
      node.x = (Math.random() - 0.5) * w * 0.6;
      node.y = (Math.random() - 0.5) * h * 0.6;
      node.vx = 0;
      node.vy = 0;
    }
    transformRef.current = { x: w / 2, y: h / 2, scale: 1 };
  }, []);

  const exportGraph = useCallback(() => {
    if (!graphData) return;
    const dataStr = JSON.stringify(graphData, null, 2);
    const blob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "knowledge-graph.json";
    a.click();
    URL.revokeObjectURL(url);
  }, [graphData]);

  const clearGraph = useCallback(async () => {
    if (!confirm("确定要清空整个知识图谱吗？\n所有节点和关系将被永久删除，此操作不可撤销！")) return;
    try {
      await api.delete("/knowledge-graph/graph");
      await Promise.all([fetchGraph(), fetchStats()]);
      setSelectedNode(null);
      setNodeDetail(null);
      setActiveSource(null);
      setSearchResults([]);
      alert("图谱已清空");
    } catch (err) {
      console.error(err);
      alert("清空失败");
    }
  }, [fetchGraph, fetchStats]);

  const toggleFullscreen = useCallback(() => {
    const container = canvasRef.current?.parentElement;
    if (!container) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen();
    }
  }, []);

  const resetView = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const w = canvas.parentElement?.clientWidth || 800;
    const h = canvas.parentElement?.clientHeight || 600;
    transformRef.current = {
      x: w / 2,
      y: h / 2,
      scale: 1,
    };
  }, []);

  const deleteNode = useCallback(async (nodeId: string) => {
    if (!confirm("确定要删除此节点吗？")) return;
    try {
      await api.delete(`/knowledge-graph/node/${nodeId}`);
      await Promise.all([fetchGraph(), fetchStats()]);
      setSelectedNode(null);
    } catch (err) {
      console.error(err);
      alert("删除失败");
    }
  }, [fetchGraph, fetchStats]);

  const updateNode = useCallback(async () => {
    if (!editNode) return;
    try {
      await api.put(`/knowledge-graph/node/${editNode.id}`, {
        name: editNode.name,
        type: editNode.type,
      });
      const nodes = simNodesRef.current;
      const node = nodes.find((n) => n.id === editNode.id);
      if (node) {
        node.name = editNode.name;
        node.type = editNode.type;
      }
      setEditDialogOpen(false);
      setEditNode(null);
      await Promise.all([fetchGraph(), fetchStats()]);
    } catch (err) {
      console.error(err);
      alert("更新失败");
    }
  }, [editNode, fetchGraph, fetchStats]);

  const addNode = useCallback(async () => {
    if (!newNodeName.trim()) return;
    try {
      await api.post("/knowledge-graph/node", {
        name: newNodeName.trim(),
        type: newNodeType,
      });
      setNewNodeName("");
      setEditDialogOpen(false);
      await Promise.all([fetchGraph(), fetchStats()]);
    } catch (err) {
      console.error(err);
      alert("添加失败");
    }
  }, [newNodeName, newNodeType, fetchGraph, fetchStats]);

  useEffect(() => {
    async function init() {
      setLoading(true);
      try {
        await Promise.all([fetchGraph(), fetchStats(), fetchAvailableDocs(), fetchAvailableCases(), fetchSources()]);
      } catch (e) {
        console.error("Knowledge graph init failed:", e);
      }
      setLoading(false);
    }
    init();
  }, [fetchGraph, fetchStats, fetchAvailableDocs, fetchAvailableCases, fetchSources]);

  // v23 修复：把 selectedNode/hoveredNode 同步到 ref，
  // 避免 useEffect 因 hover/click 重启而重置 simNodesRef.current
  useEffect(() => { selectedNodeRef.current = selectedNode; }, [selectedNode]);
  useEffect(() => { hoveredNodeRef.current = hoveredNode; }, [hoveredNode]);

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
      x: (Math.random() - 0.5) * w * 0.85,
      y: (Math.random() - 0.5) * h * 0.85,
      vx: 0,
      vy: 0,
    }));

    const nodeMap = new Map(simNodesRef.current.map((n) => [n.id, n]));
    const edges = graphData.edges;

    const REPULSION = 25000;
    const SPRING_K = 0.003;
    const SPRING_LEN = 180;
    const DAMPING = 0.82;
    const CENTER_GRAVITY = 0.008;
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

      ctx.fillStyle = isLight ? "rgba(248, 250, 252, 1)" : "rgba(10, 10, 26, 1)";
      ctx.fillRect(0, 0, w, h);

      const gridStep = 40;
      ctx.strokeStyle = isLight ? 'rgba(59, 130, 246, 0.15)' : 'rgba(99, 102, 241, 0.15)';
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
      const sel = selectedNodeRef.current;  // v23: 从 ref 读最新值
      if (sel) {
        highlightedIds.add(sel.id);
        for (const edge of edges) {
          if (edge.source === sel.id || edge.target === sel.id) {
            highlightedIds.add(edge.source);
            highlightedIds.add(edge.target);
            highlightedEdges.add(edge.id);
          }
        }
      }
      // v28: 路径搜索高亮
      if (pathResult && pathResult.length > 0) {
        for (const nid of pathResult) highlightedIds.add(nid);
        if (pathEdges) for (const eid of pathEdges) highlightedEdges.add(eid);
      }

      for (const edge of edges) {
        const src = nodeMap.get(edge.source);
        const tgt = nodeMap.get(edge.target);
        if (!src || !tgt) continue;
        const isHL = highlightedEdges.has(edge.id);
        const isDim = highlightedIds.size > 0 && !isHL;
        drawEdge(ctx, edge, src, tgt, isHL, isDim, t, EDGE_COLORS);
      }

      for (const node of simNodesRef.current) {
        const isHL = highlightedIds.has(node.id);
        const isDim = highlightedIds.size > 0 && !isHL;
        drawNode(ctx, node, isHL, isDim, t, NODE_COLORS);
      }

      const hov = hoveredNodeRef.current;  // v23: 从 ref 读最新值
      if (hov && !sel) {
        const hx = hov.x * t.scale + t.x;
        const hy = hov.y * t.scale + t.y;
        ctx.save();
        ctx.fillStyle = colors.cardBg;
        ctx.strokeStyle = NODE_COLORS[hov.type] || colors.textSecondary;
        ctx.lineWidth = 1.5;
        const label = `${hov.name} (${TYPE_LABELS[hov.type] || hov.type})`;
        ctx.font = "bold 13px sans-serif";
        const tw = ctx.measureText(label).width;
        const px = 10;
        const py = 5;
        const bx = hx - tw / 2 - px;
        const by = hy - (NODE_SIZES[hov.type] || 16) * t.scale - 32;
        ctx.beginPath();
        safeRoundRect(ctx, bx, by, tw + px * 2, 26, 6);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = colors.textPrimary;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(label, hx, by + 13);
        ctx.restore();
      }

      const currentZoom = Math.round(transformRef.current.scale * 100);
      if (currentZoom !== zoomLevel) setZoomLevel(currentZoom);

      animFrameRef.current = requestAnimationFrame(render);
    }

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
    };
  }, [graphData, pathResult, pathEdges]);  // v28: 路径搜索高亮触发重绘

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

    function onTouchStart(e: TouchEvent) {
      e.preventDefault();
      if (!canvas || e.touches.length === 0) return;
      const touch = e.touches[0];
      const rect = canvas.getBoundingClientRect();
      const mx = touch.clientX - rect.left;
      const my = touch.clientY - rect.top;
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

    function onTouchMove(e: TouchEvent) {
      e.preventDefault();
      if (!canvas || e.touches.length === 0) return;
      const touch = e.touches[0];
      const rect = canvas.getBoundingClientRect();
      const mx = touch.clientX - rect.left;
      const my = touch.clientY - rect.top;

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
      }
    }

    function onTouchEnd(e: TouchEvent) {
      e.preventDefault();
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
    }

    canvas.addEventListener("mousedown", onMouseDown);
    canvas.addEventListener("mousemove", onMouseMove);
    canvas.addEventListener("mouseup", onMouseUp);
    canvas.addEventListener("mouseleave", onMouseUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    canvas.addEventListener("touchstart", onTouchStart, { passive: false });
    canvas.addEventListener("touchmove", onTouchMove, { passive: false });
    canvas.addEventListener("touchend", onTouchEnd, { passive: false });

    function onKeyDown(e: KeyboardEvent) {
      if (e.ctrlKey && (e.key === '=' || e.key === '+')) {
        e.preventDefault();
        const t = transformRef.current;
        t.scale = Math.min(5, t.scale * 1.2);
      } else if (e.ctrlKey && (e.key === '-' || e.key === '_')) {
        e.preventDefault();
        const t = transformRef.current;
        t.scale = Math.max(0.1, t.scale * 0.8);
      }
    }
    window.addEventListener('keydown', onKeyDown);

    return () => {
      canvas.removeEventListener("mousedown", onMouseDown);
      canvas.removeEventListener("mousemove", onMouseMove);
      canvas.removeEventListener("mouseup", onMouseUp);
      canvas.removeEventListener("mouseleave", onMouseUp);
      canvas.removeEventListener("wheel", onWheel);
      canvas.removeEventListener("touchstart", onTouchStart);
      canvas.removeEventListener("touchmove", onTouchMove);
      canvas.removeEventListener("touchend", onTouchEnd);
      window.removeEventListener('keydown', onKeyDown);
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
      const res = await api.get("/knowledge-graph/search", {
        params: { query: searchQuery },
      });
      const data = res.data as Record<string, unknown>;
      setSearchResults((data.nodes as KGNode[]) || []);
    } catch {
      setSearchResults([]);
    }
  }, [searchQuery]);

  const pollExtractionProgress = useCallback(async (tid: string) => {
    try {
      const res = await api.get<ExtractionTaskProgress>(`/knowledge-graph/extraction-progress/${tid}`);
      const progress = res.data;
      setTaskProgress(progress);
      setExtractProgress(progress.progress);

      if (progress.status === "completed") {
        setExtracting(false);
        await Promise.all([fetchGraph(), fetchStats(), fetchAvailableCases(), fetchAvailableDocs(), fetchSources()]);
        setTimeout(() => {
          setTaskId(null);
          setTaskProgress(null);
          setExtractProgress(0);
        }, 3000);
        return;
      }

      setTimeout(() => pollExtractionProgress(tid), 2000);
    } catch (err: unknown) {
      const is404 = err && typeof err === "object" && "response" in err &&
        (err as { response?: { status?: number } }).response?.status === 404;
      if (is404) {
        setExtractError("抽取任务已丢失（服务可能已重启），请重新开始抽取");
        setExtracting(false);
        setTaskId(null);
        setTaskProgress(null);
        return;
      }
      setTimeout(() => pollExtractionProgress(tid), 3000);
    }
  }, [fetchGraph, fetchStats, fetchAvailableCases, fetchAvailableDocs, fetchSources]);

  const startExtraction = useCallback(async (endpoint: string, body?: unknown) => {
    if (extracting) return;
    setExtracting(true);
    setExtractProgress(0);
    setExtractError(null);
    setTaskId(null);
    setTaskProgress(null);

    try {
      const res = await api.post(endpoint, body);
      const tid = res.data?.task_id;
      if (tid) {
        setTaskId(tid);
        await pollExtractionProgress(tid);
      } else {
        setExtracting(false);
        await Promise.all([fetchGraph(), fetchStats()]);
      }
    } catch (err: unknown) {
      let errorMsg = "实体抽取失败，请检查LLM服务是否可用";
      if (err && typeof err === "object" && "response" in err) {
        const resp = (err as { response?: { data?: { detail?: string; message?: string } } }).response;
        if (resp?.data?.detail) {
          errorMsg = resp.data.detail;
        } else if (resp?.data?.message) {
          errorMsg = resp.data.message;
        }
      } else if (err instanceof Error) {
        errorMsg = err.message;
      }
      setExtractError(errorMsg);
      setExtracting(false);
    }
  }, [extracting, pollExtractionProgress, fetchGraph, fetchStats]);

  const handleExtractAll = useCallback(async () => {
    const endpoint = extractSource === "documents"
      ? "/knowledge-graph/extract-documents"
      : "/knowledge-graph/extract-all";
    await startExtraction(endpoint);
  }, [extractSource, startExtraction]);

  const handleExtractSelected = useCallback(async () => {
    if (selectedDocIds.size === 0) return;
    await startExtraction("/knowledge-graph/extract-selected", { document_ids: Array.from(selectedDocIds) });
  }, [selectedDocIds, startExtraction]);

  const toggleDocSelection = useCallback((docId: string) => {
    setSelectedDocIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  }, []);

  const toggleSelectAllDocs = useCallback(() => {
    if (selectedDocIds.size === availableDocs.length) {
      setSelectedDocIds(new Set());
    } else {
      setSelectedDocIds(new Set(availableDocs.map((d) => d.id)));
    }
  }, [selectedDocIds.size, availableDocs]);

  const toggleCaseSelection = useCallback((caseId: string) => {
    setSelectedCaseIds((prev) => {
      const next = new Set(prev);
      if (next.has(caseId)) {
        next.delete(caseId);
      } else {
        next.add(caseId);
      }
      return next;
    });
  }, []);

  const toggleSelectAllCases = useCallback(() => {
    if (selectedCaseIds.size === availableCases.length) {
      setSelectedCaseIds(new Set());
    } else {
      setSelectedCaseIds(new Set(availableCases.map((c) => c.id)));
    }
  }, [selectedCaseIds.size, availableCases]);

  const handleExtractSelectedCases = useCallback(async () => {
    if (selectedCaseIds.size === 0) return;
    await startExtraction("/knowledge-graph/extract-selected-cases", { case_ids: Array.from(selectedCaseIds) });
  }, [selectedCaseIds, startExtraction]);

  const handleReprocessDocs = useCallback(async () => {
    if (selectedDocIds.size === 0) return;
    await startExtraction("/knowledge-graph/reprocess-documents", { document_ids: Array.from(selectedDocIds) });
  }, [selectedDocIds, startExtraction]);

  const formatFileSize = useCallback((bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  }, []);

  const handleSourceFilter = useCallback(async (source: GraphSource | null) => {
    if (!source) {
      setActiveSource(null);
      await fetchGraph();
      return;
    }
    try {
      const res = await api.get<GraphData>("/knowledge-graph/graph-by-source", {
        params: { source_id: source.id, source_type: source.type },
      });
      setActiveSource(source);
      setGraphData(res.data);
      graphDataRef.current = res.data;
    } catch {
      setActiveSource(null);
      await fetchGraph();
    }
  }, [fetchGraph]);

  const openEditDialog = (node: SimNode) => {
    setEditNode({ id: node.id, name: node.name, type: node.type });
    setEditDialogOpen(true);
  };

  const openAddDialog = () => {
    setEditNode(null);
    setNewNodeName("");
    setNewNodeType("device");
    setEditDialogOpen(true);
  };

  const isEmpty = (!graphData) || (graphData.nodes.length === 0 && graphData.edges.length === 0);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-12 h-12 border-4 border-muted border-t-primary rounded-full animate-spin" />
        <p className="text-muted-foreground text-sm">加载知识图谱...</p>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className={`space-y-6 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#3b82f6] to-[#2563eb] flex items-center justify-center shadow-lg tilt-card-3d" style={{
              boxShadow: isLight 
                ? '0 4px 15px rgba(59,130,246,0.2)' 
                : '0 4px 25px rgba(59,130,246,0.5)'
            }}>
              <TreePine size={28} className="text-black" />
            </div>
            <div>
              <GradientText as="h1" className="text-2xl font-bold neon-text" style={{ 
                background: isLight 
                  ? 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)' 
                  : 'linear-gradient(135deg, #ffffff 0%, #3b82f6 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                textShadow: isLight 
                  ? 'none' 
                  : '0 0 30px rgba(99,102,241,0.4)'
              }}>
                知识图谱
              </GradientText>
              <p className="text-sm text-muted-foreground">Knowledge Graph Visualization</p>
            </div>
          </div>
        </div>

        <div className="glass-card p-12 text-center depth-shadow-lg" style={{
          background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)',
          border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(59,130,246,0.3)'}`,
          boxShadow: isLight ? '0 4px 20px rgba(0, 0, 0, 0.08)' : 'none'
        }}>
          <TreePine className="h-20 w-20 mx-auto mb-6" style={{ color: isLight ? '#94a3b8' : '#606080' }} />
          <GradientText as="h2" className="text-2xl font-bold mb-3 gradient-text" style={{ 
            background: isLight 
              ? 'linear-gradient(135deg, #1e293b 0%, #3b82f6 100%)'
              : 'linear-gradient(135deg, #f0f0f0 0%, #3b82f6 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            知识图谱为空
          </GradientText>
          <p className="text-muted-foreground max-w-md mx-auto mb-8">
            当前没有图谱数据。可以从已审核的检修案例或知识文档中抽取实体和关系来构建知识图谱。
          </p>
          {isAdmin ? (
            <div className="flex flex-col items-center gap-4">
              <div className="flex items-center gap-2 rounded-xl border border-[rgba(99,102,241,0.3)] bg-[rgba(99,102,241,0.1)] p-1">
                <button
                  onClick={() => setExtractSource("cases")}
                  className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm transition-all ${
                    extractSource === "cases"
                      ? "bg-[#6366f1] text-white shadow-lg"
                      : "text-muted-foreground hover:text-white"
                  }`}
                >
                  <AlertTriangle className="h-4 w-4" />
                  从案例抽取
                </button>
                <button
                  onClick={() => setExtractSource("documents")}
                  className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm transition-all ${
                    extractSource === "documents"
                      ? "bg-[#6366f1] text-white shadow-lg"
                      : "text-muted-foreground hover:text-white"
                  }`}
                >
                  <FileText className="h-4 w-4" />
                  从文档抽取
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                {extractSource === "cases"
                  ? "从已审核通过的检修案例中抽取设备、故障、解决方案等实体"
                  : "从已审核的知识文档中抽取设备、故障、操作流程、标准规范等实体"}
              </p>

              {extractSource === "cases" && availableCases.length > 0 && (
                <div className="w-full max-w-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">已选 {selectedCaseIds.size}/{availableCases.length} 个案例</span>
                    <button
                      onClick={toggleSelectAllCases}
                      className="text-xs flex items-center gap-1 hover:opacity-80 transition-colors"
                      style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }}
                    >
                      <CheckSquare className="h-3 w-3" />
                      {selectedCaseIds.size === availableCases.length ? '取消全选' : '全选'}
                    </button>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1 rounded-lg p-2" style={{
                    background: isLight ? '#f8fafc' : 'rgba(10,10,30,0.5)',
                    border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.15)'}`
                  }}>
                    {availableCases.map((c) => (
                      <label
                        key={c.id}
                        className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:opacity-80 transition-colors"
                        style={{ background: selectedCaseIds.has(c.id) ? (isLight ? 'rgba(99,102,241,0.08)' : 'rgba(99,102,241,0.15)') : 'transparent' }}
                      >
                        <Checkbox
                          checked={selectedCaseIds.has(c.id)}
                          onCheckedChange={() => toggleCaseSelection(c.id)}
                          className="h-3.5 w-3.5"
                        />
                        <span className="text-xs truncate flex-1" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>{c.title}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {extractSource === "documents" && availableDocs.length > 0 && (
                <div className="w-full max-w-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">已选 {selectedDocIds.size}/{availableDocs.length} 个文档</span>
                    <button
                      onClick={toggleSelectAllDocs}
                      className="text-xs flex items-center gap-1 hover:opacity-80 transition-colors"
                      style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }}
                    >
                      <CheckSquare className="h-3 w-3" />
                      {selectedDocIds.size === availableDocs.length ? '取消全选' : '全选'}
                    </button>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1 rounded-lg p-2" style={{
                    background: isLight ? '#f8fafc' : 'rgba(10,10,30,0.5)',
                    border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.15)'}`
                  }}>
                    {availableDocs.map((doc) => (
                      <label
                        key={doc.id}
                        className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:opacity-80 transition-colors"
                        style={{ background: selectedDocIds.has(doc.id) ? (isLight ? 'rgba(99,102,241,0.08)' : 'rgba(99,102,241,0.15)') : 'transparent' }}
                      >
                        <Checkbox
                          checked={selectedDocIds.has(doc.id)}
                          onCheckedChange={() => toggleDocSelection(doc.id)}
                          className="h-3.5 w-3.5"
                        />
                        <span className="text-xs truncate flex-1" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>{doc.filename}</span>
                        {doc.chunk_count === 0 && (
                          <Badge variant="outline" className="text-[9px] px-1 py-0" style={{ borderColor: '#f59e0b', color: '#f59e0b' }}>
                            无分块
                          </Badge>
                        )}
                        {doc.extracted && (
                          <Badge variant="outline" className="text-[9px] px-1 py-0" style={{ borderColor: '#10b981', color: '#10b981' }}>
                            已抽取
                          </Badge>
                        )}
                        <Badge variant="outline" className="text-[9px] px-1 py-0" style={{ borderColor: isLight ? '#cbd5e1' : 'rgba(99,102,241,0.3)' }}>
                          {doc.category}
                        </Badge>
                      </label>
                    ))}
                  </div>
                  {availableDocs.some(d => d.chunk_count === 0) && (
                    <p className="text-[10px] px-1" style={{ color: '#f59e0b' }}>
                      ⚠ 标记"无分块"的文档需要先重新处理才能抽取实体
                    </p>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  onClick={handleExtractAll}
                  disabled={extracting}
                  size="lg"
                  className="bg-gradient-to-r from-[#6366f1] to-[#4f46e5] hover:from-[#4f46e5] hover:to-[#4338ca] shadow-xl shadow-[rgba(99,102,241,0.4)] transition-all"
                >
                  {extracting ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      抽取中...
                    </>
                  ) : (
                    <>
                      <Zap className="mr-2 h-5 w-5" />
                      {extractSource === "cases" ? "全部案例抽取" : "全部文档抽取"}
                    </>
                  )}
                </Button>
                {extractSource === "cases" && selectedCaseIds.size > 0 && (
                  <Button
                    onClick={handleExtractSelectedCases}
                    disabled={extracting}
                    size="lg"
                    variant="outline"
                    className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]"
                  >
                    <ListChecks className="mr-2 h-5 w-5" />
                    抽取选中({selectedCaseIds.size})
                  </Button>
                )}
                {extractSource === "documents" && selectedDocIds.size > 0 && (
                  <Button
                    onClick={handleExtractSelected}
                    disabled={extracting}
                    size="lg"
                    variant="outline"
                    className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]"
                  >
                    <ListChecks className="mr-2 h-5 w-5" />
                    抽取选中({selectedDocIds.size})
                  </Button>
                )}
                {extractSource === "documents" && selectedDocIds.size > 0 && (
                  <Button
                    onClick={handleReprocessDocs}
                    disabled={extracting}
                    size="lg"
                    variant="outline"
                    className="border-[rgba(245,158,11,0.5)] hover:bg-[rgba(245,158,11,0.1)] text-[#f59e0b]"
                  >
                    <RefreshCw className="mr-2 h-5 w-5" />
                    重新处理({selectedDocIds.size})
                  </Button>
                )}
              </div>
              {extracting && (
                <div className="w-72 space-y-2">
                  <Progress value={extractProgress} className="h-2" />
                  <p className="text-xs text-muted-foreground text-center">
                    {taskProgress?.status === "completed"
                      ? taskProgress.source === "reprocess"
                        ? `处理完成！成功${taskProgress.success_count}个，失败${taskProgress.fail_count}个`
                        : `抽取完成！成功${taskProgress.success_count}个，失败${taskProgress.fail_count}个`
                      : taskProgress
                        ? taskProgress.current_doc
                          ? `${taskProgress.current_doc} (${Math.round(extractProgress)}%)`
                          : taskProgress.source === "reprocess"
                            ? `正在处理... ${taskProgress.current}/${taskProgress.total} (${Math.round(extractProgress)}%)`
                            : `正在抽取... ${taskProgress.current}/${taskProgress.total} (${Math.round(extractProgress)}%)`
                        : `正在启动... ${Math.round(extractProgress)}%`
                    }
                  </p>
                </div>
              )}
              {extractError && (
                <p className="text-sm text-[#ef4444]">{extractError}</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">请联系管理员执行实体抽取操作</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex h-[calc(100vh-4rem)] flex-col gap-4 transition-all duration-700 ${mounted ? 'opacity-100' : 'opacity-0'}`}>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#3b82f6] to-[#2563eb] flex items-center justify-center shadow-lg tilt-card-3d" style={{
            boxShadow: isLight 
              ? '0 4px 15px rgba(59,130,246,0.2)' 
              : '0 4px 25px rgba(59,130,246,0.5)'
          }}>
            <TreePine size={24} className="text-black" />
          </div>
          <div>
            <GradientText as="h1" className="text-2xl font-bold" style={{ 
              background: isLight 
                ? 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)' 
                : 'linear-gradient(135deg, #ffffff 0%, #3b82f6 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              知识图谱
            </GradientText>
            <p className="text-xs text-muted-foreground">Knowledge Graph</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" onClick={resetView} className="border-[rgba(59,130,246,0.5)] hover:bg-[rgba(59,130,246,0.1)]">
            <RefreshCw className="mr-1 h-4 w-4" />
            重置视图
            </Button>
            <Button size="sm" variant="outline" onClick={relayoutGraph} className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]">
              <RefreshCw className="mr-1 h-4 w-4" />
              重排布局
            </Button>
            <Button size="sm" variant="outline" onClick={toggleFullscreen} className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]">
            {isFullscreen ? <Minimize2 className="mr-1 h-4 w-4" /> : <Maximize2 className="mr-1 h-4 w-4" />}
            {isFullscreen ? '退出全屏' : '全屏'}
          </Button>
          <Button size="sm" variant="outline" onClick={exportGraph} className="border-[rgba(59,130,246,0.5)] hover:bg-[rgba(59,130,246,0.1)]">
            <Download className="mr-1 h-4 w-4" />
            导出
          </Button>
          <Button size="sm" variant="outline" onClick={exportGraphImage} className="border-[rgba(59,130,246,0.5)] hover:bg-[rgba(59,130,246,0.1)]">
            <Download className="mr-1 h-4 w-4" />
            导出图片
          </Button>
          {isAdmin && (
            <>
            <Button size="sm" onClick={openAddDialog} className="bg-[#6366f1] hover:bg-[#4f46e5]">
              <Plus className="mr-1 h-4 w-4" />
              添加节点
            </Button>
            <Button size="sm" variant="outline" onClick={clearGraph} className="border-[rgba(239,68,68,0.5)] text-[#ef4444] hover:bg-[rgba(239,68,68,0.1)]">
              <Trash2 className="mr-1 h-4 w-4" />
              清空图谱
            </Button>
            </>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        {[
          { label: '节点总数', value: stats?.total_nodes ?? 0, icon: Circle, color: '#6366f1' },
          { label: '边总数', value: stats?.total_edges ?? 0, icon: Link2, color: '#3b82f6' },
          { label: '设备数', value: stats?.node_types?.device ?? 0, icon: Cpu, color: '#6366f1' },
          { label: '故障数', value: stats?.node_types?.fault ?? 0, icon: AlertTriangle, color: '#ef4444' },
          { label: '解决方案', value: stats?.node_types?.solution ?? 0, icon: Square, color: '#10b981' },
          { label: '操作流程', value: stats?.node_types?.procedure ?? 0, icon: Zap, color: '#eab308' },
        ].map((stat) => (
          <div 
            key={stat.label}
            className="glass-card p-3 depth-shadow-lg tilt-card-3d transition-all hover:scale-[1.02]"
            style={{ 
              background: `linear-gradient(135deg, ${stat.color}15 0%, ${stat.color}05 100%)`,
              border: `1px solid ${stat.color}30`
            }}
          >
            <div className="flex items-center justify-between">
              <stat.icon size={16} style={{ color: stat.color }} />
              <span className="text-xl font-bold" style={{ color: stat.color }}>{stat.value}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Main Content */}
      <div className="flex min-h-0 flex-1 flex-col lg:flex-row gap-4">
        {/* Graph Canvas */}
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-2xl depth-shadow-lg min-h-[400px]" style={{
          background: isLight ? '#f8fafc' : 'linear-gradient(180deg, rgba(10,10,26,0.95) 0%, rgba(15,15,35,0.95) 100%)',
          border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(59,130,246,0.3)'}`
        }}>
          <canvas ref={canvasRef} className="h-full w-full" style={{ cursor: "grab", touchAction: "none", display: 'block' }} />

          {/* Legend */}
          <div className="absolute bottom-4 left-4 flex items-center gap-3 flex-wrap max-w-[calc(100%-2rem)]">
            {[
              { type: 'device', label: '设备', color: '#6366f1' },
              { type: 'fault', label: '故障', color: '#ef4444' },
              { type: 'solution', label: '解决方案', color: '#10b981' },
              { type: 'procedure', label: '操作流程', color: '#eab308' },
              { type: 'standard', label: '标准规范', color: '#3b82f6' },
            ].map((item) => (
              <Badge 
                key={item.type}
                variant="outline" 
                className="border-2"
                style={{ 
                  borderColor: item.color,
                  backgroundColor: `${item.color}20`,
                  color: item.color
                }}
              >
                <Circle className="mr-1.5 h-2 w-2" style={{ fill: item.color }} />
                {item.label}
              </Badge>
            ))}
          </div>

          {/* Controls hint */}
          <div className="absolute bottom-4 right-4 text-xs bg-[rgba(10,10,26,0.9)] px-3 py-2 rounded-lg hidden sm:block" style={{ color: isLight ? '#64748b' : '#606080' }}>
            <span className="mr-3">拖拽: 节点/画布</span>
            <span className="mr-3">滚轮: 缩放</span>
            <span>点击: 选中</span>
          </div>

          {/* Zoom Controls */}
          <div className="absolute bottom-14 right-4 flex flex-col items-center gap-1 rounded-xl p-1 shadow-lg backdrop-blur-lg z-10" style={{
            background: isLight ? 'rgba(255,255,255,0.9)' : 'rgba(15,15,35,0.9)',
            border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.3)'}`
          }}>
            <button
              onClick={() => { const t = transformRef.current; t.scale = Math.min(5, t.scale * 1.2); }}
              className="w-7 h-7 flex items-center justify-center rounded-lg hover:opacity-80 transition-colors text-sm font-bold"
              style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}
            >+</button>
            <span className="text-xs font-mono px-2 py-0.5" style={{ color: isLight ? '#64748b' : '#9090a0' }}>
              {zoomLevel}%
            </span>
            <button
              onClick={() => { const t = transformRef.current; t.scale = Math.max(0.1, t.scale * 0.8); }}
              className="w-7 h-7 flex items-center justify-center rounded-lg hover:opacity-80 transition-colors text-sm font-bold"
              style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}
            >-</button>
            <button
              onClick={() => {
                const canvas = canvasRef.current;
                if (!canvas) return;
                const w = canvas.parentElement?.clientWidth || 800;
                const h = canvas.parentElement?.clientHeight || 600;
                transformRef.current = { x: w / 2, y: h / 2, scale: 1 };
              }}
              className="w-7 h-7 flex items-center justify-center rounded-lg hover:opacity-80 transition-colors text-xs"
              style={{ color: isLight ? '#64748b' : '#9090a0' }}
            >⟲</button>
          </div>

          {/* Selected Node Panel */}
          {selectedNode && (
            <div className="absolute left-4 top-4 max-w-xs rounded-2xl depth-shadow-lg p-4 shadow-xl backdrop-blur-lg" style={{
              border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(59,130,246,0.3)'}`,
              background: isLight ? '#ffffff' : 'rgba(15,15,35,0.95)'
            }}>
              <div className="mb-3 flex items-center justify-between">
                <span className="font-bold text-lg" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{selectedNode.name}</span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="w-6 h-6 rounded-full flex items-center justify-center hover:opacity-80 transition-colors"
                  style={{ background: isLight ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.2)', color: isLight ? '#ef4444' : '#ef4444' }}
                >
                  ×
                </button>
              </div>
              <div className="flex flex-wrap gap-2 mb-3">
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
              </div>
              {nodeDetail && (
                <div className="mt-3 space-y-2 text-xs mb-4">
                  {Object.entries(nodeDetail).map(([k, v]) => (
                    <div className="flex justify-between gap-2 p-2 rounded-lg" style={{ background: isLight ? 'rgba(59,130,246,0.08)' : 'rgba(59,130,246,0.1)' }}>
                      <span style={{ color: isLight ? '#64748b' : 'muted-foreground' }}>{k}</span>
                      <span className="font-medium" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                {isAdmin && (
                  <>
                    <Button size="sm" variant="outline" onClick={() => openEditDialog(selectedNode)} className="flex-1 border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]">
                      <Edit3 className="mr-1 h-3 w-3" />
                      编辑
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => deleteNode(selectedNode.id)} className="border-[rgba(239,68,68,0.5)] text-[#ef4444] hover:bg-[rgba(239,68,68,0.1)]">
                      <Trash2 className="mr-1 h-3 w-3" />
                      删除
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Side Panel */}
        <div className={`flex w-full flex-shrink-0 flex-col gap-3 ${isFullscreen ? 'hidden' : 'lg:w-72'}`}>
          {/* Search */}
          <Card className="glass-card depth-shadow-lg" style={{
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.9)',
            border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.2)'}`
          }}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Search size={14} style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }} />
                搜索节点
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Input
                  placeholder="输入关键词..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  className="glass-input"
                />
                <Button size="icon" onClick={handleSearch} variant="outline" className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]">
                  <Search className="h-4 w-4" />
                </Button>
              </div>
              {searchResults.length > 0 && (
                <div className="max-h-52 space-y-1 overflow-y-auto">
                  {searchResults.map((node) => (
                    <button
                      key={node.id}
                      onClick={() => focusNode(node.id)}
                      className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:opacity-80 transition-colors"
                      style={{ background: isLight ? 'rgba(99,102,241,0.05)' : 'rgba(99,102,241,0.1)' }}
                    >
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[node.type] || "#9ca3af" }}
                      />
                      <span className="text-sm" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>{node.name}</span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {TYPE_LABELS[node.type] || node.type}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Extraction */}
          {isAdmin && (
            <Card className="glass-card depth-shadow-lg" style={{
              background: isLight ? '#ffffff' : 'rgba(15,15,30,0.9)',
              border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.2)'}`
            }}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Sparkles size={14} style={{ color: isLight ? colors.CYBER_PURPLE : '#eab308' }} />
                  实体抽取
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-1 rounded-xl p-0.5" style={{ 
                  border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.3)'}`,
                  background: isLight ? '#f8fafc' : 'rgba(99,102,241,0.05)'
                }}>
                  <button
                    onClick={() => setExtractSource("cases")}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-lg px-3 py-2 text-xs transition-all ${
                      extractSource === "cases"
                        ? "text-white shadow-lg"
                        : "transition-colors"
                    }`}
                    style={extractSource === "cases" ? { background: isLight ? colors.CYBER_BLUE : '#6366f1' } : { color: isLight ? '#64748b' : 'muted-foreground' }}
                  >
                    <AlertTriangle className="h-3 w-3" />
                    案例
                  </button>
                  <button
                    onClick={() => setExtractSource("documents")}
                    className={`flex flex-1 items-center justify-center gap-1 rounded-lg px-3 py-2 text-xs transition-all ${
                      extractSource === "documents"
                        ? "text-white shadow-lg"
                        : "transition-colors"
                    }`}
                    style={extractSource === "documents" ? { background: isLight ? colors.CYBER_BLUE : '#6366f1' } : { color: isLight ? '#64748b' : 'muted-foreground' }}
                  >
                    <FileText className="h-3 w-3" />
                    文档
                  </button>
                </div>

                {extractSource === "documents" && availableDocs.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        已选 {selectedDocIds.size}/{availableDocs.length} 个文档
                      </span>
                      <button
                        onClick={toggleSelectAllDocs}
                        className="text-xs flex items-center gap-1 hover:opacity-80 transition-colors"
                        style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }}
                      >
                        <CheckSquare className="h-3 w-3" />
                        {selectedDocIds.size === availableDocs.length ? '取消全选' : '全选'}
                      </button>
                    </div>
                    <div className="max-h-40 overflow-y-auto space-y-1 rounded-lg p-1" style={{ 
                      background: isLight ? '#f8fafc' : 'rgba(10,10,30,0.5)',
                      border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.15)'}`
                    }}>
                      {availableDocs.map((doc) => (
                        <label
                          key={doc.id}
                          className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:opacity-80 transition-colors"
                          style={{ background: selectedDocIds.has(doc.id) ? (isLight ? 'rgba(99,102,241,0.08)' : 'rgba(99,102,241,0.15)') : 'transparent' }}
                        >
                          <Checkbox
                            checked={selectedDocIds.has(doc.id)}
                            onCheckedChange={() => toggleDocSelection(doc.id)}
                            className="h-3.5 w-3.5"
                          />
                          <span className="text-xs truncate flex-1" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>
                            {doc.filename}
                          </span>
                          {doc.chunk_count === 0 && (
                            <Badge variant="outline" className="text-[9px] px-1 py-0" style={{ borderColor: '#f59e0b', color: '#f59e0b' }}>
                              无分块
                            </Badge>
                          )}
                          {doc.extracted && (
                            <Badge variant="outline" className="text-[9px] px-1 py-0" style={{ borderColor: '#10b981', color: '#10b981' }}>
                              已抽取
                            </Badge>
                          )}
                          <span className="text-[9px] shrink-0" style={{ color: isLight ? '#94a3b8' : '#606080' }}>
                            {doc.file_size ? formatFileSize(doc.file_size) : ''}
                          </span>
                        </label>
                      ))}
                    </div>
                    {availableDocs.some(d => d.chunk_count === 0) && (
                      <p className="text-[10px] px-1" style={{ color: '#f59e0b' }}>
                        ⚠ "无分块"文档需先重新处理
                      </p>
                    )}
                  </div>
                )}

                {extractSource === "documents" && availableDocs.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-2">暂无可抽取的文档</p>
                )}

                {extractSource === "cases" && availableCases.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        已选 {selectedCaseIds.size}/{availableCases.length} 个案例
                      </span>
                      <button
                        onClick={toggleSelectAllCases}
                        className="text-xs flex items-center gap-1 hover:opacity-80 transition-colors"
                        style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }}
                      >
                        <CheckSquare className="h-3 w-3" />
                        {selectedCaseIds.size === availableCases.length ? '取消全选' : '全选'}
                      </button>
                    </div>
                    <div className="max-h-40 overflow-y-auto space-y-1 rounded-lg p-1" style={{
                      background: isLight ? '#f8fafc' : 'rgba(10,10,30,0.5)',
                      border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.15)'}`
                    }}>
                      {availableCases.map((c) => (
                        <label
                          key={c.id}
                          className="flex items-center gap-2 px-2 py-1.5 rounded-md cursor-pointer hover:opacity-80 transition-colors"
                          style={{ background: selectedCaseIds.has(c.id) ? (isLight ? 'rgba(99,102,241,0.08)' : 'rgba(99,102,241,0.15)') : 'transparent' }}
                        >
                          <Checkbox
                            checked={selectedCaseIds.has(c.id)}
                            onCheckedChange={() => toggleCaseSelection(c.id)}
                            className="h-3.5 w-3.5"
                          />
                          <span className="text-xs truncate flex-1" style={{ color: isLight ? '#1e293b' : '#e8e8e8' }}>
                            {c.title}
                          </span>
                          {c.extracted && (
                            <Badge variant="outline" className="text-[9px] px-1 py-0" style={{ borderColor: '#10b981', color: '#10b981' }}>
                              已抽取
                            </Badge>
                          )}
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                {extractSource === "cases" && availableCases.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-2">暂无可抽取的案例</p>
                )}

                <p className="text-xs text-muted-foreground">
                  {extractSource === "cases"
                    ? "从已审核案例抽取设备、故障、解决方案"
                    : "从已审核文档抽取设备、故障、流程、规范"}
                </p>

                <div className="flex gap-2">
                  <Button
                    onClick={handleExtractAll}
                    disabled={extracting}
                    className="flex-1 bg-gradient-to-r from-[#6366f1] to-[#4f46e5] hover:from-[#4f46e5] hover:to-[#4338ca]"
                  >
                    <Zap className="mr-1 h-4 w-4" />
                    {extracting ? "抽取中..." : "全部抽取"}
                  </Button>
                  {extractSource === "documents" && selectedDocIds.size > 0 && (
                    <Button
                      onClick={handleExtractSelected}
                      disabled={extracting}
                      variant="outline"
                      className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]"
                    >
                      <ListChecks className="mr-1 h-4 w-4" />
                      抽取选中({selectedDocIds.size})
                    </Button>
                  )}
                  {extractSource === "cases" && selectedCaseIds.size > 0 && (
                    <Button
                      onClick={handleExtractSelectedCases}
                      disabled={extracting}
                      variant="outline"
                      className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]"
                    >
                      <ListChecks className="mr-1 h-4 w-4" />
                      抽取选中({selectedCaseIds.size})
                    </Button>
                  )}
                  {extractSource === "documents" && selectedDocIds.size > 0 && (
                    <Button
                      onClick={handleReprocessDocs}
                      disabled={extracting}
                      variant="outline"
                      className="border-[rgba(245,158,11,0.5)] hover:bg-[rgba(245,158,11,0.1)] text-[#f59e0b]"
                    >
                      <RefreshCw className="mr-1 h-4 w-4" />
                      重新处理({selectedDocIds.size})
                    </Button>
                  )}
                </div>

                {extracting && (
                  <div className="space-y-1">
                    <Progress value={extractProgress} className="h-2" />
                    <p className="text-xs text-muted-foreground text-center">
                      {taskProgress?.status === "completed"
                        ? taskProgress.source === "reprocess"
                          ? `处理完成！成功${taskProgress.success_count}个，失败${taskProgress.fail_count}个`
                          : `抽取完成！成功${taskProgress.success_count}个，失败${taskProgress.fail_count}个`
                        : taskProgress
                          ? taskProgress.current_doc
                            ? `${taskProgress.current_doc} (${Math.round(extractProgress)}%)`
                            : taskProgress.source === "reprocess"
                              ? `正在处理... ${taskProgress.current}/${taskProgress.total} (${Math.round(extractProgress)}%)`
                              : `正在抽取... ${taskProgress.current}/${taskProgress.total} (${Math.round(extractProgress)}%)`
                          : `正在启动... ${Math.round(extractProgress)}%`
                      }
                    </p>
                  </div>
                )}
                {extractError && (
                  <p className="text-xs text-[#ef4444]">{extractError}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Path Search Card */}
          <Card className="glass-card depth-shadow-lg" style={{
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.9)',
            border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.2)'}`
          }}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <GitBranch size={14} style={{ color: isLight ? '#6366f1' : '#6366f1' }} />
                路径搜索
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <div>
                  <Label className="text-xs text-muted-foreground">起点</Label>
                  <Select value={pathSourceId} onValueChange={setPathSourceId}>
                    <SelectTrigger className="glass-input h-8 text-xs">
                      <SelectValue placeholder="选择起点节点" />
                    </SelectTrigger>
                    <SelectContent>
                      {(graphData?.nodes || []).map(n => (
                        <SelectItem key={n.id} value={n.id} className="text-xs">
                          {n.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">终点</Label>
                  <Select value={pathTargetId} onValueChange={setPathTargetId}>
                    <SelectTrigger className="glass-input h-8 text-xs">
                      <SelectValue placeholder="选择终点节点" />
                    </SelectTrigger>
                    <SelectContent>
                      {(graphData?.nodes || []).map(n => (
                        <SelectItem key={n.id} value={n.id} className="text-xs">
                          {n.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  size="sm"
                  onClick={searchPath}
                  disabled={!pathSourceId || !pathTargetId}
                  className="w-full bg-gradient-to-r from-[#6366f1] to-[#4f46e5]"
                >
                  <GitBranch className="mr-1 h-4 w-4" />
                  搜索路径
                </Button>
              </div>

              {pathResult && pathResult.length === 0 && (
                <p className="text-xs text-[#ef4444] text-center py-2">未找到路径</p>
              )}

              {pathResult && pathResult.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-medium" style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>
                    找到路径 ({pathResult.length - 1} 步)
                  </div>
                  <div className="flex flex-wrap items-center gap-1 text-xs rounded-lg p-2" style={{
                    background: isLight ? 'rgba(99,102,241,0.08)' : 'rgba(99,102,241,0.1)'
                  }}>
                    {pathResult.map((nodeId, idx) => {
                      const node = graphData?.nodes.find(n => n.id === nodeId);
                      return (
                        <>
                          {idx > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                          <span
                            className="cursor-pointer hover:underline"
                            style={{ color: (NODE_COLORS as any)[node?.type || ''] || '#6366f1' }}
                            onClick={() => focusNode(nodeId)}
                          >
                            {node?.name || nodeId}
                          </span>
                        </>
                      );
                    })}
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => { setPathResult(null); setPathEdges(null); setPathSourceId(""); setPathTargetId(""); }}
                    className="w-full border-[rgba(239,68,68,0.5)] text-[#ef4444]"
                  >
                    清除结果
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Source Filter */}
          {sources.length > 0 && (
            <Card className="glass-card depth-shadow-lg" style={{
              background: isLight ? '#ffffff' : 'rgba(15,15,30,0.9)',
              border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.2)'}`
            }}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Network size={14} style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }} />
                  按来源筛选
                  {activeSource && (
                    <button
                      onClick={() => handleSourceFilter(null)}
                      className="ml-auto text-xs px-2 py-0.5 rounded-md hover:opacity-80 transition-colors"
                      style={{ background: isLight ? 'rgba(239,68,68,0.1)' : 'rgba(239,68,68,0.2)', color: '#ef4444' }}
                    >
                      清除筛选
                    </button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                {activeSource && (
                  <div className="text-xs p-2 rounded-lg mb-2" style={{
                    background: isLight ? 'rgba(59,130,246,0.08)' : 'rgba(59,130,246,0.1)',
                    border: `1px solid ${isLight ? '#bfdbfe' : 'rgba(59,130,246,0.3)'}`
                  }}>
                    <span style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>当前: </span>
                    <span className="font-medium" style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }}>{activeSource.name}</span>
                    <span className="ml-1 text-muted-foreground">({activeSource.node_count}节点 {activeSource.edge_count}边)</span>
                  </div>
                )}
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {sources.map((source) => (
                    <button
                      key={`${source.type}-${source.id}`}
                      onClick={() => handleSourceFilter(activeSource?.id === source.id ? null : source)}
                      className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-xs hover:opacity-80 transition-colors"
                      style={{
                        background: activeSource?.id === source.id
                          ? (isLight ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.2)')
                          : 'transparent',
                        border: activeSource?.id === source.id ? `1px solid ${isLight ? '#818cf8' : 'rgba(99,102,241,0.5)'}` : '1px solid transparent'
                      }}
                    >
                      <span className="h-3 w-3 rounded-sm flex items-center justify-center shrink-0" style={{
                        backgroundColor: source.type === 'case' ? '#f59e0b' : '#3b82f6',
                      }}>
                        {source.type === 'case' ? <AlertTriangle className="h-2 w-2 text-white" /> : <FileText className="h-2 w-2 text-white" />}
                      </span>
                      <span className="flex-1 min-w-0" style={{ color: isLight ? '#1e293b' : '#e8e8e8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{source.name}</span>
                      <span className="text-muted-foreground shrink-0">{source.node_count}N/{source.edge_count}E</span>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Relation Types */}
          <Card className="glass-card depth-shadow-lg" style={{
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.9)',
            border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(59,130,246,0.2)'}`
          }}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <GitBranch size={14} style={{ color: isLight ? colors.CYBER_BLUE : '#3b82f6' }} />
                关系类型
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {stats?.edge_types &&
                Object.entries(stats.edge_types).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm p-2 rounded-lg hover:opacity-80 transition-colors" style={{ color: isLight ? '#64748b' : 'inherit' }}>
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-8"
                        style={{
                          backgroundColor: EDGE_COLORS[type] || "#6b7280",
                          opacity: 0.7,
                          borderStyle: EDGE_DASH[type] ? "dashed" : "solid",
                          borderWidth: 2,
                          borderColor: EDGE_COLORS[type] || "#6b7280",
                        }}
                      />
                      <span style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>
                        {RELATION_LABELS[type] || type}
                      </span>
                    </div>
                    <span style={{ color: isLight ? '#64748b' : 'muted-foreground' }}>{count}</span>
                  </div>
                ))}
            </CardContent>
          </Card>

          {/* Node Types */}
          <Card className="glass-card depth-shadow-lg" style={{
            background: isLight ? '#ffffff' : 'rgba(15,15,30,0.9)',
            border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.2)'}`
          }}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Atom size={14} style={{ color: isLight ? colors.CYBER_BLUE : '#6366f1' }} />
                节点类型
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {stats?.node_types &&
                Object.entries(stats.node_types).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm p-2 rounded-lg hover:opacity-80 transition-colors">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[type] || "#9ca3af" }}
                      />
                      <span style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}>
                        {TYPE_LABELS[type] || type}
                      </span>
                    </div>
                    <span style={{ color: isLight ? '#64748b' : 'muted-foreground' }}>{count}</span>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit/Add Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="glass-card-enhanced" style={{
          background: isLight ? '#ffffff' : 'rgba(15,15,30,0.95)',
          border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.3)'}`
        }}>
          <DialogHeader>
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#6366f1] to-[#4f46e5] flex items-center justify-center">
                <Atom size={20} className="text-white" />
              </div>
              <GradientText as="h2" className="text-xl gradient-text" style={{ 
                background: 'linear-gradient(135deg, #ffffff 0%, #6366f1 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>
                {editNode ? "编辑节点" : "添加节点"}
              </GradientText>
            </div>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label className="text-[#c0c0d0]">节点名称</Label>
              <Input
                value={editNode ? editNode.name : newNodeName}
                onChange={(e) => {
                  if (editNode) {
                    setEditNode({ ...editNode, name: e.target.value });
                  } else {
                    setNewNodeName(e.target.value);
                  }
                }}
                className="glass-input"
                placeholder="输入节点名称"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-[#c0c0d0]">节点类型</Label>
              <Select
                value={editNode ? editNode.type : newNodeType}
                onValueChange={(val) => {
                  if (editNode) {
                    setEditNode({ ...editNode, type: val });
                  } else {
                    setNewNodeType(val);
                  }
                }}
              >
                <SelectTrigger className="glass-input">
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent className="glass-card" style={{ background: 'rgba(20,20,40,0.95)' }}>
                  {Object.entries(TYPE_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key} className="hover:bg-[rgba(99,102,241,0.1)]">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: NODE_COLORS[key] }} />
                        {label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)} className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]">
              取消
            </Button>
            <Button
              onClick={editNode ? updateNode : addNode}
              className="bg-[#6366f1] hover:bg-[#4f46e5]"
            >
              <Save className="mr-2 h-4 w-4" />
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}