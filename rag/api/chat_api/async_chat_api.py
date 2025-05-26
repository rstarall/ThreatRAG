from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from rag.mq.conversation_worker import ConversationWorker
from rag.mq.vector_search_worker import VectorSearchWorker
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建路由
async_chat_api = APIRouter(prefix="/async_chat")

# 请求模型定义
class AsyncChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    temperature: float = 0.7

# 初始化工作器
conversation_worker = ConversationWorker(num_workers=3)
vector_search_worker = VectorSearchWorker(num_workers=3)

# 启动工作器
conversation_worker.start_workers()
vector_search_worker.start_workers()

# 活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}

@async_chat_api.post("/conversation")
async def async_conversation(request: AsyncChatRequest):
    """异步会话API"""
    try:
        # 创建Future对象用于等待结果
        result_future = asyncio.Future()
        
        # 定义回调函数
        def on_result(result):
            # 设置Future的结果
            if not result_future.done():
                asyncio.run_coroutine_threadsafe(
                    result_future.set_result(result),
                    asyncio.get_event_loop()
                )
        
        # 提交会话任务
        request_id = conversation_worker.submit_conversation_task(
            message=request.message,
            conversation_id=request.conversation_id,
            temperature=request.temperature,
            callback=on_result
        )
        
        # 等待结果
        try:
            # 设置超时时间为60秒
            result = await asyncio.wait_for(result_future, timeout=60.0)
            
            # 返回结果
            return {
                "request_id": request_id,
                "conversation_id": result.get("conversation_id"),
                "response": result.get("response"),
                "conversation_title": result.get("conversation_title"),
                "rag_context": result.get("rag_context", [])
            }
        except asyncio.TimeoutError:
            # 超时处理
            return {
                "request_id": request_id,
                "error": "请求超时，请稍后查询结果"
            }
    except Exception as e:
        logger.error(f"处理异步会话请求时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@async_chat_api.post("/vector_search")
async def async_vector_search(query: str, k: int = 5):
    """异步向量检索API"""
    try:
        # 创建Future对象用于等待结果
        result_future = asyncio.Future()
        
        # 定义回调函数
        def on_result(result):
            # 设置Future的结果
            if not result_future.done():
                asyncio.run_coroutine_threadsafe(
                    result_future.set_result(result),
                    asyncio.get_event_loop()
                )
        
        # 提交检索任务
        request_id = vector_search_worker.submit_search_task(
            query=query,
            k=k
        )
        
        # 等待结果
        try:
            # 设置超时时间为30秒
            result = await asyncio.wait_for(result_future, timeout=30.0)
            
            # 返回结果
            return {
                "request_id": request_id,
                "results": result.get("results", []),
                "search_time": result.get("search_time", 0)
            }
        except asyncio.TimeoutError:
            # 超时处理
            return {
                "request_id": request_id,
                "error": "检索请求超时，请稍后查询结果"
            }
    except Exception as e:
        logger.error(f"处理异步向量检索请求时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@async_chat_api.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket端点，用于实时通信"""
    await websocket.accept()
    active_connections[client_id] = websocket
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            # 提取请求参数
            message = request_data.get("message", "")
            conversation_id = request_data.get("conversation_id")
            temperature = request_data.get("temperature", 0.7)
            
            # 定义回调函数
            async def on_result(result):
                # 发送结果到WebSocket
                await websocket.send_json({
                    "type": "conversation_result",
                    "conversation_id": result.get("conversation_id"),
                    "response": result.get("response"),
                    "conversation_title": result.get("conversation_title"),
                    "rag_context": result.get("rag_context", [])
                })
            
            # 包装回调函数
            def callback_wrapper(result):
                asyncio.run_coroutine_threadsafe(
                    on_result(result),
                    asyncio.get_event_loop()
                )
            
            # 提交会话任务
            request_id = conversation_worker.submit_conversation_task(
                message=message,
                conversation_id=conversation_id,
                temperature=temperature,
                callback=callback_wrapper
            )
            
            # 发送确认消息
            await websocket.send_json({
                "type": "request_received",
                "request_id": request_id
            })
    
    except WebSocketDisconnect:
        # 客户端断开连接
        if client_id in active_connections:
            del active_connections[client_id]
            logger.info(f"客户端 {client_id} 断开连接")
    except Exception as e:
        logger.error(f"WebSocket处理出错: {str(e)}")
        # 尝试发送错误消息
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
        
        # 清理连接
        if client_id in active_connections:
            del active_connections[client_id]
