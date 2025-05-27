import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Redis配置
REDIS_CONFIG = {
    "url": os.getenv("REDIS_URL", "redis://localhost:6379"),
    "db": int(os.getenv("REDIS_DB", "0")),
    "password": os.getenv("REDIS_PASSWORD", None),
    "socket_timeout": float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0")),
    "socket_connect_timeout": float(os.getenv("REDIS_CONNECT_TIMEOUT", "5.0")),
    "retry_on_timeout": os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true",
    "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
}

# 会话配置
SESSION_CONFIG = {
    "expire_time": int(os.getenv("SESSION_EXPIRE_TIME", "3600")),  # 会话过期时间(秒)
    "max_history_length": int(os.getenv("MAX_HISTORY_LENGTH", "50")),  # 最大历史记录长度
}

# 协程池配置
COROUTINE_POOL_CONFIG = {
    "max_workers": int(os.getenv("MAX_CONCURRENT_CHATS", "20")),  # 最大并发聊天数
}