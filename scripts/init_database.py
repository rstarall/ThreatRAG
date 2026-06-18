"""
数据库初始化工具
用于初始化 PostgreSQL 数据库表结构
"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def init_database():
    """初始化数据库表结构"""
    try:
        from src.utils.postgres_manager import PostgreSQLManager
        from src.utils.logging_config import logger

        logger.info("=" * 60)
        logger.info("ThreatRAG 数据库初始化工具")
        logger.info("=" * 60)

        # 创建 PostgreSQL 管理器
        pg_manager = PostgreSQLManager()

        # 测试连接
        if not pg_manager.test_connection():
            logger.error("无法连接到 PostgreSQL 数据库，请检查配置")
            return False

        logger.info("成功连接到 PostgreSQL 数据库")

        # 创建表结构
        logger.info("正在创建数据库表...")
        pg_manager.create_tables()

        logger.info("数据库表创建成功!")
        logger.info("=" * 60)

        return True

    except Exception as e:
        print(f"数据库初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def drop_database():
    """删除所有数据库表"""
    try:
        from src.utils.postgres_manager import PostgreSQLManager
        from src.utils.logging_config import logger

        logger.info("=" * 60)
        logger.info("警告: 即将删除所有数据库表!")
        logger.info("=" * 60)

        pg_manager = PostgreSQLManager()

        if not pg_manager.test_connection():
            logger.error("无法连接到 PostgreSQL 数据库")
            return False

        confirm = input("确认删除所有表? (输入 'yes' 确认): ")
        if confirm.lower() != "yes":
            logger.info("操作已取消")
            return True

        pg_manager.drop_tables()
        logger.info("所有表已删除")

        return True

    except Exception as e:
        print(f"删除数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ThreatRAG 数据库初始化工具")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="删除所有数据库表"
    )

    args = parser.parse_args()

    if args.drop:
        success = drop_database()
    else:
        success = init_database()

    sys.exit(0 if success else 1)
