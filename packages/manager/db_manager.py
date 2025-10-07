import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from packages.manager.db_model import Base, User
from packages import config
from packages.utils.logging_config import logger

class DBManager:
    """数据库管理器 - 提供MySQL数据库连接和会话管理"""

    def __init__(self):
        # 从环境变量或配置中获取MySQL连接信息
        mysql_host = os.getenv("MYSQL_HOST", "mysql")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_db = os.getenv("MYSQL_DB", "knowledge_db")
        mysql_user = os.getenv("MYSQL_USER", "mysql")
        mysql_password = os.getenv("MYSQL_PASSWORD", "12345678")
        
        # 构建MySQL连接URL
        self.db_url = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
        
        # 创建SQLAlchemy引擎
        self.engine = create_engine(self.db_url)
        
        # 创建会话工厂
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info(f"Database connected to MySQL at {mysql_host}:{mysql_port}")

    def get_session(self):
        """获取数据库会话"""
        return self.Session()

    @contextmanager
    def get_session_context(self):
        """获取数据库会话的上下文管理器"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            session.close()

    def check_first_run(self):
        """检查是否首次运行"""
        session = self.get_session()
        try:
            # 检查是否有任何用户存在
            return session.query(User).count() == 0
        finally:
            session.close()

# 创建全局数据库管理器实例
db_manager = DBManager()