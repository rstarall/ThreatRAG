"""
问答引擎
整合rag/service/chat_service.py的核心对话功能
"""

import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
import uuid
import json

from ...config import get_config
from ...utils.logging_config import logger
from ...models.chat_model import select_model, GeneralResponse
from ..retrieval.retriever import Retriever
from .session_manager import SessionManager


class ChatEngine:
    """问答引擎类"""
    
    def __init__(self):
        """初始化问答引擎"""
        self.retriever = None
        self.session_manager = SessionManager()
        
        # 初始化检索器
        if self._should_enable_retrieval():
            try:
                self.retriever = Retriever()
                logger.info("Retriever initialized")
            except Exception as e:
                logger.error(f"Failed to initialize retriever: {e}")
    
    def _should_enable_retrieval(self) -> bool:
        """判断是否应该启用检索功能"""
        cfg = get_config()
        return (cfg.enable_knowledge_base or 
                cfg.enable_knowledge_graph)
    
    def _need_retrieve(self, meta: Dict[str, Any]) -> bool:
        """判断是否需要检索"""
        return (meta.get("use_web") or 
                meta.get("use_graph") or 
                meta.get("db_id"))
    
    def _make_chunk(self, content: Optional[str] = None, 
                   meta: Optional[Dict[str, Any]] = None,
                   session_id: Optional[str] = None, **kwargs) -> bytes:
        """创建SSE格式的响应数据块
        
        Args:
            content: 响应内容
            meta: 元数据
            session_id: 会话ID
            **kwargs: 其他参数
            
        Returns:
            bytes: SSE格式的数据块
        """
        data = json.dumps({
            "response": content,
            "meta": meta or {},
            "session_id": session_id,
            **kwargs
        }, ensure_ascii=False)
        
        return f"data: {data}\n\n".encode('utf-8')
    
    async def _handle_retrieval(self, query: str, history: List[Dict[str, str]], 
                               meta: Dict[str, Any], session_id: str) -> AsyncGenerator[bytes, None]:
        """处理检索阶段
        
        Args:
            query: 用户查询
            history: 对话历史
            meta: 元数据
            session_id: 会话ID
            
        Yields:
            bytes: 检索状态或结果
        """
        yield self._make_chunk(status="searching", session_id=session_id)
        
        try:
            if self.retriever:
                enhanced_query, refs = await self.retriever(query, history, meta)
                
                # 构造检索结果信息
                retrieved_docs = self._format_retrieved_docs(refs)
                
                yield enhanced_query, refs, retrieved_docs
            else:
                logger.warning("Retriever not initialized, skipping retrieval")
                yield query, None, []
                
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            yield self._make_chunk(
                message=f"检索出错: {e}", 
                status="error", 
                session_id=session_id
            )
            yield query, None, []
    
    def _format_retrieved_docs(self, refs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """格式化检索到的文档
        
        Args:
            refs: 检索结果引用
            
        Returns:
            List[Dict[str, Any]]: 格式化的文档列表
        """
        retrieved_docs = []
        
        # 处理知识库文档
        if refs and "knowledge_base" in refs and "results" in refs["knowledge_base"]:
            for doc in refs["knowledge_base"]["results"]:
                if "entity" in doc and "text" in doc["entity"]:
                    text = doc["entity"]["text"]
                    retrieved_docs.append({
                        "type": "document",
                        "id": doc.get("id", ""),
                        "filename": doc.get("entity", {}).get("metadata", {}).get("filename", "未知文档"),
                        "content": text[:200] + "..." if len(text) > 200 else text,
                        "score": doc.get("distance", 0.0)
                    })
        
        # 处理图谱信息
        if refs and "graph_base" in refs and "results" in refs["graph_base"]:
            graph_data = refs["graph_base"]["results"]
            if "nodes" in graph_data and len(graph_data["nodes"]) > 0:
                for node in graph_data["nodes"]:
                    # 使用 graph_model.Entity 标准字段
                    retrieved_docs.append({
                        "type": "graph_node",
                        "entity_id": node.get("entity_id", ""),
                        "entity_name": node.get("entity_name", ""),
                        "entity_type": node.get("entity_type", ""),
                        "entity_sub_type": node.get("entity_sub_type", ""),
                        "labels": node.get("labels", []),
                        "times": node.get("times", []),
                        "entity_variant_names": node.get("entity_variant_names", []),
                        "properties": node.get("properties", {})
                    })
        
        return retrieved_docs
    
    async def _handle_generation(self, messages: List[Dict[str, str]], 
                                meta: Dict[str, Any], session_id: str) -> AsyncGenerator[Any, None]:
        """处理生成阶段
        
        Args:
            messages: 消息列表
            meta: 元数据
            session_id: 会话ID
            
        Yields:
            bytes or tuple: 生成的内容或结果元组
        """
        try:
            model = select_model()
            content = ""
            reasoning_content = ""
            
            # 获取流式输出
            model_stream = model.predict(messages, stream=True)
            
            # 使用线程池处理同步生成器
            loop = asyncio.get_event_loop()
            
            def get_next_delta():
                """获取下一个delta"""
                try:
                    return next(model_stream)
                except StopIteration:
                    return None
            
            # 处理流式响应
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                while True:
                    delta = await loop.run_in_executor(executor, get_next_delta)
                    
                    if delta is None:  # 流结束
                        break
                    
                    if not isinstance(delta, GeneralResponse):
                        logger.warning(f"Unexpected delta type: {type(delta)}")
                        continue
                    
                    # 处理推理内容
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_content += delta.reasoning_content
                        chunk = self._make_chunk(
                            reasoning_content=reasoning_content,
                            status="reasoning",
                            session_id=session_id
                        )
                        yield chunk
                        
                        if not delta.content:
                            continue
                    
                    # 处理正常内容
                    if hasattr(delta, 'is_full') and delta.is_full:
                        content = delta.content or ""
                    else:
                        content += delta.content or ""
                    
                    # 发送增量内容（不含meta以减少冗余传输）
                    if delta.content:
                        chunk = self._make_chunk(
                            content=delta.content,
                            status="loading",
                            session_id=session_id
                        )
                        yield chunk
            
            logger.debug(f"Generated response length: {len(content)}")
            yield (content, reasoning_content)
            
        except Exception as e:
            logger.error(f"Generation error: {e}")
            yield self._make_chunk(
                message=f"生成回答时出错: {e}",
                status="error",
                session_id=session_id
            )
            raise
    
    async def _generate_session_title(self, query: str, response: str, 
                                     session_id: str) -> AsyncGenerator[bytes, None]:
        """生成会话标题
        
        Args:
            query: 用户问题
            response: 助手回答
            session_id: 会话ID
            
        Yields:
            bytes: 标题生成状态
        """
        try:
            yield self._make_chunk(status="title_generating", session_id=session_id)
            
            # 构造标题生成提示
            title_prompt = f"""请根据以下对话内容，生成一个简洁的会话标题（不超过20个字符）：

用户问题：{query}
助手回答：{response[:200]}...

要求：
1. 标题要简洁明了，能概括对话主题
2. 不超过20个字符
3. 不要包含标点符号
4. 直接返回标题，不要其他内容

标题："""
            
            model = select_model()
            title_response = await asyncio.to_thread(model.predict, title_prompt)
            title = title_response.content.strip()
            
            # 清理标题
            title = title.replace("标题：", "").replace("：", "").replace(":", "").strip()
            if len(title) > 20:
                title = title[:20]
            
            if not title:
                title = "新对话"
            
            # 更新会话标题
            await self.session_manager.update_session_title(session_id, title)
            
            yield self._make_chunk(
                status="title_generated",
                title=title,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(f"Title generation error: {e}")
            default_title = "新对话"
            await self.session_manager.update_session_title(session_id, default_title)
            
            yield self._make_chunk(
                status="title_generated",
                title=default_title,
                session_id=session_id
            )
    
    async def process_chat_stream(self, query: str,
                                 meta: Optional[Dict[str, Any]] = None,
                                 history: Optional[List[Dict[str, str]]] = None,
                                 session_id: Optional[str] = None,
                                 user_id: Optional[str] = None) -> AsyncGenerator[bytes, None]:
        """处理聊天请求的主要逻辑

        Args:
            query: 用户查询
            meta: 元数据（其中 user_id 会覆盖参数中的 user_id）
            history: 对话历史
            session_id: 会话ID
            user_id: 用户ID（用于会话归属，可选）

        Yields:
            bytes: 流式响应数据块
        """
        meta = meta or {}
        # meta 中的 user_id 优先级更高
        effective_user_id = meta.pop("user_id", None) or user_id

        model = select_model()
        meta["server_model_name"] = model.model_name

        is_new_session = False

        # 会话管理
        if not session_id:
            session_id = str(uuid.uuid4())
            is_new_session = True
            logger.debug(f"Created new session_id: {session_id} for user {effective_user_id}")
        
        # 获取或初始化历史
        if not history:
            history = await self.session_manager.get_session_history(session_id)
        
        modified_query = query
        refs = None
        retrieved_docs = []
        
        # 1. 检索阶段
        if meta and self._need_retrieve(meta):
            async for chunk in self._handle_retrieval(query, history, meta, session_id):
                if isinstance(chunk, tuple):
                    modified_query, refs, retrieved_docs = chunk
                    break
                else:
                    yield chunk
            
            yield self._make_chunk(
                status="generating",
                retrieved_docs=retrieved_docs,
                session_id=session_id
            )
        else:
            yield self._make_chunk(status="generating", session_id=session_id)
        
        # 2. 准备消息
        messages = self._prepare_messages(modified_query, history, meta)
        
        # 更新会话历史
        await self.session_manager.add_message(session_id, "user", query, user_id=effective_user_id)
        
        # 3. 生成阶段
        content = ""
        reasoning_content = ""
        
        try:
            async for chunk in self._handle_generation(messages, meta, session_id):
                if isinstance(chunk, tuple):
                    content, reasoning_content = chunk
                    break
                else:
                    yield chunk
            
            # 更新会话历史
            await self.session_manager.add_message(session_id, "assistant", content, user_id=effective_user_id)
            
            # 发送完成状态
            yield self._make_chunk(
                status="finished",
                content=content,
                history=history + [
                    {"role": "user", "content": query},
                    {"role": "assistant", "content": content}
                ],
                refs=refs,
                meta=meta,
                session_id=session_id
            )
            
            # 4. 生成标题（新会话）
            if is_new_session and content and query:
                async for chunk in self._generate_session_title(query, content, session_id):
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            yield self._make_chunk(
                message=f"对话处理出错: {e}",
                status="error",
                session_id=session_id
            )
    
    def _prepare_messages(self, query: str, history: List[Dict[str, str]], 
                         meta: Dict[str, Any]) -> List[Dict[str, str]]:
        """准备发送给模型的消息
        
        Args:
            query: 查询文本
            history: 历史消息
            meta: 元数据
            
        Returns:
            List[Dict[str, str]]: 消息列表
        """
        messages = []
        
        # 添加系统提示
        system_prompt = meta.get("system_prompt", "你是一个有用的AI助手，请根据提供的信息回答用户的问题。")
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史对话（限制轮数）
        max_history_rounds = meta.get("history_round", 5)
        if history and max_history_rounds > 0:
            recent_history = history[-(max_history_rounds * 2):]  # 每轮包含用户和助手消息
            messages.extend(recent_history)
        
        # 添加当前查询
        messages.append({"role": "user", "content": query})
        
        return messages
    
    async def call_model_directly(self, query: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """直接调用模型（不使用检索）
        
        Args:
            query: 用户查询
            meta: 元数据
            
        Returns:
            Dict[str, Any]: 模型响应
        """
        try:
            model = select_model(
                model_provider=meta.get("model_provider") if meta else None,
                model_name=meta.get("model_name") if meta else None
            )
            
            response = await asyncio.to_thread(model.predict, query)
            
            return {
                "response": response.content,
                "model_name": model.model_name
            }
            
        except Exception as e:
            logger.error(f"Direct model call failed: {e}")
            raise Exception(f"模型调用失败: {str(e)}")


__all__ = ["ChatEngine"]
