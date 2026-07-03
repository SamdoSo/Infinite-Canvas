import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from typing import Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import User
from db.auth_utils import get_password_hash, verify_password, create_access_token
from db.auth import get_current_user
from db.context import real_user_id_var

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4, max_length=50)
    display_name: Optional[str] = Field(None, max_length=50)

class UserLoginRequest(BaseModel):
    username: str = Field(...)
    password: str = Field(...)
    remember_me: bool = Field(False)

class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    is_admin: bool
    is_active: bool
    is_impersonated: bool = False
    real_user_id: Optional[str] = None
    real_user_name: Optional[str] = None

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """用户注册：第一个注册的用户自动成为管理员"""
    # 检查用户名是否重复
    existing_user = db.query(User).filter(User.username == req.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在，请尝试其他名称。"
        )

    # 如果是系统的第一个用户，则默认设置为管理员
    is_first_user = db.query(User).count() == 0

    password_hash = get_password_hash(req.password)
    user_id = uuid.uuid4().hex
    display_name = req.display_name or req.username

    new_user = User(
        id=user_id,
        username=req.username,
        password_hash=password_hash,
        display_name=display_name,
        is_admin=is_first_user,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "success": True,
        "message": "注册成功！" + (" (您已成为系统管理员)" if is_first_user else ""),
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "display_name": new_user.display_name,
            "is_admin": new_user.is_admin
        }
    }

@auth_router.post("/login")
def login(req: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    """用户登录：验证凭据并写入 HttpOnly Cookie"""
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确。"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账户已被禁用，请联系管理员。"
        )

    # 设置 Token 过期时间 (记住我 -> 7天，否则 -> 24小时)
    expires_delta = timedelta(days=7) if req.remember_me else timedelta(hours=24)
    token = create_access_token(data={"sub": user.id}, expires_delta=expires_delta)

    # 写入 Secure HttpOnly Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=int(expires_delta.total_seconds()),
        samesite="lax",
        secure=False # 本地调试默认不强制 HTTPS，生产环境建议开启
    )

    return {
        "success": True,
        "message": "登录成功！",
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
            "is_active": user.is_active
        }
    }

@auth_router.post("/logout")
def logout(response: Response):
    """用户登出：清除 Cookie"""
    response.delete_cookie("access_token")
    return {"success": True, "message": "已成功登出。"}

@auth_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户信息
    
    如果管理员处于幽灵登录（impersonation）状态，会返回：
    - is_impersonated: true
    - real_user_id: 真实管理员的 ID
    - real_user_name: 真实管理员的用户名
    """
    real_uid = real_user_id_var.get()
    is_impersonated = bool(real_uid and real_uid != current_user.id)
    real_user = None
    if is_impersonated:
        real_user = db.query(User).filter(User.id == real_uid).first()
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name or current_user.username,
        is_admin=current_user.is_admin,
        is_active=current_user.is_active,
        is_impersonated=is_impersonated,
        real_user_id=real_user.id if real_user else None,
        real_user_name=real_user.username if real_user else None
    )
