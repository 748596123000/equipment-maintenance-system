# 银河麒麟V11-LoongArch 部署指南

本文档详细说明如何在银河麒麟高级服务器版V11（LoongArch架构）上部署设备检修知识检索与作业系统。

## 一、系统环境要求

### 硬件要求
- CPU: 龙芯3A5000/3A6000系列（LoongArch架构）
- 内存: 建议16GB以上（用于LLM模型加载）
- 存储: 建议50GB以上可用空间
- GPU: 可选（龙芯GPU或AMD显卡，用于加速）

### 软件要求
- 操作系统: 银河麒麟高级服务器版V11 (LoongArch)
- Python: 3.10+ (龙芯版本)
- Node.js: 18+ (龙芯版本)

## 二、环境准备

### 1. 安装Python（龙芯版本）

麒麟V11通常已预装Python，检查版本：
```bash
python3 --version
# 需要 Python 3.10 或更高版本
```

如需安装/升级：
```bash
# 使用麒麟软件源
sudo apt update
sudo apt install python3 python3-pip python3-dev

# 或从龙芯官方源安装
# 参考: http://www.loongnix.cn
```

### 2. 安装Node.js（龙芯版本）

```bash
# 检查是否已安装
node --version

# 从龙芯软件源安装
sudo apt install nodejs npm

# 或从龙芯官方下载预编译版本
# 参考: http://www.loongnix.cn/zh/api/nodejs/
```

### 3. 安装系统依赖

```bash
# OCR相关
sudo apt install tesseract-ocr tesseract-ocr-chi-sim

# PDF处理相关
sudo apt install poppler-utils

# 编译工具（部分Python包需要源码编译）
sudo apt install build-essential gcc g++ make

# 其他依赖
sudo apt install libffi-dev libssl-dev libjpeg-dev zlib1g-dev
```

### 4. 配置pip镜像源

由于LoongArch架构部分包需要从源码编译，建议配置国内镜像：

```bash
# 创建pip配置
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
timeout = 120
EOF
```

## 三、项目部署

### 1. 获取项目代码

方式一：从压缩包解压
```bash
# 将ruanjianbei.zip上传到服务器
unzip ruanjianbei.zip -d /opt/
cd /opt/feature-redesign
```

方式二：从Git克隆（如有）
```bash
git clone <项目地址> /opt/feature-redesign
cd /opt/feature-redesign
```

### 2. 运行LoongArch专用安装脚本

```bash
chmod +x install_loongarch.sh
sudo ./install_loongarch.sh
```

### 3. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置
vim .env
```

关键配置项：
```bash
# LoongArch专用配置
CHROMA_DB_IMPL=duckdb+parquet
ANNOY_ENABLED=0

# LLM配置（使用Ollama本地模型）
LLM_BACKEND=ollama
LLM_API_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen2.5:7b

# 或使用云端API（更稳定）
LLM_BACKEND=dashscope
DASHSCOPE_API_KEY=your_api_key_here
LLM_MODEL=qwen-max
```

## 四、安装Ollama（可选）

### 方式一：使用龙芯版Ollama

```bash
# 从龙芯官方下载
# 参考: http://www.loongnix.cn/zh/api/ollama/

# 安装后启动服务
ollama serve &

# 下载模型
ollama pull qwen2.5:7b
```

### 方式二：使用云端LLM API

如果Ollama在LoongArch上不稳定，建议使用云端API：
- 阿里云DashScope（通义千问）
- 智谱AI（GLM）
- DeepSeek

配置示例：
```bash
# .env 配置
LLM_BACKEND=dashscope
DASHSCOPE_API_KEY=sk-xxxxx
LLM_MODEL=qwen-max
```

## 五、启动服务

### 1. 启动后端

```bash
cd /opt/feature-redesign

# 方式一：直接启动
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 方式二：使用systemd服务（推荐生产环境）
sudo cp deploy/loongarch-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable loongarch-backend
sudo systemctl start loongarch-backend
```

### 2. 启动前端

```bash
cd /opt/feature-redesign/frontend

# 开发模式
npm run dev

# 生产模式（构建后使用nginx代理）
npm run build
```

### 3. 配置Nginx（生产环境推荐）

```bash
sudo apt install nginx

# 创建配置
sudo vim /etc/nginx/sites-available/loongarch-app
```

Nginx配置示例：
```nginx
server {
    listen 80;
    server_name localhost;

    # 前端静态文件
    location / {
        root /opt/feature-redesign/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端API代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/loongarch-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 六、LoongArch特殊注意事项

### 1. ChromaDB兼容性

LoongArch架构下，ChromaDB的默认hnswlib索引可能有兼容性问题。解决方案：

```bash
# .env 配置
CHROMA_DB_IMPL=duckdb+parquet  # 使用duckdb后端
ANNOY_ENABLED=0                 # 禁用annoy索引
```

### 2. Python包编译

部分Python包没有LoongArch预编译版本，需要从源码编译：

```bash
# 可能需要源码编译的包
pip install --no-binary :all: chromadb
pip install --no-binary :all: sentence-transformers
```

如果编译失败，可尝试：
```bash
# 安装编译依赖
sudo apt install python3-dev libffi-dev libssl-dev

# 设置编译环境变量
export CFLAGS="-march=loongarch64"
export LDFLAGS="-march=loongarch64"
```

### 3. PyMuPDF兼容性

PyMuPDF在LoongArch上可能有问题，替代方案：

```bash
# 如果pymupdf安装失败，使用pdfplumber替代
pip install pdfplumber pypdf
```

### 4. GPU加速

如果有龙芯GPU或AMD显卡：
```bash
# 安装ROCm（AMD显卡）
# 参考: https://rocm.docs.amd.com/

# PyTorch GPU版本
pip install torch --index-url https://download.pytorch.org/whl/rocm5.7
```

## 七、验证部署

### 1. 检查后端服务

```bash
curl http://localhost:8000/api/health
# 应返回 {"status": "ok", ...}
```

### 2. 检查前端

浏览器访问 http://localhost (或服务器IP)

### 3. 检查LLM服务

```bash
# Ollama
ollama list

# API测试
curl http://localhost:8000/api/admin/llm-status
```

## 八、常见问题

### Q1: pip安装包失败
**原因**: LoongArch架构部分包无预编译版本
**解决**: 
```bash
pip install --no-binary :all: <包名>
# 或寻找龙芯专用版本
```

### Q2: ChromaDB初始化失败
**原因**: hnswlib索引不兼容
**解决**: 配置使用duckdb后端
```bash
CHROMA_DB_IMPL=duckdb+parquet
```

### Q3: Ollama模型加载慢
**原因**: LoongArch CPU性能相对较低
**解决**: 
- 使用更小的模型（如qwen2.5:3b）
- 或使用云端LLM API

### Q4: 前端构建失败
**原因**: Node.js依赖问题
**解决**: 
```bash
# 清除缓存重新安装
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

## 九、性能优化建议

### 1. 内存优化
```bash
# 限制ChromaDB内存使用
export CHROMA_MAX_MEMORY=4GB
```

### 2. 模型选择
- 小内存（<16GB）: 使用云端API或小模型
- 大内存（>=32GB）: 可使用本地7B模型

### 3. 并发配置
```bash
# uvicorn多进程
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 十、技术支持

- 龙芯官方: http://www.loongnix.cn
- 银河麒麟: https://www.kylinos.cn
- 项目问题: 提交Issue或联系开发团队