import redis.asyncio as redis
import json
import asyncio
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta

class RedisSessionManager:
    """Redis会话管理器，用于异步缓存会话信息"""

    def __init__(self, redis_url: str = "redis://localhost:6379", expire_time: int = 3600):
        """初始化Redis会话管理器

        Args:
            redis_url: Redis连接URL
            expire_time: 会话过期时间(秒)
        """
        self.redis_url = redis_url
        self.expire_time = expire_time
        self.redis = None
        self._connection_lock = asyncio.Lock()

    async def _get_redis(self):
        """获取Redis连接"""
        if self.redis is None:
            async with self._connection_lock:
                if self.redis is None:
                    self.redis = redis.from_url(self.redis_url, decode_responses=True)
        return self.redis

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典或None
        """
        redis = await self._get_redis()
        data = await redis.get(f"session:{session_id}")
        if data:
            # 更新过期时间
            await redis.expire(f"session:{session_id}", self.expire_time)
            return json.loads(data)
        return None

    async def set_session(self, session_id: str, data: Dict) -> bool:
        """设置会话信息

        Args:
            session_id: 会话ID
            data: 会话数据

        Returns:
            是否成功
        """
        redis = await self._get_redis()
        await redis.set(
            f"session:{session_id}",
            json.dumps(data),
            ex=self.expire_time
        )
        return True

    async def get_history(self, session_id: str) -> List[Dict]:
        """获取会话历史记录

        Args:
            session_id: 会话ID

        Returns:
            会话历史记录列表
        """
        session = await self.get_session(session_id)
        if session and "history" in session:
            return session["history"]
        return []

    async def add_message(self, session_id: str, role: str, content: str) -> List[Dict]:
        """添加消息到会话历史

        Args:
            session_id: 会话ID
            role: 角色(user/assistant/system)
            content: 消息内容

        Returns:
            更新后的历史记录
        """
        session = await self.get_session(session_id) or {"history": []}

        if "history" not in session:
            session["history"] = []

        # 添加消息
        session["history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # 更新会话
        await self.set_session(session_id, session)
        return session["history"]

    async def create_session(self, system_prompt: str = None) -> str:
        """创建新会话

        Args:
            system_prompt: 系统提示词

        Returns:
            新会话ID
        """
        session_id = str(uuid.uuid4())
        session = {"history": []}

        # 如果有系统提示词，添加到历史记录
        if system_prompt:
            session["history"].append({
                "role": "system",
                "content": system_prompt,
                "timestamp": datetime.now().isoformat()
            })

        await self.set_session(session_id, session)
        return session_id

    async def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        redis = await self._get_redis()
        result = await redis.delete(f"session:{session_id}")
        return result > 0

    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()