# 设备检修知识检索与作业系统

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115.0-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Streamlit-1.40.0-FF4B4B?style=flat-square&logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/ChromaDB-0.5.0-FF6B6B?style=flat-square" alt="ChromaDB">
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
  <a href="#安全特性">安全特性</a> •
  <a href="#部署指南">部署指南</a>
</p>

---

## 项目简介

本项目是**第15届中国软件杯竞赛**参赛作品，旨在为工业设备检修领域提供一套完整的知识检索与智能作业解决方案。系统融合多模态大模型技术，支持文本、图片等多种形式的检修知识检索，提供AI智能问答、作业指引生成、案例管理等功能。

系统内置**摩托车发动机维修手册**作为示例数据，首次启动自动导入知识库，开箱即用。

### 核心能力

- 🔍 **多模态知识检索** — 支持文本语义检索、关键词检索、混合检索
- 🤖 **AI智能问答** — 基于大模型的检修知识问答，支持上下文记忆与图片输入
- 📋 **作业指引生成** — 自动生成标准化检修作业指导书，支持导出
- 📚 **案例管理** — 检修案例的创建、审核、检索与复用
- 📄 **文档管理** — PDF文档上传、解析、向量化存储与在线预览
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

- 📤 PDF批量上传与自动解析
- 🔍 PDF内容解析、分块与向量化存储
- 👁️ PDF在线预览
- ✅ 文档审批流程（待审批/已通过/已拒绝）
- 🏷️ 文档分类与关键词搜索

---

## 技术架构

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Streamlit)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 登录页面  │ │ 知识检索  │ │ 作业指引  │ │ 案例管理  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 知识管理  │ │ 系统管理  │ │ PDF数据库 │ │ 知识库    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │ Bearer Token / HTTPS
┌────────────────────────▼────────────────────────────────────┐
│                      API层 (FastAPI)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 用户认证  │ │ 知识检索  │ │ 文件上传  │ │ AI问答   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                     │
│  │ 作业指引  │ │ 案例管理  │ │ 系统管理  │                     │
│  └──────────┘ └──────────┘ └──────────┘                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      服务层                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Embedding服务 │ │ LLM服务      │ │ RAG引擎      │        │
│  │ (通义千问)    │ │ (通义千问)    │ │ (检索增强)   │        │
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
| 前端 | Streamlit | 1.40.0 | 数据应用框架 |
| 后端 | FastAPI | 0.115.0 | 高性能Web框架 |
| 服务器 | Uvicorn | 0.32.0 | ASGI服务器 |
| 数据库 | SQLite | - | 轻量级关系数据库 |
| 向量库 | ChromaDB | 0.5.0 | 向量数据库(duckdb后端) |
| 大模型 | 通义千问 | qwen-max | 大语言模型 |
| 向量化 | 通义千问 Embedding | text-embedding-v3 | 文本向量化(1024维) |
| 密码哈希 | bcrypt | 4.0.1 | 安全密码存储 |
| 缓存 | cachetools | 5.3.3 | LRU/TTL缓存 |
| 容器化 | Docker + Docker Compose | - | 多阶段构建+安全加固 |

---

## 快速开始

### 环境要求

- Python 3.10+
- 4GB+ 内存
- 通义千问 API Key ([阿里云DashScope](https://dashscope.console.aliyun.com/))

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/yourusername/equipment-maintenance-system.git
cd equipment-maintenance-system
```

2. **创建虚拟环境**

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
# 如需开发/测试依赖
pip install -r requirements-dev.txt
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
CORS_ORIGINS=["http://localhost:8501"]
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
```

5. **启动服务**

方式一：分别启动（开发推荐）

```bash
# 终端1：启动后端
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端2：启动前端
streamlit run ui/app.py
```

方式二：一键启动

```bash
bash deploy/start.sh
```

6. **访问系统**

- 前端界面：http://localhost:8501
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
- ✅ **路由级认证依赖** — 所有API端点默认需要认证
- ✅ **对象级授权** — 资源所有权校验（案例/指引/会话/文档），防止越权访问
- ✅ **管理员审批制** — 用户注册需管理员审批
- ✅ **SSE流认证** — GET端点通过Token查询参数验证身份
- ✅ **登录枚举防护** — 统一错误消息，防止账户枚举攻击

### 防护机制

- ✅ **速率限制** — 登录5次/5分钟，API 60次/分钟
- ✅ **XSS防护** — html.escape() 转义所有动态内容
- ✅ **SQL注入防护** — 参数化查询 + 列名白名单 + LIKE转义
- ✅ **路径遍历防护** — basename + realpath 校验
- ✅ **文件上传安全** — 类型/大小/PDF魔数三重校验
- ✅ **错误信息脱敏** — 前后端统一友好错误提示，不暴露内部实现
- ✅ **Token自动清理** — 后台异步任务每小时清理过期Token

### 安全响应头

| 响应头 | 值 | 说明 |
|--------|-----|------|
| X-Content-Type-Options | nosniff | 防止MIME嗅探 |
| X-Frame-Options | DENY | 防止点击劫持 |
| Content-Security-Policy | default-src 'self'; ... | 防止XSS注入 |
| Strict-Transport-Security | max-age=31536000 | 强制HTTPS |
| Permissions-Policy | camera=(), microphone=() | 限制浏览器API |

### Docker安全

- ✅ 多阶段构建，运行时无编译工具
- ✅ 非root用户运行 (appuser)
- ✅ `no-new-privileges:true` 防止提权
- ✅ `cap_drop: ALL` 最小权限
- ✅ 日志大小限制
- ✅ 双服务健康检查

### 配置安全

- 生产环境强制 DEBUG=False
- 依赖版本精确锁定（含bcrypt兼容版本）
- 敏感文件排除在版本控制外（.env, .initial_passwords, *.db, data/）
- 开发依赖独立管理（requirements-dev.txt）
- CI集成安全扫描（bandit）

---

## 部署指南

### 方式一：Docker部署（推荐生产环境）

1. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env，填入API Key和生产环境配置
```

2. **构建并启动**

```bash
docker-compose up -d --build
```

3. **查看状态**

```bash
docker-compose ps
docker-compose logs -f
```

4. **停止服务**

```bash
docker-compose down
```

### 方式二：银河麒麟/龙芯架构部署

项目提供完整的麒麟Linux部署脚本，支持LoongArch架构：

```bash
# 1. 上传项目到服务器
scp -r equipment-maintenance-system/ user@kylin-server:/opt/

# 2. 执行部署脚本
cd /opt/equipment-maintenance-system
bash deploy/kylin_setup.sh
```

部署脚本会自动：
- 检测系统架构和包管理器
- 安装Python 3.10+和系统依赖
- 创建虚拟环境并安装Python依赖
- 配置数据目录和权限
- 生成初始管理员密码

### 方式三：手动部署

1. **安装依赖**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **配置环境**

```bash
cp .env.example .env
# 编辑 .env
```

3. **启动服务**

```bash
# 使用启动脚本（含健康检查和PID管理）
bash deploy/start.sh

# 或手动启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
streamlit run ui/app.py --server.port 8501 &
```

4. **停止服务**

```bash
bash deploy/stop.sh
```

### 生产环境Nginx配置

```nginx
# HTTP重定向到HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS主配置
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # API后端
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://localhost:8000;
    }

    # Streamlit前端（含WebSocket支持）
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 数据备份

```bash
# 执行备份脚本（SQLite + ChromaDB + 上传文件）
bash deploy/backup.sh

# 备份文件保存在 ./backups/ 目录
# 默认保留最近7个备份
```

---

## 项目结构

```
equipment-maintenance-system/
├── app/                          # 后端API
│   ├── api/                      # API路由
│   │   ├── auth.py              # 用户认证（Bearer Token + bcrypt）
│   │   ├── chat.py              # AI问答（SSE流式 + 会话管理）
│   │   ├── search.py            # 知识检索（语义/关键词/混合）
│   │   ├── upload.py            # 文件上传（PDF解析 + 向量化）
│   │   ├── guide.py             # 作业指引（SSE流式生成）
│   │   ├── case.py              # 案例管理（审核流程）
│   │   └── admin.py             # 系统管理（配置持久化）
│   ├── core/                     # 核心逻辑
│   │   ├── retriever.py         # 检索引擎（LRUCache）
│   │   ├── rag_engine.py        # RAG引擎（LRUCache）
│   │   ├── guide_generator.py   # 指引生成
│   │   ├── chunker.py           # 文本分块
│   │   └── pdf_parser.py        # PDF解析（并发图片处理）
│   ├── models/                   # 数据模型
│   │   └── database.py          # 数据库操作
│   ├── services/                 # 外部服务
│   │   ├── llm_service.py       # 大模型服务
│   │   └── embedding_service.py # 向量化服务（LRUCache）
│   ├── utils/                    # 工具函数
│   │   ├── helpers.py           # 公共工具（JSON提取等）
│   │   └── init_data.py         # 示例数据自动导入
│   ├── config.py                # 配置管理（环境变量+数据库持久化）
│   └── main.py                  # FastAPI入口（安全中间件）
├── ui/                           # 前端界面
│   ├── app.py                   # Streamlit主应用
│   ├── pages/                   # 页面组件
│   │   ├── 00_登录.py           # 登录注册
│   │   ├── 01_首页.py           # 首页仪表盘
│   │   ├── 02_知识检索.py       # 智能问答
│   │   ├── 03_作业指引.py       # 指引生成
│   │   ├── 04_知识管理.py       # 文档审批
│   │   ├── 05_系统管理.py       # 系统配置
│   │   ├── 06_PDF数据库.py      # PDF管理
│   │   └── 07_知识库.py         # 知识库浏览
│   └── components/              # UI组件
│       ├── common.py            # 公共工具（认证/错误处理）
│       ├── preview.py           # PDF预览
│       └── chat_component.py    # 聊天组件
├── samples/                      # 示例数据
│   └── 摩托车发动机维修手册.pdf  # 内置维修手册
├── deploy/                       # 部署脚本
│   ├── start.sh                 # 启动脚本（健康检查+PID管理）
│   ├── stop.sh                  # 停止脚本（优雅停机）
│   ├── backup.sh                # 备份脚本（验证+保留策略）
│   └── kylin_setup.sh           # 银河麒麟部署
├── tests/                        # 测试
├── .github/workflows/ci.yml     # CI（测试+安全扫描+Docker构建）
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git忽略文件
├── .dockerignore                 # Docker忽略文件
├── Dockerfile                    # Docker镜像（多阶段构建）
├── docker-compose.yml            # Docker编排（安全加固）
├── requirements.txt              # Python依赖
├── requirements-dev.txt          # 开发/测试依赖
└── README.md                     # 项目介绍
```

---

## 开发团队

- **项目**: 第15届中国软件杯竞赛作品
- **技术栈**: FastAPI + Streamlit + 通义千问 + ChromaDB
- **安全**: 全面安全审计与加固

---

## 许可证

[MIT License](./LICENSE)

---

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Web框架
- [Streamlit](https://streamlit.io/) - 数据应用框架
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [通义千问](https://tongyi.aliyun.com/) - 大语言模型
- [中国软件杯](http://www.cnsoftbei.com/) - 竞赛平台

---

<p align="center">
  Made with ❤️ for Industrial Equipment Maintenance
</p>
