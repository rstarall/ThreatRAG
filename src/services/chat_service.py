"""
聊天业务服务
整合ChatEngine的高层业务逻辑
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
import traceback

from ..core.chat.chat_engine import ChatEngine
from ..utils.logging_config import logger


class ChatService:
    """聊天业务服务类"""

    def __init__(self):
        """初始化聊天服务"""
        self.chat_engine = ChatEngine()

    async def chat_stream(self, query: str,
                                 meta: Optional[Dict[str, Any]] = None,
                                 history: Optional[List[Dict[str, str]]] = None,
                                 session_id: Optional[str] = None,
                                 user_id: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        """处理流式聊天请求

        Args:
            query: 用户查询文本
            meta: 请求元数据
            history: 对话历史
            session_id: 会话ID
            user_id: 用户ID（用于会话归属）
        """
        try:
            async for chunk in self.chat_engine.process_chat_stream(
                query=query,
                meta=meta,
                history=history,
                session_id=session_id,
                user_id=user_id
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Chat stream processing failed: {e}\n{traceback.format_exc()}")
            error_chunk = self.chat_engine._make_chunk(
                message=f"聊天处理失败: {e}",
                status="error",
                meta=meta or {},
                session_id=session_id
            )
            yield error_chunk

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 会话信息
        """
        try:
            session = await self.chat_engine.session_manager.get_session(session_id)

            if session:
                return {"status": "success", "session": session}
            else:
                return {"status": "failed", "message": "会话不存在", "code": 404}

        except Exception as e:
            logger.error(f"Get session failed: {e}")
            return {"status": "failed", "message": str(e)}

    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """删除会话

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 删除结果
        """
        try:
            success = await self.chat_engine.session_manager.delete_session(session_id)

            if success:
                return {"status": "success", "message": "会话删除成功"}
            else:
                return {"status": "failed", "message": "会话不存在或删除失败", "code": 404}

        except Exception as e:
            logger.error(f"Delete session failed: {e}")
            return {"status": "failed", "message": str(e)}

    async def list_sessions(self, user_id: Optional[str] = None,
                           limit: int = 50) -> Dict[str, Any]:
        """获取会话列表

        Args:
            user_id: 用户ID（可选，用于过滤该用户的会话）
            limit: 结果限制

        Returns:
            Dict[str, Any]: 会话列表
        """
        try:
            sessions = await self.chat_engine.session_manager.list_sessions(
                user_id=user_id, limit=limit
            )
            return {"status": "success", "sessions": sessions}

        except Exception as e:
            logger.error(f"List sessions failed: {e}")
            return {"status": "failed", "message": str(e)}

    async def update_session_title(self, session_id: str, title: str) -> Dict[str, Any]:
        """更新会话标题

        Args:
            session_id: 会话ID
            title: 新标题

        Returns:
            Dict[str, Any]: 更新结果
        """
        try:
            success = await self.chat_engine.session_manager.update_session_title(session_id, title)

            if success:
                return {"status": "success", "message": "标题更新成功"}
            else:
                return {"status": "failed", "message": "会话不存在或更新失败"}

        except Exception as e:
            logger.error(f"Update session title failed: {e}")
            return {"status": "failed", "message": str(e)}

    def get_chat_models(self, model_provider: str) -> Dict[str, Any]:
        """获取聊天模型列表

        Args:
            model_provider: 模型提供商

        Returns:
            Dict[str, Any]: 模型列表
        """
        from ..models.chat_model import select_model

        model = select_model(model_provider=model_provider)
        models = model.get_models()

        return {"status": "success", "models": models}


__all__ = ["ChatService"]
