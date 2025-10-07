import hashlib
# rag/utils/auth_utils.py
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from jose import jwt
from passlib.context import CryptContext


class AuthUtils:
    # 密码哈希工具
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    # JWT配置
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "br-chat-aision")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

    @classmethod
    def verify_password(cls, stored_password, plain_password):
        """验证密码"""
        # 如果存储的密码已经是哈希值，则使用哈希验证
        if (stored_password.startswith("$2b$") or
            stored_password.startswith("$2a$") or
                stored_password.startswith("$pbkdf2-sha256$")):  # 修正这里的前缀检查
            return cls.pwd_context.verify(plain_password, stored_password)
        # 如果是明文密码（不推荐），则直接比较
        return stored_password == plain_password

    @classmethod
    def hash_password(cls, password):
        """哈希密码"""
        # 调试信息
        print(f"密码长度: {len(password)} 字符, {len(password.encode('utf-8'))} 字节")

        # 确保密码不超过72字节
        password_bytes = password.encode(
            'utf-8') if isinstance(password, str) else password
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
            password = password_bytes.decode(
                'utf-8') if isinstance(password, bytes) else password[:72]

        return cls.pwd_context.hash(password)

    @classmethod
    def create_access_token(cls, data: Dict):
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def decode_token(cls, token: str):
        """解码令牌"""
        try:
            payload = jwt.decode(token, cls.SECRET_KEY,
                                 algorithms=[cls.ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None

    @staticmethod
    def verify_access_token(token: str) -> dict[str, Any]:
        """验证访问令牌，如果无效则抛出异常"""
        try:
            # 修复这里，使用AuthUtils的类变量
            payload = jwt.decode(token, AuthUtils.SECRET_KEY,
                                 algorithms=[AuthUtils.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("令牌已过期")
        except jwt.InvalidTokenError:
            raise ValueError("无效的令牌")
