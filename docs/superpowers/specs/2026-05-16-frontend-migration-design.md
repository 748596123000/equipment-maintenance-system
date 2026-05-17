# 前端技术栈迁移设计：Streamlit → React + Vite

## 概述

将设备检修知识检索与作业系统的前端从 Streamlit（Python）迁移到 React + Vite + shadcn/ui + Tailwind CSS，实现更专业的工业系统界面、更好的交互体验和长期可维护性。

## 技术栈

| 层次 | 选型 | 版本 |
|------|------|------|
| 构建工具 | Vite | 5.x |
| 框架 | React + TypeScript | 18.x |
| 路由 | React Router | 6.x |
| 状态管理 | Zustand | 4.x |
| UI组件 | shadcn/ui (Radix UI) | latest |
| 样式 | Tailwind CSS | 3.x |
| HTTP | Axios | 1.x |
| PDF预览 | react-pdf (PDF.js) | latest |
| 图表 | Recharts | 2.x |
| 部署 | Nginx 静态托管 | - |

## 项目结构

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── lib/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   └── utils.ts
│   ├── stores/
│   │   ├── auth-store.ts
│   │   └── chat-store.ts
│   ├── hooks/
│   │   ├── use-auth.ts
│   │   └── use-api.ts
│   ├── components/
│   │   ├── ui/          # shadcn/ui
│   │   ├── layout/
│   │   ├── chat/
│   │   ├── document/
│   │   └── guards/
│   └── pages/
│       ├── login.tsx
│       ├── dashboard.tsx
│       ├── search.tsx
│       ├── guide.tsx
│       ├── knowledge.tsx
│       ├── admin.tsx
│       ├── database.tsx
│       └── knowledge-base.tsx
```

## 页面路由映射

| 原页面 | 新页面 | 路由 | 权限 |
|--------|--------|------|------|
| 00_登录 | Login | /login | 公开 |
| 01_首页 | Dashboard | / | 登录 |
| 02_知识检索 | Search | /search | 登录 |
| 03_作业指引 | Guide | /guide | 登录 |
| 04_知识管理 | Knowledge | /knowledge | 登录 |
| 05_系统管理 | Admin | /admin | 管理员 |
| 06_PDF数据库 | Database | /database | 管理员 |
| 07_知识库 | KnowledgeBase | /kb | 登录 |

## 核心设计

### 认证
- Token 存 localStorage + Zustand store
- Axios 拦截器自动附加 Authorization header
- 401 响应自动跳转登录页
- AuthGuard / AdminGuard 路由守卫

### 聊天组件
- Zustand store 管理多会话状态
- 支持流式响应（SSE）
- 引用来源可折叠卡片

### 文档预览
- PDF: react-pdf 渲染，支持翻页/缩放
- 图片: 直接 img 标签展示
- 其他: 显示提取的文本内容

### 多格式上传
- 拖拽 + 点击上传
- 文件类型图标区分
- 上传进度条
- 批量上传

## 后端改动
- FastAPI 添加 CORS 中间件
- 无其他后端改动

## 银河麒麟部署
- Node.js 18+ 预编译包可用
- npm run build 生成纯静态文件
- Nginx try_files 处理 SPA 路由
