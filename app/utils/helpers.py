"""
通用辅助函数模块

提供系统中常用的工具函数：
- 唯一ID生成
- 文件类型验证
- 文件大小格式化
- 文本截断
- 文件名安全化
- 时间戳获取
- 文本处理
- 响应格式化
"""

import os
import re
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_id(prefix: str = "") -> str:
    """
    生成唯一ID

    基于时间戳和随机数生成唯一标识符，支持添加前缀。

    Args:
        prefix: ID前缀（可选）

    Returns:
        str: 唯一ID字符串

    Examples:
        >>> generate_id()
        'a1b2c3d4e5f6'
        >>> generate_id("doc")
        'doc_a1b2c3d4e5f6'
    """
    # 使用时间戳（毫秒级）+ 随机数生成唯一ID
    timestamp_part = str(int(time.time() * 1000))[-8:]
    random_part = uuid.uuid4().hex[:8]
    unique_id = f"{timestamp_part}{random_part}"
    return f"{prefix}_{unique_id}" if prefix else unique_id


def validate_file_type(filename: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    验证文件类型是否在允许的扩展名列表中

    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表（不含点号），默认为 ["pdf"]

    Returns:
        bool: 文件类型是否合法

    Examples:
        >>> validate_file_type("document.pdf")
        True
        >>> validate_file_type("image.jpg", ["pdf", "jpg", "png"])
        True
        >>> validate_file_type("script.exe")
        False
    """
    if not filename:
        return False

    if allowed_extensions is None:
        allowed_extensions = ["pdf"]

    # 获取文件扩展名（转小写，去除点号）
    ext = os.path.splitext(filename)[1].lower().lstrip(".")

    return ext in [e.lower().lstrip(".") for e in allowed_extensions]


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    将字节数转换为人类可读的文件大小字符串。

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        str: 格式化后的文件大小字符串

    Examples:
        >>> format_file_size(500)
        '500 B'
        >>> format_file_size(1536)
        '1.5 KB'
        >>> format_file_size(1048576)
        '1.0 MB'
        >>> format_file_size(1073741824)
        '1.00 GB'
    """
    if size_bytes < 0:
        return "0 B"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """
    截断文本

    当文本长度超过指定最大长度时，在末尾添加省略后缀。

    Args:
        text: 原始文本
        max_length: 最大长度（包含后缀）
        suffix: 截断后缀

    Returns:
        str: 截断后的文本

    Examples:
        >>> truncate_text("短文本", 10)
        '短文本'
        >>> truncate_text("这是一段很长的文本内容", 10)
        '这是一段很长的文...'
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    # 确保截断后的长度不超过max_length
    return text[:max_length - len(suffix)] + suffix


def safe_filename(filename: str) -> str:
    """
    安全化文件名

    去除文件名中的危险字符和路径遍历成分，防止安全漏洞。
    保留中文、字母、数字、下划线、连字符和点号。

    Args:
        filename: 原始文件名

    Returns:
        str: 安全化后的文件名

    Examples:
        >>> safe_filename("../../../etc/passwd")
        'etc_passwd'
        >>> safe_filename("file name with spaces.pdf")
        'file_name_with_spaces.pdf'
        >>> safe_filename("设备检修手册.pdf")
        '设备检修手册.pdf'
    """
    if not filename:
        return "unnamed"

    # 获取纯文件名（去除路径）
    filename = os.path.basename(filename)

    # 替换空格为下划线
    filename = filename.replace(" ", "_")

    # 只保留安全字符：中文、字母、数字、下划线、连字符、点号
    # Unicode范围：\u4e00-\u9fff（中文），\u3000-\u303f（中文标点）
    filename = re.sub(r'[^\w\u4e00-\u9fff\u3000-\u303f.\-]', '_', filename)

    # 去除连续的下划线
    filename = re.sub(r'_+', '_', filename)

    # 去除首尾的下划线和点号
    filename = filename.strip('._')

    # 限制文件名长度（保留扩展名）
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    filename = name + ext

    # 如果处理后为空，返回默认文件名
    if not filename or filename == ext:
        return f"unnamed_{uuid.uuid4().hex[:8]}{ext}"

    return filename


def timestamp_now(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    获取当前时间戳字符串

    Args:
        fmt: 时间格式字符串，默认为 "%Y-%m-%d %H:%M:%S"

    Returns:
        str: 格式化后的当前时间字符串

    Examples:
        >>> timestamp_now()
        '2024-01-15 10:30:00'
        >>> timestamp_now("%Y%m%d")
        '20240115'
    """
    return datetime.now().strftime(fmt)


# ========== 以下为兼容现有代码的辅助函数 ==========

def format_datetime(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间

    Args:
        dt: datetime对象，为None则使用当前时间
        fmt: 格式字符串

    Returns:
        str: 格式化后的时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def parse_datetime(date_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
    """
    解析日期时间字符串

    Args:
        date_str: 日期时间字符串
        fmt: 格式字符串

    Returns:
        Optional[datetime]: 解析后的datetime对象，失败返回None
    """
    try:
        return datetime.strptime(date_str, fmt)
    except (ValueError, TypeError):
        return None


def clean_text(text: str) -> str:
    """
    清理文本内容

    去除多余空白、特殊字符等

    Args:
        text: 原始文本

    Returns:
        str: 清理后的文本
    """
    if not text:
        return ""
    # 替换多个连续空白为单个空格
    text = re.sub(r'\s+', ' ', text)
    # 去除首尾空白
    text = text.strip()
    # 去除零宽字符
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    return text


def extract_chinese(text: str) -> str:
    """
    提取文本中的中文字符

    Args:
        text: 原始文本

    Returns:
        str: 仅包含中文的文本
    """
    return re.sub(r'[^\u4e00-\u9fff]', '', text)


def is_valid_pdf(file_path: str) -> bool:
    """
    验证文件是否为有效的PDF文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否为有效PDF
    """
    if not os.path.exists(file_path):
        return False
    if not file_path.lower().endswith(".pdf"):
        return False
    try:
        with open(file_path, "rb") as f:
            header = f.read(5)
            return header == b"%PDF-"
    except Exception:
        return False


def ensure_dir(path: str) -> str:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        str: 目录路径
    """
    os.makedirs(path, exist_ok=True)
    return path


def build_success_response(data: Any = None, message: str = "success") -> Dict[str, Any]:
    """
    构建成功响应

    Args:
        data: 响应数据
        message: 响应消息

    Returns:
        dict: 标准响应格式
    """
    return {
        "code": 200,
        "message": message,
        "data": data,
    }


def build_error_response(
    code: int = 500,
    message: str = "服务器内部错误",
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    """
    构建错误响应

    Args:
        code: 错误码
        message: 错误消息
        detail: 错误详情

    Returns:
        dict: 标准错误响应格式
    """
    response = {
        "code": code,
        "message": message,
    }
    if detail:
        response["detail"] = detail
    return response


def safe_json_serialize(obj: Any) -> Any:
    """
    安全的JSON序列化处理

    处理datetime等不可序列化的类型

    Args:
        obj: 待序列化的对象

    Returns:
        Any: 可序列化的对象
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    elif hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif hasattr(obj, "__dict__"):
        return str(obj)
    return obj


def calculate_pagination(page: int, page_size: int, total: int) -> Dict[str, Any]:
    """
    计算分页信息

    Args:
        page: 当前页码
        page_size: 每页数量
        total: 总记录数

    Returns:
        dict: 分页信息
    """
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    has_prev = page > 1
    has_next = page < total_pages

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": has_prev,
        "has_next": has_next,
    }
