# 设备检修知识检索与作业系统 Dockerfile
# 适配银河麒麟高级服务器版 V10/V11 + LoongArch架构
#
# 注意：龙芯LoongArch架构不支持Docker Hub官方镜像
# 请使用银河麒麟系统自带Python或龙芯云平台提供的开发环境
#
# 方案一：在银河麒麟系统上直接部署（推荐）
# 方案二：使用龙芯云平台提供的LoongArch容器镜像

# === 方案一：直接部署（推荐） ===
# 在银河麒麟系统上直接运行，无需Docker
# 请参考 deploy/kylin_setup.sh 脚本

# === 方案二：LoongArch容器镜像 ===
# FROM loongarch64/python:3.10
# 如果龙芯云平台提供适配的Python基础镜像，可取消注释使用

# ---- 阶段1: 构建依赖 ----
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

# ---- 阶段2: 运行时 ----
FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CHROMA_DB_IMPL=duckdb+parquet \
    ANNOY_ENABLED=0

# Docker基础镜像为Debian，使用apt包管理器
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libmupdf-dev \
    mupdf-tools \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .

RUN mkdir -p /app/data/pdfs /app/data/images /app/data/chroma_db /app/data/logs

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health && curl -f http://localhost:8501/_stcore/health || exit 1

COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
