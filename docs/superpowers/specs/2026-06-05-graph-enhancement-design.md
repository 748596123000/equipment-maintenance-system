# 知识图谱能力优化设计文档

## 概述

在已有 Canvas 知识图谱基础上，新增 5 项核心能力 + 节点文字可读性优化。

## 功能列表

### 1. 缩放控件
- **位置**: 画布右下角，绝对定位浮动面板
- **UI**: 
  - `+` 按钮：放大 1.2x
  - 百分比显示（如 `72%`）
  - `-` 按钮：缩小 0.8x
  - `⟲` 重置按钮：恢复 100%
- **快捷键**: `Ctrl+=` 放大，`Ctrl+-` 缩小
- **实现**: 操作 `transformRef.current.scale`，与 `wheel` 事件共享同一 state

### 2. 全屏模式
- **按钮位置**: 头栏工具区
- **功能**: Fullscreen API 将 canvas 容器全屏
- **状态**: 全屏时图标切换为 `Minimize2`，退出恢复 `Maximize2`
- **侧栏行为**: 全屏时隐藏侧栏（`lg:w-72` 卡片列），退出恢复

### 3. 导出图片
- **按钮位置**: 头栏「导出」按钮改为下拉菜单（导出 JSON / 导出 PNG）
- **实现**: `canvas.toDataURL("image/png")` → 创建 `<a>` 下载

### 4. 自动布局重排
- **触发**: 头栏按钮「重排布局」/ 缩放控件内重置按钮
- **行为**: `simNodesRef.current` 重新随机分配 x/y，重置 alpha=1.0，力导向模拟重新运行
- **不刷新后端**: 纯前端操作

### 5. 路径搜索
- **位置**: 侧栏新卡片「路径搜索」，位于「搜索节点」下方
- **UI**: 起点下拉 + 终点下拉（选项为所有节点名），「搜索」按钮
- **算法**: 前端 BFS（无权图，`graphData.edges`）
- **结果**: 搜索成功后，路径节点和边通过已有 `highlightedIds` 高亮，自动聚焦到起点
- **无结果**: 显示「未找到路径」

### 6. 节点文字颜色
- **修改位置**: `drawNode()` L267
- **改动**: `#ffffff` → `#000000`，并加白色阴影描边 `shadowColor=rgba(255,255,255,0.8)` `shadowBlur=4`

## 不涉及后端修改
以上所有功能均为纯前端 Canvas 操作 + DOM UI，无需新增后端端点。

## 技术要点
- 缩放控件复用 `transformRef.current.scale`
- 路径搜索 BFS 用 `graphDataRef.current.edges` 构建邻接表
- 全屏用 `element.requestFullscreen()` / `document.exitFullscreen()`
- 分步构建，每步可独立测试