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

FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # ChromaDB在LoongArch上需要使用纯Python的hnswlib替代方案
    CHROMA_DB_IMPL=duckdb+parquet \
    ANNOY_ENABLED=0

# 安装系统依赖
# 银河麒麟基于Debian，使用apt包管理器
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    # PDF解析所需的系统库
    libmupdf-dev \
    mupdf-tools \
    # 图片处理库
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装Python依赖
COPY requirements.txt .
# LoongArch架构下部分包需要源码编译，增加编译超时时间
RUN pip install --no-cache-dir -r requirements.txt \
    || pip install --no-cache-dir -r requirements.txt --use-pep517

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data/pdfs /app/data/images /app/data/chroma_db /app/data/logs

# 创建非root用户
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8501 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令：使用shell脚本管理多进程
COPY deploy/start.sh /app/start.sh
RUN chmod +x /app/start.sh
CMD ["/app/start.sh"]
