from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv
from rag.agents.conversation_agent import StreamingConversationalAgent
from rag.chains.conversation_chain import StreamingConversationChain
from rag.vector.vector_database import get_vector_database_instance

# 加载环境变量
load_dotenv()

# 创建路由
chat_api = APIRouter(prefix="/chat")
rag_api = APIRouter(prefix="/rag")

# 请求模型定义
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    temperature: float = 0.7
    use_rag: bool = False

# 初始化全局代理实例
streaming_conversation = StreamingConversationChain(
    verbose=False,
    model_name=os.getenv("BASE_MODEL"),
    api_base=os.getenv("API_BASE"),
    api_key=os.getenv("API_KEY"),
    use_rag=False,  # 默认不启用RAG
    vector_database=get_vector_database_instance()
)

# RAG特性代理
rag_conversation = StreamingConversationChain(
    verbose=False,
    model_name=os.getenv("BASE_MODEL"),
    api_base=os.getenv("API_BASE"),
    api_key=os.getenv("API_KEY"),
    use_rag=True,  # 启用RAG
    vector_database=get_vector_database_instance()
)

# 聊天流接口：普通聊天（不使用RAG）
@chat_api.post("/stream")
async def chat_stream(request: ChatRequest):
    try:
        conversation_id = request.conversation_id
        message = request.message
        use_rag = request.use_rag  # 可选参数，默认为 False
        
        async def generate_stream(conversation_id: str):
            full_response = ""
            conversation_id = await streaming_conversation.get_or_create_conversation(conversation_id)
            yield f"data:[conversation_id]:{conversation_id}\n\n"

            async for token_json in streaming_conversation.astream(
                message=message,
                conversation_id=conversation_id,
                use_rag=use_rag
            ):
                if token_json:
                    full_response += token_json
                    yield f"data: {token_json}\n\n"

            conversation_title = await streaming_conversation.get_title_from_conversation(conversation_id)
            yield f"data:[conversation_title]:{conversation_title}\n\n"
            yield f"event: complete\ndata: {json.dumps({'type': 'conversation_full', 'data': full_response})}\n\n"

        return StreamingResponse(
            generate_stream(conversation_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        import traceback
        print(f"错误: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# RAG流接口：启用RAG
@rag_api.post("/stream")
async def rag_stream(request: ChatRequest):
    try:
        conversation_id = request.conversation_id
        message = request.message
        use_rag = request.use_rag if hasattr(request, "use_rag") else True  # 默认启用RAG

        async def generate_stream(conversation_id: str):
            full_response = ""
            conversation_id = await rag_conversation.get_or_create_conversation(conversation_id)
            yield f"data:[conversation_id]:{conversation_id}\n\n"

            async for token_json in rag_conversation.astream(
                message=message,
                conversation_id=conversation_id,
                use_rag=use_rag
            ):
                if token_json:
                    full_response += token_json
                    yield f"data: {token_json}\n\n"

            conversation_title = await rag_conversation.get_title_from_conversation(conversation_id)
            yield f"data:[conversation_title]:{conversation_title}\n\n"
            yield f"event: complete\ndata: {json.dumps({'type': 'conversation_full', 'data': full_response})}\n\n"

        return StreamingResponse(
            generate_stream(conversation_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream"
            }
        )

    except Exception as e:
        import traceback
        print(f"错误: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
