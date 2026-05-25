import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_gpu_info_cache: Optional[Dict] = None
_gpu_cache_time: float = 0
_GPU_CACHE_TTL: float = 30.0


def detect_gpu() -> Dict:
    global _gpu_info_cache, _gpu_cache_time
    now = time.time()
    if _gpu_info_cache is not None and (now - _gpu_cache_time) < _GPU_CACHE_TTL:
        return _gpu_info_cache

    info = {
        "available": False,
        "cuda_available": False,
        "device_count": 0,
        "devices": [],
        "paddle_gpu": False,
        "torch_gpu": False,
    }

    try:
        import torch
        info["torch_available"] = True
        if torch.cuda.is_available():
            info["torch_gpu"] = True
            info["cuda_available"] = True
            info["device_count"] = torch.cuda.device_count()
            for i in range(info["device_count"]):
                props = torch.cuda.get_device_properties(i)
                mem_alloc = torch.cuda.memory_allocated(i)
                mem_total = props.total_memory
                info["devices"].append({
                    "index": i,
                    "name": props.name,
                    "total_vram_mb": round(mem_total / 1024 / 1024),
                    "used_vram_mb": round(mem_alloc / 1024 / 1024),
                    "free_vram_mb": round((mem_total - mem_alloc) / 1024 / 1024),
                    "compute_capability": f"{props.major}.{props.minor}",
                })
    except ImportError:
        info["torch_available"] = False
    except Exception as e:
        logger.debug(f"torch GPU 检测失败: {e}")

    try:
        import paddle
        info["paddle_available"] = True
        if paddle.is_compiled_with_cuda():
            info["paddle_gpu"] = True
            if not info["cuda_available"]:
                info["cuda_available"] = True
                try:
                    gpu_count = paddle.device.cuda.device_count()
                    info["device_count"] = max(info["device_count"], gpu_count)
                except Exception:
                    pass
    except ImportError:
        info["paddle_available"] = False
    except Exception as e:
        logger.debug(f"paddle GPU 检测失败: {e}")

    info["available"] = info["cuda_available"]
    _gpu_info_cache = info
    _gpu_cache_time = time.time()
    return info


def get_device() -> str:
    info = detect_gpu()
    if info["available"]:
        return "cuda"
    return "cpu"


def get_gpu_info() -> Dict:
    return detect_gpu()


def clear_gpu_cache():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
    try:
        import paddle
        paddle.device.cuda.empty_cache()
    except (ImportError, Exception):
        pass
