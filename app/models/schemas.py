"""
Pydantic数据结构定义模块

定义系统中使用的所有数据传输对象（DTO）和请求/响应模型，
用于API接口的参数验证和序列化。

包含：
- 通用响应模型
- 对话相关模型
- 检索相关模型
- 作业指引相关模型
- 检修案例相关模型
- 文档相关模型
- 用户相关模型
- 系统管理相关模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ========== 通用响应模型 ==========

class APIResponse(BaseModel):
    """通用API响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[Any] = Field(default=None, description="响应数据")


class PaginatedResponse(BaseModel):
    """分页响应"""
    code: int = Field(default=200)
    message: str = Field(default="success")
    data: Dict[str, Any] = Field(default_factory=dict)


# ========== 对话相关模型 ==========

class ChatMessage(BaseModel):
    """对话消息"""
    role: str = Field(..., description="角色: user / assistant / system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., min_length=1, max_length=5000, description="用户消息")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    history: Optional[List[ChatMessage]] = Field(default=None, description="对话历史")


class ChatResponse(BaseModel):
    """对话响应"""
    answer: str = Field(..., description="AI回答内容")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="引用来源")
    session_id: str = Field(default="", description="会话ID")


# ========== 检索相关模型 ==========

class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., min_length=1, max_length=1000, description="检索查询")
    search_type: str = Field(default="text", description="检索类型: text / keyword / image / model")
    top_k: int = Field(default=5, ge=1, le=20, description="返回数量")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="筛选条件")


class SearchResultItem(BaseModel):
    """单条检索结果"""
    content: str = Field(..., description="文本内容")
    source: str = Field(..., description="来源文档")
    page: Optional[int] = Field(default=None, description="页码")
    score: float = Field(default=0.0, description="相似度分数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SearchResponse(BaseModel):
    """检索响应"""
    results: List[SearchResultItem] = Field(default_factory=list, description="检索结果列表")


# ========== 作业指引相关模型 ==========

class GuideStep(BaseModel):
    """作业步骤"""
    step_number: int = Field(..., description="步骤序号")
    title: str = Field(..., description="步骤标题")
    description: str = Field(..., description="步骤详细描述")
    warnings: List[str] = Field(default_factory=list, description="安全警告")
    tools: List[str] = Field(default_factory=list, description="所需工具")


class GuideRequest(BaseModel):
    """作业指引生成请求"""
    task_description: str = Field(..., min_length=1, max_length=5000, description="作业任务描述")
    device_model: Optional[str] = Field(default=None, description="设备型号")
    fault_type: Optional[str] = Field(default=None, description="故障类型")
    safety_level: str = Field(default="standard", description="安全等级: low / standard / high / critical")
    detail_level: str = Field(default="medium", description="详细程度: brief / medium / detailed")


class GuideResponse(BaseModel):
    """作业指引响应"""
    title: str = Field(..., description="指引标题")
    steps: List[GuideStep] = Field(default_factory=list, description="作业步骤列表")
    safety_notes: List[str] = Field(default_factory=list, description="安全注意事项")
    tools_required: List[str] = Field(default_factory=list, description="所需工具清单")


# ========== 检修案例相关模型 ==========

class CaseCreate(BaseModel):
    """案例创建请求"""
    title: str = Field(..., min_length=1, max_length=200, description="案例标题")
    description: str = Field(..., min_length=1, description="故障描述")
    device_model: str = Field(default="", description="设备型号")
    fault_type: str = Field(default="", description="故障类型")
    solution: str = Field(default="", description="解决方案")


class CaseResponse(BaseModel):
    """案例完整信息"""
    id: str = Field(..., description="案例ID")
    title: str = Field(..., description="案例标题")
    description: str = Field(default="", description="故障描述")
    device_model: str = Field(default="", description="设备型号")
    fault_type: str = Field(default="", description="故障类型")
    solution: str = Field(default="", description="解决方案")
    author_id: Optional[str] = Field(default=None, description="作者ID")
    status: str = Field(default="pending", description="状态: pending / approved / rejected")
    created_at: Optional[str] = Field(default=None, description="创建时间")
    updated_at: Optional[str] = Field(default=None, description="更新时间")


# ========== 文档相关模型 ==========

class UploadResponse(BaseModel):
    """文档上传响应"""
    document_id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    status: str = Field(default="processing", description="处理状态")
    message: str = Field(default="上传成功", description="响应消息")


# ========== 系统统计模型 ==========

class StatsResponse(BaseModel):
    """系统统计信息"""
    total_documents: int = Field(default=0, description="文档总数")
    total_cases: int = Field(default=0, description="案例总数")
    total_queries: int = Field(default=0, description="查询总数")
    total_users: int = Field(default=0, description="用户总数")


# ========== 以下为兼容现有API模块的模型定义 ==========

class DocumentInfo(BaseModel):
    """文档信息"""
    document_id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    file_size: int = Field(default=0, description="文件大小（字节）")
    category: str = Field(default="通用", description="文档分类")
    description: str = Field(default="", description="文档描述")
    page_count: int = Field(default=0, description="页数")
    chunk_count: int = Field(default=0, description="文本块数量")
    status: str = Field(default="pending", description="处理状态")
    uploaded_by: Optional[str] = Field(default=None, description="上传者")
    created_at: Optional[str] = Field(default=None, description="上传时间")


class DocumentUploadResult(BaseModel):
    """文档上传结果"""
    document_id: str
    filename: str
    category: str
    file_size: int
    status: str
    chunk_count: int = 0


class SearchHit(BaseModel):
    """单条检索结果（兼容旧版）"""
    chunk_id: str = Field(..., description="文本块ID")
    content: str = Field(..., description="文本内容")
    source: str = Field(..., description="来源文档")
    page_number: Optional[int] = Field(default=None, description="页码")
    score: float = Field(..., description="相似度分数")
    category: Optional[str] = Field(default=None, description="分类")
    highlight: Optional[str] = Field(default=None, description="高亮文本")


class SearchResult(BaseModel):
    """检索结果集（兼容旧版）"""
    query: str
    total: int
    results: List[SearchHit] = Field(default_factory=list)
    search_mode: str = Field(default="hybrid")


class ChatMessageSchema(BaseModel):
    """对话消息（兼容旧版）"""
    role: str = Field(..., description="角色: user / assistant / system")
    content: str = Field(..., description="消息内容")


class ChatRequestSchema(BaseModel):
    """对话请求（兼容旧版）"""
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")
    session_id: Optional[str] = Field(default=None, description="会话ID")
    history: Optional[List[ChatMessageSchema]] = Field(default=None, description="对话历史")
    search_mode: str = Field(default="hybrid", description="检索模式")
    top_k: int = Field(default=5, ge=1, le=20, description="检索数量")


class ChatSourceSchema(BaseModel):
    """引用来源（兼容旧版）"""
    source: str = Field(..., description="来源文档")
    content: str = Field(..., description="引用内容摘要")
    score: float = Field(default=0.0, description="相似度分数")
    page_number: Optional[int] = Field(default=None, description="页码")


class ChatResponseSchema(BaseModel):
    """对话响应（兼容旧版）"""
    session_id: str
    answer: str
    sources: List[ChatSourceSchema] = Field(default_factory=list)
    confidence: float = Field(default=0.0)


class GuideStepSchema(BaseModel):
    """作业步骤（兼容旧版）"""
    step_number: int
    title: str
    description: str
    warnings: List[str] = Field(default_factory=list)
    tools_required: List[str] = Field(default_factory=list)
    estimated_time: Optional[str] = None
    tips: List[str] = Field(default_factory=list)


class GuideRequestSchema(BaseModel):
    """作业指引生成请求（兼容旧版）"""
    task_description: str = Field(..., min_length=1, max_length=5000)
    equipment_model: Optional[str] = None
    equipment_type: Optional[str] = None
    work_environment: Optional[str] = None
    safety_level: str = Field(default="standard")
    detail_level: str = Field(default="medium")


class GuideResponseSchema(BaseModel):
    """作业指引响应（兼容旧版）"""
    guide_id: str
    title: str
    task_summary: str
    preparation: List[str] = Field(default_factory=list)
    steps: List[GuideStepSchema] = Field(default_factory=list)
    safety_notes: List[str] = Field(default_factory=list)
    completion_criteria: List[str] = Field(default_factory=list)


class CaseSchema(BaseModel):
    """检修案例（兼容旧版）"""
    case_id: str
    title: str
    equipment_type: str
    equipment_model: str = ""
    fault_description: str
    fault_analysis: str = ""
    repair_process: str = ""
    repair_result: str = ""
    lessons_learned: str = ""
    tags: List[str] = Field(default_factory=list)
    status: str = Field(default="pending_review")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CaseCreateSchema(BaseModel):
    """案例创建请求（兼容旧版）"""
    title: str = Field(..., min_length=1, max_length=200)
    equipment_type: str = Field(..., min_length=1)
    equipment_model: str = ""
    fault_description: str = Field(..., min_length=1)
    fault_analysis: str = ""
    repair_process: str = ""
    repair_result: str = ""
    lessons_learned: str = ""
    tags: List[str] = Field(default_factory=list)


class UserSchema(BaseModel):
    """用户信息"""
    user_id: str
    username: str
    role: str = "user"
    is_active: bool = True
    created_at: Optional[str] = None


class UserCreateSchema(BaseModel):
    """用户创建请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(default="user")


class UserUpdateSchema(BaseModel):
    """用户更新请求"""
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class SystemStats(BaseModel):
    """系统统计信息（兼容旧版）"""
    document_count: int = 0
    case_count: int = 0
    total_chunks: int = 0
    user_count: int = 0
    chat_count: int = 0
    guide_count: int = 0
    chroma_status: str = "unknown"
    db_size_mb: float = 0.0


class SystemConfigSchema(BaseModel):
    """系统配置"""
    llm_model: str = "qwen-max"
    embedding_model: str = "text-embedding-v3"
    llm_temperature: float = 0.7
    chunk_size: int = 512
    chunk_overlap: int = 50
    top_k_results: int = 5


class LogEntry(BaseModel):
    """日志条目"""
    id: str
    user_id: Optional[str] = None
    action: str
    detail: str = ""
    ip_address: str = ""
    created_at: str
