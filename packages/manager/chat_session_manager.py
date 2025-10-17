"""
聊天会话管理器 - 整合 MySQL 主存储和 Redis 缓存
"""
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from packages.manager.db_model import ChatSession, ChatMessage, User
from packages.manager.db_manager import db_manager
from packages.utils.logging_config import logger


class ChatSessionManager:
    """聊天会话管理器 - MySQL作为主存储，Redis作为缓存"""

    def __init__(self, redis_manager=None):
        """初始化会话管理器
        
        Args:
            redis_manager: Redis会话管理器实例（可选）
        """
        self.redis_manager = redis_manager
        self.cache_expire_time = 3600  # Redis缓存1小时

    def _get_cache_key(self, session_id: str) -> str:
        """获取Redis缓存键"""
        return f"chat_session:{session_id}"

    async def create_session(
        self,
        user_id: int,
        title: str = None,
        system_prompt: str = None
    ) -> str:
        """创建新会话
        
        Args:
            user_id: 用户ID
            title: 会话标题（可选，最大50字符）
            system_prompt: 系统提示词（可选）
            
        Returns:
            新会话ID (UUID格式)
        """
        session_id = str(uuid.uuid4())
        
        try:
            with db_manager.get_session_context() as db_session:
                # 生成默认标题
                default_title = f"对话 {datetime.now().strftime('%m-%d %H:%M')}"
                
                # 确保标题不超过50字符
                if title:
                    title = title[:50] if len(title) > 50 else title
                else:
                    title = default_title
                
                # 创建会话记录
                new_session = ChatSession(
                    session_id=session_id,
                    user_id=user_id,
                    title=title,
                    system_prompt=system_prompt
                )
                db_session.add(new_session)
                db_session.flush()
                
                # 如果有系统提示词，添加为第一条消息
                if system_prompt:
                    system_msg = ChatMessage(
                        session_id=session_id,
                        role="system",
                        content=system_prompt
                    )
                    db_session.add(system_msg)
                
                db_session.commit()
                
                logger.info(f"创建新会话成功: session_id={session_id}, user_id={user_id}")
                
                # 缓存到Redis
                if self.redis_manager:
                    session_data = {
                        "session_id": session_id,
                        "user_id": user_id,
                        "title": new_session.title,
                        "system_prompt": system_prompt,
                        "history": [{"role": "system", "content": system_prompt}] if system_prompt else []
                    }
                    await self.redis_manager.set_session(session_id, session_data)
                
                return session_id
                
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            raise

    async def get_session(
        self,
        session_id: str,
        user_id: int = None,
        include_messages: bool = False
    ) -> Optional[Dict]:
        """获取会话信息（先从Redis查，再从MySQL查）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（可选，用于权限校验）
            include_messages: 是否包含消息列表
            
        Returns:
            会话信息字典或None
        """
        # 1. 先尝试从Redis获取
        if self.redis_manager and not include_messages:
            try:
                cached_session = await self.redis_manager.get_session(session_id)
                if cached_session:
                    # 校验用户权限
                    if user_id and cached_session.get("user_id") != user_id:
                        logger.warning(f"用户 {user_id} 无权访问会话 {session_id}")
                        return None
                    logger.debug(f"从Redis缓存获取会话: {session_id}")
                    return cached_session
            except Exception as e:
                logger.warning(f"从Redis获取会话失败: {e}")
        
        # 2. 从MySQL获取
        try:
            with db_manager.get_session_context() as db_session:
                query = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id,
                    ChatSession.is_deleted == 0
                )
                
                # 如果提供了user_id，添加权限过滤
                if user_id:
                    query = query.filter(ChatSession.user_id == user_id)
                
                session = query.first()
                
                if not session:
                    logger.warning(f"会话不存在或无权访问: {session_id}")
                    return None
                
                session_data = session.to_dict(include_messages=include_messages)
                
                logger.debug(f"从MySQL获取会话: {session_id}")
                
                # 缓存到Redis（不包含完整消息列表）
                if self.redis_manager and not include_messages:
                    await self.redis_manager.set_session(session_id, session_data)
                
                return session_data
                
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return None

    async def get_history(
        self,
        session_id: str,
        user_id: int = None,
        limit: int = None
    ) -> List[Dict]:
        """获取会话历史消息（先从Redis查，再从MySQL查）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（可选，用于权限校验）
            limit: 限制返回消息数量（可选）
            
        Returns:
            消息列表
        """
        # 1. 先尝试从Redis获取
        if self.redis_manager:
            try:
                cached_history = await self.redis_manager.get_history(session_id)
                if cached_history:
                    # 简单的权限校验：通过session获取user_id
                    session = await self.redis_manager.get_session(session_id)
                    if session and (not user_id or session.get("user_id") == user_id):
                        logger.debug(f"从Redis缓存获取历史: {session_id}, {len(cached_history)} 条消息")
                        if limit:
                            return cached_history[-limit:]
                        return cached_history
            except Exception as e:
                logger.warning(f"从Redis获取历史失败: {e}")
        
        # 2. 从MySQL获取
        try:
            with db_manager.get_session_context() as db_session:
                # 先验证会话权限
                session_query = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id,
                    ChatSession.is_deleted == 0
                )
                if user_id:
                    session_query = session_query.filter(ChatSession.user_id == user_id)
                
                session = session_query.first()
                if not session:
                    logger.warning(f"会话不存在或无权访问: {session_id}")
                    return []
                
                # 查询消息
                messages_query = db_session.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id,
                    ChatMessage.is_deleted == 0
                ).order_by(ChatMessage.created_at)
                
                if limit:
                    # 获取最近的N条消息
                    messages_query = messages_query.order_by(desc(ChatMessage.created_at)).limit(limit)
                    messages = list(reversed(messages_query.all()))
                else:
                    messages = messages_query.all()
                
                history = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat() if msg.created_at else None
                    }
                    for msg in messages
                ]
                
                logger.debug(f"从MySQL获取历史: {session_id}, {len(history)} 条消息")
                
                # 缓存到Redis
                if self.redis_manager:
                    session_data = {
                        "session_id": session_id,
                        "user_id": session.user_id,
                        "title": session.title,
                        "system_prompt": session.system_prompt,
                        "history": history
                    }
                    await self.redis_manager.set_session(session_id, session_data)
                
                return history
                
        except Exception as e:
            logger.error(f"获取历史消息失败: {e}")
            return []

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: int = None,
        meta: Dict = None
    ) -> bool:
        """添加消息到会话（同时写入MySQL和Redis）
        
        Args:
            session_id: 会话ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            user_id: 用户ID（可选，用于权限校验）
            meta: 额外元数据（可选）
            
        Returns:
            是否成功
        """
        try:
            # 1. 写入MySQL
            with db_manager.get_session_context() as db_session:
                # 验证会话权限
                session_query = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id,
                    ChatSession.is_deleted == 0
                )
                if user_id:
                    session_query = session_query.filter(ChatSession.user_id == user_id)
                
                session = session_query.first()
                if not session:
                    logger.warning(f"会话不存在或无权访问: {session_id}")
                    return False
                
                # 创建消息
                new_message = ChatMessage(
                    session_id=session_id,
                    role=role,
                    content=content,
                    meta=json.dumps(meta) if meta else None
                )
                db_session.add(new_message)
                
                # 更新会话的updated_at
                session.updated_at = datetime.now()
                
                db_session.commit()
                
                logger.debug(f"添加消息到MySQL: session={session_id}, role={role}")
            
            # 2. 更新Redis缓存
            if self.redis_manager:
                try:
                    await self.redis_manager.add_message(session_id, role, content)
                    logger.debug(f"添加消息到Redis缓存: session={session_id}, role={role}")
                except Exception as e:
                    logger.warning(f"更新Redis缓存失败: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"添加消息失败: {e}")
            return False

    async def update_session(
        self,
        session_id: str,
        user_id: int,
        title: str = None,
        system_prompt: str = None
    ) -> bool:
        """更新会话信息
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            title: 新标题（可选，最大50字符）
            system_prompt: 新系统提示词（可选）
            
        Returns:
            是否成功
        """
        try:
            with db_manager.get_session_context() as db_session:
                session = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id,
                    ChatSession.user_id == user_id,
                    ChatSession.is_deleted == 0
                ).first()
                
                if not session:
                    logger.warning(f"会话不存在或无权访问: {session_id}")
                    return False
                
                if title is not None:
                    # 确保标题不超过50字符
                    session.title = title[:50] if len(title) > 50 else title
                if system_prompt is not None:
                    session.system_prompt = system_prompt
                
                session.updated_at = datetime.now()
                db_session.commit()
                
                logger.info(f"更新会话成功: {session_id}")
                
                # 清除Redis缓存，下次访问时重新加载
                if self.redis_manager:
                    try:
                        await self.redis_manager.delete_session(session_id)
                    except Exception as e:
                        logger.warning(f"清除Redis缓存失败: {e}")
                
                return True
                
        except Exception as e:
            logger.error(f"更新会话失败: {e}")
            return False

    async def delete_session(
        self,
        session_id: str,
        user_id: int,
        hard_delete: bool = False
    ) -> bool:
        """删除会话（软删除或硬删除）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            hard_delete: 是否硬删除（默认软删除）
            
        Returns:
            是否成功
        """
        try:
            with db_manager.get_session_context() as db_session:
                session = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                
                if not session:
                    logger.warning(f"会话不存在或无权访问: {session_id}")
                    return False
                
                if hard_delete:
                    # 硬删除：物理删除记录
                    db_session.delete(session)
                    logger.info(f"硬删除会话: {session_id}")
                else:
                    # 软删除：标记为已删除
                    session.is_deleted = 1
                    session.updated_at = datetime.now()
                    logger.info(f"软删除会话: {session_id}")
                
                db_session.commit()
                
                # 删除Redis缓存
                if self.redis_manager:
                    try:
                        await self.redis_manager.delete_session(session_id)
                        logger.debug(f"删除Redis缓存: {session_id}")
                    except Exception as e:
                        logger.warning(f"删除Redis缓存失败: {e}")
                
                return True
                
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False

    async def list_user_sessions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Dict]:
        """获取用户的所有会话列表
        
        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量
            include_deleted: 是否包含已删除的会话
            
        Returns:
            会话列表
        """
        try:
            with db_manager.get_session_context() as db_session:
                query = db_session.query(ChatSession).filter(
                    ChatSession.user_id == user_id
                )
                
                if not include_deleted:
                    query = query.filter(ChatSession.is_deleted == 0)
                
                sessions = query.order_by(
                    desc(ChatSession.updated_at)
                ).limit(limit).offset(offset).all()
                
                result = [session.to_dict(include_messages=False) for session in sessions]
                
                logger.debug(f"获取用户 {user_id} 的会话列表: {len(result)} 个")
                
                return result
                
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {e}")
            return []

    async def delete_message(
        self,
        message_id: int,
        session_id: str,
        user_id: int
    ) -> bool:
        """删除单条消息（软删除）
        
        Args:
            message_id: 消息ID
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            是否成功
        """
        try:
            with db_manager.get_session_context() as db_session:
                # 验证权限
                session = db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id,
                    ChatSession.user_id == user_id,
                    ChatSession.is_deleted == 0
                ).first()
                
                if not session:
                    logger.warning(f"会话不存在或无权访问: {session_id}")
                    return False
                
                # 删除消息
                message = db_session.query(ChatMessage).filter(
                    ChatMessage.id == message_id,
                    ChatMessage.session_id == session_id
                ).first()
                
                if not message:
                    logger.warning(f"消息不存在: {message_id}")
                    return False
                
                message.is_deleted = 1
                session.updated_at = datetime.now()
                
                db_session.commit()
                
                logger.info(f"删除消息: message_id={message_id}")
                
                # 清除Redis缓存
                if self.redis_manager:
                    try:
                        await self.redis_manager.delete_session(session_id)
                    except Exception as e:
                        logger.warning(f"清除Redis缓存失败: {e}")
                
                return True
                
        except Exception as e:
            logger.error(f"删除消息失败: {e}")
            return False


# 创建全局会话管理器实例（在API中初始化时注入Redis管理器）
chat_session_manager = None


def get_chat_session_manager(redis_manager=None):
    """获取会话管理器实例（单例模式）"""
    global chat_session_manager
    if chat_session_manager is None:
        chat_session_manager = ChatSessionManager(redis_manager=redis_manager)
    return chat_session_manager

