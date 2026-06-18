"""
FastAPI服务器
整合rag/api/server.py
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import chat_router, knowledge_router, graph_router, user_router
from ..utils.logging_config import logger


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    
    app = FastAPI(
        title="ThreatRAG API",
        description="威胁情报RAG系统API接口",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境中应该指定具体的前端域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(chat_router)
    app.include_router(knowledge_router)
    app.include_router(graph_router)
    app.include_router(user_router)
    
    # 健康检查端点
    @app.get("/")
    async def root():
        """根路径健康检查"""
        return {
            "message": "ThreatRAG API Server",
            "status": "ok",
            "version": "2.0.0"
        }
    
    @app.get("/health")
    async def health_check():
        """详细健康检查"""
        from ..utils.database_manager import service_checker
        from ..config import get_config
        cfg = get_config()

        # 检查数据库服务状态
        service_status = service_checker.get_service_status()
        
        health_info = {
            "status": "ok",
            "version": "2.0.0",
            "services": service_status,
            "features": {
                "knowledge_base": cfg.enable_knowledge_base,
                "knowledge_graph": cfg.enable_knowledge_graph,
                "reranker": cfg.enable_reranker,
                "web_search": cfg.enable_web_search
            }
        }
        
        # 如果关键服务不可用，返回警告状态
        if cfg.enable_knowledge_base and not service_status.get("milvus"):
            health_info["status"] = "warning"
            health_info["warnings"] = health_info.get("warnings", [])
            health_info["warnings"].append("Milvus service not available")
        
        if cfg.enable_knowledge_graph and not service_status.get("neo4j"):
            health_info["status"] = "warning" 
            health_info["warnings"] = health_info.get("warnings", [])
            health_info["warnings"].append("Neo4j service not available")
        
        return health_info
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """全局异常处理器"""
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "服务器内部错误，请稍后重试",
                "detail": str(exc) if app.debug else None
            }
        )
    
    # 启动事件
    @app.on_event("startup")
    async def startup_event():
        """应用启动时的初始化操作"""
        logger.info("ThreatRAG API Server starting up...")

        # 检查服务依赖
        from ..utils.database_manager import service_checker
        from ..config import get_config
        cfg = get_config()

        # 检查数据库服务
        service_status = service_checker.check_all_services(cfg)
        
        if cfg.enable_knowledge_base and not service_status.get("milvus"):
            logger.warning("Milvus service not available - knowledge base features may not work")
        
        if cfg.enable_knowledge_graph and not service_status.get("neo4j"):
            logger.warning("Neo4j service not available - graph features may not work")
        
        logger.info("ThreatRAG API Server startup completed")
    
    # 关闭事件
    @app.on_event("shutdown")
    async def shutdown_event():
        """应用关闭时的清理操作"""
        logger.info("ThreatRAG API Server shutting down...")
        
        # 这里可以添加清理逻辑，比如关闭数据库连接等
        
        logger.info("ThreatRAG API Server shutdown completed")
    
    return app


# 创建应用实例
app = create_app()

__all__ = ["app", "create_app"]
