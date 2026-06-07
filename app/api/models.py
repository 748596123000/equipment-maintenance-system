import logging
import os
import platform
import shutil
import subprocess
import threading
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import require_admin
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 检测 LoongArch 架构
_ARCH = platform.machine().lower()
_IS_LOONGARCH = "loongarch" in _ARCH or "loong64" in _ARCH

# GGUF 模型保存目录
_GGUF_MODEL_DIR = os.path.expanduser("~/models")

# ── 标准架构（x86/ARM）模型列表 ──
AVAILABLE_MODELS_X86 = [
    {
        "id": "Qwen/Qwen2-VL-2B-Instruct",
        "name": "Qwen2-VL-2B",
        "type": "vision",
        "size": "4GB",
        "description": "通义千问视觉语言模型2B版，适合图片描述和OCR辅助",
        "recommended": True,
    },
    {
        "id": "Qwen/Qwen2-VL-7B-Instruct",
        "name": "Qwen2-VL-7B",
        "type": "vision",
        "size": "15GB",
        "description": "通义千问视觉语言模型7B版，精度更高，需更多显存",
        "recommended": False,
    },
    {
        "id": "openbmb/MiniCPM-V-2_6",
        "name": "MiniCPM-V-2.6",
        "type": "vision",
        "size": "8GB",
        "description": "面壁智能多模态大模型，中文OCR能力优秀",
        "recommended": False,
    },
    {
        "id": "PaddleOCR/PPOCRv4",
        "name": "PPOCRv4",
        "type": "ocr",
        "size": "150MB",
        "description": "PaddleOCR v4模型，安装PaddleOCR时自动下载",
        "recommended": True,
    },
]

# ── LoongArch 架构模型列表（GGUF 格式，llama.cpp 可用） ──
AVAILABLE_MODELS_LOONGARCH = [
    {
        "id": "gguf/Qwen2.5-7B-Instruct-Q4_K_M",
        "name": "Qwen2.5-7B-Instruct (GGUF)",
        "type": "llm",
        "size": "4.7GB",
        "description": "通义千问文本大模型 GGUF 量化版，llama-server 本地推理，LoongArch 推荐",
        "recommended": True,
        "gguf_url": "https://modelscope.cn/models/qwen/Qwen2.5-7B-Instruct-GGUF/resolve/master/qwen2.5-7b-instruct-q4_k_m.gguf",
        "gguf_file": "qwen2.5-7b-instruct-q4_k_m.gguf",
    },
    {
        "id": "gguf/Qwen2.5-3B-Instruct-Q4_K_M",
        "name": "Qwen2.5-3B-Instruct (GGUF)",
        "type": "llm",
        "size": "2.0GB",
        "description": "通义千问文本大模型3B GGUF 量化版，内存占用小，适合低配机器",
        "recommended": False,
        "gguf_url": "https://modelscope.cn/models/qwen/Qwen2.5-3B-Instruct-GGUF/resolve/master/qwen2.5-3b-instruct-q4_k_m.gguf",
        "gguf_file": "qwen2.5-3b-instruct-q4_k_m.gguf",
    },
    {
        "id": "gguf/Qwen2.5-14B-Instruct-Q4_K_M",
        "name": "Qwen2.5-14B-Instruct (GGUF)",
        "type": "llm",
        "size": "8.7GB",
        "description": "通义千问文本大模型14B GGUF 量化版，精度更高，需较大内存",
        "recommended": False,
        "gguf_url": "https://modelscope.cn/models/qwen/Qwen2.5-14B-Instruct-GGUF/resolve/master/qwen2.5-14b-instruct-q4_k_m.gguf",
        "gguf_file": "qwen2.5-14b-instruct-q4_k_m.gguf",
    },
    {
        "id": "gguf/Qwen2-VL-2B-Instruct-Q4_K_M",
        "name": "Qwen2-VL-2B (GGUF视觉)",
        "type": "vision",
        "size": "1.8GB",
        "description": "通义千问视觉语言模型2B GGUF量化版，llama.cpp多模态推理，LoongArch可用",
        "recommended": True,
        "gguf_url": "https://modelscope.cn/models/Qwen/Qwen2-VL-2B-Instruct-GGUF/resolve/master/qwen2-vl-2b-instruct-q4_k_m.gguf",
        "gguf_file": "qwen2-vl-2b-instruct-q4_k_m.gguf",
    },
    {
        "id": "gguf/Qwen2-VL-7B-Instruct-Q4_K_M",
        "name": "Qwen2-VL-7B (GGUF视觉)",
        "type": "vision",
        "size": "5.2GB",
        "description": "通义千问视觉语言模型7B GGUF量化版，精度更高，需较大内存",
        "recommended": False,
        "gguf_url": "https://modelscope.cn/models/Qwen/Qwen2-VL-7B-Instruct-GGUF/resolve/master/qwen2-vl-7b-instruct-q4_k_m.gguf",
        "gguf_file": "qwen2-vl-7b-instruct-q4_k_m.gguf",
    },
    {
        "id": "gguf/MiniCPM-V-2_6-Q4_K_M",
        "name": "MiniCPM-V-2.6 (GGUF视觉)",
        "type": "vision",
        "size": "5.0GB",
        "description": "面壁智能多模态大模型GGUF量化版，中文OCR能力优秀",
        "recommended": False,
        "gguf_url": "https://modelscope.cn/models/OpenBMB/MiniCPM-V-2_6-gguf/resolve/master/minicpmv-2_6-q4_k_m.gguf",
        "gguf_file": "minicpmv-2_6-q4_k_m.gguf",
    },
    {
        "id": "PaddleOCR/PPOCRv4",
        "name": "PPOCRv4",
        "type": "ocr",
        "size": "150MB",
        "description": "PaddleOCR v4模型（LoongArch不兼容，推荐使用RapidOCR或DashScope API）",
        "recommended": False,
    },
]

# 根据架构选择模型列表
AVAILABLE_MODELS = AVAILABLE_MODELS_LOONGARCH if _IS_LOONGARCH else AVAILABLE_MODELS_X86

_download_tasks: Dict[str, Dict] = {}


def _download_gguf_python(url: str, dest_path: str, task: Dict, model_id: str):
    """使用 Python urllib 下载 GGUF 文件（无 wget/curl 时的回退方案）"""
    import urllib.request
    import tempfile

    tmp_path = dest_path + ".tmp"
    try:
        urllib.request.urlretrieve(url, tmp_path)
        os.rename(tmp_path, dest_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _get_mirror_endpoint() -> str:
    return os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")


def _get_model_cache_dir() -> str:
    cache_dir = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    return cache_dir


def _check_vision_dependencies() -> list:
    missing = []
    try:
        import transformers
    except ImportError:
        missing.append("transformers")
    try:
        import torch
    except ImportError:
        missing.append("torch")
    try:
        import qwen_vl_utils
    except ImportError:
        missing.append("qwen-vl-utils")
    try:
        import accelerate
    except ImportError:
        missing.append("accelerate")
    return missing


def _is_package_installed(package: str) -> bool:
    import_name = package.replace("-", "_")
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False


def _get_model_dependencies(model_id: str) -> list:
    if model_id == "PaddleOCR/PPOCRv4":
        return ["paddleocr", "paddlepaddle"]
    # GGUF 模型不需要 Python 依赖，llama-server 是系统级二进制
    if model_id.startswith("gguf/"):
        return []
    model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
    if model_info and model_info.get("type") == "vision":
        return ["transformers", "torch", "qwen-vl-utils", "accelerate"]
    return []


def _install_dependencies(packages: list) -> bool:
    import subprocess
    import sys
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + packages,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            logger.info(f"依赖安装成功: {packages}")
            return True
        else:
            logger.error(f"依赖安装失败: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"依赖安装异常: {e}")
        return False


def _check_model_downloaded(model_id: str) -> bool:
    try:
        # GGUF 模型：检查文件是否存在
        if model_id.startswith("gguf/"):
            model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
            if model_info and model_info.get("gguf_file"):
                gguf_path = os.path.join(_GGUF_MODEL_DIR, model_info["gguf_file"])
                return os.path.exists(gguf_path)
            return False

        if model_id == "PaddleOCR/PPOCRv4":
            try:
                import paddleocr
                return True
            except ImportError:
                return False

        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        for repo in cache.repos:
            if repo.repo_id == model_id:
                return True
        return False
    except Exception:
        model_dir = os.path.join(_get_model_cache_dir(), "hub", f"models--{model_id.replace('/', '--')}")
        return os.path.exists(model_dir)


def _monitor_download_progress(model_id: str, total_size: int, stop_event: threading.Event):
    cache_dir = _get_model_cache_dir()
    model_dir = os.path.join(cache_dir, "hub", f"models--{model_id.replace('/', '--')}")

    while not stop_event.is_set():
        try:
            if os.path.exists(model_dir):
                downloaded_size = 0
                for root, _dirs, files in os.walk(model_dir):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            downloaded_size += os.path.getsize(fp)
                        except OSError:
                            pass

                if model_id in _download_tasks and total_size > 0:
                    progress = min(99, int((downloaded_size / total_size) * 100))
                    _download_tasks[model_id]["progress"] = progress
        except Exception:
            pass

        stop_event.wait(2)


def _download_model_thread(model_id: str):
    task = _download_tasks.get(model_id)
    if not task:
        return

    stop_monitor = threading.Event()

    try:
        task["status"] = "downloading"
        task["progress"] = 0

        # ── GGUF 模型下载（LoongArch） ──
        if model_id.startswith("gguf/"):
            model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
            if not model_info or not model_info.get("gguf_url"):
                raise ValueError(f"GGUF 模型信息缺失: {model_id}")

            gguf_url = model_info["gguf_url"]
            gguf_file = model_info["gguf_file"]
            os.makedirs(_GGUF_MODEL_DIR, exist_ok=True)
            dest_path = os.path.join(_GGUF_MODEL_DIR, gguf_file)

            logger.info(f"开始下载 GGUF 模型: {gguf_url} -> {dest_path}")

            # 使用 wget 或 curl 下载（支持断点续传）
            try:
                if shutil.which("wget"):
                    cmd = ["wget", "-c", "-O", dest_path, gguf_url]
                elif shutil.which("curl"):
                    cmd = ["curl", "-L", "-C", "-", "-o", dest_path, gguf_url]
                else:
                    # 回退到 Python urllib
                    _download_gguf_python(gguf_url, dest_path, task, model_id)
                    task["status"] = "completed"
                    task["progress"] = 100
                    task["path"] = dest_path
                    logger.info(f"GGUF 模型下载完成: {dest_path}")
                    return

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                # 简单等待完成
                for line in proc.stdout:
                    logger.debug(f"download: {line.strip()}")
                proc.wait()

                if proc.returncode != 0:
                    raise RuntimeError(f"下载命令返回非零: {proc.returncode}")

                if not os.path.exists(dest_path) or os.path.getsize(dest_path) < 1024:
                    raise RuntimeError("下载文件不存在或过小")

                task["status"] = "completed"
                task["progress"] = 100
                task["path"] = dest_path
                logger.info(f"GGUF 模型下载完成: {dest_path}")
            except Exception as e:
                raise RuntimeError(f"GGUF 下载失败: {e}")
            return

        # ── PaddleOCR 下载 ──
        if model_id == "PaddleOCR/PPOCRv4":
            import paddleocr
            ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            del ocr
            task["status"] = "completed"
            task["progress"] = 100
            return

        # ── 标准 HuggingFace 下载 ──
        from huggingface_hub import HfApi, snapshot_download

        endpoint = _get_mirror_endpoint()

        total_size = 0
        try:
            old_offline = os.environ.pop("HF_HUB_OFFLINE", None)
            try:
                hf_api = HfApi(endpoint=endpoint)
                repo_info = hf_api.model_info(model_id)
                for f in (repo_info.siblings or []):
                    total_size += getattr(f, 'size', 0) or 0
            finally:
                if old_offline is not None:
                    os.environ["HF_HUB_OFFLINE"] = old_offline
                else:
                    os.environ["HF_HUB_OFFLINE"] = "1"
        except Exception as e:
            logger.warning(f"获取模型信息失败，将无法显示精确下载进度: {e}")

        if total_size > 0:
            monitor = threading.Thread(
                target=_monitor_download_progress,
                args=(model_id, total_size, stop_monitor),
                daemon=True,
            )
            monitor.start()

        old_offline = os.environ.pop("HF_HUB_OFFLINE", None)
        try:
            path = snapshot_download(
                model_id,
                local_files_only=False,
                max_workers=4,
                endpoint=endpoint,
            )
        finally:
            if old_offline is not None:
                os.environ["HF_HUB_OFFLINE"] = old_offline
            else:
                os.environ["HF_HUB_OFFLINE"] = "1"

        stop_monitor.set()

        deps = _get_model_dependencies(model_id)
        if deps:
            missing = [p for p in deps if not _is_package_installed(p)]
            if missing:
                logger.info(f"模型 {model_id} 下载完成，自动安装依赖: {missing}")
                task["status"] = "installing_deps"
                install_ok = _install_dependencies(missing)
                if not install_ok:
                    logger.warning(f"依赖安装失败: {missing}，模型已下载但可能无法使用")

        task["status"] = "completed"
        task["progress"] = 100
        task["path"] = path
        logger.info(f"模型下载完成: {model_id} -> {path}")

    except Exception as e:
        stop_monitor.set()
        logger.error(f"模型下载失败: {model_id} - {e}")
        if model_id in _download_tasks:
            _download_tasks[model_id]["status"] = "failed"
            _download_tasks[model_id]["error"] = str(e)


class DownloadModelRequest(BaseModel):
    model_id: str = Field(..., description="模型ID，如 Qwen/Qwen2-VL-2B-Instruct")


class SetVisionModelRequest(BaseModel):
    model_id: str = Field(..., description="视觉模型ID")


@router.get("/available", summary="获取可用模型列表")
async def list_available_models(admin: dict = Depends(require_admin)):
    models = []
    for m in AVAILABLE_MODELS:
        downloaded = _check_model_downloaded(m["id"])
        task = _download_tasks.get(m["id"])
        models.append({
            **m,
            "downloaded": downloaded,
            "download_status": task["status"] if task else None,
            "download_progress": task.get("progress", 0) if task else 0,
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {"models": models},
    }


@router.get("/downloaded", summary="获取已下载模型列表")
async def list_downloaded_models(admin: dict = Depends(require_admin)):
    downloaded = []
    for m in AVAILABLE_MODELS:
        if _check_model_downloaded(m["id"]):
            downloaded.append(m)

    try:
        from huggingface_hub import scan_cache_dir
        cache = scan_cache_dir()
        for repo in cache.repos:
            already = any(m["id"] == repo.repo_id for m in AVAILABLE_MODELS)
            if not already and repo.repo_id:
                size_mb = sum(s.size_on_disk for s in repo.revisions) / 1024 / 1024
                downloaded.append({
                    "id": repo.repo_id,
                    "name": repo.repo_id.split("/")[-1],
                    "type": "unknown",
                    "size": f"{size_mb:.0f}MB",
                    "description": "自定义下载的模型",
                    "recommended": False,
                })
    except Exception:
        pass

    return {
        "code": 200,
        "message": "查询成功",
        "data": {"models": downloaded},
    }


@router.post("/download", summary="下载模型")
async def download_model(request: DownloadModelRequest, admin: dict = Depends(require_admin)):
    model_id = request.model_id

    valid_ids = [m["id"] for m in AVAILABLE_MODELS]
    if model_id not in valid_ids:
        raise HTTPException(status_code=400, detail=f"不支持的模型: {model_id}")

    if _check_model_downloaded(model_id):
        return {
            "code": 200,
            "message": "模型已下载",
            "data": {"model_id": model_id, "status": "already_downloaded"},
        }

    existing = _download_tasks.get(model_id)
    if existing and existing["status"] == "downloading":
        return {
            "code": 200,
            "message": "模型正在下载中",
            "data": {"model_id": model_id, "status": "downloading", "progress": existing.get("progress", 0)},
        }

    _download_tasks[model_id] = {
        "status": "pending",
        "progress": 0,
        "error": None,
        "path": None,
    }

    thread = threading.Thread(target=_download_model_thread, args=(model_id,), daemon=True)
    thread.start()

    return {
        "code": 200,
        "message": "开始下载模型",
        "data": {"model_id": model_id, "status": "downloading"},
    }


@router.get("/download/{model_id:path}/status", summary="获取模型下载状态")
async def get_download_status(model_id: str, admin: dict = Depends(require_admin)):
    task = _download_tasks.get(model_id)
    if not task:
        downloaded = _check_model_downloaded(model_id)
        if downloaded:
            return {
                "code": 200,
                "message": "查询成功",
                "data": {"model_id": model_id, "status": "completed", "progress": 100},
            }
        return {
            "code": 200,
            "message": "查询成功",
            "data": {"model_id": model_id, "status": "not_started", "progress": 0},
        }

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "model_id": model_id,
            "status": task["status"],
            "progress": task.get("progress", 0),
            "error": task.get("error"),
        },
    }


@router.delete("/download/{model_id:path}", summary="删除已下载模型")
async def delete_model(model_id: str, admin: dict = Depends(require_admin)):
    if model_id == "PaddleOCR/PPOCRv4":
        raise HTTPException(status_code=400, detail="PaddleOCR模型随包安装，无法单独删除")

    if not _check_model_downloaded(model_id):
        raise HTTPException(status_code=404, detail="模型未下载")

    try:
        # GGUF 模型：删除文件
        if model_id.startswith("gguf/"):
            model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
            if model_info and model_info.get("gguf_file"):
                gguf_path = os.path.join(_GGUF_MODEL_DIR, model_info["gguf_file"])
                if os.path.exists(gguf_path):
                    os.remove(gguf_path)
        else:
            model_dir = os.path.join(_get_model_cache_dir(), "hub", f"models--{model_id.replace('/', '--')}")
            if os.path.exists(model_dir):
                shutil.rmtree(model_dir, ignore_errors=True)

        _download_tasks.pop(model_id, None)

        return {
            "code": 200,
            "message": "模型已删除",
            "data": {"model_id": model_id},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模型失败: {e}")


@router.put("/vision-model", summary="切换视觉模型")
async def set_vision_model(request: SetVisionModelRequest, admin: dict = Depends(require_admin)):
    model_id = request.model_id

    if not _check_model_downloaded(model_id):
        raise HTTPException(status_code=400, detail=f"模型未下载: {model_id}，请先下载模型")

    # GGUF 视觉模型：不需要 PyTorch 依赖
    if model_id.startswith("gguf/"):
        model_info = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
        gguf_file = model_info.get("gguf_file", "") if model_info else ""
        gguf_path = os.path.join(_GGUF_MODEL_DIR, gguf_file) if gguf_file else ""

        settings.LOCAL_VISION_MODEL = model_id
        settings.VISION_BACKEND = "local"

        # 同时设置 GGUF 路径供 vision_service 使用
        if gguf_path and os.path.exists(gguf_path):
            settings.LLAMA_CPP_EMBED_MODEL_PATH = gguf_path

        try:
            from app.models.database import get_database
            db = get_database()
            db.set_config("local_vision_model", model_id)
            db.set_config("vision_backend", "local")
        except Exception:
            pass

        try:
            from app.services.vision_service import reset_vision_service
            reset_vision_service()
        except Exception:
            pass

        return {
            "code": 200,
            "message": f"视觉模型已切换为 {model_id}（GGUF），请启动 llama-server 加载此模型后使用",
            "data": {"model_id": model_id, "backend": "local", "gguf_path": gguf_path},
        }

    missing_deps = _check_vision_dependencies()
    if missing_deps:
        logger.info(f"自动安装视觉模型缺失依赖: {missing_deps}")
        install_ok = _install_dependencies(missing_deps)
        if not install_ok:
            raise HTTPException(
                status_code=500,
                detail=f"视觉模型依赖安装失败: {', '.join(missing_deps)}，请手动执行: pip install {' '.join(missing_deps)}",
            )

    settings.LOCAL_VISION_MODEL = model_id
    settings.VISION_BACKEND = "local"

    try:
        from app.models.database import get_database
        db = get_database()
        db.set_config("local_vision_model", model_id)
        db.set_config("vision_backend", "local")
    except Exception:
        pass

    from app.services.vision_service import reset_vision_service
    reset_vision_service()

    return {
        "code": 200,
        "message": f"视觉模型已切换为 {model_id}，后端已设为本地模型",
        "data": {"model_id": model_id, "backend": "local"},
    }
