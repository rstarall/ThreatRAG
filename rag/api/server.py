from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# 导入路由
from rag.api.chat_api.chat_api import chat_api  # 这一行很重要
from rag.api.file_api.file_api import upload_router
from rag.api.chat_api.chat_api import rag_api
fastapi_server = FastAPI()

# 配置CORS
fastapi_server.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 明确指定允许的前端源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加路由
fastapi_server.include_router(chat_api)
fastapi_server.include_router(upload_router)
fastapi_server.include_router(rag_api)

@fastapi_server.get("/")
async def root():
    return {"message": "Hello World"}



