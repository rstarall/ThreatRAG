"""
用户认证API路由
提供用户注册、登录等认证接口
"""

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, Dict, Any

from ...services.user_service import AuthService, get_auth_service


# 创建路由
user_router = APIRouter(prefix="/auth", tags=["auth"])

# 初始化认证服务
auth_service: Optional[AuthService] = None


def get_user_router() -> tuple[APIRouter, AuthService]:
    """获取用户路由和认证服务实例"""
    global auth_service
    if auth_service is None:
        auth_service = get_auth_service()
    return user_router, auth_service


@user_router.post("/register")
async def register(
    username: str = Body(..., description="用户名"),
    password: str = Body(..., description="密码"),
    email: Optional[str] = Body(None, description="邮箱"),
    display_name: Optional[str] = Body(None, description="显示名称")
):
    """用户注册

    Args:
        username: 用户名（3-32字符，只能包含字母、数字和下划线）
        password: 密码（至少6个字符）
        email: 邮箱（可选）
        display_name: 显示名称（可选，默认为用户名）

    Returns:
        注册结果，包含用户信息
    """
    try:
        result = auth_service.register(username, password, email, display_name)

        if not result.get("success"):
            return result

        # 注册成功后返回用户信息（不含密码）
        user = result.get("user", {})
        user.pop("password_hash", None)
        return {"success": True, "user": user}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@user_router.post("/login")
async def login(
    username: str = Body(..., description="用户名"),
    password: str = Body(..., description="密码")
):
    """用户登录

    Args:
        username: 用户名
        password: 密码

    Returns:
        登录结果，包含用户信息
    """
    try:
        result = auth_service.login(username, password)

        if not result.get("success"):
            return result

        user = result.get("user", {})
        user.pop("password_hash", None)
        return {"success": True, "user": user}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@user_router.get("/user/{user_id}")
async def get_user_info(user_id: str):
    """获取用户信息

    Args:
        user_id: 用户ID

    Returns:
        用户信息
    """
    try:
        result = auth_service.get_user_info(user_id)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "用户不存在"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")


@user_router.post("/change-password")
async def change_password(
    user_id: str = Body(..., description="用户ID"),
    old_password: str = Body(..., description="旧密码"),
    new_password: str = Body(..., description="新密码")
):
    """修改密码

    Args:
        user_id: 用户ID
        old_password: 旧密码
        new_password: 新密码（至少6个字符）

    Returns:
        修改结果
    """
    try:
        result = auth_service.change_password(user_id, old_password, new_password)

        if not result.get("success"):
            return result

        return {"success": True, "message": "密码修改成功"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"密码修改失败: {str(e)}")


@user_router.get("/validate/username")
async def validate_username(username: str = Query(..., description="用户名")):
    """验证用户名格式

    Args:
        username: 用户名

    Returns:
        验证结果
    """
    result = auth_service.validate_username(username)
    return result


@user_router.get("/validate/password")
async def validate_password(password: str = Query(..., description="密码")):
    """验证密码格式

    Args:
        password: 密码

    Returns:
        验证结果
    """
    result = auth_service.validate_password(password)
    return result


__all__ = ["user_router", "get_user_router"]
