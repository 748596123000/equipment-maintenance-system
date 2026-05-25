# GPU调度加速实施计划

## 当前状态

### 已完成（步骤1-4）
- ✅ `app/utils/gpu_utils.py` — GPU检测工具（detect_gpu, get_device, clear_gpu_cache）
- ✅ `app/services/ocr_service.py` — PaddleOCR服务（支持GPU/CPU自动切换）
- ✅ `app/services/vision_service.py` — 本地视觉模型服务（Qwen2-VL + DashScope降级链）
- ✅ `app/config.py` — 新增OCR和视觉模型配置字段
- ✅ `app/core/document_parser.py` — 集成OCR + VisionService
- ✅ `app/core/pdf_parser.py` — 集成VisionService
- ✅ `app/api/admin.py` — ConfigUpdateRequest和config端点已更新

### 待完成
- ❌ 步骤5：添加 `GET /admin/gpu-status` API端点
- ❌ 步骤6：更新前端 API 管理页面（OCR/视觉/GPU状态卡片）
- ❌ 步骤7：创建GPU依赖文件和部署配置
- ❌ 步骤8：测试验证

---

## 步骤5：添加后端 GPU 状态 API

### 5.1 在 `app/api/admin.py` 添加 `GET /admin/gpu-status` 端点

在 `health_check` 端点之后添加新端点，返回：

```python
@router.get("/gpu-status", summary="获取GPU状态")
async def get_gpu_status():
```

返回数据结构：
```json
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "gpu": {
      "available": true,
      "cuda_available": true,
      "device_count": 1,
      "devices": [
        {
          "index": 0,
          "name": "NVIDIA GeForce RTX 4090",
          "total_vram_mb": 24576,
          "used_vram_mb": 1024,
          "free_vram_mb": 23552,
          "compute_capability": "8.9"
        }
      ],
      "torch_gpu": true,
      "paddle_gpu": true
    },
    "ocr": {
      "backend": "auto",
      "use_gpu": true,
      "language": "ch",
      "available": true,
      "engine_loaded": true
    },
    "vision": {
      "backend": "dashscope",
      "local_model": "Qwen/Qwen2-VL-2B-Instruct",
      "local_available": false,
      "current_backend": "dashscope"
    }
  }
}
```

实现逻辑：
1. 调用 `gpu_utils.get_gpu_info()` 获取GPU信息（强制刷新缓存）
2. 调用 `ocr_service.get_ocr_service()` 获取OCR状态
3. 调用 `vision_service.get_vision_service()` 获取视觉模型状态
4. 组装返回数据

### 5.2 添加 `POST /admin/gpu-cache/clear` 端点（可选）

用于手动清理GPU缓存：
```python
@router.post("/gpu-cache/clear", summary="清理GPU缓存")
async def clear_gpu_cache():
```

---

## 步骤6：更新前端 API 管理页面

### 6.1 更新 `SystemConfig` 接口

在 `frontend/src/pages/api-settings.tsx` 中扩展：

```typescript
interface SystemConfig {
  // ... 现有字段
  ocr_backend: string
  ocr_use_gpu: boolean
  ocr_language: string
  vision_backend: string
  local_vision_model: string
}
```

### 6.2 新增 GPU 状态接口

```typescript
interface GpuStatus {
  gpu: {
    available: boolean
    cuda_available: boolean
    device_count: number
    devices: Array<{
      index: number
      name: string
      total_vram_mb: number
      used_vram_mb: number
      free_vram_mb: number
      compute_capability: string
    }>
    torch_gpu: boolean
    paddle_gpu: boolean
  }
  ocr: {
    backend: string
    use_gpu: boolean
    language: string
    available: boolean
    engine_loaded: boolean
  }
  vision: {
    backend: string
    local_model: string
    local_available: boolean
    current_backend: string
  }
}
```

### 6.3 新增 GPU 状态卡片

在现有卡片之后添加两个新卡片：

**卡片1：GPU 状态监控**
- 显示GPU可用性（Badge：可用/不可用）
- GPU设备列表（名称、VRAM使用情况进度条）
- CUDA状态、torch/paddle GPU支持状态
- 刷新按钮 + 清理缓存按钮
- 无GPU时显示提示信息

**卡片2：OCR / 视觉模型配置**
- OCR后端选择（auto / paddleocr / none）
- OCR使用GPU开关
- OCR语言选择（ch / en / ch_en）
- 视觉模型后端选择（dashscope / local / auto）
- 本地视觉模型名称输入
- 当前OCR/视觉模型状态指示

### 6.4 添加 GPU 状态自动刷新

使用 `useEffect` + `setInterval` 每30秒自动刷新GPU状态。

---

## 步骤7：更新依赖和部署配置

### 7.1 创建 `requirements-gpu.txt`

在项目根目录创建GPU加速专用依赖文件：

```
# GPU加速依赖（需CUDA环境）
# PaddleOCR + PaddlePaddle GPU
paddlepaddle-gpu>=2.6.0
paddleocr>=2.8.0

# 本地视觉模型
torch>=2.1.0
transformers>=4.40.0
qwen-vl-utils>=0.0.1
accelerate>=0.27.0
```

### 7.2 更新 `Dockerfile`

在现有Dockerfile基础上，添加GPU构建阶段的条件逻辑：
- 新增 `Dockerfile.gpu` 文件，基于NVIDIA CUDA镜像
- 安装CUDA toolkit和GPU依赖

### 7.3 创建 `docker-compose.gpu.yml`

基于现有 `docker-compose.yml`，添加GPU支持：
- 使用NVIDIA runtime
- 添加GPU设备映射
- 增加内存限制（GPU模型需要更多内存）
- 添加GPU相关环境变量

---

## 步骤8：测试验证

### 8.1 后端API测试
- 启动后端服务
- 测试 `GET /admin/gpu-status` 返回正确数据
- 测试 `PUT /admin/config` 更新OCR/视觉配置
- 测试文档上传时OCR和视觉模型是否正确调用

### 8.2 前端页面测试
- 打开API管理页面
- 验证GPU状态卡片正确显示
- 验证OCR/视觉配置可修改并保存
- 验证GPU缓存清理功能

### 8.3 降级链测试
- 无GPU环境：验证自动降级到CPU/API模式
- 有GPU环境：验证GPU加速正常工作

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/api/admin.py` | 修改 | 添加 gpu-status 和 gpu-cache/clear 端点 |
| `frontend/src/pages/api-settings.tsx` | 修改 | 添加GPU状态卡片和OCR/视觉配置 |
| `requirements-gpu.txt` | 新建 | GPU加速专用依赖 |
| `Dockerfile.gpu` | 新建 | GPU版Docker构建文件 |
| `docker-compose.gpu.yml` | 新建 | GPU版Docker编排文件 |
