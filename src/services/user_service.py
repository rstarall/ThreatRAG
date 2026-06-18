"""
用户服务层
封装用户核心业务逻辑，提供给 API 层调用
"""

from typing import Dict, Any, Optional

from ..core.user.user import (
    UserService,
    UserRepository,
    PasswordHasher,
    UserValidator,
    get_user_service,
)
from ..utils.logging_config import logger


class AuthService:
    """认证服务 - 提供用户注册和登录功能"""

    def __init__(self):
        self.user_service: UserService = get_user_service()

    def register(self, username: str, password: str, email: Optional[str] = None,
                 display_name: Optional[str] = None) -> Dict[str, Any]:
        """用户注册

        Args:
            username: 用户名
            password: 密码
            email: 邮箱（可选）
            display_name: 显示名称（可选）

        Returns:
            Dict[str, Any]: {"success": bool, "user"?: dict, "error"?: str}
        """
        try:
            return self.user_service.register(username, password, email, display_name)
        except Exception as e:
            logger.error(f"Register failed: {e}")
            return {"success": False, "error": f"注册失败: {e}"}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            Dict[str, Any]: {"success": bool, "user"?: dict, "error"?: str}
        """
        try:
            return self.user_service.login(username, password)
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return {"success": False, "error": f"登录失败: {e}"}

    def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Dict[str, Any]: {"success": bool, "user"?: dict, "error"?: str}
        """
        try:
            user = self.user_service.get_user_by_id(user_id)
            if user:
                user.pop("password_hash", None)
                return {"success": True, "user": user}
            return {"success": False, "error": "用户不存在"}
        except Exception as e:
            logger.error(f"Get user info failed: {e}")
            return {"success": False, "error": str(e)}

    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """修改密码

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            Dict[str, Any]: {"success": bool, "error"?: str}
        """
        try:
            return self.user_service.change_password(user_id, old_password, new_password)
        except Exception as e:
            logger.error(f"Change password failed: {e}")
            return {"success": False, "error": f"密码修改失败: {e}"}

    def validate_username(self, username: str) -> Dict[str, Any]:
        """验证用户名格式

        Args:
            username: 用户名

        Returns:
            Dict[str, Any]: {"valid": bool, "message"?: str}
        """
        valid, msg = UserValidator.validate_username(username)
        return {"valid": valid, "message": msg}

    def validate_password(self, password: str) -> Dict[str, Any]:
        """验证密码格式

        Args:
            password: 密码

        Returns:
            Dict[str, Any]: {"valid": bool, "message"?: str}
        """
        valid, msg = UserValidator.validate_password(password)
        return {"valid": valid, "message": msg}


_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """获取认证服务实例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


__all__ = [
    "AuthService",
    "UserService",
    "UserRepository",
    "PasswordHasher",
    "UserValidator",
    "get_auth_service",
    "get_user_service",
]
