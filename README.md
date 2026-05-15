# 设备检修知识检索与作业系统

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115.0-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Streamlit-1.40.0-FF4B4B?style=flat-square&logo=streamlit" alt="Streamlit">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/ChromaDB-0.5.0-FF6B6B?style=flat-square" alt="ChromaDB">
  <img src="https://img.shields.io/badge/Security-8.8%2F10-brightgreen?style=flat-square" alt="Security">
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

### 核心能力

- 🔍 **多模态知识检索** — 支持文本语义检索、关键词检索、图片相似度检索
- 🤖 **AI智能问答** — 基于大模型的检修知识问答，支持上下文记忆
- 📋 **作业指引生成** — 自动生成标准化检修作业指导书
- 📚 **案例管理** — 检修案例的创建、审核、检索与复用
- 📄 **文档管理** — PDF文档上传、解析、向量化存储
- 👥 **用户权限管理** — 管理员审批制用户注册，细粒度权限控制

---

## 功能特性

### 1. 知识检索模块

| 功能 | 描述 |
|------|------|
| 语义检索 | 基于向量相似度的语义理解检索 |
| 关键词检索 | 传统TF-IDF关键词匹配 |
| 混合检索 | 语义+关键词融合排序 |
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

- 📝 检修案例创建与编辑
- ✔️ 管理员审核流程
- 🔍 案例检索与推荐
- 📊 案例统计分析

### 5. 文档管理模块

- 📤 PDF批量上传
- 🔍 PDF内容解析与向量化
- 👁️ PDF在线预览
- ✅ 文档审批流程

---

## 技术架构

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Streamlit)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 登录页面  │ │ 知识检索  │ │ 作业指引  │ │ 案例管理  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/HTTP
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

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | Streamlit | 1.40.0 |
| 后端 | FastAPI | 0.115.0 |
| 服务器 | Uvicorn | 0.32.0 |
| 数据库 | SQLite | - |
| 向量库 | ChromaDB | 0.5.0 |
| 大模型 | 通义千问 (DashScope) | qwen-max |
| 向量化 | 通义千问 Embedding | text-embedding-v3 |
| 密码哈希 | bcrypt (passlib) | 1.7.4 |
| 容器化 | Docker + Docker Compose | - |

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

5. **启动后端服务**

```bash
python -m app.main
# 或使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6. **启动前端界面**

```bash
streamlit run ui/app.py
```

7. **访问系统**

- 前端界面：http://localhost:8501
- API文档：http://localhost:8000/docs (DEBUG=True时)

---

## 安全特性

本项目经过全面安全审计，修复了41个安全问题，安全评分达到 **8.8/10**。

### 认证与授权

- ✅ **Bearer Token 认证** — HTTPBearer + 24小时过期
- ✅ **bcrypt 密码哈希** — 自动升级旧版SHA256哈希
- ✅ **路由级认证依赖** — 所有API端点默认需要认证
- ✅ **对象级授权** — 资源所有权校验，防止越权访问
- ✅ **管理员审批制** — 用户注册需管理员审批

### 防护机制

- ✅ **速率限制** — 登录5次/5分钟，API 60次/分钟
- ✅ **XSS防护** — html.escape() 转义所有动态内容
- ✅ **SQL注入防护** — 参数化查询 + 列名白名单
- ✅ **路径遍历防护** — basename + realpath 校验
- ✅ **文件上传安全** — 类型/大小/魔数三重校验

### 安全响应头

- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Content-Security-Policy
- Strict-Transport-Security
- Permissions-Policy

### 配置安全

- 生产环境强制 DEBUG=False
- 依赖版本精确锁定
- 敏感文件排除在版本控制外
- Docker非root用户运行

详细安全报告：[security_best_practices_report.md](./security_best_practices_report.md)

---

## 部署指南

### Docker 部署

1. **构建镜像**

```bash
docker-compose build
```

2. **启动服务**

```bash
docker-compose up -d
```

3. **查看日志**

```bash
docker-compose logs -f
```

### 生产环境部署

1. **配置环境变量**

```env
ENVIRONMENT=production
DEBUG=False
ALLOWED_HOSTS=["your-domain.com"]
CORS_ORIGINS=["https://your-frontend.com"]
```

2. **配置 Nginx 反向代理**

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **麒麟/龙芯架构部署**

```bash
# 使用提供的部署脚本
bash deploy/kylin_setup.sh
```

---

## 项目结构

```
equipment-maintenance-system/
├── app/                          # 后端API
│   ├── api/                      # API路由
│   │   ├── auth.py              # 用户认证
│   │   ├── chat.py              # AI问答
│   │   ├── search.py            # 知识检索
│   │   ├── upload.py            # 文件上传
│   │   ├── guide.py             # 作业指引
│   │   ├── case.py              # 案例管理
│   │   └── admin.py             # 系统管理
│   ├── core/                     # 核心逻辑
│   │   ├── retriever.py         # 检索引擎
│   │   ├── rag_engine.py        # RAG引擎
│   │   ├── guide_generator.py   # 指引生成
│   │   └── pdf_parser.py        # PDF解析
│   ├── models/                   # 数据模型
│   │   └── database.py          # 数据库操作
│   ├── services/                 # 外部服务
│   │   ├── llm_service.py       # 大模型服务
│   │   └── embedding_service.py # 向量化服务
│   ├── utils/                    # 工具函数
│   ├── config.py                # 配置管理
│   └── main.py                  # FastAPI入口
├── ui/                           # 前端界面
│   ├── app.py                   # Streamlit主应用
│   ├── pages/                   # 页面组件
│   └── components/              # UI组件
├── deploy/                       # 部署脚本
├── data/                         # 数据目录
├── docs/                         # 文档
├── tests/                        # 测试
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git忽略文件
├── Dockerfile                    # Docker镜像
├── docker-compose.yml            # Docker编排
├── requirements.txt              # Python依赖
├── security_best_practices_report.md  # 安全报告
└── README.md                     # 项目介绍
```

---

## 开发团队

- **项目**: 第15届中国软件杯竞赛作品
- **技术栈**: FastAPI + Streamlit + 通义千问
- **安全评分**: 8.8/10

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
