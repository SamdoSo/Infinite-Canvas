import contextvars

# 存储当前请求中的用户 ID 上下文（可能是被模拟的目标用户）
current_user_id_var = contextvars.ContextVar("current_user_id", default=None)

# 存储当前请求的真实用户 ID（即原始登录用户，不受 impersonation 影响）
real_user_id_var = contextvars.ContextVar("real_user_id", default=None)
