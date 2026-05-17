# 设备检修知识检索与作业系统 Dockerfile
# 适配银河麒麟高级服务器版 V10/V11 + LoongArch架构
#
# 多阶段构建：
# 1. frontend-builder: Node.js 构建 React 前端
# 2. builder: Python 编译依赖
# 3. runtime: 最终运行时镜像

# ---- 阶段1: 构建前端 ----
FROM node:20-slim AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- 阶段2: 构建Python依赖 ----
FROM python:3.10-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmupdf-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt \
    || pip install --no-cache-dir --prefix=/install -r requirements.txt --use-pep517

# ---- 阶段3: 运行时 ----
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CHROMA_DB_IMPL=duckdb+parquet \
    ANNOY_ENABLED=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nginx \
    libmupdf-dev \
    mupdf-tools \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .

COPY --from=frontend-builder /build/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

RUN mkdir -p /app/data/pdfs /app/data/images /app/data/chroma_db /app/data/logs \
    && rm -f /etc/nginx/sites-enabled/default

RUN useradd -m appuser \
    && chown -R appuser:appuser /app \
    && chown -R appuser:appuser /usr/share/nginx/html

EXPOSE 80 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health && curl -f http://localhost:80/ || exit 1

COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
