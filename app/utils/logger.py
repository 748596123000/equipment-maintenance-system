"""
日志工具模块

提供统一的日志配置和管理：
- 控制台日志输出（带颜色：DEBUG蓝色，INFO绿色，WARNING黄色，ERROR红色）
- 文件日志输出（按天轮转，保留30天）
- 日志格式统一配置
- 不同模块的日志级别控制
"""

import logging
import os
import re
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler


# 日志颜色配置
class LogColors:
    """终端日志颜色"""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"


# 日志级别对应的颜色
LEVEL_COLORS = {
    "DEBUG": LogColors.CYAN,
    "INFO": LogColors.GREEN,
    "WARNING": LogColors.YELLOW,
    "ERROR": LogColors.RED,
    "CRITICAL": LogColors.MAGENTA,
}


class ColoredFormatter(logging.Formatter):
    """
    带颜色的日志格式化器

    为不同级别的日志添加对应的终端颜色：
    - DEBUG: 蓝色（CYAN）
    - INFO: 绿色
    - WARNING: 黄色
    - ERROR: 红色
    - CRITICAL: 紫色
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录，添加颜色

        Args:
            record: 日志记录

        Returns:
            str: 格式化后的日志文本（带ANSI颜色码）
        """
        # 保存原始levelname
        original_levelname = record.levelname

        # 为levelname添加颜色
        color = LEVEL_COLORS.get(record.levelname, LogColors.RESET)
        record.levelname = f"{color}{record.levelname:<8}{LogColors.RESET}"

        # 格式化日志
        formatted = super().format(record)

        # 恢复原始levelname（避免影响其他handler）
        record.levelname = original_levelname

        return formatted


class CleanFormatter(logging.Formatter):
    """
    纯文本日志格式化器（不带颜色）

    用于文件日志输出，确保日志文件中不包含ANSI颜色码。
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录（纯文本，去除颜色码）

        Args:
            record: 日志记录

        Returns:
            str: 格式化后的纯文本日志
        """
        # 清除可能残留的ANSI颜色码
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._strip_ansi(record.msg)
        if hasattr(record, 'levelname'):
            record.levelname = self._strip_ansi(record.levelname)

        return super().format(record)

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """
        去除字符串中的ANSI颜色码

        Args:
            text: 可能包含颜色码的文本

        Returns:
            str: 去除颜色码后的纯文本
        """
        ansi_escape = re.compile(r'\033\[[0-9;]*m')
        return ansi_escape.sub('', text)


def setup_logger(
    level: str = "INFO",
    log_dir: str = "./data/logs",
    backup_count: int = 30,
) -> None:
    """
    配置全局日志系统

    同时配置控制台和文件两个输出通道：
    - 控制台：带颜色的彩色输出，DEBUG级别
    - 文件：按天轮转的纯文本输出，保留30天

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_dir: 日志文件目录
        backup_count: 保留的日志文件天数（默认30天）
    """
    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 生成日志文件名（按日期）
    date_str = datetime.now().strftime("%Y%m%d")
    log_file = f"app_{date_str}.log"
    log_path = os.path.join(log_dir, log_file)

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有的处理器（避免重复添加）
    root_logger.handlers.clear()

    # ========== 控制台处理器（带颜色） ==========
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # ========== 文件处理器（按天轮转，保留30天） ==========
    file_handler = TimedRotatingFileHandler(
        log_path,
        when="midnight",       # 每天午夜轮转
        interval=1,            # 每天轮转一次
        backupCount=backup_count,  # 保留30天的日志
        encoding="utf-8",
    )
    # 设置日志文件名后缀格式
    file_handler.suffix = "%Y%m%d.log"
    # 轮转时使用的文件名前缀
    file_handler.baseFilename = log_path
    file_handler.setLevel(logging.DEBUG)
    file_formatter = CleanFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    获取指定名称的日志器

    获取子日志器，可单独设置日志级别。
    子日志器会继承根日志器的handler。

    Args:
        name: 日志器名称（通常使用模块名，如 __name__）
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)

    Returns:
        logging.Logger: 日志器实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger
