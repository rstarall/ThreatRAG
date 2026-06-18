"""
会话管理器
整合rag/cache/redis_session.py的会话管理功能
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ...utils.logging_config import logger


class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        """初始化会话管理器"""
        self.redis_client = None
        self.expire_time = int(os.getenv("SESSION_EXPIRE_TIME", "3600"))  # 默认1小时
        
        # 尝试初始化Redis
        self._init_redis()
        
        # 如果Redis不可用，使用内存存储
        if not self.redis_client:
            self.memory_sessions = {}
            logger.warning("Using memory-based session storage")
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            import redis
            from urllib.parse import urlparse
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            
            # 正确解析 Redis URL (支持 redis://host:port 或 redis://user:password@host:port)
            if redis_url.startswith("redis://"):
                parsed = urlparse(redis_url)
                host = parsed.hostname or "localhost"
                port = parsed.port or 6379
                password = parsed.password
                db = int(parsed.path.lstrip('/') or 0) if parsed.path else 0
            else:
                host = "localhost"
                port = 6379
                password = None
                db = 0
            
            # 创建Redis客户端
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis connected at {host}:{port}")
            
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}")
            self.redis_client = None
    
    async def create_session(self, session_id: Optional[str] = None,
                           user_id: Optional[str] = None,
                           system_prompt: Optional[str] = None) -> str:
        """创建新会话

        Args:
            session_id: 会话ID（可选，不传则自动生成）
            user_id: 用户ID（可选）
            system_prompt: 系统提示

        Returns:
            str: 会话ID
        """
        import uuid
        session_id = session_id or str(uuid.uuid4())

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "title": "新对话",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "system_prompt": system_prompt
        }

        if self.redis_client:
            try:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"session:{session_id}",
                    self.expire_time,
                    json.dumps(session_data, ensure_ascii=False)
                )
                logger.debug(f"Created session {session_id} for user {user_id} in Redis")
            except Exception as e:
                logger.error(f"Failed to create session in Redis: {e}")
                return None
        else:
            self.memory_sessions[session_id] = session_data
            logger.debug(f"Created session {session_id} for user {user_id} in memory")

        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 会话信息
        """
        if self.redis_client:
            try:
                session_data = await asyncio.to_thread(
                    self.redis_client.get,
                    f"session:{session_id}"
                )
                
                if session_data:
                    return json.loads(session_data)
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to get session from Redis: {e}")
                return None
        else:
            # 从内存获取
            return self.memory_sessions.get(session_id)
    
    async def get_session_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取会话历史消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict[str, str]]: 历史消息列表
        """
        session = await self.get_session(session_id)
        
        if session:
            return session.get("messages", [])
        else:
            return []
    
    async def add_message(self, session_id: str, role: str, content: str,
                          user_id: Optional[str] = None) -> bool:
        """添加消息到会话

        Args:
            session_id: 会话ID
            role: 角色 (user/assistant)
            content: 消息内容
            user_id: 用户ID（创建会话时使用）

        Returns:
            bool: 是否成功
        """
        session = await self.get_session(session_id)

        if not session:
            # 如果会话不存在，创建一个（带上 session_id 和 user_id）
            new_session_id = await self.create_session(
                session_id=session_id,
                user_id=user_id
            )
            if not new_session_id:
                return False
            session = await self.get_session(new_session_id)
            if not session:
                return False
            session_id = new_session_id
        
        # 添加新消息
        new_message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        session["messages"].append(new_message)
        session["updated_at"] = datetime.now().isoformat()
        
        # 保存会话
        return await self._save_session(session_id, session)
    
    async def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题
        
        Args:
            session_id: 会话ID
            title: 新标题
            
        Returns:
            bool: 是否成功
        """
        session = await self.get_session(session_id)
        
        if not session:
            return False
        
        session["title"] = title
        session["updated_at"] = datetime.now().isoformat()
        
        return await self._save_session(session_id, session)
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功
        """
        if self.redis_client:
            try:
                result = await asyncio.to_thread(
                    self.redis_client.delete,
                    f"session:{session_id}"
                )
                
                return result > 0
                
            except Exception as e:
                logger.error(f"Failed to delete session from Redis: {e}")
                return False
        else:
            # 从内存删除
            if session_id in self.memory_sessions:
                del self.memory_sessions[session_id]
                return True
            else:
                return False
    
    async def list_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """列出会话

        Args:
            user_id: 用户ID（可选，用于过滤该用户的会话）
            limit: 结果限制

        Returns:
            List[Dict[str, Any]]: 会话列表
        """
        sessions = []

        if self.redis_client:
            try:
                session_keys = await asyncio.to_thread(
                    self.redis_client.keys,
                    "session:*"
                )

                for key in session_keys[:limit]:
                    session_data = await asyncio.to_thread(
                        self.redis_client.get,
                        key
                    )

                    if session_data:
                        session = json.loads(session_data)
                        # 按 user_id 过滤（user_id 为 None 时不过滤）
                        if user_id is not None and session.get("user_id") != user_id:
                            continue
                        sessions.append({
                            "session_id": session["session_id"],
                            "user_id": session.get("user_id"),
                            "title": session["title"],
                            "created_at": session["created_at"],
                            "updated_at": session["updated_at"],
                            "message_count": len(session.get("messages", []))
                        })
                        
            except Exception as e:
                logger.error(f"Failed to list sessions from Redis: {e}")
        else:
            # 从内存获取
            for session_id, session in list(self.memory_sessions.items())[:limit]:
                if user_id is not None and session.get("user_id") != user_id:
                    continue
                sessions.append({
                    "session_id": session_id,
                    "user_id": session.get("user_id"),
                    "title": session["title"],
                    "created_at": session["created_at"],
                    "updated_at": session["updated_at"],
                    "message_count": len(session.get("messages", []))
                })
        
        # 按更新时间排序
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return sessions
    
    async def clean_expired_sessions(self):
        """清理过期会话（仅内存存储需要）"""
        if self.redis_client:
            return  # Redis自动过期
        
        current_time = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.memory_sessions.items():
            try:
                updated_at = datetime.fromisoformat(session["updated_at"])
                if current_time - updated_at > timedelta(seconds=self.expire_time):
                    expired_sessions.append(session_id)
            except Exception:
                # 如果时间解析失败，也认为是过期的
                expired_sessions.append(session_id)
        
        # 删除过期会话
        for session_id in expired_sessions:
            del self.memory_sessions[session_id]
            logger.debug(f"Cleaned expired session: {session_id}")
        
        if expired_sessions:
            logger.info(f"Cleaned {len(expired_sessions)} expired sessions")
    
    async def _save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """保存会话数据
        
        Args:
            session_id: 会话ID
            session_data: 会话数据
            
        Returns:
            bool: 是否成功
        """
        if self.redis_client:
            try:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"session:{session_id}",
                    self.expire_time,
                    json.dumps(session_data, ensure_ascii=False)
                )
                return True
                
            except Exception as e:
                logger.error(f"Failed to save session to Redis: {e}")
                return False
        else:
            # 保存到内存
            self.memory_sessions[session_id] = session_data
            return True
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if self.redis_client:
            try:
                session_count = await asyncio.to_thread(
                    self.redis_client.dbsize
                )
                
                return {
                    "total_sessions": session_count,
                    "storage_type": "redis",
                    "expire_time": self.expire_time
                }
                
            except Exception as e:
                logger.error(f"Failed to get session stats from Redis: {e}")
                return {"error": str(e)}
        else:
            return {
                "total_sessions": len(self.memory_sessions),
                "storage_type": "memory",
                "expire_time": self.expire_time
            }


__all__ = ["SessionManager"]
