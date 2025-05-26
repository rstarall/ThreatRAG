import os
import sqlite3
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pathlib import Path

# 获取项目根目录
def get_project_root():
    current_path = Path(__file__).resolve()
    root_indicators = ['.git', 'requirements.txt', 'pyproject.toml', 'setup.py', 'README.md']

    for parent in current_path.parents:
        if any((parent / indicator).exists() for indicator in root_indicators):
            return str(parent)

    return str(current_path.parent.parent.parent)

Base = declarative_base()
class DBManager:
    """数据库管理器"""

    def __init__(self):
        project_root = get_project_root()
        self.db_path = os.path.join(project_root, "saves", "data", "server.db")
        self.ensure_db_dir()

        # 创建SQLAlchemy引擎
        self.engine = create_engine(f"sqlite:///{self.db_path}")

        # 创建会话工厂
        self.Session = sessionmaker(bind=self.engine)

        # 确保表存在
        self.create_tables()

    def ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        pathlib.Path(db_dir).mkdir(parents=True, exist_ok=True)

    def create_tables(self):
        """创建数据库表"""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """获取数据库会话"""
        return self.Session()

# 创建全局数据库管理器实例
db_manager = DBManager()