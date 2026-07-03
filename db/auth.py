from fastapi import Request, HTTPException, Depends, status
from sqlalchemy.orm import Session
from db.connection import get_db
from db.models import User
from db.auth_utils import decode_access_token

from db.context import current_user_id_var, real_user_id_var

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """获取当前请求的用户（可能是被模拟的目标用户）"""
    # 1. 从 Cookie 中获取 Token (首选)
    token = request.cookies.get("access_token")
    
    # 2. 从 Authorization 头部获取 Token (备用，支持 API/客户端调用)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录。"
        )
        
    # 3. 解密并校验 JWT Token
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录会话已过期或无效，请重新登录。"
        )
        
    user_id = payload["sub"]
    
    # 4. 从数据库中查询真实用户
    real_user = db.query(User).filter(User.id == user_id).first()
    if not real_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在。"
        )
        
    if not real_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该用户账户已被禁用。"
        )
    
    # 保存真实用户到 Request.state（同一请求内可靠传递给 get_current_admin）
    request.state.real_user = real_user
    # 同时保留 ContextVar 设置，供其他依赖链路使用
    real_user_id_var.set(real_user.id)
    
    # 5. 管理员"影子调试" (Impersonation) 逻辑
    # 只有当当前登录用户为 Admin 时，才允许通过特定的请求头或参数模拟另一个用户
    if real_user.is_admin:
        impersonate_id = request.headers.get("X-Impersonate-User-Id")
        if not impersonate_id:
            impersonate_id = request.query_params.get("impersonate_user_id")
            
        if impersonate_id:
            # 查询被模拟的用户
            target_user = db.query(User).filter(User.id == impersonate_id).first()
            if target_user and target_user.is_active:
                # 影子切换：之后所有的画布与生成操作都作用于目标用户
                current_user_id_var.set(target_user.id)
                return target_user
                
    current_user_id_var.set(real_user.id)
    return real_user

def get_current_admin(current_user: User = Depends(get_current_user), request: Request = None, db: Session = Depends(get_db)) -> User:
    """要求当前真实会话发起者必须具备管理员身份
    
    注意：即使管理员模拟了普通用户，也依然可以访问 admin 接口，
    因为这里校验的是真实用户（从 request.state.real_user 获取），
    而不是被模拟的目标用户。
    """
    # 优先从 Request.state 获取真实用户（同一请求内可靠传递）
    real_user = getattr(request.state, "real_user", None) if request else None
    
    # 回退：如果 Request.state 不可用，使用 ContextVar
    if not real_user:
        real_uid = real_user_id_var.get()
        if real_uid:
            real_user = db.query(User).filter(User.id == real_uid).first()
    
    if not real_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限。（无法获取真实用户信息）"
        )
    
    if not real_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足，需要管理员权限。用户 {real_user.username} 不是管理员。"
        )
    
    return real_user
