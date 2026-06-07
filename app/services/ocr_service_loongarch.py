"""
OCR识别服务模块 - 麒麟V11 LoongArch适配版

适配说明：
- LoongArch架构不支持PaddleOCR（无预编译wheel，paddlepaddle不支持LoongArch）
- RapidOCR依赖ONNX Runtime，LoongArch支持不确定
- 优先使用DashScope API（qwen-vl-max）进行OCR
- 如需本地OCR，需手动编译Tesseract或等待社区支持

支持后端：
- api: DashScope qwen-vl API（推荐，无需本地模型）
- rapidocr: RapidOCR（需确认ONNX Runtime LoongArch支持）
- none: 禁用OCR
"""

import base64
import logging
import os
import tempfile
from typing import Dict, List, Optional

from app.config import settings
from app.utils.gpu_utils import detect_gpu

logger = logging.getLogger(__name__)

_ocr_instance = None


class OCRResult:
    def __init__(self, text: str, confidence: float, boxes: Optional[List] = None):
        self.text = text
        self.confidence = confidence
        self.boxes = boxes or []


class OCRServiceLoongArch:
    BACKEND_RAPID = "rapidocr"
    BACKEND_API = "api"
    BACKEND_NONE = "none"

    def __init__(self, use_gpu: Optional[bool] = None, language: Optional[str] = None):
        self._engine = None
        self._engine_type = None
        self._use_gpu = use_gpu if use_gpu is not None else settings.OCR_USE_GPU
        self._language = language or settings.OCR_LANGUAGE
        self._initialized = False

    def _init_engine(self) -> bool:
        if self._initialized:
            return self._engine is not None

        backend = settings.OCR_BACKEND

        if backend == self.BACKEND_NONE:
            logger.info("OCR 后端已禁用")
            self._initialized = True
            return False

        if backend == "auto":
            if self._try_init_rapidocr():
                return True
            if self._try_init_api():
                return True
            logger.warning("LoongArch: 所有 OCR 后端均不可用")
            logger.warning("建议：配置 DASHSCOPE_API_KEY 使用API OCR，或安装 rapidocr_onnxruntime")
            self._initialized = True
            return False

        if backend == self.BACKEND_RAPID:
            if self._try_init_rapidocr():
                return True
        elif backend == self.BACKEND_API:
            if self._try_init_api():
                return True

        if backend != "auto" and settings.OCR_BACKEND != "none":
            logger.info(f"指定 OCR 后端 {backend} 不可用，尝试回退...")
            if self._try_init_api():
                return True

        self._initialized = True
        return False

    def _try_init_rapidocr(self) -> bool:
        try:
            from rapidocr_onnxruntime import RapidOCR

            logger.info("初始化 RapidOCR (CPU)")
            self._engine = RapidOCR()
            self._engine_type = self.BACKEND_RAPID
            self._initialized = True
            logger.info("RapidOCR 初始化成功")
            return True
        except ImportError:
            logger.debug("RapidOCR 未安装，跳过")
            return False
        except Exception as e:
            logger.warning(f"RapidOCR 初始化失败: {e}")
            return False

    def _try_init_api(self) -> bool:
        if not settings.DASHSCOPE_API_KEY:
            logger.debug("DashScope API Key 未配置，跳过 API OCR")
            return False

        self._engine = True
        self._engine_type = self.BACKEND_API
        self._initialized = True
        logger.info("OCR API 后端就绪 (DashScope qwen-vl)")
        return True

    def ocr_image(self, image_input) -> Optional[OCRResult]:
        if settings.OCR_BACKEND == "none":
            return None

        if not self._init_engine():
            return None

        try:
            if self._engine_type == self.BACKEND_RAPID:
                return self._ocr_rapid(image_input)
            elif self._engine_type == self.BACKEND_API:
                return self._ocr_api(image_input)
        except Exception as e:
            logger.error(f"OCR 处理失败 (后端: {self._engine_type}): {e}")
            if self._engine_type != self.BACKEND_API:
                logger.info("尝试回退到 API OCR...")
                if self._try_init_api():
                    return self._ocr_api(image_input)

        return None

    def _ocr_rapid(self, image_input) -> Optional[OCRResult]:
        import cv2
        import numpy as np

        try:
            if isinstance(image_input, bytes):
                nparr = np.frombuffer(image_input, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif isinstance(image_input, str) and os.path.exists(image_input):
                img = cv2.imread(image_input)
            else:
                logger.error(f"不支持的输入类型: {type(image_input)}")
                return None

            if img is None:
                logger.error("无法读取图片")
                return None

            result, elapse = self._engine(img)

            if not result:
                return OCRResult(text="", confidence=0.0)

            texts = []
            confidences = []
            boxes = []
            for item in result:
                boxes.append(item[0])
                texts.append(item[1])
                confidences.append(item[2])

            return OCRResult(
                text="\n".join(texts),
                confidence=sum(confidences) / len(confidences) if confidences else 0.0,
                boxes=boxes,
            )
        except Exception as e:
            logger.error(f"RapidOCR 处理失败: {e}")
            return None

    def _ocr_api(self, image_input) -> Optional[OCRResult]:
        if not settings.DASHSCOPE_API_KEY:
            return None

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

            if isinstance(image_input, bytes):
                b64 = base64.b64encode(image_input).decode("utf-8")
                mime = "image/png"
            elif isinstance(image_input, str) and os.path.exists(image_input):
                ext = os.path.splitext(image_input)[1].lstrip(".").lower()
                mime_map = {
                    "jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "png": "image/png", "bmp": "image/bmp",
                    "gif": "image/gif", "webp": "image/webp",
                }
                mime = mime_map.get(ext, "image/png")
                with open(image_input, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
            else:
                return None

            response = client.chat.completions.create(
                model="qwen-vl-max",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime};base64,{b64}"},
                            },
                            {"type": "text", "text": "请识别并提取图片中的所有文字内容，按原始排版输出。只输出识别到的文字，不要添加任何解释。"},
                        ],
                    }
                ],
                max_tokens=2000,
            )

            text = response.choices[0].message.content
            return OCRResult(text=text or "", confidence=0.9)
        except Exception as e:
            logger.error(f"API OCR 调用失败: {e}")
            return None

    def ocr_batch(self, image_inputs: List) -> List[Optional[OCRResult]]:
        results = []
        for img in image_inputs:
            results.append(self.ocr_image(img))
        return results

    @property
    def is_available(self) -> bool:
        if settings.OCR_BACKEND == "none":
            return False
        if self._initialized:
            return self._engine is not None
        return self._init_engine()

    @property
    def engine_type(self) -> Optional[str]:
        if not self._initialized:
            backend = settings.OCR_BACKEND
            if backend == "none":
                return None
            if backend == "api":
                return self.BACKEND_API if settings.DASHSCOPE_API_KEY else None
            if backend == "rapidocr":
                return self.BACKEND_RAPID
            return "auto"
        return self._engine_type


def get_ocr_service() -> OCRServiceLoongArch:
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = OCRServiceLoongArch()
    return _ocr_instance


def reset_ocr_service():
    global _ocr_instance
    _ocr_instance = None
