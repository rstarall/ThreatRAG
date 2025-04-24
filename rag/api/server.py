from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 导入路由
from rag.api.chat_api.chat_api import chat_api  # 这一行很重要
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



