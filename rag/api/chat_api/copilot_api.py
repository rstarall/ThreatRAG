from fastapi import FastAPI

from rag.chains.conversation_chain import StreamingConversationChain
from rag.vector.vector_database import get_vector_database_instance
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()


# 初始化对话链
streaming_conversation = StreamingConversationChain(
    verbose=False,
    model_name=os.getenv("BASE_MODEL"),
    api_base=os.getenv("API_BASE"),
    api_key=os.getenv("API_KEY"),
    use_rag=True,
    vector_database=get_vector_database_instance()
)

async def chat_with_ai(message: str, conversation_id: str = None, temperature: float = 0.7):
    """与AI进行对话的处理函数"""
    try:
        # 获取或创建会话ID
        conversation_id = await streaming_conversation.get_or_create_conversation(conversation_id)
        
        # 获取完整响应
        full_response = ""
        async for token in streaming_conversation.astream(
            message=message,
            conversation_id=conversation_id
        ):
            if token:
                full_response += token
        
        # 获取对话标题
        conversation_title = await streaming_conversation.get_title_from_conversation(conversation_id)
        
        return {
            "conversation_id": conversation_id,
            "response": full_response,
            "conversation_title": conversation_title
        }
    except Exception as e:
        raise Exception(f"Chat error: {str(e)}")


