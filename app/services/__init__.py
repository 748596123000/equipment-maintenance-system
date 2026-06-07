"""
服务模块 - 架构自适应加载

根据系统架构自动选择合适的服务实现：
- LoongArch: 使用 *_loongarch.py 适配版
- x86_64/aarch64: 使用原始版本
"""

import logging
import platform

logger = logging.getLogger(__name__)

ARCH = platform.machine().lower()
IS_LOONGARCH = "loongarch" in ARCH or "loong64" in ARCH

if IS_LOONGARCH:
    logger.info(f"检测到LoongArch架构 ({ARCH})，加载适配版服务模块")

    from .embedding_service_loongarch import (
        EmbeddingServiceLoongArch as EmbeddingService,
        get_embedding_service,
        reset_embedding_service,
    )
    from .ocr_service_loongarch import (
        OCRServiceLoongArch as OCRService,
        OCRResult,
        get_ocr_service,
        reset_ocr_service,
    )
    from .vision_service_loongarch import (
        VisionServiceLoongArch as VisionService,
        get_vision_service,
        reset_vision_service,
    )
else:
    logger.info(f"检测到架构 {ARCH}，加载标准服务模块")

    from .embedding_service import (
        EmbeddingService,
        get_embedding_service,
        reset_embedding_service,
    )
    from .ocr_service import (
        OCRService,
        OCRResult,
        get_ocr_service,
        reset_ocr_service,
    )
    from .vision_service import (
        VisionService,
        get_vision_service,
        reset_vision_service,
    )

__all__ = [
    "EmbeddingService",
    "OCRService",
    "OCRResult",
    "VisionService",
    "get_embedding_service",
    "get_ocr_service",
    "get_vision_service",
    "reset_embedding_service",
    "reset_ocr_service",
    "reset_vision_service",
]
