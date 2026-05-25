"""
设备铭牌信息提取服务

基于视觉模型识别设备铭牌图片，提取结构化信息：
- 设备型号
- 额定电压
- 额定电流
- 生产日期
- 厂家信息
- 序列号
"""

import base64
import json
import logging
import re
from typing import Optional, Dict, Any

from app.services.vision_service import VisionService

logger = logging.getLogger(__name__)

# 设备铭牌信息提取的系统提示词
DEVICE_PLATE_EXTRACTOR_PROMPT = """请仔细分析这张设备铭牌图片，提取以下结构化信息并以JSON格式返回：

{
    "model": "设备型号（如有）",
    "rated_voltage": "额定电压（如：10kV）",
    "rated_current": "额定电流（如：630A）",
    "rated_power": "额定功率（如：500kVA）",
    "frequency": "额定频率（如：50Hz）",
    "manufacture_date": "生产日期（如：2020年1月）",
    "manufacturer": "制造厂家",
    "serial_number": "序列号",
    "protection_class": "防护等级",
    "insulation_class": "绝缘等级",
    "standard": "执行标准",
    "weight": "重量",
    "notes": "其他备注信息"
}

注意：
1. 如果某项信息无法从图片中读取，请填写null
2. 电压、电流等数值请保留原始单位（如kV、A等）
3. 厂家信息可能包含在"制造单位"、"生产厂家"、"Manufacturer"等字段中
4. 只返回有效的JSON格式，不要包含其他文字说明
"""

# 设备铭牌识别的备用提示词（简单版）
DEVICE_PLATE_SIMPLE_PROMPT = """请识别这张设备铭牌图片，提取以下信息：
1. 设备型号/名称
2. 额定参数（电压、电流、功率等）
3. 生产厂家
4. 生产日期
5. 其他重要参数

请以结构化方式返回。
"""


class DeviceInfoExtractor:
    """设备铭牌信息提取器"""

    def __init__(self):
        self._vision_service = VisionService()
        self._cache: Dict[str, Dict[str, Any]] = {}

    def extract_from_image_bytes(
        self,
        image_bytes: bytes,
        ext: str = "png",
        use_cache: bool = False,
        image_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        从图片字节中提取设备铭牌信息

        Args:
            image_bytes: 图片的字节数据
            ext: 图片扩展名（png/jpg/jpeg等）
            use_cache: 是否使用缓存
            image_hash: 图片哈希值（用于缓存键）

        Returns:
            提取的设备铭牌信息字典，如果提取失败返回None
        """
        # 检查缓存
        if use_cache and image_hash and image_hash in self._cache:
            logger.info(f"使用缓存的铭牌信息: {image_hash}")
            return self._cache[image_hash]

        # 使用视觉模型描述图片
        description = self._vision_service.describe_image(
            image_bytes=image_bytes,
            ext=ext,
            prompt=DEVICE_PLATE_EXTRACTOR_PROMPT,
        )

        if not description:
            logger.warning("视觉模型无法识别图片")
            return None

        # 尝试解析JSON
        device_info = self._parse_device_info(description)

        # 更新缓存
        if use_cache and image_hash and device_info:
            self._cache[image_hash] = device_info

        return device_info

    def extract_from_base64(
        self,
        base64_str: str,
        use_cache: bool = False,
        image_hash: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        从Base64字符串中提取设备铭牌信息

        Args:
            base64_str: Base64编码的图片数据
            use_cache: 是否使用缓存
            image_hash: 图片哈希值（用于缓存键）

        Returns:
            提取的设备铭牌信息字典，如果提取失败返回None
        """
        # 移除可能的 data URL 前缀
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]

        try:
            image_bytes = base64.b64decode(base64_str)
            # 检测图片格式
            ext = self._detect_extension_from_bytes(image_bytes)
            return self.extract_from_image_bytes(
                image_bytes=image_bytes,
                ext=ext,
                use_cache=use_cache,
                image_hash=image_hash,
            )
        except Exception as e:
            logger.error(f"Base64解码失败: {e}")
            return None

    def _parse_device_info(self, description: str) -> Optional[Dict[str, Any]]:
        """
        解析视觉模型返回的描述文本，提取结构化信息

        Args:
            description: 视觉模型返回的描述文本

        Returns:
            解析后的设备铭牌信息字典
        """
        # 尝试从描述中提取JSON
        try:
            # 尝试直接解析为JSON
            info = json.loads(description)
            return self._normalize_device_info(info)
        except json.JSONDecodeError:
            pass

        # 尝试从文本中提取JSON
        json_match = re.search(
            r"\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\})*[^{}]*\})*[^{}]*\})*[^{}]*\}",
            description,
            re.DOTALL,
        )
        if json_match:
            try:
                info = json.loads(json_match.group())
                return self._normalize_device_info(info)
            except json.JSONDecodeError:
                pass

        # 尝试从文本中提取关键信息
        return self._extract_from_text(description)

    def _normalize_device_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        规范化设备铭牌信息

        Args:
            info: 原始设备铭牌信息

        Returns:
            规范化后的设备铭牌信息
        """
        normalized = {
            "model": info.get("model") or info.get("型号") or info.get("设备型号"),
            "rated_voltage": info.get("rated_voltage") or info.get("额定电压"),
            "rated_current": info.get("rated_current") or info.get("额定电流"),
            "rated_power": info.get("rated_power") or info.get("额定功率"),
            "frequency": info.get("frequency") or info.get("额定频率"),
            "manufacture_date": info.get("manufacture_date") or info.get("生产日期") or info.get("制造日期"),
            "manufacturer": info.get("manufacturer") or info.get("manufacture") or info.get("制造厂家") or info.get("生产厂家"),
            "serial_number": info.get("serial_number") or info.get("序列号") or info.get("出厂编号"),
            "protection_class": info.get("protection_class") or info.get("防护等级"),
            "insulation_class": info.get("insulation_class") or info.get("绝缘等级"),
            "standard": info.get("standard") or info.get("执行标准"),
            "weight": info.get("weight") or info.get("重量"),
            "notes": info.get("notes") or info.get("备注"),
        }

        # 清理None值
        normalized = {k: v for k, v in normalized.items() if v is not None}

        # 添加原始数据（如果有）
        if "raw" not in normalized:
            normalized["raw"] = info

        return normalized

    def _extract_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从非结构化文本中提取设备铭牌信息

        Args:
            text: 非结构化的描述文本

        Returns:
            提取的设备铭牌信息字典
        """
        info = {}

        # 设备型号
        model_patterns = [
            r"(?:型号|Model|Type)[：:\s]*([A-Za-z0-9\-]+)",
            r"型号[：:\s]*([\u4e00-\u9fa5A-Za-z0-9\-]+)",
        ]
        for pattern in model_patterns:
            match = re.search(pattern, text)
            if match:
                info["model"] = match.group(1)
                break

        # 额定电压
        voltage_patterns = [
            r"(\d+[.。]?\d*)\s*[kK][vV]",
            r"额定电压[：:\s]*(\d+[.。]?\d*\s*[kK][vV])",
        ]
        for pattern in voltage_patterns:
            match = re.search(pattern, text)
            if match:
                info["rated_voltage"] = match.group(1)
                break

        # 额定电流
        current_patterns = [
            r"(\d+)\s*[aA]",
            r"额定电流[：:\s]*(\d+\s*[aA])",
        ]
        for pattern in current_patterns:
            match = re.search(pattern, text)
            if match:
                info["rated_current"] = match.group(1)
                break

        # 厂家
        manufacturer_patterns = [
            r"(?:厂家|制造商|Manufacturer|制造单位)[：:\s]*([^\n，。,]+)",
        ]
        for pattern in manufacturer_patterns:
            match = re.search(pattern, text)
            if match:
                info["manufacturer"] = match.group(1)
                break

        # 生产日期
        date_patterns = [
            r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})",
            r"(\d{4})[年\-/](\d{1,2})",
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) >= 2:
                    info["manufacture_date"] = f"{match.group(1)}年{match.group(2)}月"
                if len(match.groups()) >= 3:
                    info["manufacture_date"] += match.group(3)
                break

        if not info:
            # 如果什么都没提取到，返回原始描述作为备注
            info["notes"] = text[:500]  # 限制长度

        return self._normalize_device_info(info)

    def _detect_extension_from_bytes(self, image_bytes: bytes) -> str:
        """
        根据图片字节数据检测扩展名

        Args:
            image_bytes: 图片字节数据

        Returns:
            扩展名（png/jpg等）
        """
        if len(image_bytes) < 4:
            return "png"

        # PNG
        if image_bytes[:4] == b"\x89PNG":
            return "png"
        # JPEG
        if image_bytes[:2] == b"\xff\xd8":
            return "jpg"
        # GIF
        if image_bytes[:4] == b"GIF8":
            return "gif"
        # WebP
        if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            return "webp"
        # BMP
        if image_bytes[:2] == b"BM":
            return "bmp"

        return "png"

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


# 全局单例
_extractor_instance = None


def get_extractor() -> DeviceInfoExtractor:
    """获取设备铭牌提取器单例"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = DeviceInfoExtractor()
    return _extractor_instance