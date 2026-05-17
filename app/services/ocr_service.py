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


class OCRService:
    def __init__(self, use_gpu: Optional[bool] = None, language: Optional[str] = None):
        self._engine = None
        self._use_gpu = use_gpu if use_gpu is not None else settings.OCR_USE_GPU
        self._language = language or settings.OCR_LANGUAGE
        self._initialized = False

    def _init_engine(self):
        if self._initialized:
            return self._engine is not None

        try:
            from paddleocr import PaddleOCR

            gpu_info = detect_gpu()
            use_gpu = self._use_gpu and gpu_info["available"]

            if use_gpu:
                logger.info(f"OCR 使用 GPU 加速")
            else:
                logger.info(f"OCR 使用 CPU 模式")

            self._engine = PaddleOCR(
                use_angle_cls=True,
                lang=self._language,
                use_gpu=use_gpu,
                show_log=False,
                det_db_thresh=0.3,
                det_db_box_thresh=0.5,
            )
            self._initialized = True
            return True

        except ImportError:
            logger.warning("PaddleOCR 未安装，OCR 功能不可用。请安装: pip install paddleocr paddlepaddle-gpu")
            self._initialized = True
            return False
        except Exception as e:
            logger.error(f"OCR 引擎初始化失败: {e}")
            self._initialized = True
            return False

    def ocr_image(self, image_input) -> Optional[OCRResult]:
        if settings.OCR_BACKEND == "none":
            return None

        if not self._init_engine():
            return None

        try:
            if isinstance(image_input, bytes):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(image_input)
                    tmp_path = tmp.name
                try:
                    result = self._engine.ocr(tmp_path, cls=True)
                finally:
                    os.unlink(tmp_path)
            elif isinstance(image_input, str) and os.path.exists(image_input):
                result = self._engine.ocr(image_input, cls=True)
            else:
                logger.error(f"不支持的输入类型: {type(image_input)}")
                return None

            if not result or not result[0]:
                return OCRResult(text="", confidence=0.0)

            texts = []
            confidences = []
            boxes = []

            for line in result[0]:
                box = line[0]
                text = line[1][0]
                conf = line[1][1]
                texts.append(text)
                confidences.append(conf)
                boxes.append(box)

            combined_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=combined_text,
                confidence=avg_confidence,
                boxes=boxes,
            )

        except Exception as e:
            logger.error(f"OCR 处理失败: {e}")
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
        return self._init_engine()


def get_ocr_service() -> OCRService:
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = OCRService()
    return _ocr_instance


def reset_ocr_service():
    global _ocr_instance
    _ocr_instance = None
