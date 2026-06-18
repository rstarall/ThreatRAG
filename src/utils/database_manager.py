"""
数据库服务检查器
用于检查各种数据库服务的可用性状态
"""

import os
from typing import Dict, Any
import psutil
from .logging_config import logger


class DatabaseServiceChecker:
    """数据库服务状态检查器"""

    def __init__(self):
        self.milvus_running = False
        self.neo4j_running = False
        self.redis_running = False

    def check_milvus(self, host: str = "127.0.0.1", port: int = 19530) -> bool:
        """检查Milvus向量数据库是否可用"""
        try:
            from pymilvus import MilvusClient
            client = MilvusClient(uri=f"http://{host}:{port}")
            client.list_collections()
            self.milvus_running = True
            logger.info(f"Milvus服务可用，监听 {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"无法连接到Milvus服务 {host}:{port}: {e}")
            self.milvus_running = False
            return False

    def check_neo4j(self, uri: str = "bolt://localhost:7687",
                    username: str = "neo4j", password: str = "12345678") -> bool:
        """检查Neo4j图数据库是否可用"""
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(uri, auth=(username, password))

            with driver.session() as session:
                session.run("RETURN 1")

            driver.close()
            self.neo4j_running = True
            logger.info(f"Neo4j服务可用，连接 {uri}")
            return True
        except Exception as e:
            logger.error(f"无法连接到Neo4j服务 {uri}: {e}")
            self.neo4j_running = False
            return False

    def check_redis(self, host: str = "localhost", port: int = 6379, db: int = 0, redis_url: str = None) -> bool:
        """检查Redis是否可用"""
        try:
            import redis
            from urllib.parse import urlparse

            if redis_url and redis_url.startswith("redis://"):
                parsed = urlparse(redis_url)
                host = parsed.hostname or host
                port = parsed.port or port
                db = int(parsed.path.lstrip('/') or 0) if parsed.path else db

            r = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=1)
            r.ping()
            self.redis_running = True
            logger.info(f"Redis服务可用，监听 {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"无法连接到Redis服务 {host}:{port}: {e}")
            self.redis_running = False
            return False

    def check_postgres(self, host: str = "localhost", port: int = 5432,
                      username: str = "postgres", password: str = "postgres",
                      database: str = "knowledge_db") -> bool:
        """检查PostgreSQL是否可用"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                connect_timeout=2
            )
            conn.close()
            self.postgres_running = True
            logger.info(f"PostgreSQL服务可用，监听 {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"无法连接到PostgreSQL服务 {host}:{port}: {e}")
            self.postgres_running = False
            return False

    def check_all_services(self, config: Dict[str, Any]) -> Dict[str, bool]:
        """检查所有数据库服务"""
        status = {}

        milvus_config = config.get("milvus", {})
        status["milvus"] = self.check_milvus(
            host=milvus_config.get("host", "127.0.0.1"),
            port=milvus_config.get("port", 19530)
        )

        neo4j_config = config.get("neo4j", {})
        neo4j_uri = f"bolt://{neo4j_config.get('host', '127.0.0.1')}:{neo4j_config.get('port', 7687)}"
        status["neo4j"] = self.check_neo4j(
            uri=neo4j_uri,
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "12345678")
        )

        redis_url = os.getenv("REDIS_URL")
        status["redis"] = self.check_redis(redis_url=redis_url)

        pg_config = config.get("postgres", {})
        status["postgres"] = self.check_postgres(
            host=pg_config.get("host", "127.0.0.1"),
            port=pg_config.get("port", 5432),
            username=pg_config.get("user", "postgres"),
            password=pg_config.get("password", "postgres"),
            database=pg_config.get("database", "knowledge_db")
        )

        return status

    def _is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr and conn.laddr.port == port:
                    return True
            return False
        except Exception:
            return False

    def get_service_status(self) -> Dict[str, bool]:
        """获取服务状态"""
        return {
            "milvus": self.milvus_running,
            "neo4j": self.neo4j_running,
            "redis": self.redis_running,
            "postgres": getattr(self, "postgres_running", False)
        }


service_checker = DatabaseServiceChecker()

__all__ = ["DatabaseServiceChecker", "service_checker"]
