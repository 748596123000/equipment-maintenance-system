"""
通知系统API路由
支持消息通知、审批流程、系统公告等功能
使用数据库持久化存储
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

from app.models.database import get_database

router = APIRouter(tags=["通知消息"])

class NotificationType(str, Enum):
    """通知类型枚举"""
    SYSTEM = "system"                    # 系统通知
    UPLOAD_PENDING = "upload_pending"    # 待审批（上传）
    UPLOAD_APPROVED = "upload_approved"  # 审批通过
    UPLOAD_REJECTED = "upload_rejected"  # 审批拒绝
    CASE_PENDING = "case_pending"        # 案例待审批
    CASE_APPROVED = "case_approved"     # 案例通过
    CASE_REJECTED = "case_rejected"      # 案例拒绝
    COMMENT = "comment"                  # 评论回复

class NotificationPriority(str, Enum):
    """通知优先级枚举"""
    LOW = "low"           # 低优先级
    NORMAL = "normal"     # 普通优先级
    HIGH = "high"         # 高优先级
    URGENT = "urgent"     # 紧急优先级

class NotificationCreate(BaseModel):
    """创建通知请求模型"""
    type: NotificationType = Field(..., description="通知类型")
    title: str = Field(..., description="通知标题", max_length=200)
    content: str = Field(..., description="通知内容", max_length=1000)
    priority: NotificationPriority = Field(NotificationPriority.NORMAL, description="通知优先级")
    target_user_id: Optional[str] = Field(None, description="目标用户ID，None表示发送给所有管理员")
    related_id: Optional[str] = Field(None, description="关联ID（如文档ID）")
    related_type: Optional[str] = Field(None, description="关联类型（如document, case）")

class NotificationResponse(BaseModel):
    """通知响应模型"""
    id: str = Field(..., description="通知ID")
    type: str = Field(..., description="通知类型")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    priority: str = Field(..., description="优先级")
    is_read: bool = Field(..., description="是否已读")
    created_at: str = Field(..., description="创建时间")
    related_id: Optional[str] = Field(None, description="关联ID")
    related_type: Optional[str] = Field(None, description="关联类型")
    sender_name: Optional[str] = Field(None, description="发送者名称")

class NotificationListResponse(BaseModel):
    """通知列表响应模型"""
    total: int = Field(..., description="总通知数")
    unread_count: int = Field(..., description="未读通知数")
    notifications: List[NotificationResponse] = Field(..., description="通知列表")

class NotifyAdminUploadRequest(BaseModel):
    """通知管理员上传文档请求"""
    document_id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    uploader_name: str = Field(..., description="上传者名称")
    file_type: str = Field(..., description="文件类型")
    file_size: str = Field(..., description="文件大小")

class NotifyUserApprovalRequest(BaseModel):
    """通知用户审批结果请求"""
    user_id: str = Field(..., description="用户ID")
    document_id: str = Field(..., description="文档ID")
    filename: str = Field(..., description="文件名")
    approved: bool = Field(..., description="是否通过")
    admin_name: str = Field("管理员", description="管理员名称")
    reason: str = Field("", description="拒绝原因（当approved=False时）")

def generate_id():
    """生成唯一通知ID"""
    return f"notif_{uuid.uuid4().hex[:12]}"

def get_timestamp():
    """获取当前时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@router.get("/list", summary="获取通知列表")
async def get_notifications(
    user_id: str = Query("admin", description="用户ID"),
    is_admin: bool = Query(True, description="是否为管理员"),
    skip: int = Query(0, description="跳过数量", ge=0),
    limit: int = Query(20, description="返回数量", ge=1, le=100),
    unread_only: bool = Query(False, description="仅返回未读通知")
):
    """
    获取通知列表
    
    - is_admin=True: 返回所有管理员通知（包括待审批通知）
    - is_admin=False: 返回该用户的个人通知
    
    支持分页查询和未读筛选
    """
    db = get_database()
    result = db.get_notifications(
        user_id=user_id,
        is_admin=is_admin,
        skip=skip,
        limit=limit,
        unread_only=unread_only
    )

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "total": result["total"],
            "unread_count": result["unread_count"],
            "notifications": result["notifications"]
        }
    }

@router.post("/create", summary="创建新通知")
async def create_notification(notification: NotificationCreate):
    """
    创建新通知
    
    - type: 通知类型（系统、上传待审批等）
    - priority: 优先级（低/普通/高/紧急）
    - target_user_id: 目标用户ID，为None时发送给所有管理员
    """
    db = get_database()

    notif_id = generate_id()

    db.save_notification(
        notification_id=notif_id,
        notification_type=notification.type.value,
        title=notification.title,
        content=notification.content,
        priority=notification.priority.value,
        related_id=notification.related_id,
        related_type=notification.related_type,
        target_user_id=notification.target_user_id,
        sender_name="系统"
    )

    return {
        "code": 200,
        "message": "通知创建成功",
        "data": {"notification_id": notif_id}
    }

@router.post("/{notification_id}/read", summary="标记通知为已读")
async def mark_as_read(notification_id: str = Path(..., description="通知ID")):
    """
    标记单个通知为已读
    
    参数:
        notification_id: 通知ID
    """
    db = get_database()
    success = db.mark_notification_read(notification_id)

    if success:
        return {"code": 200, "message": "已标记为已读", "data": None}
    else:
        raise HTTPException(status_code=404, detail="通知不存在")

@router.post("/read-all", summary="标记所有通知为已读")
async def mark_all_as_read(
    user_id: str = Query("admin", description="用户ID"),
    is_admin: bool = Query(True, description="是否为管理员")
):
    """
    批量标记所有通知为已读
    
    - is_admin=True: 标记所有管理员通知
    - is_admin=False: 标记该用户的所有通知
    """
    db = get_database()
    count = db.mark_all_notifications_read(user_id=user_id, is_admin=is_admin)

    return {"code": 200, "message": f"已标记 {count} 条通知为已读", "data": None}

@router.delete("/{notification_id}", summary="删除通知")
async def delete_notification(notification_id: str = Path(..., description="通知ID")):
    """
    删除指定通知
    
    参数:
        notification_id: 通知ID
    """
    db = get_database()
    success = db.delete_notification(notification_id)

    if success:
        return {"code": 200, "message": "通知已删除", "data": None}
    else:
        raise HTTPException(status_code=404, detail="通知不存在")

@router.get("/unread-count", summary="获取未读通知数量")
async def get_unread_count(
    user_id: str = Query("admin", description="用户ID"),
    is_admin: bool = Query(True, description="是否为管理员")
):
    """
    获取未读通知数量
    
    - is_admin=True: 获取管理员未读通知数
    - is_admin=False: 获取用户未读通知数
    """
    db = get_database()
    result = db.get_notifications(
        user_id=user_id,
        is_admin=is_admin,
        skip=0,
        limit=1,
        unread_only=True
    )

    return {"code": 200, "message": "查询成功", "data": {"unread_count": result["unread_count"]}}

@router.post("/upload-notify-admin", summary="用户上传文档后通知管理员")
async def notify_admin_upload(request: NotifyAdminUploadRequest):
    """
    用户上传文档后自动通知管理员
    
    这是一个便捷接口，用于用户上传文档时调用，
    会自动生成一个待审批通知并发送给所有管理员
    """
    db = get_database()
    notif_id = generate_id()

    db.save_notification(
        notification_id=notif_id,
        notification_type="upload_pending",
        title="📤 新文档待审批",
        content=f"用户「{request.uploader_name}」上传了新文档「{request.filename}」，请及时审批。",
        priority="normal",
        related_id=request.document_id,
        related_type="document",
        target_user_id=None,
        sender_name=request.uploader_name
    )

    return {
        "code": 200,
        "message": "已通知管理员",
        "data": {
            "notification_id": notif_id,
            "document_id": request.document_id
        }
    }

@router.post("/approval-notify-user", summary="管理员审批后通知用户")
async def notify_user_approval(request: NotifyUserApprovalRequest):
    """
    管理员审批文档后通知用户
    
    - approved=True: 发送审批通过通知
    - approved=False: 发送审批拒绝通知，会包含拒绝原因
    """
    db = get_database()
    notif_id = generate_id()

    if request.approved:
        notification_type = "upload_approved"
        title = "✅ 文档审批通过"
        content = f"您上传的文档「{request.filename}」已通过「{request.admin_name}」的审批。"
        priority = "normal"
    else:
        notification_type = "upload_rejected"
        title = "❌ 文档审批未通过"
        content = f"您上传的文档「{request.filename}」未通过审批。原因：{request.reason or '不符合要求'}"
        priority = "high"

    db.save_notification(
        notification_id=notif_id,
        notification_type=notification_type,
        title=title,
        content=content,
        priority=priority,
        related_id=request.document_id,
        related_type="document",
        target_user_id=request.user_id,
        sender_name=request.admin_name
    )

    return {
        "code": 200,
        "message": "已通知用户",
        "data": {
            "notification_id": notif_id,
            "user_id": request.user_id,
            "approved": request.approved
        }
    }
