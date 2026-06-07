# 知识图谱能力优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为知识图谱 Canvas 页面新增缩放控件、全屏模式、导出图片、自动布局重排、路径搜索 5 项能力，并优化节点文字可读性。

**Architecture:** 全部为纯前端修改，单文件 `knowledge-graph.tsx`。缩放控件用 DOM 浮动面板叠加在 canvas 容器上；全屏用 Fullscreen API；导出图片用 Canvas.toDataURL；路径搜索用前端 BFS 算法。

**Tech Stack:** React 18, TypeScript, Canvas 2D, lucide-react 图标库

---

### Task 1: 节点文字颜色改为黑色 + 白色背景描边

**Files:**
- Modify: `frontend/src/pages/knowledge-graph.tsx:265-271`

- [ ] **Step 1: 修改 drawNode 文字颜色**

将 `drawNode()` 函数中 L267-L268 的文字渲染逻辑：

```typescript
// 当前代码（L265-271）：
ctx.shadowBlur = 0;

if (transform.scale > 0.5) {
  ctx.fillStyle = isDimmed ? "rgba(255,255,255,0.2)" : "#ffffff";
  ctx.font = `bold ${Math.max(11, 13 * transform.scale)}px sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText(node.name, sx, sy + size + 5 * transform.scale);
}
```

改为：

```typescript
ctx.shadowBlur = 0;

if (transform.scale > 0.5) {
  const fontSize = Math.max(11, 13 * transform.scale);
  ctx.font = `bold ${fontSize}px sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";

  // 白色背景描边，让黑色文字在任何颜色节点上都清晰可读
  const textY = sy + size + 5 * transform.scale;
  const textWidth = ctx.measureText(node.name).width;
  const padding = 3 * transform.scale;
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  ctx.beginPath();
  ctx.roundRect(sx - textWidth / 2 - padding, textY - 1, textWidth + padding * 2, fontSize + 2, 3);
  ctx.fill();

  ctx.fillStyle = isDimmed ? "rgba(0,0,0,0.35)" : "#000000";
  ctx.fillText(node.name, sx, textY);
}
```

- [ ] **Step 2: 验证 build**

Run: `cd frontend && npm run build` → must exit 0

---

### Task 2: 缩放控件（浮动面板右下角）

**Files:**
- Modify: `frontend/src/pages/knowledge-graph.tsx`

- [ ] **Step 1: 添加缩放控件 UI**

在 canvas 容器（`<div className="relative ...">`）内，图例下方，添加缩放浮动面板。定位在 canvas 容器右下角，图例上方。

在 JSX 的 canvas 后面、legend 上方插入：

```tsx
{/* Zoom Controls */}
<div className="absolute bottom-4 right-12 flex flex-col items-center gap-1 rounded-xl p-1 shadow-lg backdrop-blur-lg z-10" style={{
  background: isLight ? 'rgba(255,255,255,0.9)' : 'rgba(15,15,35,0.9)',
  border: `1px solid ${isLight ? '#e2e8f0' : 'rgba(99,102,241,0.3)'}`
}}>
  <button
    onClick={() => {
      const t = transformRef.current;
      t.scale = Math.min(5, t.scale * 1.2);
    }}
    className="w-7 h-7 flex items-center justify-center rounded-lg hover:opacity-80 transition-colors text-sm font-bold"
    style={{ color: isLight ? '#1e293b' : '#f0f0f0' }}
  >+</button>
  <span className="text-xs font-mono px-2 py-0.5" style={{ color: isLight ? '#64748b' : '#9090a0' }}>
    {Math.round(transformRef.current.scale * 100)}%
  </span>
  <button
    onClick={() => {
      const t = transformRef.current;
      t.scale = Math.max(0.1, t.scale * 0.8);
    }}
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
```

- [ ] **Step 2: 添加 useRef 跟踪缩放百分比用于实时显示**

缩放控件显示百分比需要响应式。加一个 `zoomLevel` state 用于实时刷新显示。在 useEffect 的 render() 循环里更新它。

添加 state：
```typescript
const [zoomLevel, setZoomLevel] = useState(100);
```

在 `render()` 函数末尾（`animFrameRef.current = requestAnimationFrame(render)` 之前）：
```typescript
const currentZoom = Math.round(transformRef.current.scale * 100);
if (currentZoom !== zoomLevel) {
  setZoomLevel(currentZoom);
}
```

然后将缩放控件里的 `Math.round(transformRef.current.scale * 100)%` 改为 `{zoomLevel}%`。

- [ ] **Step 3: 添加快捷键 Ctrl+= / Ctrl+-**

在 canvas 事件绑定的 useEffect 里，添加 keydown 事件监听：

```typescript
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
// 在 cleanup 里移除
window.removeEventListener('keydown', onKeyDown);
```

- [ ] **Step 4: 验证 build**

Run: `cd frontend && npm run build` → must exit 0

---

### Task 3: 全屏模式

**Files:**
- Modify: `frontend/src/pages/knowledge-graph.tsx`

- [ ] **Step 1: 添加全屏 state 和切换函数**

```typescript
const [isFullscreen, setIsFullscreen] = useState(false);
```

全屏切换函数：

```typescript
const toggleFullscreen = useCallback(() => {
  const container = canvasRef.current?.parentElement;
  if (!container) return;
  if (document.fullscreenElement) {
    document.exitFullscreen();
    setIsFullscreen(false);
  } else {
    container.requestFullscreen();
    setIsFullscreen(true);
  }
}, []);
```

- [ ] **Step 2: 监听 fullscreenchange 事件（F11 退出也能同步）**

```typescript
useEffect(() => {
  function onChange() {
    setIsFullscreen(!!document.fullscreenElement);
  }
  document.addEventListener('fullscreenchange', onChange);
  return () => document.removeEventListener('fullscreenchange', onChange);
}, []);
```

- [ ] **Step 3: 在头栏加全屏按钮**

在「导出」按钮后面加：

```tsx
<Button size="sm" variant="outline" onClick={toggleFullscreen} className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]">
  {isFullscreen ? <Minimize2 className="mr-1 h-4 w-4" /> : <Maximize2 className="mr-1 h-4 w-4" />}
  {isFullscreen ? '退出全屏' : '全屏'}
</Button>
```

需要 import `Maximize2` 和 `Minimize2` 从 `lucide-react`。检查当前 imports 里是否已有，没有则加。

- [ ] **Step 4: 全屏时隐藏侧栏**

在主内容区域的 `lg:flex` 容器上添加条件类：

```tsx
<div className={`flex w-full lg:w-72 flex-shrink-0 flex-col gap-3 ${isFullscreen ? 'hidden' : ''}`}>
```

- [ ] **Step 5: 验证 build**

Run: `cd frontend && npm run build` → must exit 0

---

### Task 4: 导出图片

**Files:**
- Modify: `frontend/src/pages/knowledge-graph.tsx`

- [ ] **Step 1: 添加 exportGraphImage 函数**

```typescript
const exportGraphImage = useCallback(() => {
  const canvas = canvasRef.current;
  if (!canvas) return;
  const link = document.createElement('a');
  link.download = 'knowledge-graph.png';
  link.href = canvas.toDataURL('image/png');
  link.click();
}, []);
```

- [ ] **Step 2: 将「导出」按钮改为下拉菜单**

当前单个导出按钮，改为带下拉的 SplitButton 结构（或简单地在旁边加一个导出图片按钮）。

最简单方案：在「导出」按钮旁再加一个图片导出按钮：

```tsx
<Button size="sm" variant="outline" onClick={exportGraphImage} className="border-[rgba(59,130,246,0.5)] hover:bg-[rgba(59,130,246,0.1)]">
  <ImageDown className="mr-1 h-4 w-4" />
  导出图片
</Button>
```

需要 import `ImageDown`（或 `Image`，视 lucide-react 版本而定）。或者用已有的 download 图标但改文字。

更简方案：把「导出」按钮改为文字加下拉图标，点击弹出两个选项。但考虑到代码复杂度，直接用两个相邻按钮更简单。

**采用：** 将现有「导出」按钮文字改为「导出 JSON」，旁边加一个「导出图片」按钮。

- [ ] **Step 3: 验证 build**

Run: `cd frontend && npm run build` → must exit 0

---

### Task 5: 自动布局重排

**Files:**
- Modify: `frontend/src/pages/knowledge-graph.tsx`

- [ ] **Step 1: 添加 relayoutGraph 函数**

```typescript
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
```

- [ ] **Step 2: 在头栏添加重排按钮**

在「重置视图」按钮后加：

```tsx
<Button size="sm" variant="outline" onClick={relayoutGraph} className="border-[rgba(99,102,241,0.5)] hover:bg-[rgba(99,102,241,0.1)]">
  <RefreshCw className="mr-1 h-4 w-4" />
  重排布局
</Button>
```

- [ ] **Step 3: 验证 build**

Run: `cd frontend && npm run build` → must exit 0

---

### Task 6: 路径搜索

**Files:**
- Modify: `frontend/src/pages/knowledge-graph.tsx`

- [ ] **Step 1: 添加路径搜索相关 state**

```typescript
const [pathSourceId, setPathSourceId] = useState<string>("");
const [pathTargetId, setPathTargetId] = useState<string>("");
const [pathResult, setPathResult] = useState<string[] | null>(null);
const [pathEdges, setPathEdges] = useState<string[] | null>(null);
```

- [ ] **Step 2: 添加 BFS 路径搜索函数**

```typescript
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

  // BFS
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

  // 重建路径
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

  // 选中路径起点
  const startNode = simNodesRef.current.find(n => n.id === pathSourceId);
  if (startNode) {
    setSelectedNode(startNode);
    focusNode(pathSourceId);
  }
}, [pathSourceId, pathTargetId, focusNode]);
```

- [ ] **Step 3: 在侧栏添加路径搜索卡片**

在「搜索节点」Card 后面、源筛选 Card 前面插入：

```tsx
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
              <React.Fragment key={nodeId}>
                {idx > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
                <span
                  className="cursor-pointer hover:underline"
                  style={{ color: NODE_COLORS[node?.type || ''] || '#6366f1' }}
                  onClick={() => focusNode(nodeId)}
                >
                  {node?.name || nodeId}
                </span>
              </React.Fragment>
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
```

注意需要 import `React` 用于 `React.Fragment`。检查当前文件顶部是否有 `import React`，没有则加。

- [ ] **Step 4: 路径高亮集成到 canvas 渲染**

在现有的 `highlightedIds` / `highlightedEdges` 逻辑（L662-674）中，扩展支持路径搜索高亮：

```typescript
const highlightedIds = new Set<string>();
const highlightedEdges = new Set<string>();
const sel = selectedNodeRef.current;
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
// v27: 路径搜索高亮
if (pathResult && pathResult.length > 0) {
  for (const nid of pathResult) highlightedIds.add(nid);
  if (pathEdges) for (const eid of pathEdges) highlightedEdges.add(eid);
}
```

需要将 `pathResult` 和 `pathEdges` 引入到渲染 useEffect 的闭包依赖中。当前 useEffect 只依赖 `graphData`，需要改为依赖 `[graphData, pathResult, pathEdges]`。

- [ ] **Step 5: 验证 build**

Run: `cd frontend && npm run build` → must exit 0

---

### Task 7: 最终打包

**Files:**
- Create: `update-v28-full.tar.gz` (打包脚本)

- [ ] **Step 1: Build 最终版**

```bash
cd frontend && rm -rf dist && npm run build
```

- [ ] **Step 2: 打包**

```bash
rm -rf /tmp/v28-full && mkdir -p /tmp/v28-full/update-v28/app/api /tmp/v28-full/update-v28/frontend-dist
cp app/api/knowledge_graph.py /tmp/v28-full/update-v28/app/api/
cp -r frontend/dist/. /tmp/v28-full/update-v28/frontend-dist/
cd /tmp/v28-full && tar -czf /tmp/update-v28-full.tar.gz update-v28/
cp /tmp/update-v28-full.tar.gz /mnt/e/ruanjianbei/update-v28-full.tar.gz
echo "DONE"
```