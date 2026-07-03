import os
import jwt
import base64
import hashlib
from datetime import datetime, timedelta
from passlib.context import CryptContext
from cryptography.fernet import Fernet

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "infinite-canvas-default-jwt-secret-key-328afc2a")
ALGORITHM = "HS256"

# AES encryption key derived from a secret
AES_SECRET_KEY = os.getenv("AES_SECRET_KEY", SECRET_KEY)
derived_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(AES_SECRET_KEY.encode()).digest())
cipher_suite = Fernet(derived_fernet_key)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """生成密码的加盐哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """生成 JWT 访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24) # 默认会话有效期 24 小时
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """解码并验证 JWT 访问令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def encrypt_data(data: str) -> str:
    """对称加密敏感数据 (如用户的 API Key)"""
    if not data:
        return ""
    try:
        return cipher_suite.encrypt(data.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""

def decrypt_data(encrypted_data: str) -> str:
    """解密敏感数据"""
    if not encrypted_data:
        return ""
    try:
        return cipher_suite.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""
