#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
清除Neo4j数据库中的所有数据
"""

import os
import logging
import argparse
from neo4j import GraphDatabase
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Neo4jCleaner:
    """
    清除Neo4j数据库中的所有数据
    """

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """
        初始化Neo4j连接

        参数:
            uri: Neo4j数据库URI
            username: 用户名
            password: 密码
            database: 数据库名称，默认为neo4j
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        self._connect()

    def _connect(self):
        """
        连接到Neo4j数据库
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            logger.info(f"成功连接到Neo4j数据库: {self.uri}")
        except Exception as e:
            logger.error(f"连接Neo4j数据库失败: {str(e)}")
            raise

    def close(self):
        """
        关闭Neo4j连接
        """
        if self.driver:
            self.driver.close()
            logger.info("Neo4j连接已关闭")

    def clear_all_data(self, confirm: bool = False):
        """
        清除数据库中的所有数据

        参数:
            confirm: 是否确认清除操作，默认为False
        """
        if not confirm:
            logger.warning("清除操作未确认，请使用 --confirm 参数确认清除操作")
            return

        try:
            with self.driver.session(database=self.database) as session:
                # 1. 清除所有关系和节点
                query = """
                MATCH (n)
                DETACH DELETE n
                """
                result = session.run(query)
                summary = result.consume()
                nodes_deleted = summary.counters.nodes_deleted
                relationships_deleted = summary.counters.relationships_deleted

                logger.info(f"已清除 {nodes_deleted} 个节点和 {relationships_deleted} 个关系")

                # 2. 获取所有标签
                labels_query = """
                CALL db.labels() YIELD label
                RETURN collect(label) AS labels
                """
                labels_result = session.run(labels_query)
                labels = labels_result.single()["labels"]

                # 3. 获取所有关系类型
                rel_types_query = """
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN collect(relationshipType) AS relationshipTypes
                """
                rel_types_result = session.run(rel_types_query)
                rel_types = rel_types_result.single()["relationshipTypes"]

                logger.info(f"发现 {len(labels)} 个标签和 {len(rel_types)} 个关系类型")

                # 4. 获取所有约束和索引
                constraints_query = """
                SHOW CONSTRAINTS
                """
                try:
                    constraints_result = session.run(constraints_query)
                    constraints = list(constraints_result)

                    # 5. 删除所有约束
                    for constraint in constraints:
                        constraint_name = constraint.get("name", "")
                        if constraint_name:
                            drop_constraint_query = f"""
                            DROP CONSTRAINT {constraint_name}
                            """
                            session.run(drop_constraint_query)
                            logger.info(f"已删除约束: {constraint_name}")
                except Exception as e:
                    logger.warning(f"获取或删除约束时出错: {str(e)}")

                # 6. 获取并删除所有索引
                indexes_query = """
                SHOW INDEXES
                """
                try:
                    indexes_result = session.run(indexes_query)
                    indexes = list(indexes_result)

                    for index in indexes:
                        index_name = index.get("name", "")
                        if index_name:
                            drop_index_query = f"""
                            DROP INDEX {index_name}
                            """
                            session.run(drop_index_query)
                            logger.info(f"已删除索引: {index_name}")
                except Exception as e:
                    logger.warning(f"获取或删除索引时出错: {str(e)}")

                logger.info("数据库清除完成")
        except Exception as e:
            logger.error(f"清除数据库时出错: {str(e)}")
            raise

    def clear_property_labels(self):
        """
        清除所有属性标签
        """
        try:
            with self.driver.session(database=self.database) as session:
                # 获取所有属性键
                property_keys_query = """
                CALL db.propertyKeys() YIELD propertyKey
                RETURN collect(propertyKey) AS propertyKeys
                """
                property_keys_result = session.run(property_keys_query)
                property_keys = property_keys_result.single()["propertyKeys"]

                logger.info(f"发现 {len(property_keys)} 个属性键: {', '.join(property_keys)}")

                # 清除所有属性
                if property_keys:
                    # 对于每个属性键，将所有节点和关系上的该属性设置为null
                    for key in property_keys:
                        # 处理属性名中的特殊字符
                        # 如果属性名包含空格或特殊字符，需要使用反引号包裹
                        safe_key = f"`{key}`" if ' ' in key or '-' in key or '.' in key else key

                        # 清除节点属性
                        node_property_query = f"""
                        MATCH (n)
                        WHERE n.{safe_key} IS NOT NULL
                        SET n.{safe_key} = null
                        """
                        try:
                            session.run(node_property_query)
                            logger.info(f"已清除节点属性: {key}")
                        except Exception as e:
                            logger.warning(f"清除节点属性 {key} 时出错: {str(e)}")

                        # 清除关系属性
                        rel_property_query = f"""
                        MATCH ()-[r]->()
                        WHERE r.{safe_key} IS NOT NULL
                        SET r.{safe_key} = null
                        """
                        try:
                            session.run(rel_property_query)
                            logger.info(f"已清除关系属性: {key}")
                        except Exception as e:
                            logger.warning(f"清除关系属性 {key} 时出错: {str(e)}")

                logger.info("属性标签清除完成")
                logger.info("注意：属性键仍然存在于数据库的元数据中，要完全删除属性键，需要重新启动Neo4j数据库")
        except Exception as e:
            logger.error(f"清除属性标签时出错: {str(e)}")
            raise

    def get_database_stats(self):
        """
        获取数据库统计信息

        返回:
            包含节点数量和关系数量的元组
        """
        # 获取节点数量的Cypher查询
        node_query = """
        MATCH (n)
        RETURN count(n) AS node_count
        """

        # 获取关系数量的Cypher查询
        relationship_query = """
        MATCH ()-[r]->()
        RETURN count(r) AS relationship_count
        """

        # 获取属性键的Cypher查询
        property_keys_query = """
        CALL db.propertyKeys() YIELD propertyKey
        RETURN collect(propertyKey) AS propertyKeys
        """

        # 获取标签的Cypher查询
        labels_query = """
        CALL db.labels() YIELD label
        RETURN collect(label) AS labels
        """

        # 获取关系类型的Cypher查询
        rel_types_query = """
        CALL db.relationshipTypes() YIELD relationshipType
        RETURN collect(relationshipType) AS relationshipTypes
        """

        try:
            with self.driver.session(database=self.database) as session:
                # 获取节点数量
                node_result = session.run(node_query)
                node_count = node_result.single()["node_count"]

                # 获取关系数量
                relationship_result = session.run(relationship_query)
                relationship_count = relationship_result.single()["relationship_count"]

                # 获取属性键
                property_keys_result = session.run(property_keys_query)
                property_keys = property_keys_result.single()["propertyKeys"]

                # 获取标签
                labels_result = session.run(labels_query)
                labels = labels_result.single()["labels"]

                # 获取关系类型
                rel_types_result = session.run(rel_types_query)
                rel_types = rel_types_result.single()["relationshipTypes"]

                logger.info(f"数据库中有 {node_count} 个节点和 {relationship_count} 个关系")
                logger.info(f"数据库中有 {len(labels)} 个标签: {', '.join(labels) if labels else '无'}")
                logger.info(f"数据库中有 {len(rel_types)} 个关系类型: {', '.join(rel_types) if rel_types else '无'}")
                logger.info(f"数据库中有 {len(property_keys)} 个属性键: {', '.join(property_keys) if property_keys else '无'}")

                return node_count, relationship_count
        except Exception as e:
            logger.error(f"获取数据库统计信息时出错: {str(e)}")
            raise

def main():
    """
    主函数
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="清除Neo4j数据库中的所有数据")
    parser.add_argument("--confirm", action="store_true", help="确认清除操作")
    parser.add_argument("--stats", action="store_true", help="仅显示数据库统计信息，不清除数据")
    parser.add_argument("--clear-properties", action="store_true", help="清除所有属性标签")
    parser.add_argument("--clear-all", action="store_true", help="清除所有数据，包括节点、关系、属性标签、索引和约束")
    args = parser.parse_args()

    # 加载环境变量
    load_dotenv()

    # 从环境变量获取Neo4j连接信息
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    # 创建Neo4jCleaner实例
    cleaner = Neo4jCleaner(
        uri=neo4j_uri,
        username=neo4j_user,
        password=neo4j_password,
        database=neo4j_database
    )

    try:
        # 获取数据库统计信息
        cleaner.get_database_stats()

        # 如果只需要显示统计信息，则不清除数据
        if args.stats:
            logger.info("仅显示统计信息，不清除数据")
            return

        # 清除所有数据
        if args.clear_all and args.confirm:
            logger.info("清除所有数据，包括节点、关系、属性标签、索引和约束")
            cleaner.clear_all_data(confirm=True)
            cleaner.clear_property_labels()
            logger.info("所有数据已清除")
        else:
            # 清除节点和关系
            if args.confirm:
                cleaner.clear_all_data(confirm=True)

            # 清除属性标签
            if args.clear_properties and args.confirm:
                cleaner.clear_property_labels()

        # 再次获取数据库统计信息，确认清除结果
        if args.confirm or args.clear_properties or args.clear_all:
            cleaner.get_database_stats()
    finally:
        # 关闭连接
        cleaner.close()

if __name__ == "__main__":
    main()
