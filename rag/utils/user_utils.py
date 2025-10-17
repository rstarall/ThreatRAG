"""
用户ID生成工具
提供用户名验证和user_id自动生成功能
"""

import re
import uuid

from pypinyin import lazy_pinyin, Style


def to_pinyin(text: str) -> str:
    """
    将中文转换为拼音
    使用pypinyin库进行转换
    """
    # 使用pypinyin进行转换
    pinyin_list = lazy_pinyin(text, style=Style.NORMAL)
    return "".join(pinyin_list)


def validate_username(username: str) -> tuple[bool, str]:
    """
    验证用户名格式

    Args:
        username: 用户名

    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    if not username:
        return False, "用户名不能为空"

    if len(username) < 2:
        return False, "用户名长度不能少于2个字符"

    if len(username) > 20:
        return False, "用户名长度不能超过20个字符"

    # 检查是否包含不允许的字符
    # 允许中文、英文、数字、下划线
    if not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9_]+$", username):
        return False, "用户名只能包含中文、英文、数字和下划线"

    return True, ""


def generate_user_id(username: str) -> str:
    """
    根据用户名生成user_id，添加前缀确保与用户名不同
    """
    # 1. 基本清理
    username = username.strip()
    
    # 2. 添加前缀
    prefix = "uid_"  # 添加前缀，确保与用户名不同
    
    # 3. 转换为拼音（如果包含中文）
    user_id = prefix + to_pinyin(username)
    
    # 4. 处理特殊字符，只保留字母、数字和下划线
    user_id = re.sub(r"[^a-zA-Z0-9_]", "", user_id)
    
    # 5. 确保不以数字开头
    if user_id and user_id[0].isdigit():
        user_id = "u" + user_id
    
    # 6. 如果为空或太短，使用默认前缀
    if len(user_id) < 2:
        user_id = "user" + str(hash(username) % 10000).zfill(4)
    
    # 7. 长度限制
    if len(user_id) > 20:
        user_id = user_id[:20]
    
    return user_id.lower()


def is_valid_phone_number(phone: str) -> bool:
    """
    验证手机号格式（支持中国大陆手机号）

    Args:
        phone: 手机号字符串

    Returns:
        bool: 是否为有效手机号
    """
    if not phone:
        return False

    # 移除空格和特殊字符
    phone = re.sub(r"[\s\-\(\)]", "", phone)

    # 中国大陆手机号格式：1开头，第二位是3-9，总共11位
    pattern = r"^1[3-9]\d{9}$"

    return bool(re.match(pattern, phone))


def normalize_phone_number(phone: str) -> str:
    """
    标准化手机号格式

    Args:
        phone: 原始手机号

    Returns:
        str: 标准化后的手机号
    """
    if not phone:
        return ""

    # 移除所有非数字字符
    phone = re.sub(r"\D", "", phone)

    # 如果是中国大陆手机号，确保格式正确
    if len(phone) == 11 and phone.startswith("1"):
        return phone

    return phone


def generate_int_user_id(db) -> int:
    """
    使用UUID生成10位随机整数作为用户ID
    
    Args:
        db: 数据库会话，用于检查ID是否已存在
        
    Returns:
        int: 10位整数用户ID
    """
    from sqlalchemy import text
    
    while True:
        # 使用UUID生成随机数，取其整数值的后10位
        random_int = abs(uuid.uuid4().int) % 9000000000 + 1000000000
        
        # 确保生成的ID是10位数
        user_id = random_int
        
        # 检查是否已存在
        result = db.execute(text("SELECT COUNT(*) FROM users WHERE user_id = :user_id"), 
                           {"user_id": str(user_id)}).scalar()
        
        # 如果不存在，返回这个ID
        if result == 0:
            return user_id