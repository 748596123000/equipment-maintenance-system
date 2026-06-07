"""
用户画像个性化接口

提供用户画像管理功能：
- GET /profile - 获取当前用户画像
- PUT /profile - 更新用户画像

用户画像支持根据角色调整AI回答风格：
- novice: 新手，通俗易懂，详细解释
- technician: 技术员，标准专业
- expert: 专家，简洁扼要
- admin: 管理员，全面管理视角
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.database import get_database

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


# ============== 数据模型 ==============

class UserProfile(BaseModel):
    """用户画像模型"""
    user_id: str = Field(..., description="用户ID")
    role: str = Field(default="technician", description="用户角色: novice/technician/expert/admin")
    experience_years: int = Field(default=0, description="工作年限")
    specialties: List[str] = Field(default_factory=list, description="专业领域列表")
    preferred_detail_level: str = Field(default="medium", description="偏好详细程度: brief/medium/detailed")
    notification_enabled: bool = Field(default=True, description="是否启用通知")
    theme: str = Field(default="dark", description="偏好主题: dark/light")


class UserProfileUpdate(BaseModel):
    """用户画像更新请求"""
    role: Optional[str] = Field(default=None, description="用户角色")
    experience_years: Optional[int] = Field(default=None, description="工作年限")
    specialties: Optional[List[str]] = Field(default=None, description="专业领域列表")
    preferred_detail_level: Optional[str] = Field(default=None, description="偏好详细程度")
    notification_enabled: Optional[bool] = Field(default=None, description="是否启用通知")
    theme: Optional[str] = Field(default=None, description="偏好主题")


class UserProfileResponse(BaseModel):
    """用户画像响应"""
    success: bool
    message: str
    profile: Optional[UserProfile] = None


# ============== 数据库操作 ==============

def get_user_profile(user_id: str) -> Optional[dict]:
    """获取用户画像"""
    db = get_database()
    conn = db.get_connection()
    cursor = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    if row:
        return dict(row)
    return None


def save_user_profile(profile: dict) -> bool:
    """保存用户画像"""
    db = get_database()
    conn = db.get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO user_profiles 
            (user_id, role, experience_years, specialties, preferred_detail_level, notification_enabled, theme)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            profile["user_id"],
            profile.get("role", "technician"),
            profile.get("experience_years", 0),
            ",".join(profile.get("specialties", [])),
            profile.get("preferred_detail_level", "medium"),
            1 if profile.get("notification_enabled", True) else 0,
            profile.get("theme", "dark"),
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"保存用户画像失败: {e}")
        return False


def init_user_profile_table():
    """初始化用户画像表"""
    db = get_database()
    conn = db.get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            role TEXT DEFAULT 'technician',
            experience_years INTEGER DEFAULT 0,
            specialties TEXT DEFAULT '',
            preferred_detail_level TEXT DEFAULT 'medium',
            notification_enabled INTEGER DEFAULT 1,
            theme TEXT DEFAULT 'dark',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()


# ============== API端点 ==============

@router.get("/profile", summary="获取当前用户画像")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户画像

    Returns:
        当前用户的画像配置
    """
    try:
        user_id = current_user.get("id")
        profile_data = get_user_profile(user_id)

        if profile_data:
            # 解析specialties字段
            specialties_str = profile_data.get("specialties", "")
            specialties = specialties_str.split(",") if specialties_str else []

            profile = UserProfile(
                user_id=user_id,
                role=profile_data.get("role", "technician"),
                experience_years=profile_data.get("experience_years", 0),
                specialties=[s for s in specialties if s],
                preferred_detail_level=profile_data.get("preferred_detail_level", "medium"),
                notification_enabled=bool(profile_data.get("notification_enabled", 1)),
                theme=profile_data.get("theme", "dark"),
            )
        else:
            # 返回默认画像
            profile = UserProfile(
                user_id=user_id,
                role="technician",
                experience_years=0,
                specialties=[],
                preferred_detail_level="medium",
                notification_enabled=True,
                theme="dark",
            )
            # 保存默认画像
            save_user_profile(profile.model_dump())

        return {
            "code": 200,
            "message": "获取画像成功",
            "data": profile.model_dump(),
        }
    except Exception as e:
        logger.error(f"获取用户画像失败: {e}")
        return {
            "code": 500,
            "message": f"获取失败: {str(e)}",
            "data": None,
        }


@router.put("/profile", summary="更新用户画像")
async def update_profile(
    update: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """
    更新当前用户画像

    Args:
        update: 要更新的画像配置

    Returns:
        更新后的用户画像
    """
    try:
        user_id = current_user.get("id")

        # 获取现有画像
        existing = get_user_profile(user_id)
        if existing:
            specialties_str = existing.get("specialties", "")
            specialties = specialties_str.split(",") if specialties_str else []
            profile = UserProfile(
                user_id=user_id,
                role=existing.get("role", "technician"),
                experience_years=existing.get("experience_years", 0),
                specialties=[s for s in specialties if s],
                preferred_detail_level=existing.get("preferred_detail_level", "medium"),
                notification_enabled=bool(existing.get("notification_enabled", 1)),
                theme=existing.get("theme", "dark"),
            )
        else:
            profile = UserProfile(user_id=user_id)

        # 应用更新
        if update.role is not None:
            if update.role not in ["novice", "technician", "expert", "admin"]:
                return UserProfileResponse(
                    success=False,
                    message="无效的角色类型",
                )
            profile.role = update.role

        if update.experience_years is not None:
            profile.experience_years = update.experience_years

        if update.specialties is not None:
            profile.specialties = update.specialties

        if update.preferred_detail_level is not None:
            if update.preferred_detail_level not in ["brief", "medium", "detailed"]:
                return UserProfileResponse(
                    success=False,
                    message="无效的详细程度类型",
                )
            profile.preferred_detail_level = update.preferred_detail_level

        if update.notification_enabled is not None:
            profile.notification_enabled = update.notification_enabled

        if update.theme is not None:
            if update.theme not in ["dark", "light"]:
                return UserProfileResponse(
                    success=False,
                    message="无效的主题类型",
                )
            profile.theme = update.theme

        # 保存更新后的画像
        if save_user_profile(profile.model_dump()):
            return {
                "code": 200,
                "message": "画像更新成功",
                "data": profile.model_dump(),
            }
        else:
            return {
                "code": 500,
                "message": "保存失败",
                "data": None,
            }
    except Exception as e:
        logger.error(f"更新用户画像失败: {e}")
        return {
            "code": 500,
            "message": f"更新失败: {str(e)}",
            "data": None,
        }


@router.get("/profile/ai-hints", response_model=dict)
async def get_profile_ai_hints(current_user: dict = Depends(get_current_user)):
    """
    获取基于用户画像的AI回答提示

    根据用户角色和专业领域，返回适合的AI回答风格提示。
    用于调整RAG和Chat模块的回答风格。

    Returns:
        AI回答提示配置
    """
    try:
        user_id = current_user.get("id")
        profile_data = get_user_profile(user_id)

        if not profile_data:
            profile_data = {"role": "technician", "specialties": ""}

        role = profile_data.get("role", "technician")
        specialties_str = profile_data.get("specialties", "")
        specialties = specialties_str.split(",") if specialties_str else []

        # 根据角色生成AI提示
        role_hints = {
            "novice": {
                "explanation_level": "详细",
                "include_jargon": False,
                "include_examples": True,
                "warning_level": "high",
                "prompt_suffix": "请用通俗易懂的语言解释专业术语，每个步骤都要详细说明原因和注意事项。",
            },
            "technician": {
                "explanation_level": "标准",
                "include_jargon": True,
                "include_examples": True,
                "warning_level": "medium",
                "prompt_suffix": "请使用专业的技术语言，提供标准的操作步骤和注意事项。",
            },
            "expert": {
                "explanation_level": "简洁",
                "include_jargon": True,
                "include_examples": False,
                "warning_level": "low",
                "prompt_suffix": "请简洁扼要地提供核心信息，假设读者具备专业背景知识。",
            },
            "admin": {
                "explanation_level": "全面",
                "include_jargon": True,
                "include_examples": True,
                "warning_level": "high",
                "prompt_suffix": "请从管理和运维角度提供全面的信息，包括人员资质要求、安全规程、审批流程等。",
            },
        }

        hints = role_hints.get(role, role_hints["technician"])
        hints["specialties"] = [s for s in specialties if s]

        return {
            "code": 200,
            "message": "查询成功",
            "data": {
                "role": role,
                "hints": hints,
            },
        }
    except Exception as e:
        logger.error(f"获取AI提示失败: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None,
        }


# ============== 启动时初始化 ==============

def register_profile_routes(fastapi_app):
    """注册用户画像路由（延迟导入避免循环依赖）"""
    # 在启动时初始化表
    init_user_profile_table()

    # 注册路由
    fastapi_app.include_router(router, prefix="/api/v1", tags=["用户画像"])