"""
配置管理模块

管理系统的所有配置项，包括：
- 通义千问API密钥和模型参数
- 数据库路径和连接配置
- ChromaDB向量数据库配置
- 文件上传路径配置
- 系统运行参数

配置优先级：环境变量 > .env文件 > 默认值
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """系统配置类，从环境变量和.env文件加载配置"""

    # ========== 通义千问API配置 ==========
    DASHSCOPE_API_KEY: str = Field(
        default="",
        description="通义千问API密钥，从 https://dashscope.console.aliyun.com/ 获取"
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-v3",
        description="文本向量化模型名称"
    )
    LLM_BACKEND: str = Field(
        default="dashscope",
        description="LLM后端类型: dashscope / openai_compatible / ollama / minimax"
    )
    LLM_MODEL: str = Field(
        default="qwen-max",
        description="大语言模型名称，可选: qwen-max, qwen-plus, qwen-turbo, minimax模型"
    )
    LLM_API_BASE_URL: str = Field(
        default="",
        description="OpenAI兼容API基础URL，如 http://localhost:8000/v1"
    )
    LLM_API_KEY: str = Field(
        default="",
        description="OpenAI兼容API密钥，Ollama可留空"
    )
    LLM_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="大模型生成温度参数，值越高输出越随机"
    )
    LLM_MAX_TOKENS: int = Field(
        default=4096,
        ge=1,
        le=32768,
        description="大模型最大输出token数"
    )

    # ========== ChromaDB向量数据库配置 ==========
    CHROMA_PERSIST_DIR: str = Field(
        default="./data/chroma_db",
        description="ChromaDB持久化存储目录"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="equipment_knowledge",
        description="ChromaDB默认集合名称"
    )
    EMBEDDING_DIMENSION: int = Field(
        default=1024,
        description="向量维度"
    )

    # ========== SQLite数据库配置 ==========
    SQLITE_DB_PATH: str = Field(
        default="./data/app.db",
        description="SQLite数据库文件路径"
    )

    # ========== 文件存储配置 ==========
    UPLOAD_DIR: str = Field(
        default="./data/pdfs",
        description="文档文件上传目录"
    )
    IMAGE_DIR: str = Field(
        default="./data/images",
        description="图片存储目录"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=500 * 1024 * 1024,
        description="最大文件上传大小（字节）"
    )
    ALLOWED_EXTENSIONS: list = Field(
        default=["pdf", "docx", "xlsx", "pptx", "txt", "md", "csv", "json", "xml", "log",
                 "jpg", "jpeg", "png", "bmp", "gif", "tiff", "webp"],
        description="允许上传的文件扩展名"
    )

    # ========== 文本分块配置 ==========
    CHUNK_SIZE: int = Field(
        default=512,
        ge=100,
        le=4096,
        description="文本分块大小（字符数）"
    )
    CHUNK_OVERLAP: int = Field(
        default=50,
        ge=0,
        le=500,
        description="文本分块重叠大小（字符数）"
    )

    # ========== 检索配置 ==========
    TOP_K_RESULTS: int = Field(
        default=5,
        ge=1,
        le=20,
        description="检索返回的最大结果数"
    )
    RETRIEVER_SCORE_THRESHOLD: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="检索结果最低相似度阈值"
    )

    # ========== 服务配置 ==========
    API_HOST: str = Field(
        default="0.0.0.0",
        description="API服务监听地址"
    )
    API_PORT: int = Field(
        default=8000,
        description="API服务监听端口"
    )
    DEBUG: bool = Field(
        default=False,
        description="调试模式开关"
    )

    # ========== OCR配置 ==========
    OCR_BACKEND: str = Field(
        default="auto",
        description="OCR后端: auto / paddleocr / rapidocr / api / none"
    )
    OCR_USE_GPU: bool = Field(
        default=True,
        description="OCR是否使用GPU加速"
    )
    OCR_LANGUAGE: str = Field(
        default="ch",
        description="OCR语言: ch / en / ch_en"
    )

    # ========== 视觉模型配置 ==========
    VISION_BACKEND: str = Field(
        default="dashscope",
        description="视觉模型后端: dashscope / local / auto"
    )
    LOCAL_VISION_MODEL: str = Field(
        default="Qwen/Qwen2-VL-2B-Instruct",
        description="本地视觉模型名称"
    )
    VISION_GPU_DEVICE: str = Field(
        default="auto",
        description="视觉模型GPU设备: auto / cuda:0 / cpu"
    )
    ENVIRONMENT: str = Field(
        default="development",
        description="运行环境: development / production"
    )
    SECRET_KEY: str = Field(
        default="change-this-to-a-secure-random-string",
        description="安全密钥，用于加密签名等"
    )
    ACCESS_TOKEN_EXPIRE_HOURS: int = Field(
        default=24,
        ge=1,
        le=720,
        description="Token过期时间（小时）"
    )
    RATE_LIMIT_LOGIN_MAX: int = Field(
        default=5,
        ge=1,
        description="登录速率限制-最大尝试次数"
    )
    RATE_LIMIT_LOGIN_WINDOW: int = Field(
        default=300,
        ge=60,
        description="登录速率限制-时间窗口（秒）"
    )
    RATE_LIMIT_API_MAX: int = Field(
        default=60,
        ge=10,
        description="API速率限制-最大请求次数"
    )
    RATE_LIMIT_API_WINDOW: int = Field(
        default=60,
        ge=10,
        description="API速率限制-时间窗口（秒）"
    )

    CORS_ORIGINS: list = Field(
        default=["http://localhost:80", "http://localhost:3000"],
        description="允许跨域的来源列表"
    )
    ALLOWED_HOSTS: list = Field(
        default=["localhost", "127.0.0.1"],
        description="允许的Host头列表（防止Host头注入）"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 允许额外字段，避免LoongArch配置导致错误

    def ensure_directories(self) -> None:
        """确保所有必要的目录都已创建"""
        directories = [
            self.CHROMA_PERSIST_DIR,
            self.UPLOAD_DIR,
            self.IMAGE_DIR,
            os.path.dirname(self.SQLITE_DB_PATH),
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def load_from_database(self):
        try:
            from app.models.database import get_database
            db = get_database()
            config_map = {
                "dashscope_api_key": ("DASHSCOPE_API_KEY", str),
                "llm_model": ("LLM_MODEL", str),
                "llm_temperature": ("LLM_TEMPERATURE", float),
                "llm_max_tokens": ("LLM_MAX_TOKENS", int),
                "llm_backend": ("LLM_BACKEND", str),
                "llm_api_base_url": ("LLM_API_BASE_URL", str),
                "llm_api_key": ("LLM_API_KEY", str),
                "embedding_model": ("EMBEDDING_MODEL", str),
                "chunk_size": ("CHUNK_SIZE", int),
                "chunk_overlap": ("CHUNK_OVERLAP", int),
                "top_k_results": ("TOP_K_RESULTS", int),
                "retriever_score_threshold": ("RETRIEVER_SCORE_THRESHOLD", float),
                "access_token_expire_hours": ("ACCESS_TOKEN_EXPIRE_HOURS", int),
                "ocr_backend": ("OCR_BACKEND", str),
                "ocr_use_gpu": ("OCR_USE_GPU", lambda v: v.lower() in ("true", "1", "yes")),
                "ocr_language": ("OCR_LANGUAGE", str),
                "vision_backend": ("VISION_BACKEND", str),
                "local_vision_model": ("LOCAL_VISION_MODEL", str),
            }
            for db_key, (attr_name, type_func) in config_map.items():
                value = db.get_config(db_key)
                if value is not None:
                    setattr(self, attr_name, type_func(value))
        except Exception:
            pass


# 全局配置单例
settings = Settings()


def get_settings() -> Settings:
    """获取全局配置实例"""
    return settings
