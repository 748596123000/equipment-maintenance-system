# 项目依赖清单

本项目需要以下依赖环境，请按顺序安装。

## 1. 系统环境要求

- **Python**: 3.10+ (推荐 3.11 或 3.12)
- **Node.js**: 18+ (推荐 20+)
- **Ollama**: 用于本地LLM推理（可选，也可使用云端API）
- **Tesseract OCR**: 用于图片文字识别

## 2. Python 后端依赖

### 核心依赖 (requirements.txt)
```
fastapi
uvicorn[standard]
chromadb
pydantic
pydantic-settings
bcrypt
python-jose[cryptography]
python-multipart
pillow
pymupdf
pdfplumber
dashscope
openai
sqlalchemy
langchain
langchain-community
pytesseract
pdf2image
python-docx
openpyxl
python-pptx
beautifulsoup4
jieba
httpx
python-dotenv
itsdangerous
aiohttp
jinja2
cachetools
tqdm
gradio-client
tenacity
```

### GPU 加速依赖 (可选，用于本地视觉模型)
```
torch
transformers
accelerate
```

### Embedding 模型依赖
```
sentence-transformers
```

## 3. Node.js 前端依赖

### 生产依赖
```
axios@^1.16.1
class-variance-authority@^0.7.1
clsx@^2.1.1
dompurify@^3.4.5
lucide-react@^1.16.0
react@^18.3.1
react-dom@^18.3.1
react-pdf@^10.4.1
react-router-dom@^7.15.1
recharts@^3.8.1
tailwind-merge@^3.6.0
zustand@^5.0.13
```

### 开发依赖
```
@eslint/js@^10.0.1
@radix-ui/react-alert-dialog@^1.1.15
@radix-ui/react-avatar@^1.1.11
@radix-ui/react-checkbox@^1.3.3
@radix-ui/react-collapsible@^1.1.12
@radix-ui/react-dialog@^1.1.15
@radix-ui/react-dropdown-menu@^2.1.16
@radix-ui/react-label@^2.1.8
@radix-ui/react-popover@^1.1.15
@radix-ui/react-progress@^1.1.8
@radix-ui/react-scroll-area@^1.2.10
@radix-ui/react-select@^2.2.6
@radix-ui/react-separator@^1.1.8
@radix-ui/react-slot@^1.2.4
@radix-ui/react-switch@^1.2.6
@radix-ui/react-tabs@^1.1.13
@radix-ui/react-tooltip@^1.2.8
@tailwindcss/vite@^4.3.0
@testing-library/jest-dom@^6.4.0
@testing-library/react@^16.0.0
@types/dompurify@^3.0.5
@types/node@^24.12.3
@types/react@^19.2.14
@types/react-dom@^19.2.3
@vitejs/plugin-react@^6.0.1
eslint@^10.3.0
eslint-plugin-react-hooks@^7.1.1
eslint-plugin-react-refresh@^0.5.2
globals@^17.6.0
jsdom@^24.0.0
tailwindcss@^4.3.0
typescript@~6.0.2
typescript-eslint@^8.59.2
vite@^8.0.12
vitest@^2.0.0
```

## 4. 外部服务

### Ollama (本地LLM)
- 安装: https://ollama.ai/download
- 推荐模型: `qwen3.5:9b` 或 `qwen2.5:7b`
- 安装命令: `ollama pull qwen3.5:9b`

### Tesseract OCR
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- 安装后添加到系统PATH

## 5. 安装命令

### 自动安装 (推荐)
```bash
# Windows
python install_deps.py

# Linux/Mac
python3 install_deps.py
```

### 手动安装
```bash
# Python后端
pip install -r requirements.txt
pip install torch transformers accelerate sentence-transformers

# Node.js前端
cd frontend
npm install
```