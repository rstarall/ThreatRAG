from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag.api.routers import router
# 导入路由  # 这一行很重要
fastapi_server = FastAPI()
fastapi_server.include_router(router)
# 配置CORS
fastapi_server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 明确指定允许的前端源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加路由

@fastapi_server.get("/")
async def root():
    return {"message": "status", "status": "ok"}



