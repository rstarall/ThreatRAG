"""
聊天API路由
重构rag/api/routers/chat_api.py
"""

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from ...services.chat_service import ChatService


# 创建路由
chat_router = APIRouter(prefix="/chat", tags=["chat"])

# 初始化聊天服务
chat_service = ChatService()


@chat_router.get("/")
async def chat_get():
    """聊天接口GET测试"""
    return {"message": "Chat API is working", "status": "ok"}


@chat_router.post("/")
async def chat_post(
    query: str = Body(..., description="用户查询文本"),
    meta: Optional[Dict[str, Any]] = Body(None, description="请求元数据"),
    history: Optional[List[Dict[str, str]]] = Body(None, description="对话历史"),
    session_id: Optional[str] = Body(None, description="会话ID"),
    user_id: Optional[str] = Body(None, description="用户ID")
):
    """处理聊天请求的主要端点

    Args:
        query: 用户的输入查询文本
        meta: 包含请求元数据的字典，可以包含以下字段：
            - use_web: 是否使用网络搜索
            - use_graph: 是否使用知识图谱
            - db_id: 数据库ID
            - history_round: 历史对话轮数限制
            - system_prompt: 系统提示词
            - distanceThreshold: 向量搜索距离阈值
            - rerankThreshold: 重排序阈值
            - maxQueryCount: 最大查询数量
            - topK: 返回结果数量
        history: 对话历史记录列表
        session_id: 对话线程ID
        user_id: 用户ID（用于会话归属）

    Returns:
        StreamingResponse: 返回SSE流式响应
    """
    try:
        return StreamingResponse(
            chat_service.chat_stream(query, meta, history, session_id, user_id),
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # 禁用nginx缓冲
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")


@chat_router.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话信息
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict: 会话信息
    """
    try:
        result = await chat_service.get_session(session_id)

        if result.get("status") == "failed":
            return JSONResponse(
                status_code=result.get("code", 404),
                content={"status": result.get("code", 404)}
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话失败: {str(e)}")


@chat_router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话
    
    Args:
        session_id: 会话ID
        
    Returns:
        Dict: 删除结果
    """
    try:
        result = await chat_service.delete_session(session_id)

        if result.get("status") == "failed":
            raise HTTPException(
                status_code=result.get("code", 404),
                detail=result.get("message")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@chat_router.get("/sessions")
async def list_sessions(user_id: Optional[str] = None, limit: int = 50):
    """获取会话列表

    Args:
        user_id: 用户ID（可选，用于过滤该用户的会话）
        limit: 结果数量限制

    Returns:
        Dict: 会话列表
    """
    try:
        result = await chat_service.list_sessions(user_id=user_id, limit=limit)

        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


class UpdateSessionTitleRequest(BaseModel):
    title: str


@chat_router.put("/session/{session_id}/title")
async def update_session_title(
    session_id: str,
    body: UpdateSessionTitleRequest
):
    """更新会话标题
    
    Args:
        session_id: 会话ID
        title: 新标题
        
    Returns:
        Dict: 更新结果
    """
    try:
        result = await chat_service.update_session_title(session_id, body.title)
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=404, detail=result.get("message"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新标题失败: {str(e)}")


@chat_router.get("/models/{model_provider}")
async def get_chat_models(model_provider: str):
    """获取指定提供商的模型列表
    
    Args:
        model_provider: 模型提供商
        
    Returns:
        Dict: 模型列表
    """
    try:
        result = chat_service.get_chat_models(model_provider)
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("message"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


__all__ = ["chat_router"]
