from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List

from db.connection import get_db
from db.models import User, SystemConfig
from db.auth import get_current_admin
from db.auth_utils import get_password_hash

admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

class UserItem(BaseModel):
    id: str
    username: str
    display_name: str
    is_admin: bool
    is_active: bool
    created_at: str

class PasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=4, max_length=50)

class StatusChangeRequest(BaseModel):
    is_active: bool

class RetentionRequest(BaseModel):
    days: int = Field(..., ge=0)

@admin_router.get("/users", response_model=List[UserItem])
def get_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserItem(
            id=u.id,
            username=u.username,
            display_name=u.display_name or u.username,
            is_admin=u.is_admin,
            is_active=u.is_active,
            created_at=u.created_at.isoformat()
        )
        for u in users
    ]

@admin_router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, req: PasswordResetRequest, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="未找到该用户。")
        
    user.password_hash = get_password_hash(req.new_password)
    db.commit()
    return {"success": True, "message": "密码修改成功！"}

@admin_router.patch("/users/{user_id}/status")
def change_status(user_id: str, req: StatusChangeRequest, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    # 防止管理员将自己禁用
    # 我们应该获取真实的管理员用户来判断。
    # 这里 current_admin 已经是依赖注入验证过的管理员
    if user_id == current_admin.id:
        raise HTTPException(status_code=400, detail="您不能禁用自己的账户。")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="未找到该用户。")
        
    user.is_active = req.is_active
    db.commit()
    return {"success": True, "message": "账户状态更新成功。"}

@admin_router.get("/config/retention")
def get_retention(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    conf = db.query(SystemConfig).filter(SystemConfig.key == "data_retention_days").first()
    days = int(conf.value) if conf else 0
    return {"success": True, "days": days}

@admin_router.post("/config/retention")
def update_retention(req: RetentionRequest, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    conf = db.query(SystemConfig).filter(SystemConfig.key == "data_retention_days").first()
    if not conf:
        conf = SystemConfig(key="data_retention_days", value=str(req.days))
        db.add(conf)
    else:
        conf.value = str(req.days)
    db.commit()
    return {"success": True, "message": f"数据保存时限已更新为 {req.days} 天。"}
