from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitRemoteEndpoint, Action as CopilotAction
# 导入路由
from rag.api.chat_api.chat_api import chat_api  # 这一行很重要
from rag.api.chat_api.copilot_api import chat_with_ai
fastapi_server = FastAPI()

# 配置CORS
fastapi_server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加路由
fastapi_server.include_router(chat_api)

@fastapi_server.get("/")
async def root():
    return {"message": "Hello World"}




# 定义Copilot动作
chat_action = CopilotAction(
    name="chatWithAI",
    description="Chat with an AI assistant using RAG (Retrieval-Augmented Generation)",
    parameters=[
        {
            "name": "message",
            "type": "string",
            "description": "The message to send to the AI",
            "required": True,
        },
        {
            "name": "conversation_id",
            "type": "string",
            "description": "The ID of the conversation (optional)",
            "required": False,
        },
        {
            "name": "temperature",
            "type": "number",
            "description": "The temperature parameter for response generation (0.0 to 1.0)",
            "required": False,
        }
    ],
    handler=chat_with_ai
)

# 初始化CopilotKit SDK
sdk = CopilotKitRemoteEndpoint(actions=[chat_action])

# 添加CopilotKit端点
add_fastapi_endpoint(
    fastapi_server, 
    sdk, 
    "/copilotkit_remote"  # 直接使用完整路
)