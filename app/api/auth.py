"""
用户登录认证接口

提供用户注册、登录、获取当前用户信息和退出登录功能：
- POST /api/v1/auth/login - 用户登录
- POST /api/v1/auth/register - 用户注册（注册后待管理员审批）
- GET /api/v1/auth/me - 获取当前用户信息
- POST /api/v1/auth/logout - 退出登录
- GET /api/v1/auth/pending-users - 获取待审批用户列表（仅管理员）
- POST /api/v1/auth/{user_id}/approve - 审批通过用户（仅管理员）
- POST /api/v1/auth/{user_id}/reject - 拒绝用户注册（仅管理员）

使用 Bearer Token 机制进行会话管理，token 存储在内存字典中。
密码使用 bcrypt 进行哈希存储，兼容旧版 SHA256 哈希。
"""

import asyncio
import hashlib
import io
import logging
import random
import string
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.models.database import get_database

logger = logging.getLogger(__name__)

_login_attempts: dict = {}
_LOGIN_RATE_LIMIT = 5
_LOGIN_RATE_WINDOW = 300

_api_call_counts: dict = {}
_API_RATE_LIMIT = 60
_API_RATE_WINDOW = 60

router = APIRouter()


@router.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(_cleanup_expired_tokens())


security = HTTPBearer(auto_error=False)

_token_store: dict = {}
_token_expire_hours = 24

_captcha_store: dict = {}
_captcha_expire_seconds = 300


async def _cleanup_expired_tokens():
    while True:
        await asyncio.sleep(3600)
        now = datetime.now(timezone.utc)
        expired = [t for t, d in _token_store.items() if now > d.get("expires_at", now)]
        for t in expired:
            _token_store.pop(t, None)
        current_time = time.time()
        for username in list(_login_attempts.keys()):
            _login_attempts[username] = [
                at for at in _login_attempts[username]
                if current_time - at < _LOGIN_RATE_WINDOW
            ]
            if not _login_attempts[username]:
                del _login_attempts[username]
        for ip in list(_api_call_counts.keys()):
            _api_call_counts[ip] = [
                at for at in _api_call_counts[ip]
                if current_time - at < _API_RATE_WINDOW
            ]
            if not _api_call_counts[ip]:
                del _api_call_counts[ip]
        current_time = time.time()
        for cid in list(_captcha_store.keys()):
            if current_time - _captcha_store[cid]["created_at"] > _captcha_expire_seconds:
                del _captcha_store[cid]


def _check_login_rate_limit(username: str) -> None:
    now = time.time()
    if username not in _login_attempts:
        _login_attempts[username] = []
    _login_attempts[username] = [
        t for t in _login_attempts[username]
        if now - t < _LOGIN_RATE_WINDOW
    ]
    if len(_login_attempts[username]) >= _LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"登录尝试过于频繁，请{_LOGIN_RATE_WINDOW // 60}分钟后重试"
        )
    _login_attempts[username].append(now)


async def rate_limit_dependency(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    if client_ip not in _api_call_counts:
        _api_call_counts[client_ip] = []
    _api_call_counts[client_ip] = [
        t for t in _api_call_counts[client_ip]
        if now - t < _API_RATE_WINDOW
    ]
    if len(_api_call_counts[client_ip]) >= _API_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="请求过于频繁，请稍后重试"
        )
    _api_call_counts[client_ip].append(now)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=100, description="密码")
    captcha_id: str = Field(default="", description="验证码ID")
    captcha_code: str = Field(default="", description="验证码")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名（至少3个字符）")
    password: str = Field(..., min_length=6, max_length=100, description="密码（至少6个字符）")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=100, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码（至少6个字符）")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    legacy_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return legacy_hash == hashed_password


def _generate_token() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="未提供认证凭据")

    token = credentials.credentials
    token_data = _token_store.get(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="无效或已过期的Token")

    if datetime.now(timezone.utc) > token_data["expires_at"]:
        _token_store.pop(token, None)
        raise HTTPException(status_code=401, detail="Token已过期，请重新登录")

    db = get_database()
    user = db.get_user_by_id(token_data["user_id"])
    if user and "password_hash" in user:
        user = {k: v for k, v in user.items() if k != "password_hash"}
    if not user or not user.get("is_active"):
        _token_store.pop(token, None)
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    return user


async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return current_user


def _generate_captcha_image(code: str) -> str:
    from PIL import Image, ImageDraw, ImageFont

    width, height = 120, 40
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    for _ in range(6):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(200, 200, 200), width=1)

    for _ in range(30):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(180, 180, 180))

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except (IOError, OSError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except (IOError, OSError):
            font = ImageFont.load_default()

    colors = [
        (0, 0, 180), (180, 0, 0), (0, 130, 0),
        (130, 0, 130), (0, 130, 130), (180, 100, 0),
    ]
    char_width = width // (len(code) + 1)
    for i, ch in enumerate(code):
        color = random.choice(colors)
        x = char_width * i + random.randint(5, 12)
        y = random.randint(2, 8)
        draw.text((x, y), ch, fill=color, font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    import base64
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@router.get("/captcha", summary="获取验证码")
async def get_captcha():
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    captcha_id = uuid.uuid4().hex

    image_base64 = _generate_captcha_image(code)

    _captcha_store[captcha_id] = {
        "code": code,
        "created_at": time.time(),
    }

    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "captcha_id": captcha_id,
            "captcha_image": f"data:image/png;base64,{image_base64}",
        },
    }


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest):
    if not request.captcha_id or not request.captcha_code:
        raise HTTPException(status_code=400, detail="请输入验证码")

    captcha_data = _captcha_store.pop(request.captcha_id, None)
    if not captcha_data:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if time.time() - captcha_data["created_at"] > _captcha_expire_seconds:
        raise HTTPException(status_code=400, detail="验证码已过期，请重新获取")
    if captcha_data["code"].upper() != request.captcha_code.upper():
        raise HTTPException(status_code=400, detail="验证码错误")

    db = get_database()
    _check_login_rate_limit(request.username)

    user = db.get_user_by_username_all(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.get("is_active"):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user_status = user.get("status", "active")
    if user_status == "pending_approval":
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    elif user_status == "rejected":
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user["password_hash"].startswith("$2b$") and not user["password_hash"].startswith("$2a$"):
        new_hash = hash_password(request.password)
        db.update_user(user_id=user["id"], password_hash=new_hash)

    token = _generate_token()
    _token_store[token] = {
        "user_id": user["id"],
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=_token_expire_hours),
    }

    db.save_log(
        user_id=user["id"],
        action="用户登录",
        detail=f"username={request.username}",
    )

    logger.info(f"用户登录成功: {request.username}")

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "token": token,
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"],
        }
    }


@router.post("/register", summary="用户注册")
async def register(request: RegisterRequest):
    db = get_database()

    existing = db.get_user_by_username_all(request.username)
    if existing:
        raise HTTPException(status_code=400, detail=f"用户名 '{request.username}' 已存在")

    try:
        user_id = str(uuid.uuid4())
        password_hash = hash_password(request.password)

        db.create_user(
            user_id=user_id,
            username=request.username,
            password_hash=password_hash,
            role="user",
            status="pending_approval",
        )

        db.save_log(
            user_id=user_id,
            action="用户注册（待审批）",
            detail=f"username={request.username}",
        )

        logger.info(f"用户注册成功（待审批）: {request.username}")

        return {
            "code": 200,
            "message": "注册成功，请等待管理员审批",
            "data": {
                "user_id": user_id,
                "username": request.username,
            }
        }
    except Exception as e:
        logger.error(f"用户注册失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")


@router.put("/password", summary="修改密码")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    db = get_database()
    user = db.get_user_by_username_all(current_user["username"])
    if not user or not verify_password(request.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="旧密码不正确")
    new_hash = hash_password(request.new_password)
    db.update_user(user_id=current_user["id"], password_hash=new_hash)
    db.save_log(user_id=current_user["id"], action="修改密码", detail="")
    return {"code": 200, "message": "密码修改成功", "data": None}


@router.get("/me", summary="获取当前用户信息")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "user_id": current_user["id"],
            "username": current_user["username"],
            "role": current_user["role"],
            "created_at": current_user.get("created_at", ""),
        }
    }


@router.post("/logout", summary="退出登录")
async def logout(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    tokens_to_remove = [
        token for token, data in _token_store.items()
        if data.get("user_id") == user_id
    ]
    for token in tokens_to_remove:
        _token_store.pop(token, None)

    db = get_database()
    db.save_log(
        user_id=user_id,
        action="用户退出登录",
        detail="",
    )

    return {
        "code": 200,
        "message": "退出登录成功",
        "data": None
    }


@router.get("/pending-users", summary="获取待审批用户列表")
async def get_pending_users(admin: dict = Depends(require_admin)):
    db = get_database()
    result = db.list_users(page=1, page_size=100, status="pending_approval")

    users = []
    for user in result["users"]:
        users.append({
            "user_id": user["id"],
            "username": user["username"],
            "role": user.get("role", "user"),
            "created_at": user.get("created_at", ""),
            "status": user.get("status", "pending_approval"),
        })

    return {
        "code": 200,
        "message": "查询成功",
        "data": {
            "users": users,
            "total": result["total"],
        }
    }


@router.post("/{user_id}/approve", summary="审批通过用户")
async def approve_user(
    user_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_database()

    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail=f"用户当前状态为 '{user.get('status', '')}'，无法审批")

    db.update_user(user_id=user_id, status="active")

    db.save_log(
        user_id=admin["id"],
        action="审批通过用户",
        detail=f"approved_user_id={user_id}, username={user['username']}",
    )

    logger.info(f"用户审批通过: {user_id} ({user['username']})")

    return {
        "code": 200,
        "message": "用户审批通过",
        "data": {
            "user_id": user_id,
            "username": user["username"],
            "status": "active",
        }
    }


@router.post("/{user_id}/reject", summary="拒绝用户注册")
async def reject_user(
    user_id: str,
    admin: dict = Depends(require_admin),
):
    db = get_database()

    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail=f"用户当前状态为 '{user.get('status', '')}'，无法审批")

    db.update_user(user_id=user_id, status="rejected")

    db.save_log(
        user_id=admin["id"],
        action="拒绝用户注册",
        detail=f"rejected_user_id={user_id}, username={user['username']}",
    )

    logger.info(f"用户注册被拒绝: {user_id} ({user['username']})")

    return {
        "code": 200,
        "message": "已拒绝用户注册",
        "data": {
            "user_id": user_id,
            "username": user["username"],
            "status": "rejected",
        }
    }
