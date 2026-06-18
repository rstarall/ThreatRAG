"""
用户核心模块
提供用户注册、登录、认证等核心业务逻辑
"""

import re
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import bcrypt

from ...utils.postgres_manager import get_postgres_manager
from ...models.orm_models import User
from ...utils.logging_config import logger


class PasswordHasher:
    """密码哈希工具"""

    @staticmethod
    def hash_password(password: str) -> str:
        """对密码进行哈希"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False


class UserValidator:
    """用户数据验证器"""

    MIN_USERNAME_LENGTH = 3
    MAX_USERNAME_LENGTH = 32
    MIN_PASSWORD_LENGTH = 6
    MAX_PASSWORD_LENGTH = 128

    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]+$')

    @classmethod
    def validate_username(cls, username: str) -> tuple[bool, str]:
        if not username:
            return False, "用户名不能为空"
        if len(username) < cls.MIN_USERNAME_LENGTH:
            return False, f"用户名长度不能少于 {cls.MIN_USERNAME_LENGTH} 个字符"
        if len(username) > cls.MAX_USERNAME_LENGTH:
            return False, f"用户名长度不能超过 {cls.MAX_USERNAME_LENGTH} 个字符"
        if not cls.USERNAME_PATTERN.match(username):
            return False, "用户名只能包含字母、数字和下划线"
        return True, ""

    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, str]:
        if not password:
            return False, "密码不能为空"
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            return False, f"密码长度不能少于 {cls.MIN_PASSWORD_LENGTH} 个字符"
        if len(password) > cls.MAX_PASSWORD_LENGTH:
            return False, f"密码长度不能超过 {cls.MAX_PASSWORD_LENGTH} 个字符"
        return True, ""

    @classmethod
    def validate_email(cls, email: Optional[str]) -> tuple[bool, str]:
        if not email:
            return True, ""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            return False, "邮箱格式不正确"
        return True, ""


class UserRepository:
    """用户数据仓储层"""

    def __init__(self):
        self.pg_manager = get_postgres_manager()

    def create(self, username: str, password_hash: str, email: Optional[str] = None,
               display_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """创建用户"""
        user_id = f"u_{uuid.uuid4().hex[:12]}"
        try:
            with self.pg_manager.get_session() as session:
                user = User(
                    user_id=user_id,
                    username=username,
                    password_hash=password_hash,
                    email=email,
                    display_name=display_name or username,
                    is_active=True,
                    is_superuser=False
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                return user.to_dict()
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        try:
            with self.pg_manager.get_session() as session:
                user = session.query(User).filter(User.username == username).first()
                if user:
                    return user.to_dict(include_sensitive=True)
                return None
        except Exception as e:
            logger.error(f"Failed to get user by username: {e}")
            return None

    def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据 user_id 获取用户"""
        try:
            with self.pg_manager.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    return user.to_dict()
                return None
        except Exception as e:
            logger.error(f"Failed to get user by user_id: {e}")
            return None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱获取用户"""
        try:
            with self.pg_manager.get_session() as session:
                user = session.query(User).filter(User.email == email).first()
                if user:
                    return user.to_dict(include_sensitive=True)
                return None
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    def username_exists(self, username: str) -> bool:
        """检查用户名是否存在"""
        try:
            with self.pg_manager.get_session() as session:
                return session.query(User).filter(User.username == username).first() is not None
        except Exception as e:
            logger.error(f"Failed to check username existence: {e}")
            return False

    def email_exists(self, email: str) -> bool:
        """检查邮箱是否存在"""
        try:
            with self.pg_manager.get_session() as session:
                return session.query(User).filter(User.email == email).first() is not None
        except Exception as e:
            logger.error(f"Failed to check email existence: {e}")
            return False

    def update_last_login(self, user_id: str) -> bool:
        """更新最后登录时间"""
        try:
            with self.pg_manager.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.last_login_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            return False

    def update_password(self, user_id: str, new_password_hash: str) -> bool:
        """更新密码"""
        try:
            with self.pg_manager.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.password_hash = new_password_hash
                    user.updated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to update password: {e}")
            return False

    def deactivate(self, user_id: str) -> bool:
        """禁用用户"""
        try:
            with self.pg_manager.get_session() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if user:
                    user.is_active = False
                    user.updated_at = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to deactivate user: {e}")
            return False


class UserService:
    """用户服务层"""

    def __init__(self):
        self.repository = UserRepository()
        self.password_hasher = PasswordHasher()
        self.validator = UserValidator()

    def register(self, username: str, password: str, email: Optional[str] = None,
                 display_name: Optional[str] = None) -> Dict[str, Any]:
        """用户注册

        Args:
            username: 用户名
            password: 密码
            email: 邮箱
            display_name: 显示名称

        Returns:
            Dict[str, Any]: 结果
        """
        # 验证用户名
        valid, msg = self.validator.validate_username(username)
        if not valid:
            return {"success": False, "error": msg}

        # 检查用户名是否已存在
        if self.repository.username_exists(username):
            return {"success": False, "error": "用户名已存在"}

        # 验证密码
        valid, msg = self.validator.validate_password(password)
        if not valid:
            return {"success": False, "error": msg}

        # 验证邮箱
        if email:
            valid, msg = self.validator.validate_email(email)
            if not valid:
                return {"success": False, "error": msg}
            if self.repository.email_exists(email):
                return {"success": False, "error": "邮箱已被注册"}

        # 哈希密码
        password_hash = self.password_hasher.hash_password(password)

        # 创建用户
        user = self.repository.create(
            username=username,
            password_hash=password_hash,
            email=email,
            display_name=display_name
        )

        if user:
            logger.info(f"User registered: {username}")
            return {"success": True, "user": user}

        return {"success": False, "error": "注册失败，请稍后重试"}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            Dict[str, Any]: 结果
        """
        if not username or not password:
            return {"success": False, "error": "用户名和密码不能为空"}

        user = self.repository.get_by_username(username)

        if not user:
            return {"success": False, "error": "用户名或密码错误"}

        if not user.get("is_active", True):
            return {"success": False, "error": "账号已被禁用"}

        if not self.password_hasher.verify_password(password, user["password_hash"]):
            return {"success": False, "error": "用户名或密码错误"}

        # 更新最后登录时间
        self.repository.update_last_login(user["user_id"])

        # 返回用户信息（不含密码）
        user.pop("password_hash", None)
        logger.info(f"User logged in: {username}")

        return {"success": True, "user": user}

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取用户信息"""
        return self.repository.get_by_user_id(user_id)

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码"""
        # 验证新密码
        valid, msg = self.validator.validate_password(new_password)
        if not valid:
            return {"success": False, "error": msg}

        user = self.repository.get_by_user_id(user_id)
        if not user:
            return {"success": False, "error": "用户不存在"}

        # 验证旧密码
        if not self.password_hasher.verify_password(old_password, user["password_hash"]):
            return {"success": False, "error": "原密码不正确"}

        # 更新密码
        new_hash = self.password_hasher.hash_password(new_password)
        if self.repository.update_password(user_id, new_hash):
            logger.info(f"Password changed for user: {user_id}")
            return {"success": True}

        return {"success": False, "error": "密码修改失败"}


_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """获取用户服务实例"""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service


__all__ = [
    "UserService",
    "UserRepository",
    "PasswordHasher",
    "UserValidator",
    "get_user_service",
]
