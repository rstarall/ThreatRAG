from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from rag.agents.conversation_agent import StreamingConversationalAgent
from rag.chains.conversation_chain import StreamingConversationChain
from rag.vector.vector_database import get_vector_database_instance
import json
# 加载环境变量
load_dotenv()

# 创建路由
chat_api = APIRouter(prefix="/chat")

# 请求模型定义
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    temperature: float = 0.7



# 初始化全局代理实例
# streaming_conversation = StreamingConversationalAgent(verbose=False,
#                                                 model_name=os.getenv("BASE_MODEL"),
#                                                 api_base=os.getenv("API_BASE"),
#                                                 api_key=os.getenv("API_KEY"),
#                                                 use_rag=True,
#                                                 vector_database=get_vector_database_instance()
#                                                )

streaming_conversation = StreamingConversationChain(verbose=False,
                                                model_name=os.getenv("BASE_MODEL"),
                                                api_base=os.getenv("API_BASE"),
                                                api_key=os.getenv("API_KEY"),
                                                use_rag=True,
                                                vector_database=get_vector_database_instance()
                                               )

@chat_api.post("/stream")
async def chat_stream(request: ChatRequest):
    try:
        conversation_id = request.conversation_id
        message = request.message  # 保持原始消息格式
        
        async def generate_stream(conversation_id: str):
            full_response = ""

            #检查是否有历史会话，如果没有则创建一个新的会话
            conversation_id = await streaming_conversation.get_or_create_conversation(conversation_id)

            yield f"data:[conversation_id]:{conversation_id}\n\n"
            async for token_json in streaming_conversation.astream(
                message=message,
                conversation_id=conversation_id
            ):
                if token_json:
                    full_response += token_json
                    yield f"data: {token_json}\n\n"

            conversation_title = await streaming_conversation.get_title_from_conversation(conversation_id)
            yield f"data:[conversation_title]:{conversation_title}\n\n"
            yield f"event: complete\ndata: {json.dumps({'type':'conversation_full','data':full_response})}\n\n"
            
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
        error_details = f"错误: {str(e)}\n{traceback.format_exc()}"
        print(error_details)
        raise HTTPException(status_code=500, detail=str(e))

@chat_api.get("/health")
def health_check():
    return {"status": "OK"}