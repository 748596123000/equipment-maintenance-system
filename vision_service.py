import base64
import logging
from typing import Optional

from app.config import settings
from app.utils.gpu_utils import detect_gpu

logger = logging.getLogger(__name__)

_vision_instance = None


class VisionService:
    def __init__(self):
        self._model = None
        self._processor = None
        self._device = None
        self._initialized = False
        self._local_available = None
        self._backend = settings.VISION_BACKEND

    def _init_local_model(self):
        if self._local_available is not None:
            return self._local_available

        gpu_info = detect_gpu()
        if not gpu_info["available"]:
            logger.info("无 GPU 设备，跳过本地视觉模型加载，使用 API 后端")
            self._local_available = False
            self._initialized = True
            return False

        try:
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
            from qwen_vl_utils import process_vision_info

            device = "cuda" if gpu_info["available"] else "cpu"
            self._device = device

            model_name = settings.LOCAL_VISION_MODEL
            logger.info(f"加载本地视觉模型: {model_name} (设备: {device})")

            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_name,
                torch_dtype="auto",
                device_map="auto",
            )
            self._processor = AutoProcessor.from_pretrained(model_name)
            self._initialized = True
            self._local_available = True
            logger.info("本地视觉模型加载成功")
            return True

        except ImportError as e:
            logger.warning(f"本地视觉模型依赖未安装: {e}")
            logger.warning("请安装: pip install transformers qwen-vl-utils accelerate torch")
            self._local_available = False
            self._initialized = True
            return False
        except Exception as e:
            logger.error(f"本地视觉模型加载失败: {e}")
            self._local_available = False
            self._initialized = True
            return False

    def _resolve_backend(self) -> str:
        backend = self._backend
        if backend == "auto":
            gpu_info = detect_gpu()
            if gpu_info["available"] and self._init_local_model():
                return "local"
            elif settings.DASHSCOPE_API_KEY:
                return "dashscope"
            elif self._init_local_model():
                return "local"
            else:
                return "unavailable"
        elif backend == "local":
            if self._init_local_model():
                return "local"
            logger.warning("本地视觉模型不可用，回退到 DashScope API")
            if settings.DASHSCOPE_API_KEY:
                return "dashscope"
            return "unavailable"
        elif backend == "dashscope":
            if settings.DASHSCOPE_API_KEY:
                return "dashscope"
            logger.warning("DashScope API Key 未配置，尝试本地模型")
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
            logger.warning("本地视觉模型推理失败，回退到 DashScope API")
            return self._describe_dashscope(image_bytes, ext, prompt)
        elif resolved == "dashscope":
            return self._describe_dashscope(image_bytes, ext, prompt)
        else:
            logger.warning("无可用的视觉模型后端")
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

    def _describe_dashscope(
        self, image_bytes: bytes, ext: str, prompt: str
    ) -> Optional[str]:
        if not settings.DASHSCOPE_API_KEY:
            logger.warning("未配置 DASHSCOPE_API_KEY，跳过图片描述生成")
            return None

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
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
                model="qwen-vl-max",
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

    @property
    def backend(self) -> str:
        return self._backend

    @backend.setter
    def backend(self, value: str):
        self._backend = value
        self._resolved_backend = None

    @property
    def is_local_available(self) -> bool:
        if self._local_available is not None:
            return self._local_available
        gpu_info = detect_gpu()
        if not gpu_info["available"]:
            self._local_available = False
            return False
        return self._init_local_model()

    _resolved_backend: Optional[str] = None

    @property
    def current_backend(self) -> str:
        if self._resolved_backend is not None:
            return self._resolved_backend
        self._resolved_backend = self._resolve_backend()
        return self._resolved_backend


def get_vision_service() -> VisionService:
    global _vision_instance
    if _vision_instance is None:
        _vision_instance = VisionService()
    return _vision_instance


def reset_vision_service():
    global _vision_instance
    _vision_instance = None
