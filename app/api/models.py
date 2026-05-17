import logging
import os
import shutil
import threading
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import require_admin
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

AVAILABLE_MODELS = [
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

_download_tasks: Dict[str, Dict] = {}


def _get_model_cache_dir() -> str:
    cache_dir = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    return cache_dir


def _check_model_downloaded(model_id: str) -> bool:
    try:
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


def _download_model_thread(model_id: str):
    task = _download_tasks.get(model_id)
    if not task:
        return

    try:
        task["status"] = "downloading"
        task["progress"] = 0

        if model_id == "PaddleOCR/PPOCRv4":
            import paddleocr
            ocr = paddleocr.PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            del ocr
            task["status"] = "completed"
            task["progress"] = 100
            return

        from huggingface_hub import snapshot_download

        def progress_callback(progress: float):
            if model_id in _download_tasks:
                _download_tasks[model_id]["progress"] = int(progress * 100)

        path = snapshot_download(
            model_id,
            local_files_only=False,
            max_workers=4,
        )
        task["status"] = "completed"
        task["progress"] = 100
        task["path"] = path
        logger.info(f"模型下载完成: {model_id} -> {path}")

    except Exception as e:
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

    settings.LOCAL_VISION_MODEL = model_id

    from app.services.vision_service import reset_vision_service
    reset_vision_service()

    return {
        "code": 200,
        "message": f"视觉模型已切换为 {model_id}",
        "data": {"model_id": model_id},
    }
