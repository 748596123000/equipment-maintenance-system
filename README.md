# 设备检修知识检索与作业系统

> 基于大模型的设备检修知识图谱系统 — 银河麒麟V11 LoongArch 版

## 项目简介

本项目是一个面向电力/工业设备检修领域的智能化知识管理平台，集成了大语言模型（LLM）、知识图谱、向量检索等技术，帮助检修人员快速获取设备故障诊断、维修方案等专业知识。

**核心能力：**
- **智能问答**：基于知识库 RAG 检索增强生成，支持多厂商 LLM API（DashScope、DeepSeek、MiniMax、智谱、百川、月之暗面、硅基流动等）
- **知识图谱**：Canvas 2D 自绘引擎，支持力导向布局、节点拖拽、缩放、路径搜索（BFS）、导出图片
- **文档管理**：PDF/Word/Excel/PPT 多格式文档解析，自动分块入库，支持图文混排预览
- **案例管理**：检修案例的创建、审核、检索全流程
- **作业指引**：结构化检修规程检索与智能问答
- **多模态**：图片 OCR 识别、图片描述生成、以图搜图

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (React 18 + Vite)                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 知识检索 │ │ 知识图谱 │ │ 知识库  │ │ 案例管理 │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 作业指引 │ │ 智能问答 │ │ 系统管理 │ │ 用户中心 │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                      后端 (FastAPI + Python)                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 用户认证 │ │ 文档解析 │ │ RAG引擎 │ │ 知识图谱 │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ LLM服务 │ │ Embedding│ │ OCR服务 │ │ 视觉服务 │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据层                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ SQLite  │ │ ChromaDB │ │ 向量索引 │ │ 文件存储 │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 部署环境

- **操作系统**：银河麒麟高级服务器版 V11 (LoongArch 架构)
- **CPU**：龙芯 3A5000/3A6000 系列
- **Python**：3.10+
- **Node.js**：18+
- **Nginx**：反向代理 + 静态文件服务

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/748596123000/equipment-maintenance-system.git
cd equipment-maintenance-system
```

### 2. 安装后端依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. 构建前端

```bash
cd frontend
npm install
npm run build
```

### 4. 启动服务

```bash
# 启动后端
cd ..
source venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 配置 Nginx 指向前端 dist 目录
# 参考 deploy/loongarch-frontend.service
```

详细部署步骤请参考 [DEPLOY_LOONGARCH.md](DEPLOY_LOONGARCH.md)。

## 项目结构

```
.
├── app/                          # 后端代码
│   ├── api/                      # API 路由
│   │   ├── admin.py              # 系统管理、配置、API测试
│   │   ├── auth.py               # 用户认证
│   │   ├── case.py               # 检修案例管理
│   │   ├── chat.py               # 智能问答
│   │   ├── guide.py              # 作业指引
│   │   ├── knowledge_graph.py    # 知识图谱
│   │   ├── search.py             # 知识检索
│   │   └── upload.py             # 文档上传
│   ├── core/                     # 核心引擎
│   │   ├── document_parser.py    # 文档解析
│   │   ├── pdf_parser.py         # PDF 解析
│   │   ├── rag_engine.py         # RAG 检索增强生成
│   │   ├── retriever.py          # 向量检索
│   │   └── image_retriever.py    # 图片检索
│   ├── models/                   # 数据模型
│   │   └── database.py           # SQLite 数据库操作
│   ├── services/                 # 服务层
│   │   ├── llm_service.py        # LLM 服务（多厂商支持）
│   │   ├── embedding_service.py  # Embedding 服务
│   │   ├── vision_service.py     # 视觉服务
│   │   └── ocr_service.py        # OCR 服务
│   └── main.py                   # FastAPI 应用入口
├── frontend/                     # 前端代码
│   ├── src/
│   │   ├── pages/                # 页面组件
│   │   │   ├── knowledge-graph.tsx   # 知识图谱
│   │   │   ├── search.tsx            # 知识检索
│   │   │   ├── knowledge-base.tsx    # 知识库
│   │   │   ├── cases.tsx             # 案例管理
│   │   │   ├── guide.tsx             # 作业指引
│   │   │   ├── api-settings.tsx      # API 设置
│   │   │   └── admin.tsx             # 系统管理
│   │   ├── components/           # 公共组件
│   │   ├── stores/               # 状态管理
│   │   └── lib/                  # 工具库
│   └── dist/                     # 构建产物
├── deploy/                       # 部署脚本
├── docs/                         # 项目文档
├── requirements.txt              # Python 依赖
└── README.md                     # 本文件
```

## 支持的 LLM 厂商

| 厂商 | 类型 | LoongArch 兼容性 |
|------|------|-----------------|
| DashScope (通义千问) | 云端 API | 完全兼容 |
| DeepSeek | 云端 API | 完全兼容 |
| MiniMax | 云端 API | 完全兼容 |
| 智谱 AI (Zhipu) | 云端 API | 完全兼容 |
| 百川智能 | 云端 API | 完全兼容 |
| 月之暗面 (Kimi) | 云端 API | 完全兼容 |
| 硅基流动 (SiliconFlow) | 云端 API | 完全兼容 |
| llama.cpp | 本地推理 | 需源码编译 |
| Ollama | 本地推理 | 需 x86 环境 |
| OpenAI 兼容 API | 通用接口 | 完全兼容 |

## 开发日志

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| v25 | 2026-06-04 | 节点 CRUD API、部署脚本修复 |
| v26 | 2026-06-05 | TDZ 错误修复、删除按钮文字 |
| v27 | 2026-06-05 | 清空图谱、桌面启动脚本 |
| v28 | 2026-06-06 | 图谱 5 项能力优化（缩放、全屏、导出、重排、路径搜索） |
| v29 | 2026-06-06 | API Key 切换修复（前后端） |
| v30 | 2026-06-07 | 7 项问题修复（emoji、图文混排、rejected 文档过滤等） |
| v31 | 2026-06-07 | LLMService api_key 回退逻辑修复、案例数据库迁移 |

## 许可证

MIT License
