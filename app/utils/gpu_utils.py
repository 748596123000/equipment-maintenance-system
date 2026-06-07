import logging
import subprocess
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_gpu_info_cache: Optional[Dict] = None
_gpu_cache_time: float = 0
_GPU_CACHE_TTL: float = 30.0


def _detect_nvidia_smi() -> Dict:
    result = {
        "nvidia_driver_available": False,
        "driver_version": None,
        "cuda_driver_version": None,
        "gpu_names": [],
        "gpu_count": 0,
    }
    try:
        output = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if output.returncode == 0 and output.stdout.strip():
            lines = [l.strip() for l in output.stdout.strip().split("\n") if l.strip()]
            result["gpu_count"] = len(lines)
            result["nvidia_driver_available"] = True
            for line in lines:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    result["gpu_names"].append(parts[0])
                    result["driver_version"] = parts[1]

        ver_output = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, timeout=10,
        )
        if ver_output.returncode == 0:
            for line in ver_output.stdout.split("\n"):
                if "CUDA Version" in line:
                    import re
                    m = re.search(r"CUDA Version:\s*([\d.]+)", line)
                    if m:
                        result["cuda_driver_version"] = m.group(1)
                    break
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass
    except Exception as e:
        logger.debug(f"nvidia-smi 检测失败: {e}")

    return result


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
        "nvidia_driver_available": False,
        "diagnostics": {},
    }

    nvidia_smi = _detect_nvidia_smi()
    info["nvidia_driver_available"] = nvidia_smi["nvidia_driver_available"]
    info["diagnostics"]["nvidia_driver_version"] = nvidia_smi["driver_version"]
    info["diagnostics"]["cuda_driver_version"] = nvidia_smi["cuda_driver_version"]
    info["diagnostics"]["nvidia_gpu_names"] = nvidia_smi["gpu_names"]

    try:
        import torch
        info["torch_available"] = True
        info["diagnostics"]["torch_version"] = torch.__version__
        info["diagnostics"]["torch_cuda_version"] = getattr(torch.version, "cuda", None)
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
        else:
            if nvidia_smi["nvidia_driver_available"]:
                info["diagnostics"]["torch_gpu_reason"] = (
                    f"PyTorch {torch.__version__} 未启用 CUDA 支持（当前为 CPU 版本），"
                    f"请安装 CUDA 版 PyTorch: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128"
                )
            else:
                info["diagnostics"]["torch_gpu_reason"] = "未检测到 NVIDIA GPU 驱动"
    except ImportError:
        info["torch_available"] = False
        info["diagnostics"]["torch_gpu_reason"] = "PyTorch 未安装"
    except Exception as e:
        logger.debug(f"torch GPU 检测失败: {e}")
        info["diagnostics"]["torch_gpu_reason"] = f"torch 检测异常: {e}"

    try:
        import paddle
        info["paddle_available"] = True
        info["diagnostics"]["paddle_version"] = paddle.__version__
        if paddle.is_compiled_with_cuda():
            info["paddle_gpu"] = True
            if not info["cuda_available"]:
                info["cuda_available"] = True
                try:
                    gpu_count = paddle.device.cuda.device_count()
                    info["device_count"] = max(info["device_count"], gpu_count)
                except Exception:
                    pass
        else:
            if nvidia_smi["nvidia_driver_available"]:
                info["diagnostics"]["paddle_gpu_reason"] = (
                    f"PaddlePaddle {paddle.__version__} 未编译 CUDA 支持，"
                    f"请安装 GPU 版本: pip install paddlepaddle-gpu"
                )
    except ImportError:
        info["paddle_available"] = False
        info["diagnostics"]["paddle_gpu_reason"] = "PaddlePaddle 未安装"
    except Exception as e:
        logger.debug(f"paddle GPU 检测失败: {e}")
        info["diagnostics"]["paddle_gpu_reason"] = f"paddle 检测异常: {e}"

    if not info["cuda_available"] and nvidia_smi["nvidia_driver_available"]:
        if not info["devices"]:
            for i, name in enumerate(nvidia_smi["gpu_names"]):
                info["devices"].append({
                    "index": i,
                    "name": name,
                    "total_vram_mb": 0,
                    "used_vram_mb": 0,
                    "free_vram_mb": 0,
                    "compute_capability": "N/A",
                })
            info["device_count"] = nvidia_smi["gpu_count"]

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
