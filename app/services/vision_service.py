import base64
import logging
import os
import platform
import threading
import traceback
from typing import Optional

os.environ["HF_HUB_OFFLINE"] = "1"

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.config import settings
from app.utils.gpu_utils import detect_gpu

logger = logging.getLogger(__name__)


def _get_vision_llama_url() -> str:
    # 优先 VISION_API_BASE_URL（旧 llama_cpp 配置作为兜底）
    return (settings.VISION_API_BASE_URL
            or "http://127.0.0.1:8081")


def _get_vision_llama_model() -> str:
    return (settings.VISION_MODEL_NAME
            or "Qwen2-VL-2B-Instruct-Q4_K_M")


def _get_vision_vendor() -> str:
    return (settings.VISION_VENDOR or "").lower() or (settings.VISION_BACKEND or "dashscope").lower()


def _get_vision_api_key() -> str:
    return (settings.VISION_API_KEY
            or settings.OPENAI_COMPATIBLE_API_KEY
            or settings.DASHSCOPE_API_KEY)


_vision_instance = None
_vision_lock = threading.Lock()

# 架构检测
_ARCH = platform.machine().lower()
_IS_LOONGARCH = "loongarch" in _ARCH or "loong64" in _ARCH


class VisionService:
    def __init__(self):
        self._model = None
        self._processor = None
        self._device = None
        self._initialized = False
        self._local_available = None
        self._init_error = None
        # 优先用 VISION_VENDOR，兼容 VISION_BACKEND
        self._backend = (settings.VISION_VENDOR or settings.VISION_BACKEND or "dashscope").lower()
        self._load_lock = threading.Lock()
        self._unavailable_logged = False

    def _init_local_model(self):
        if self._local_available is not None:
            return self._local_available

        with self._load_lock:
            if self._local_available is not None:
                return self._local_available

            # LoongArch架构警告
            if _IS_LOONGARCH:
                logger.warning("LoongArch: 本地视觉模型需要手动安装torch/transformers并下载模型")
                logger.warning("建议：使用DashScope API（配置DASHSCOPE_API_KEY）")

            gpu_info = detect_gpu()
            if gpu_info["available"]:
                device = "cuda"
            else:
                device = "cpu"
                logger.info("未检测到GPU，将以CPU模式加载本地视觉模型（速度较慢）")

            self._device = device

            try:
                from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
                from qwen_vl_utils import process_vision_info

                model_name = settings.LOCAL_VISION_MODEL
                if not model_name:
                    self._local_available = False
                    self._init_error = "未配置本地视觉模型"
                    return False

                logger.info(f"开始加载本地视觉模型: {model_name} (设备: {device})")

                load_kwargs = {"local_files_only": True}
                if device == "cpu":
                    import torch
                    load_kwargs["torch_dtype"] = torch.float32
                else:
                    load_kwargs["torch_dtype"] = "auto"

                self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                    model_name,
                    device_map="auto" if device == "cuda" else None,
                    **load_kwargs,
                )
                if device == "cpu":
                    self._model = self._model.to("cpu")

                self._processor = AutoProcessor.from_pretrained(model_name, local_files_only=True)
                self._initialized = True
                self._local_available = True
                self._init_error = None
                logger.info(f"本地视觉模型加载成功 (设备: {device})")
                return True

            except ImportError as e:
                self._local_available = False
                self._init_error = f"依赖未安装: {e}"
                logger.error(f"本地视觉模型依赖未安装: {e}")
                if _IS_LOONGARCH:
                    logger.error("LoongArch需从源码编译安装: pip install transformers qwen-vl-utils accelerate torch")
                else:
                    logger.error("请安装: pip install transformers qwen-vl-utils accelerate torch")
                return False
            except Exception as e:
                self._local_available = False
                self._init_error = str(e)
                logger.error(f"本地视觉模型加载失败: {e}")
                logger.debug(f"详细错误:\n{traceback.format_exc()}")
                return False

    def _has_dashscope_key(self) -> bool:
        key = settings.DASHSCOPE_API_KEY
        return bool(key) and key != "your_api_key_here"

    def _resolve_backend(self) -> str:
        # 优先使用独立的 VISION_VENDOR 字段，其次回退到 VISION_BACKEND 兼容旧配置
        backend = (settings.VISION_VENDOR or "").lower() or (self._backend or "").lower()
        if backend == "auto" or backend == "":
            if self._init_local_model():
                return "local"
            if self._has_dashscope_key() or _get_vision_api_key():
                return "dashscope"
            return "unavailable"
        if backend == "local":
            if self._init_local_model():
                return "local"
            if not self._unavailable_logged:
                logger.warning(f"本地视觉模型不可用: {self._init_error or '未知错误'}，回退到 DashScope API")
                self._unavailable_logged = True
            if self._has_dashscope_key() or _get_vision_api_key():
                return "dashscope"
            return "unavailable"
        if backend == "dashscope":
            if self._has_dashscope_key() or _get_vision_api_key():
                return "dashscope"
            if self._init_local_model():
                return "local"
            return "unavailable"
        return "unavailable"

    def describe_image(
        self,
        image_bytes: bytes,
        ext: str = "png",
        prompt: str = "请详细描述这张设备检修相关图片的内容，包括设备名称、部件、操作步骤等",
    ) -> Optional[str]:
        resolved = self._resolve_backend()

        if resolved == "local":
            result = self._describe_local(image_bytes, ext, prompt)
            if result is not None:
                return result
            if self._has_dashscope_key():
                return self._describe_dashscope(image_bytes, ext, prompt)
            return None
        elif resolved == "dashscope":
            result = self._describe_dashscope(image_bytes, ext, prompt)
            if result is not None:
                return result
            if self._local_available is True:
                return self._describe_local(image_bytes, ext, prompt)
            return None
        else:
            if not self._unavailable_logged:
                logger.warning("无可用的视觉模型后端，图片描述将被跳过")
                if _IS_LOONGARCH:
                    logger.warning("建议：配置 DASHSCOPE_API_KEY 使用DashScope API")
                self._unavailable_logged = True
            return None

    def _describe_local(
        self, image_bytes: bytes, ext: str, prompt: str
    ) -> Optional[str]:
        if not self._init_local_model():
            return None

        try:
            import torch
            from qwen_vl_utils import process_vision_info

            mime_map = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "bmp": "image/bmp",
                "gif": "image/gif", "tiff": "image/tiff",
                "webp": "image/webp",
            }
            mime_type = mime_map.get(ext, "image/png")
            base64_str = base64.b64encode(image_bytes).decode("utf-8")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "image": f"data:{mime_type};base64,{base64_str}",
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ]

            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            image_inputs, video_inputs = process_vision_info(messages)
            inputs = self._processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            ).to(self._device)

            with torch.no_grad():
                generated_ids = self._model.generate(**inputs, max_new_tokens=300)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self._processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )

            return output_text[0] if output_text else None

        except Exception as e:
            logger.error(f"本地视觉模型推理失败: {e}")
            return None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(3),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        reraise=True,
    )
    def _describe_dashscope(self, image_bytes: bytes, ext: str, prompt: str) -> Optional[str]:
        # 优先 VISION_API_KEY，回退通用 DASHSCOPE_API_KEY
        api_key = (_get_vision_api_key()
                   or settings.DASHSCOPE_API_KEY)
        if not api_key or api_key == "your_api_key_here":
            return None

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                timeout=60.0,
            )

            mime_map = {
                "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "bmp": "image/bmp",
                "gif": "image/gif", "tiff": "image/tiff",
                "webp": "image/webp",
            }
            mime_type = mime_map.get(ext, "image/png")
            base64_str = base64.b64encode(image_bytes).decode("utf-8")

            response = client.chat.completions.create(
                model=settings.VISION_MODEL_NAME or "qwen-vl-max",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_str}"
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=300,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DashScope 视觉模型调用失败: {e}")
            return None

    def warmup(self):
        try:
            logger.info("预热视觉模型...")
            result = self._init_local_model()
            if result:
                logger.info("视觉模型预热完成")
            else:
                logger.warning(f"视觉模型预热失败: {self._init_error}")
        except Exception as e:
            logger.warning(f"视觉模型预热异常: {e}")

    @property
    def backend(self) -> str:
        return self._backend

    @backend.setter
    def backend(self, value: str):
        self._backend = value

    @property
    def is_local_available(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        return self._init_local_model()

    @property
    def current_backend(self) -> str:
        return self._resolve_backend()


def get_vision_service() -> VisionService:
    global _vision_instance
    with _vision_lock:
        if _vision_instance is None:
            _vision_instance = VisionService()
        return _vision_instance


def reset_vision_service():
    global _vision_instance
    with _vision_lock:
        _vision_instance = None
