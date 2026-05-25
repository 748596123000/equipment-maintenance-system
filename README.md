# 设备检修知识检索与作业系统

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115.0-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react" alt="React">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/ChromaDB-0.5.0-FF6B6B?style=flat-square" alt="ChromaDB">
  <img src="https://img.shields.io/badge/GPU-CUDA%20Accelerated-76B900?style=flat-square&logo=nvidia" alt="GPU">
  <img src="https://img.shields.io/badge/Security-Hardened-brightgreen?style=flat-square" alt="Security">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License">
</p>

<p align="center">
  <b>基于多模态大模型技术的工业设备检修知识检索与智能作业系统</b>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#技术架构">技术架构</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#gpu加速">GPU加速</a> •
  <a href="#安全特性">安全特性</a> •
  <a href="#部署指南">部署指南</a>
</p>

---

## 项目简介

本项目是**第15届中国软件杯竞赛**参赛作品，旨在为工业设备检修领域提供一套完整的知识检索与智能作业解决方案。系统融合多模态大模型技术，支持文本、图片等多种形式的检修知识检索，提供AI智能问答、作业指引生成、案例管理等功能。

系统内置**摩托车发动机维修手册**作为示例数据，首次启动自动导入知识库，开箱即用。

### 核心能力

- 🔍 **多模态知识检索** — 支持文本语义检索、关键词检索、混合检索、以图搜图
- 🤖 **AI智能问答** — 基于大模型的检修知识问答，支持上下文记忆与图片输入
- 📋 **作业指引生成** — 自动生成标准化检修作业指导书，支持导出
- 📚 **案例管理** — 检修案例的创建、审核、检索与复用
- 📄 **文档管理** — 多格式文档上传、OCR识别、向量化存储与在线预览
- ⚡ **GPU加速** — PaddleOCR GPU加速 + 本地视觉模型推理，支持CPU/API自动降级
- 🎯 **验证码防护** — 登录图形验证码，防止暴力破解
- 👥 **用户权限管理** — 管理员审批制用户注册，细粒度权限控制
- 🔒 **安全加固** — Bearer Token认证、bcrypt密码哈希、速率限制、XSS/SQL注入/路径遍历防护

---

## 功能特性

### 1. 知识检索模块

| 功能 | 描述 |
|------|------|
| 语义检索 | 基于向量相似度的语义理解检索 |
| 关键词检索 | 传统TF-IDF关键词匹配 |
| 混合检索 | 语义+关键词融合排序，效果最佳 |
| 图片检索 | 以图搜图，查找相似故障图片 |

### 2. AI问答模块

- 💬 多轮对话，支持上下文记忆
- 🖼️ 支持图片输入，图文混合问答
- 📊 检索结果溯源，显示知识来源
- 📝 会话历史保存与管理

### 3. 作业指引模块

- 🎯 根据设备型号和故障类型生成作业指导书
- ⚙️ 支持多种安全等级和详细程度配置
- 📄 导出Word格式文档
- 🔄 历史指引管理与复用

### 4. 案例管理模块

- 📝 检修案例创建与编辑（含故障分析、维修过程、经验总结）
- ✔️ 管理员审核流程（待审核/已通过/已拒绝）
- 🔍 案例检索与推荐
- 📊 案例统计分析

### 5. 文档管理模块

- 📤 多格式文档上传（PDF/Word/Excel/PPT/图片等）
- 🔍 智能解析：PDF提取 + OCR文字识别 + 视觉模型图片描述
- 👁️ 文档在线预览
- ✅ 文档审批流程（待审批/已通过/已拒绝）
- 🏷️ 文档分类与关键词搜索

### 6. API管理模块

- ⚙️ 在线配置LLM/Embedding模型参数
- 🔍 检索参数调优（Top K、相似度阈值）
- 📦 文本分块策略配置
- 🖥️ GPU状态实时监控
- 👁️ OCR/视觉模型后端切换

---

## 技术架构

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端层 (React + Vite)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 登录页面  │ │ 知识检索  │ │ 作业指引  │ │ 案例管理  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 知识管理  │ │ 知识库    │ │ 个人中心  │ │ API管理   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │ Bearer Token / Vite Proxy
┌────────────────────────▼────────────────────────────────────┐
│                      API层 (FastAPI)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 用户认证  │ │ 知识检索  │ │ 文件上传  │ │ AI问答   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 作业指引  │ │ 案例管理  │ │ 系统管理  │ │ GPU状态   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      服务层                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Embedding服务 │ │ LLM服务      │ │ RAG引擎      │        │
│  │ (通义千问)    │ │ (通义千问)    │ │ (检索增强)   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ OCR服务      │ │ 视觉模型服务  │ │ GPU检测      │        │
│  │ (PaddleOCR)  │ │ (Qwen2-VL)   │ │ (CUDA)      │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      数据层                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ SQLite       │ │ ChromaDB     │ │ 文件系统     │        │
│  │ (结构化数据)  │ │ (向量数据库)  │ │ (PDF/图片)   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| 前端 | React | 18+ | 现代化SPA界面 |
| 前端构建 | Vite | 5+ | 极速开发与构建 |
| UI组件 | shadcn/ui + Radix | - | 高质量可访问组件 |
| 后端 | FastAPI | 0.115.0 | 高性能Web框架 |
| 服务器 | Uvicorn | 0.32.0 | ASGI服务器 |
| 数据库 | SQLite | - | 轻量级关系数据库 |
| 向量库 | ChromaDB | 0.5.0 | 向量数据库(duckdb后端) |
| 大模型 | 通义千问 | qwen-max | 大语言模型 |
| 向量化 | 通义千问 Embedding | text-embedding-v3 | 文本向量化(1024维) |
| OCR | PaddleOCR | 2.8+ | GPU加速文字识别 |
| 视觉模型 | Qwen2-VL | 2B-Instruct | 本地图片理解 |
| 密码哈希 | bcrypt | 4.0.1 | 安全密码存储 |
| 容器化 | Docker + Docker Compose | - | 多阶段构建+GPU支持 |

---

## GPU加速

系统支持GPU加速文档解析和OCR识别，提供完整的降级链：

```
GPU模式 → CPU模式 → API模式
```

### GPU加速功能

| 组件 | GPU模式 | CPU模式 | API模式 |
|------|---------|---------|---------|
| OCR识别 | PaddleOCR + CUDA | PaddleOCR + CPU | 关闭 |
| 图片描述 | Qwen2-VL 本地推理 | - | DashScope qwen-vl-max |
| GPU检测 | torch + paddle 自动检测 | - | - |

### GPU部署

```bash
# 安装GPU依赖
pip install -r requirements-gpu.txt

# 使用GPU版Docker部署
docker compose -f docker-compose.gpu.yml up -d --build
```

### GPU配置

通过API管理页面可在线配置：

- **OCR后端**：auto / paddleocr / none
- **OCR GPU加速**：开启/关闭
- **OCR语言**：中文/英文/中英混合
- **视觉模型后端**：auto / dashscope / local
- **本地视觉模型**：Qwen/Qwen2-VL-2B-Instruct

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（前端构建）
- 4GB+ 内存（GPU模式需8GB+）
- 通义千问 API Key ([阿里云DashScope](https://dashscope.console.aliyun.com/))

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/748596123000/equipment-maintenance-system.git
cd equipment-maintenance-system
```

2. **创建虚拟环境并安装后端依赖**

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
# 如需GPU加速
pip install -r requirements-gpu.txt
```

3. **安装前端依赖并构建**

```bash
cd frontend
npm install
npm run build
cd ..
```

4. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 DashScope API Key
```

`.env` 文件示例：

```env
DASHSCOPE_API_KEY=your-api-key-here
ENVIRONMENT=development
DEBUG=False
CORS_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
```

5. **启动服务**

方式一：分别启动（开发推荐）

```bash
# 终端1：启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端2：启动前端开发服务器
cd frontend
npm run dev
```

方式二：一键启动（Windows）

```powershell
.\start.bat
```

方式三：一键启动（Linux）

```bash
bash deploy/start.sh
```

6. **访问系统**

- 前端界面：http://localhost:3000
- API文档：http://localhost:8000/docs (DEBUG=True时)
- 健康检查：http://localhost:8000/health

7. **默认账号**

系统首次启动自动创建管理员账号，密码保存在 `data/.initial_passwords` 文件中。

> 💡 **示例数据**：系统首次启动时会自动扫描 `samples/` 目录，将摩托车发动机维修手册导入知识库，无需手动上传。

---

## 安全特性

本项目经过全面安全审计与加固，实现了多层安全防护。

### 认证与授权

- ✅ **Bearer Token 认证** — HTTPBearer + 24小时过期 + 服务端Token存储
- ✅ **bcrypt 密码哈希** — 自动升级旧版SHA256哈希，登录时无缝迁移
- ✅ **图形验证码** — 登录强制验证码，防止暴力破解
- ✅ **路由级认证依赖** — 所有API端点默认需要认证
- ✅ **对象级授权** — 资源所有权校验（案例/指引/会话/文档），防止越权访问
- ✅ **管理员审批制** — 用户注册需管理员审批
- ✅ **登录枚举防护** — 统一错误消息，防止账户枚举攻击

### 防护机制

- ✅ **速率限制** — 登录5次/5分钟，API 60次/分钟
- ✅ **XSS防护** — html.escape() 转义所有动态内容
- ✅ **SQL注入防护** — 参数化查询 + 列名白名单 + LIKE转义
- ✅ **路径遍历防护** — basename + realpath 校验
- ✅ **文件上传安全** — 类型/大小/魔数三重校验
- ✅ **错误信息脱敏** — 前后端统一友好错误提示，不暴露内部实现
- ✅ **Token自动清理** — 后台异步任务每小时清理过期Token
- ✅ **验证码一次性使用** — 验证码校验后立即销毁，5分钟过期

### Docker安全

- ✅ 多阶段构建，运行时无编译工具
- ✅ 非root用户运行 (appuser)
- ✅ `no-new-privileges:true` 防止提权
- ✅ `cap_drop: ALL` 最小权限
- ✅ 日志大小限制
- ✅ 双服务健康检查

---

## 部署指南

### 方式一：Docker部署（推荐生产环境）

**CPU版：**

```bash
cp .env.example .env
# 编辑 .env
docker compose up -d --build
```

**GPU版（需NVIDIA Container Toolkit）：**

```bash
cp .env.example .env
# 编辑 .env
docker compose -f docker-compose.gpu.yml up -d --build
```

### 方式二：银河麒麟/龙芯架构部署

```bash
scp -r equipment-maintenance-system/ user@kylin-server:/opt/
cd /opt/equipment-maintenance-system
bash deploy/kylin_setup.sh
```

### 方式三：手动部署

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && npm run build && cd ..

cp .env.example .env
# 编辑 .env

bash deploy/start.sh
```

### 数据备份

```bash
bash deploy/backup.sh
# 备份文件保存在 ./backups/ 目录
```

---

## 项目结构

```
equipment-maintenance-system/
├── app/                          # 后端API
│   ├── api/                      # API路由
│   │   ├── auth.py              # 用户认证（验证码 + Bearer Token + bcrypt）
│   │   ├── chat.py              # AI问答（SSE流式 + 会话管理）
│   │   ├── search.py            # 知识检索（语义/关键词/混合/图片）
│   │   ├── upload.py            # 文件上传（多格式解析 + 向量化）
│   │   ├── guide.py             # 作业指引（SSE流式生成）
│   │   ├── case.py              # 案例管理（审核流程）
│   │   └── admin.py             # 系统管理（配置 + GPU状态）
│   ├── core/                     # 核心逻辑
│   │   ├── retriever.py         # 检索引擎
│   │   ├── rag_engine.py        # RAG引擎
│   │   ├── guide_generator.py   # 指引生成
│   │   ├── chunker.py           # 文本分块
│   │   ├── pdf_parser.py        # PDF解析（GPU视觉模型）
│   │   ├── document_parser.py   # 多格式文档解析（OCR + 视觉）
│   │   └── image_retriever.py   # 图片检索
│   ├── models/                   # 数据模型
│   │   └── database.py          # 数据库操作
│   ├── services/                 # 外部服务
│   │   ├── llm_service.py       # 大模型服务
│   │   ├── embedding_service.py # 向量化服务
│   │   ├── ocr_service.py       # OCR服务（PaddleOCR + GPU）
│   │   └── vision_service.py    # 视觉模型服务（Qwen2-VL + DashScope降级）
│   ├── utils/                    # 工具函数
│   │   ├── helpers.py           # 公共工具
│   │   ├── gpu_utils.py         # GPU检测与缓存管理
│   │   └── init_data.py         # 示例数据自动导入
│   ├── config.py                # 配置管理（环境变量 + OCR/视觉/GPU配置）
│   └── main.py                  # FastAPI入口（安全中间件）
├── frontend/                     # React前端
│   ├── src/
│   │   ├── pages/               # 页面组件
│   │   │   ├── login.tsx        # 登录（验证码）
│   │   │   ├── dashboard.tsx    # 首页仪表盘
│   │   │   ├── search.tsx       # 知识检索
│   │   │   ├── guide.tsx        # 作业指引
│   │   │   ├── knowledge.tsx    # 知识管理
│   │   │   ├── knowledge-base.tsx # 知识库
│   │   │   ├── admin.tsx        # 系统管理
│   │   │   ├── profile.tsx      # 个人中心
│   │   │   └── api-settings.tsx # API管理（GPU状态监控）
│   │   ├── components/          # UI组件
│   │   │   ├── layout/          # 布局（侧边栏/头部）
│   │   │   ├── guards/          # 路由守卫（认证/权限）
│   │   │   ├── document/        # 文档组件
│   │   │   └── ui/              # shadcn/ui基础组件
│   │   ├── stores/              # Zustand状态管理
│   │   └── lib/                 # 工具库（API客户端）
│   ├── vite.config.ts           # Vite配置（代理）
│   └── package.json             # 前端依赖
├── samples/                      # 示例数据
│   └── 摩托车发动机维修手册.pdf  # 内置维修手册
├── deploy/                       # 部署脚本
│   ├── start.sh                 # 启动脚本
│   ├── stop.sh                  # 停止脚本
│   ├── backup.sh                # 备份脚本
│   └── kylin_setup.sh           # 银河麒麟部署
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git忽略文件
├── Dockerfile                    # Docker镜像（CPU版）
├── Dockerfile.gpu                # Docker镜像（GPU版，NVIDIA CUDA）
├── docker-compose.yml            # Docker编排（CPU版）
├── docker-compose.gpu.yml        # Docker编排（GPU版）
├── requirements.txt              # Python依赖
├── requirements-gpu.txt          # GPU加速依赖
└── README.md                     # 项目介绍
```

---

## 开发团队

- **项目**: 第15届中国软件杯竞赛作品
- **技术栈**: React + FastAPI + 通义千问 + ChromaDB + PaddleOCR
- **特色**: GPU加速文档解析 + 多模态知识检索 + 全面安全加固

---

## 许可证

[MIT License](./LICENSE)

---

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Web框架
- [React](https://react.dev/) - 用户界面构建库
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - OCR文字识别
- [Qwen2-VL](https://github.com/QwenLM/Qwen2-VL) - 视觉语言模型
- [通义千问](https://tongyi.aliyun.com/) - 大语言模型
- [中国软件杯](http://www.cnsoftbei.com/) - 竞赛平台

---

<p align="center">
  Made with ❤️ for Industrial Equipment Maintenance
</p>
