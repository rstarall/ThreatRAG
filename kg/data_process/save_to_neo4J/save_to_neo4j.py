#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
将JSON格式的实体关系图谱数据保存到Neo4j数据库
"""

import os
import json
import logging
import uuid
from typing import Dict, Any, List
import glob
from neo4j import GraphDatabase
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Neo4jGraphSaver:
    """
    将JSON格式的实体关系图谱数据保存到Neo4j数据库的类
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

    def _generate_u4id(self) -> str:
        """
        生成唯一的u4id标识符

        返回:
            唯一的u4id标识符
        """
        return str(uuid.uuid4())

    def _create_basic_entity(self, entity_name: str, entity_type: str) -> None:
        """
        创建基本实体，只包含名称和类型

        参数:
            entity_name: 实体名称
            entity_type: 实体类型
        """
        query = """
        MERGE (e:`{entity_type}` {{name: $entity_name}})
        RETURN e
        """.format(entity_type=entity_type)

        try:
            with self.driver.session(database=self.database) as session:
                session.run(query, entity_name=entity_name)
                logger.debug(f"创建/确认基本实体: {entity_name}, 类型: {entity_type}")
        except Exception as e:
            logger.error(f"创建基本实体时出错: {str(e)}, 实体: {entity_name}, 类型: {entity_type}")

    def _flatten_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        将嵌套的属性字典扁平化

        参数:
            properties: 嵌套的属性字典

        返回:
            扁平化后的属性字典
        """
        if not properties:
            return {}

        flattened = {}

        # 处理Properties字段
        if "Properties" in properties:
            props = properties["Properties"]
            if isinstance(props, dict):
                for key, value in props.items():
                    flattened[key] = value

        # 处理Labels字段
        if "Labels" in properties:
            labels = properties["Labels"]
            if isinstance(labels, dict) and "Labels" in labels:
                flattened["labels"] = labels["Labels"]
            elif isinstance(labels, list):
                flattened["labels"] = labels

        # 处理EntityVariantNames字段
        if "EntityVariantNames" in properties:
            variant_names = properties["EntityVariantNames"]
            if isinstance(variant_names, dict) and "EntityVariantNames" in variant_names:
                flattened["variant_names"] = variant_names["EntityVariantNames"]
            elif isinstance(variant_names, list):
                flattened["variant_names"] = variant_names

        return flattened

    def process_file(self, file_path: str, save_enhanced: bool = False) -> None:
        """
        处理单个JSON文件并将数据保存到Neo4j

        参数:
            file_path: JSON文件路径
            save_enhanced: 是否保存增强后的JSON数据
        """
        try:
            # 读取JSON文件
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 创建实体和关系的映射
            entity_map = {}

            # 处理实体
            if "Entities" in data and data["Entities"]:
                # 先创建所有实体
                for entity in data["Entities"]:
                    if "EntityName" in entity and "EntityType" in entity:
                        entity_name = entity["EntityName"]
                        entity_type = entity["EntityType"].capitalize()
                        # 创建基本实体
                        self._create_basic_entity(entity_name, entity_type)
                        # 保存到映射中
                        entity_map[entity_name] = entity_type

                # 然后处理实体的详细属性
                self._process_entities(data["Entities"], file_path)
            else:
                logger.warning(f"文件 {file_path} 中没有找到有效的 'Entities' 字段")

            # 处理关系
            if "Relationships" in data and data["Relationships"]:
                # 先确保所有关系中的实体都存在
                for relationship in data["Relationships"]:
                    if "Source" in relationship and "Target" in relationship:
                        source_name = relationship["Source"]
                        target_name = relationship["Target"]

                        # 如果实体不在映射中，创建基本实体
                        if source_name not in entity_map:
                            self._create_basic_entity(source_name, "Entity")
                            entity_map[source_name] = "Entity"

                        if target_name not in entity_map:
                            self._create_basic_entity(target_name, "Entity")
                            entity_map[target_name] = "Entity"

                # 然后处理关系
                self._process_relationships(data["Relationships"], file_path)
            else:
                logger.warning(f"文件 {file_path} 中没有找到有效的 'Relationships' 字段")

            logger.info(f"文件 {file_path} 处理完成")

        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {str(e)}")

    def _process_entities(self, entities: List[Dict[str, Any]], file_path: str) -> None:
        """
        处理实体数据并保存到Neo4j

        参数:
            entities: 实体数据列表
            file_path: 源文件路径
        """
        for entity in entities:
            try:
                # 检查必要的字段
                if not all(k in entity for k in ["EntityId", "EntityName", "EntityType"]):
                    logger.warning(f"实体数据缺少必要字段: {entity}")
                    continue

                # 提取实体属性
                entity_id = entity["EntityId"]
                entity_name = entity["EntityName"]
                entity_type = entity["EntityType"].capitalize()  # 首字母大写
                entity_subtype = entity.get("EntitySubType", "")

                # 扁平化属性
                properties = {}
                properties["id"] = entity_id
                properties["name"] = entity_name
                properties["type"] = entity_type
                properties["subtype"] = entity_subtype

                # 处理其他属性
                if "Properties" in entity:
                    flattened_props = self._flatten_properties(entity["Properties"])
                    properties.update(flattened_props)

                # 处理Labels
                if "Labels" in entity:
                    if isinstance(entity["Labels"], dict) and "Labels" in entity["Labels"]:
                        properties["labels"] = entity["Labels"]["Labels"]
                    elif isinstance(entity["Labels"], list):
                        properties["labels"] = entity["Labels"]

                # 处理EntityVariantNames
                if "EntityVariantNames" in entity:
                    if isinstance(entity["EntityVariantNames"], dict) and "EntityVariantNames" in entity["EntityVariantNames"]:
                        properties["variant_names"] = entity["EntityVariantNames"]["EntityVariantNames"]
                    elif isinstance(entity["EntityVariantNames"], list):
                        properties["variant_names"] = entity["EntityVariantNames"]

                # 保存实体到Neo4j
                self._save_entity_to_neo4j(entity_name, entity_type, properties)
            except Exception as e:
                logger.error(f"处理实体时出错: {str(e)}, 实体: {entity.get('EntityName', 'Unknown')}")

    def _process_relationships(self, relationships: List[Dict[str, Any]], file_path: str) -> None:
        """
        处理关系数据并保存到Neo4j

        参数:
            relationships: 关系数据列表
            file_path: 源文件路径
        """
        for relationship in relationships:
            try:
                # 检查必要的字段
                if not all(k in relationship for k in ["RelationshipId", "RelationshipType", "Source", "Target"]):
                    logger.warning(f"关系数据缺少必要字段: {relationship}")
                    continue

                # 提取关系属性
                relationship_id = relationship["RelationshipId"]
                relationship_type = relationship["RelationshipType"]
                source_name = relationship["Source"]
                target_name = relationship["Target"]

                # 创建关系属性
                properties = {
                    "id": relationship_id
                }

                # 保存关系到Neo4j
                self._save_relationship_to_neo4j(source_name, target_name, relationship_type, properties)
            except Exception as e:
                logger.error(f"处理关系时出错: {str(e)}, 关系: {relationship.get('RelationshipId', 'Unknown')}")

    def _save_entity_to_neo4j(self, entity_name: str, entity_type: str, properties: Dict[str, Any]) -> None:
        """
        将实体保存到Neo4j数据库

        参数:
            entity_name: 实体名称
            entity_type: 实体类型
            properties: 实体属性
        """
        # 创建Cypher查询
        query = """
        MERGE (e:`{entity_type}` {{name: $entity_name}})
        SET e += $properties
        RETURN e
        """.format(entity_type=entity_type)

        # 执行查询
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    query,
                    entity_name=entity_name,
                    properties=properties
                )
                result.consume()
                logger.debug(f"创建/更新了实体: {entity_name}, 类型: {entity_type}")
        except Exception as e:
            logger.error(f"保存实体到Neo4j时出错: {str(e)}")

    def _save_relationship_to_neo4j(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        properties: Dict[str, Any]
    ) -> None:
        """
        将关系保存到Neo4j数据库

        参数:
            source_name: 源实体名称
            target_name: 目标实体名称
            relationship_type: 关系类型
            properties: 关系属性
        """
        # 创建Cypher查询 - 使用MATCH查找已存在的实体
        query = """
        MATCH (source) WHERE source.name = $source_name
        MATCH (target) WHERE target.name = $target_name
        MERGE (source)-[r:`{relationship_type}`]->(target)
        SET r += $properties
        RETURN source, r, target
        """.format(relationship_type=relationship_type.upper())

        # 执行查询
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(
                    query,
                    source_name=source_name,
                    target_name=target_name,
                    properties=properties
                )
                result.consume()
                logger.debug(f"创建/更新了关系: {source_name} -[{relationship_type}]-> {target_name}")
        except Exception as e:
            logger.error(f"保存关系到Neo4j时出错: {str(e)}, 源: {source_name}, 目标: {target_name}")

    def process_directory(self, directory_path: str, pattern: str = "**/*.json", save_enhanced: bool = False) -> None:
        """
        处理目录中的所有JSON文件

        参数:
            directory_path: 目录路径
            pattern: 文件匹配模式
            save_enhanced: 是否保存增强后的JSON数据
        """
        # 获取所有匹配的文件
        file_paths = glob.glob(os.path.join(directory_path, pattern), recursive=True)

        if not file_paths:
            logger.warning(f"在目录 {directory_path} 中没有找到匹配 {pattern} 的文件")
            return

        logger.info(f"找到 {len(file_paths)} 个文件需要处理")

        # 处理每个文件
        for file_path in file_paths:
            self.process_file(file_path, save_enhanced)

        logger.info(f"目录 {directory_path} 处理完成")


def main():
    """
    主函数
    """
    # 加载环境变量
    load_dotenv()

    # 从环境变量获取Neo4j连接信息
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")

    # 数据目录
    data_dir = os.getenv(
        "DATA_DIR",
        os.path.join("kg", "data_process", "extracted_json", "results")
    )

    # 创建Neo4jGraphSaver实例
    saver = Neo4jGraphSaver(
        uri=neo4j_uri,
        username=neo4j_user,
        password=neo4j_password,
        database=neo4j_database
    )

    try:
        # 处理数据目录
        saver.process_directory(data_dir)
    finally:
        # 关闭连接
        saver.close()


if __name__ == "__main__":
    main()