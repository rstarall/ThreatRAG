"""
PostgreSQL 数据库管理器
提供 SQL 数据库的连接和操作功能
"""

import os
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

from .logging_config import logger

Base = declarative_base()


class PostgreSQLManager:
    """PostgreSQL 数据库管理器"""

    def __init__(self, database_url: str = None):
        """初始化 PostgreSQL 管理器

        Args:
            database_url: 数据库连接 URL
        """
        if database_url:
            self.database_url = database_url
        else:
            self.database_url = self._build_database_url()

        self.engine = None
        self.SessionLocal = None
        self._initialize()

    def _build_database_url(self) -> str:
        """从配置构建数据库 URL"""
        from ..config import get_config
        pg_config = get_config().get("postgres", {})

        host = pg_config.get("host", "127.0.0.1")
        port = pg_config.get("port", 5432)
        username = pg_config.get("user", "postgres")
        password = pg_config.get("password", "postgres")
        database = pg_config.get("database", "knowledge_db")

        # 优先使用环境变量覆盖
        host = os.getenv("POSTGRES_HOST", host)
        port = int(os.getenv("POSTGRES_PORT", port))
        username = os.getenv("POSTGRES_USER", username)
        password = os.getenv("POSTGRES_PASSWORD", password)
        database = os.getenv("POSTGRES_DB", database)

        return f"postgresql://{username}:{password}@{host}:{port}/{database}"

    def _initialize(self):
        """初始化数据库连接"""
        try:
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=False
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            logger.info(f"PostgreSQL engine initialized: {self.engine.url.database}@{self.engine.url.host}")

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL engine: {e}")
            raise

    def create_tables(self):
        """创建所有表"""
        try:
            from ..models.orm_models import (
                User,
                KnowledgeDatabase, Document, DocumentChunk,
                ChatSession, ChatMessage, VectorIndexTask, SystemConfig
            )
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise

    def drop_tables(self):
        """删除所有表"""
        try:
            from ..models.orm_models import (
                User,
                KnowledgeDatabase, Document, DocumentChunk,
                ChatSession, ChatMessage, VectorIndexTask, SystemConfig
            )
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise

    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话的上下文管理器

        Yields:
            Session: SQLAlchemy 会话对象
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def execute_raw_sql(self, sql: str, params: Dict[str, Any] = None) -> Any:
        """执行原始 SQL

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            查询结果
        """
        with self.get_session() as session:
            result = session.execute(text(sql), params or {})
            if result.returns_rows:
                return result.fetchall()
            return result.rowcount

    def test_connection(self) -> bool:
        """测试数据库连接

        Returns:
            bool: 连接是否成功
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("PostgreSQL connection test successful")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            logger.info("PostgreSQL connection closed")


# 全局 PostgreSQL 管理器实例
postgres_manager: Optional[PostgreSQLManager] = None


def get_postgres_manager() -> PostgreSQLManager:
    """获取 PostgreSQL 管理器实例"""
    global postgres_manager
    if postgres_manager is None:
        postgres_manager = PostgreSQLManager()
    return postgres_manager


__all__ = ["PostgreSQLManager", "Base", "get_postgres_manager", "postgres_manager"]
