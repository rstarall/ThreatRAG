import os
import json
import asyncio
import traceback
import uuid
from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk
from packages import executor, retriever, config
from packages.core import HistoryManager
from packages.models import select_model
from packages.utils.logging_config import logger
from rag.cache.redis_session import RedisSessionManager
from rag.utils.coroutine_pool import CoroutinePool
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建路由
chat = APIRouter(prefix="/chat")

# 初始化Redis会话管理器
redis_session = RedisSessionManager(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    expire_time=int(os.getenv("SESSION_EXPIRE_TIME", "3600"))
)

# 初始化协程池
coroutine_pool = CoroutinePool(
    max_workers=int(os.getenv("MAX_CONCURRENT_CHATS", "20"))
)

@chat.get("/")
async def chat_get():
    return "Chat Get!"

@chat.post("/stream")
async def chat_post(
        query: str = Body(...),
        meta: dict = Body(None),
        history: list[dict] | None = Body(None),
        thread_id: str | None = Body(None)):
    """处理聊天请求的主要端点。
    Args:
        query: 用户的输入查询文本
        meta: 包含请求元数据的字典，可以包含以下字段：
            - use_web: 是否使用网络搜索
            - use_graph: 是否使用知识图谱
            - db_id: 数据库ID
            - history_round: 历史对话轮数限制
            - system_prompt: 系统提示词（str，不含变量）
            - search_mode: 图搜索模式 (local/global/hybrid，默认hybrid)
            - top_k: 搜索结果数量限制 (默认10)
            - threshold: 相似度阈值 (默认0.7)
        history: 对话历史记录列表
        thread_id: 对话线程ID
    Returns:
        StreamingResponse: 返回一个流式响应
    """
    meta = meta or {}
    model = select_model()
    meta["server_model_name"] = model.model_name
    
    # 如果提供了thread_id，尝试从Redis获取历史记录
    if thread_id:
        try:
            # 从Redis获取会话历史
            cached_history = await redis_session.get_history(thread_id)
            if cached_history and not history:
                history = cached_history
                logger.debug(f"Using cached history for thread_id: {thread_id}")
        except Exception as e:
            logger.error(f"Error fetching history from Redis: {e}")
    else:
        # 如果没有thread_id，创建新会话
        thread_id = await redis_session.create_session(system_prompt=meta.get("system_prompt"))
        logger.debug(f"Created new session with thread_id: {thread_id}")
    
    # 初始化历史管理器
    history_manager = HistoryManager(history, system_prompt=meta.get("system_prompt"))
    logger.debug(f"Received query: {query} with meta: {meta}")
    
    # 确保meta中包含show_retrieval_info参数，默认为True
    if "show_retrieval_info" not in meta:
        meta["show_retrieval_info"] = True

    def make_chunk(content=None, **kwargs):
        return json.dumps({
            "response": content,
            "meta": meta,
            "thread_id": thread_id,  # 返回thread_id给客户端
            **kwargs
        }, ensure_ascii=False).encode('utf-8') + b"\n"

    def need_retrieve(meta):
        return meta.get("use_web") or meta.get("use_graph") or meta.get("db_id")

    async def process_chat():
        modified_query = query
        refs = None

        # 处理知识库检索
        if meta and need_retrieve(meta):
            yield make_chunk(status="searching")

            try:
                # 使用协程池提交检索任务
                retrieval_result = await coroutine_pool.submit(
                    asyncio.to_thread(retriever, modified_query, history_manager.messages, meta)
                )
                modified_query, refs = retrieval_result
            except Exception as e:
                logger.error(f"Retriever error: {e}, {traceback.format_exc()}")
                yield make_chunk(message=f"Retriever error: {e}", status="error")
                return

            yield make_chunk(status="generating")

        messages = history_manager.get_history_with_msg(modified_query, max_rounds=meta.get('history_round'))
        history_manager.add_user(query)  # 注意这里使用原始查询
        
        # 更新Redis中的会话历史
        try:
            await redis_session.add_message(thread_id, "user", query)
        except Exception as e:
            logger.error(f"Error updating Redis history: {e}")

        content = ""
        reasoning_content = ""
        try:
            # 使用协程池提交模型预测任务
            model_stream = model.predict(messages, stream=True)
            
            for delta in model_stream:
                if not delta.content and hasattr(delta, 'reasoning_content'):
                    reasoning_content += delta.reasoning_content or ""
                    chunk = make_chunk(reasoning_content=reasoning_content, status="reasoning")
                    yield chunk
                    continue

                # 文心一言
                if hasattr(delta, 'is_full') and delta.is_full:
                    content = delta.content
                else:
                    content += delta.content or ""

                chunk = make_chunk(content=delta.content, status="loading")
                yield chunk

            logger.debug(f"Final response: {content}")
            logger.debug(f"Final reasoning response: {reasoning_content}")
            
            # 更新Redis中的会话历史
            try:
                await redis_session.add_message(thread_id, "assistant", content)
            except Exception as e:
                logger.error(f"Error updating Redis history: {e}")
                
            # 只返回refs的摘要信息，避免输出大量数据
            refs_summary = None
            if refs:
                refs_summary = {
                    "knowledge_base_count": len(refs.get("knowledge_base", {}).get("results", [])),
                    "graph_base_count": len(refs.get("graph_base", {}).get("results", [])),
                    "web_search_count": len(refs.get("web_search", {}).get("results", [])),
                    "entities": refs.get("entities", [])[:5]  # 只返回前5个实体
                }
            
            yield make_chunk(status="finished",
                            history=history_manager.update_ai(content),
                            refs=refs_summary)
        except Exception as e:
            logger.error(f"Model error: {e}, {traceback.format_exc()}")
            yield make_chunk(message=f"Model error: {e}", status="error")
            return

    # 使用StreamingResponse返回异步生成器
    return StreamingResponse(process_chat(), media_type='application/json')

@chat.post("/call")
async def call(query: str = Body(...), meta: dict = Body(None)):
    meta = meta or {}
    model = select_model(model_provider=meta.get("model_provider"), model_name=meta.get("model_name"))
    
    async def predict_async(query):
        # 使用协程池提交预测任务
        return await coroutine_pool.submit(
            asyncio.to_thread(model.predict, query)
        )

    response = await predict_async(query)
    logger.debug({"query": query, "response": response.content})

    return {"response": response.content}

@chat.get("/sessions/{thread_id}")
async def get_session(thread_id: str):
    """获取指定会话的历史记录
    
    Args:
        thread_id: 会话ID
        
    Returns:
        会话历史记录
    """
    try:
        session = await redis_session.get_session(thread_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chat.delete("/sessions/{thread_id}")
async def delete_session(thread_id: str):
    """删除指定会话
    
    Args:
        thread_id: 会话ID
        
    Returns:
        删除结果
    """
    try:
        result = await redis_session.delete_session(thread_id)
        if not result:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@chat.get("/models")
async def get_chat_models(model_provider: str):
    """获取指定模型提供商的模型列表"""
    model = select_model(model_provider=model_provider)
    return {"models": model.get_models()}

@chat.post("/models/update")
async def update_chat_models(model_provider: str, model_names: list[str]):
    """更新指定模型提供商的模型列表"""
    config.model_names[model_provider]["models"] = model_names
    config._save_models_to_file()
    return {"models": config.model_names[model_provider]["models"]}

