"""
ThreatRAG 主启动文件 - 重构版本
整合和简化原main.py的功能
"""

import uvicorn
import signal
import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径（src的父目录）
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path.parent))

from src.config import config
from src.utils.logging_config import logger
from src.utils.database_manager import service_checker


class ThreatRAGServer:
    """ThreatRAG服务器管理类"""
    
    def __init__(self):
        self.is_shutting_down = False
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        if not self.is_shutting_down:
            self.is_shutting_down = True
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self._cleanup()
            sys.exit(0)
    
    def _cleanup(self):
        """清理资源"""
        logger.info("Cleaning up resources...")
        # 这里可以添加清理逻辑
        logger.info("Cleanup completed")
    
    def check_dependencies(self):
        """检查依赖服务"""
        logger.info("Checking service dependencies...")
        
        service_status = service_checker.check_all_services(config)
        
        # 检查Milvus
        if config.enable_knowledge_base:
            if service_status.get("milvus"):
                logger.info("✓ Milvus service is available")
            else:
                logger.error("✗ Milvus service is not available")
                logger.error("Please ensure Milvus is running. You can start it with:")
                logger.error("docker run -d --name milvus_standalone -p 19530:19530 milvusdb/milvus:latest")
                if self._is_strict_mode():
                    sys.exit(1)
        
        # 检查Neo4j
        if config.enable_knowledge_graph:
            if service_status.get("neo4j"):
                logger.info("✓ Neo4j service is available")
            else:
                logger.error("✗ Neo4j service is not available")
                logger.error("Please ensure Neo4j is running with correct credentials")
                if self._is_strict_mode():
                    sys.exit(1)
        
        # 检查Redis
        if service_status.get("redis"):
            logger.info("✓ Redis service is available")
        else:
            logger.warning("⚠️ Redis service is not available - session cache will not work")
            logger.warning("Install and start Redis server to enable session caching:")
            logger.warning("https://redis.io/docs/getting-started/")
        
        # 检查环境变量
        self._check_environment_variables()
    
    def _is_strict_mode(self) -> bool:
        """检查是否为严格模式（生产环境）"""
        return os.getenv("STRICT_MODE", "false").lower() == "true"
    
    def _check_environment_variables(self):
        """检查必要的环境变量"""
        logger.info("Checking environment variables...")
        
        required_vars = []
        
        # 检查模型API密钥
        if config.model_provider == "deepseek" and not os.getenv("DEEPSEEK_API_KEY"):
            required_vars.append("DEEPSEEK_API_KEY")
        
        if config.model_provider == "siliconflow" and not os.getenv("SILICONFLOW_API_KEY"):
            required_vars.append("SILICONFLOW_API_KEY")
        
        # 检查Neo4j凭据
        if config.enable_knowledge_graph:
            if not os.getenv("NEO4J_PASSWORD"):
                logger.warning("NEO4J_PASSWORD not set, using default password")
        
        if required_vars:
            logger.error(f"✗ Missing required environment variables: {', '.join(required_vars)}")
            logger.error("Please set these variables in your .env file or environment")
            if self._is_strict_mode():
                sys.exit(1)
        else:
            logger.info("✓ All required environment variables are set")
    
    def initialize_services(self):
        """初始化服务"""
        logger.info("Initializing services...")
        
        # 创建必要的目录
        self._create_directories()
        
        # 初始化向量索引（如果需要）
        if config.enable_knowledge_graph:
            self._initialize_graph_indices()
        
        logger.info("Services initialized successfully")
    
    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            config.save_dir,
            os.path.join(config.save_dir, "knowledge_base"),
            os.path.join(config.save_dir, "graph_data"),
            os.path.join(config.save_dir, "uploads"),
            "logs"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")
    
    def _initialize_graph_indices(self):
        """初始化图数据库索引"""
        try:
            from src.core.graph.graph_store import GraphStore
            
            graph_store = GraphStore()
            if graph_store.is_running():
                # 创建向量索引
                try:
                    graph_store.client.create_vector_index("Entity", "embedding")
                    logger.info("✓ Graph vector index created/verified")
                except Exception as e:
                    logger.warning(f"Graph vector index creation failed: {e}")
            else:
                logger.warning("Graph store not running, skipping index creation")
                
        except Exception as e:
            logger.error(f"Graph service initialization failed: {e}")
    
    def start_server(self):
        """启动服务器"""
        try:
            # 导入应用
            from src.api.server import app
            
            # 获取服务器配置
            host = config.fastapi_server.get("host", "localhost")
            port = config.fastapi_server.get("port", 8000)
            
            logger.info(f"Starting ThreatRAG API server at http://{host}:{port}")
            logger.info("API Documentation available at:")
            logger.info(f"  - Swagger UI: http://{host}:{port}/docs")
            logger.info(f"  - ReDoc: http://{host}:{port}/redoc")
            
            # 启动服务器
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            sys.exit(1)
    
    def run(self):
        """运行服务器"""
        try:
            logger.info("=" * 60)
            logger.info("ThreatRAG - 威胁情报RAG系统 v2.0.0")
            logger.info("=" * 60)
            
            # 检查依赖
            self.check_dependencies()
            
            # 初始化服务
            self.initialize_services()
            
            # 启动服务器
            self.start_server()
            
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server startup failed: {e}")
            sys.exit(1)
        finally:
            self._cleanup()


def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    
    # 创建并运行服务器
    server = ThreatRAGServer()
    server.run()


if __name__ == "__main__":
    main()
