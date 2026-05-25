"""
设备铭牌OCR识别接口

提供设备铭牌图片识别功能：
- POST /ocr/device-plate - 识别设备铭牌图片
- GET /ocr/device-plate/result/{task_id} - 获取识别结果

功能：
1. 接收图片（Base64或文件上传）
2. 使用视觉模型识别铭牌信息
3. 自动检索相关检修知识
4. 返回结构化铭牌数据
"""

import base64
import hashlib
import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, field_validator

from app.api.auth import get_current_user
from app.services.device_info_extractor import get_extractor, DeviceInfoExtractor
from app.core.retriever import get_retriever

logger = logging.getLogger(__name__)

# Base64图片大小限制（10MB）
MAX_IMAGE_SIZE = 10 * 1024 * 1024

# Base64格式正则（标准Base64）
BASE64_PATTERN = re.compile(r'^[A-Za-z0-9+/=\s]+$')

router = APIRouter(dependencies=[Depends(get_current_user)])


# ============== 请求和响应模型 ==============

class DevicePlateRequest(BaseModel):
    """设备铭牌识别请求"""
    image_base64: str = Field(..., description="图片Base64编码字符串，支持data:image/...格式")
    use_cache: bool = Field(default=True, description="是否使用缓存")

    @field_validator('image_base64')
    @classmethod
    def validate_image_base64(cls, v: str) -> str:
        """验证Base64格式和大小"""
        # 移除 data:image/... 前缀
        if v.startswith('data:'):
            v = re.sub(r'^data:[^;]+;base64,', '', v)
        
        # 移除空白字符
        v = v.strip()
        
        # 检查大小
        if len(v) > MAX_IMAGE_SIZE:
            raise ValueError(f'图片Base64大小不能超过{MAX_IMAGE_SIZE // (1024*1024)}MB')
        
        # 检查格式（允许空白）
        if not BASE64_PATTERN.match(v):
            raise ValueError('Base64格式无效')
        
        return v


class DevicePlateResponse(BaseModel):
    """设备铭牌识别响应"""
    success: bool
    message: str
    device_info: Optional[dict] = None
    related_knowledge: Optional[list] = None
    task_id: Optional[str] = None


class DeviceInfo(BaseModel):
    """设备信息"""
    model: Optional[str] = None
    rated_voltage: Optional[str] = None
    rated_current: Optional[str] = None
    rated_power: Optional[str] = None
    frequency: Optional[str] = None
    manufacture_date: Optional[str] = None
    manufacturer: Optional[str] = None
    serial_number: Optional[str] = None
    protection_class: Optional[str] = None
    insulation_class: Optional[str] = None
    standard: Optional[str] = None
    weight: Optional[str] = None
    notes: Optional[str] = None


# ============== API端点 ==============

@router.post("/ocr/device-plate", response_model=DevicePlateResponse)
async def recognize_device_plate(request: DevicePlateRequest):
    """
    识别设备铭牌图片

    Args:
        request: 包含Base64编码图片的请求

    Returns:
        识别的设备铭牌信息和相关检修知识
    """
    try:
        extractor = get_extractor()

        # 生成图片哈希
        image_hash = hashlib.md5(request.image_base64.encode()).hexdigest()

        # 提取设备铭牌信息
        device_info = extractor.extract_from_base64(
            base64_str=request.image_base64,
            use_cache=request.use_cache,
            image_hash=image_hash,
        )

        if not device_info:
            return DevicePlateResponse(
                success=False,
                message="无法识别设备铭牌，请确保图片清晰且包含铭牌信息",
            )

        # 根据设备型号检索相关知识
        related_knowledge = []
        model = device_info.get("model")
        if model:
            try:
                retriever = get_retriever()
                search_results = retriever.search(
                    query=f"{model} 检修 维护",
                    top_k=5,
                    mode="hybrid",
                )
                related_knowledge = [
                    {
                        "id": r.get("id", ""),
                        "title": r.get("title", ""),
                        "score": r.get("score", 0),
                        "excerpt": r.get("content", "")[:200],
                    }
                    for r in search_results
                ]
            except Exception as e:
                logger.warning(f"检索相关知识失败: {e}")

        return DevicePlateResponse(
            success=True,
            message="设备铭牌识别成功",
            device_info=device_info,
            related_knowledge=related_knowledge,
            task_id=image_hash,
        )

    except Exception as e:
        logger.error(f"设备铭牌识别失败: {e}")
        return DevicePlateResponse(
            success=False,
            message=f"识别失败: {str(e)}",
        )


@router.post("/ocr/device-plate/upload", response_model=DevicePlateResponse)
async def recognize_device_plate_upload(
    file: UploadFile = File(..., description="设备铭牌图片文件"),
    use_cache: bool = True,
):
    """
    通过文件上传识别设备铭牌

    Args:
        file: 上传的设备铭牌图片文件
        use_cache: 是否使用缓存

    Returns:
        识别的设备铭牌信息和相关检修知识
    """
    try:
        # 读取文件内容
        contents = await file.read()

        # 转换为Base64
        base64_str = base64.b64encode(contents).decode("utf-8")

        # 调用识别接口
        extractor = get_extractor()
        device_info = extractor.extract_from_image_bytes(
            image_bytes=contents,
            ext=file.filename.split(".")[-1] if "." in file.filename else "png",
            use_cache=use_cache,
            image_hash=hashlib.md5(contents).hexdigest(),
        )

        if not device_info:
            return DevicePlateResponse(
                success=False,
                message="无法识别设备铭牌，请确保图片清晰且包含铭牌信息",
            )

        # 根据设备型号检索相关知识
        related_knowledge = []
        model = device_info.get("model")
        if model:
            try:
                retriever = get_retriever()
                search_results = retriever.search(
                    query=f"{model} 检修 维护",
                    top_k=5,
                    mode="hybrid",
                )
                related_knowledge = [
                    {
                        "id": r.get("id", ""),
                        "title": r.get("title", ""),
                        "score": r.get("score", 0),
                        "excerpt": r.get("content", "")[:200],
                    }
                    for r in search_results
                ]
            except Exception as e:
                logger.warning(f"检索相关知识失败: {e}")

        return DevicePlateResponse(
            success=True,
            message="设备铭牌识别成功",
            device_info=device_info,
            related_knowledge=related_knowledge,
        )

    except Exception as e:
        logger.error(f"设备铭牌识别失败: {e}")
        return DevicePlateResponse(
            success=False,
            message=f"识别失败: {str(e)}",
        )


# ============== 主应用注册 ==============

def register_ocr_routes(fastapi_app):
    """注册OCR路由到主应用（延迟导入避免循环依赖）"""
    fastapi_app.include_router(router, prefix="/api/v1", tags=["OCR识别"])