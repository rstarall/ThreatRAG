#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
将 JSON 格式的实体关系图谱数据保存到 Neo4j 数据库。

数据模型统一使用 src.models.graph_model 中定义的 Entity / Relationship / KnowledgeGraph。
Neo4j 存储 schema 与 src/core/graph/neo4j_client.py 保持一致：

- 节点统一使用 :Entity 标签，entityType 作为节点属性存储。
- 属性命名使用 camelCase（entityName / entityType / entityVariantNames 等）。
- entityVariantNames 存储为 JSON 字符串。
- 关系 MERGE 按 entityName 匹配，源/目标节点不存在时自动创建占位节点。

注意：嵌入向量不在本脚本中处理。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

# 让脚本能从任意工作目录运行，自动找到项目根目录下的 src 模块
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)  # 统一工作目录，确保相对路径正确

import glob
from neo4j import GraphDatabase, Driver, Session
from dotenv import load_dotenv

from src.models.graph_model import Entity, Relationship
import src.models.graph_model as _gm

KnowledgeGraph = _gm.KnowledgeGraph


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_VALID_ENTITY_TYPES: Set[str] = {
    "attacker", "victim", "event", "asset", "vul",
    "ioc", "tool", "file", "env",
}
_VALID_RELATIONSHIP_TYPES: Set[str] = {
    "use", "trigger", "involve", "target", "has",
    "exploit", "affect", "related_to", "belong_to",
}
_DEFAULT_LABELS: List[str] = ["TA0001"]


def _serialize_properties(props: Optional[Dict[str, Any]]) -> str:
    """
    将 properties dict 序列化为 JSON 字符串，存入 properties_json 属性。

    空 properties 时返回 '[]'。
    """
    if not props:
        return "[]"
    return json.dumps(props, ensure_ascii=False, separators=(",", ":"))


class Neo4jGraphSaver:
    """
    将 JSON 格式的实体关系图谱数据保存到 Neo4j 数据库。

    所有实体/关系均使用 src.models.graph_model 中定义的 Entity / Relationship 模型，
    并按照 neo4j_client.py 的存储 schema 写入：
      - 节点统一使用 :Entity 标签
      - 属性命名使用 camelCase（entityName / entityType 等）
      - entityVariantNames 存储为 JSON 字符串
    """

    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver: Optional[Driver] = None
        self.is_connected: bool = False
        self._connect()

    # -------------------------------------------------------------------------
    # 连接管理
    # -------------------------------------------------------------------------

    def _connect(self) -> None:
        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.username, self.password),
            )
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            self.is_connected = True
            logger.info(f"Neo4j connected at {self.uri} (database={self.database})")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            self.is_connected = False
            raise

    def close(self) -> None:
        if self.driver:
            self.driver.close()
            self.is_connected = False
            logger.info("Neo4j connection closed")

    def _session(self) -> Session:
        if not self.is_connected:
            raise ConnectionError("Not connected to Neo4j")
        return self.driver.session(database=self.database)  # type: ignore[return-value]

    def _read(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        params = params or {}
        with self._session() as sess:
            result = sess.run(query, params)
            return [dict(record) for record in result]

    def _write(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        with self._session() as sess:
            result = sess.run(query, params)
            counters = result.consume().counters
            return {
                "nodes_created": counters.nodes_created,
                "relationships_created": counters.relationships_created,
                "nodes_deleted": counters.nodes_deleted,
                "relationships_deleted": counters.relationships_deleted,
                "properties_set": counters.properties_set,
            }

    # -------------------------------------------------------------------------
    # Schema 初始化
    # -------------------------------------------------------------------------

    def ensure_schema(self) -> None:
        """
        创建 schema 约束和索引。

        - entityName 全局唯一性约束
        - 全文索引（用于模糊搜索）
        """
        # entityName 唯一性约束
        try:
            self._write(
                "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                "FOR (n) REQUIRE n.entityName IS NOT NULL AND "
                "size([(n)-->() | 1]) >= 0"
            )
        except Exception as exc:
            if "already exists" in str(exc).lower() or "EquivalentSchemaRuleAlreadyExists" in str(exc):
                logger.info("Constraint entity_name_unique already exists")
            else:
                try:
                    self._write(
                        "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                        "FOR (n:Entity) REQUIRE n.entityName IS UNIQUE"
                    )
                    logger.info("Constraint entity_name_unique (Entity label) ensured")
                except Exception as exc2:
                    if "already exists" in str(exc2).lower() or "EquivalentSchemaRuleAlreadyExists" in str(exc2):
                        logger.info("Constraint entity_name_unique already exists")
                    else:
                        logger.warning(f"Failed to create entityName constraint: {exc2}")

    # -------------------------------------------------------------------------
    # Entity 写入
    # -------------------------------------------------------------------------

    def upsert_entity(self, entity: Entity) -> Dict[str, Any]:
        """
        创建或更新单个 Entity 节点。

        节点统一使用 :Entity 标签，entityType / entitySubType 作为节点属性存储。
        entityVariantNames 存储为 JSON 字符串。
        properties 整体序列化为 JSON 字符串存入 properties_json 属性。

        参数:
            entity: Entity 对象

        返回:
            写统计信息（含 nodes_created / properties_set 等）
        """
        variant_names_json = json.dumps(entity.entity_variant_names or [], ensure_ascii=False)
        properties_json = _serialize_properties(entity.properties)

        base_props = [
            "    n.entityId           = $entity_id,",
            "    n.entityType         = $entity_type,",
            "    n.entitySubType      = $entity_sub_type,",
            "    n.labels             = $labels,",
            "    n.times              = $times,",
            "    n.entityVariantNames = $variant_names_json,",
            "    n.properties_json    = $properties_json",
        ]

        params: Dict[str, Any] = {
            "entity_name": entity.entity_name,
            "entity_id": entity.entity_id,
            "entity_type": entity.entity_type,
            "entity_sub_type": entity.entity_sub_type,
            "labels": entity.labels or _DEFAULT_LABELS,
            "times": entity.times or [],
            "variant_names_json": variant_names_json,
            "properties_json": properties_json,
        }

        query = "\n".join([
            "MERGE (n:Entity {entityName: $entity_name})",
            "ON CREATE SET",
            "\n".join(base_props),
            "ON MATCH SET",
            "\n".join(base_props),
            "RETURN elementId(n) AS neo4j_id",
        ])
        return self._write(query, params)

    def upsert_entities_batch(self, entities: List[Entity]) -> Dict[str, Any]:
        """
        批量创建或更新 Entity 节点。

        使用 UNWIND 批量查询，与 neo4j_client.upsert_entities_batch 行为一致。
        properties 整体序列化为 JSON 字符串存入 properties_json 属性。

        参数:
            entities: Entity 对象列表

        返回:
            写统计信息
        """
        if not entities:
            return {"nodes_created": 0}

        prepared = []
        for e in entities:
            row = {
                "entity_id": e.entity_id,
                "entity_name": e.entity_name,
                "entity_type": e.entity_type,
                "entity_sub_type": e.entity_sub_type,
                "labels": e.labels or _DEFAULT_LABELS,
                "times": e.times or [],
                "variant_names_json": json.dumps(e.entity_variant_names or [], ensure_ascii=False),
                "properties_json": _serialize_properties(e.properties),
            }
            prepared.append(row)

        base_lines = [
            "    n.entityId           = row.entity_id,",
            "    n.entityType         = row.entity_type,",
            "    n.entitySubType      = row.entity_sub_type,",
            "    n.labels             = row.labels,",
            "    n.times              = row.times,",
            "    n.entityVariantNames = row.variant_names_json,",
            "    n.properties_json    = row.properties_json",
        ]

        query = "\n".join([
            "UNWIND $entities AS row",
            "MERGE (n:Entity {entityName: row.entity_name})",
            "ON CREATE SET",
            "\n".join(base_lines),
            "ON MATCH SET",
            "\n".join(base_lines),
            "RETURN count(n) AS total",
        ])
        return self._write(query, {"entities": prepared})

    # -------------------------------------------------------------------------
    # Relationship 写入
    # -------------------------------------------------------------------------

    def upsert_relationship(
        self,
        relationship: Relationship,
        source_entity_type: str = "asset",
        target_entity_type: str = "asset",
    ) -> Dict[str, Any]:
        """
        创建或更新单个 Relationship。

        按 entityName 匹配源/目标节点；若节点不存在，会按 source_entity_type /
        target_entity_type 创建占位 :Entity 节点。

        参数:
            relationship:        Relationship 对象
            source_entity_type:  源实体类型（用于创建占位节点）
            target_entity_type:  目标实体类型（用于创建占位节点）

        返回:
            写统计信息
        """
        rt = relationship.relationship_type.lower() if relationship.relationship_type else relationship.relationship_type
        if rt not in _VALID_RELATIONSHIP_TYPES:
            logger.warning(
                f"Unknown relationship type '{rt}', falling back to 'related_to'"
            )
            rt = "related_to"

        query = f"""
        MERGE (s:Entity {{entityName: $source_name}})
        ON MATCH SET
            s.entityType = $source_entity_type
        ON CREATE SET
            s.entityId           = $source_name,
            s.entityType         = $source_entity_type,
            s.entitySubType      = '',
            s.labels             = [],
            s.times              = [],
            s.entityVariantNames = '[]',
            s.properties         = {{}}
        WITH s
        MERGE (t:Entity {{entityName: $target_name}})
        ON MATCH SET
            t.entityType = $target_entity_type
        ON CREATE SET
            t.entityId           = $target_name,
            t.entityType         = $target_entity_type,
            t.entitySubType      = '',
            t.labels             = [],
            t.times              = [],
            t.entityVariantNames = '[]',
            t.properties         = {{}}
        WITH s, t
        MERGE (s)-[r:`{rt}`]->(t)
        SET r.relationshipId = $relationship_id
        RETURN count(r) AS total
        """
        return self._write(query, {
            "source_name": relationship.source,
            "target_name": relationship.target,
            "source_entity_type": source_entity_type,
            "target_entity_type": target_entity_type,
            "relationship_id": relationship.relationship_id,
        })

    def upsert_relationships_batch(
        self,
        relationships: List[Relationship],
        entity_name_to_type: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        批量创建关系。

        每个 Relationship 若源/目标节点不存在，会按 entity_name_to_type 中的类型
        创建占位节点；若 entity_name_to_type 中无记录，默认类型为 "asset"。

        参数:
            relationships:       Relationship 对象列表
            entity_name_to_type: entity_name -> entity_type 映射

        返回:
            写统计信息（含 relationships_created 总计数）
        """
        if not relationships:
            return {"relationships_created": 0}

        entity_name_to_type = entity_name_to_type or {}
        total_created = 0

        for rel in relationships:
            src_type = entity_name_to_type.get(rel.source, "asset")
            tgt_type = entity_name_to_type.get(rel.target, "asset")
            try:
                result = self.upsert_relationship(rel, src_type, tgt_type)
                total_created += result.get("relationships_created", 0)
            except Exception as exc:
                logger.error(
                    f"Failed to upsert relationship "
                    f"{rel.source} -[{rel.relationship_type}]-> {rel.target}: {exc}"
                )

        return {"relationships_created": total_created}

    # -------------------------------------------------------------------------
    # KnowledgeGraph 整体写入
    # -------------------------------------------------------------------------

    def save_knowledge_graph(self, kg: KnowledgeGraph) -> Dict[str, Any]:
        """
        将整个 KnowledgeGraph 批量保存到 Neo4j。

        流程：
        1. 批量 upsert 所有实体
        2. 建立 entity_name -> entity_type 映射
        3. 批量 upsert 所有关系（自动创建占位节点）

        参数:
            kg: KnowledgeGraph 对象

        返回:
            合并后的写统计信息
        """
        if not kg.entities:
            logger.warning("KnowledgeGraph 中没有实体，跳过保存")
            return {"nodes_created": 0}

        stats: Dict[str, Any] = {}

        entity_stats = self.upsert_entities_batch(kg.entities)
        stats["entity_stats"] = entity_stats
        logger.info(f"Saved {kg.entity_count} entities: {entity_stats}")

        entity_name_to_type = {e.entity_name: e.entity_type for e in kg.entities}

        if kg.relationships:
            rel_stats = self.upsert_relationships_batch(
                kg.relationships, entity_name_to_type
            )
            stats["relationship_stats"] = rel_stats
            logger.info(f"Saved {kg.relationship_count} relationships: {rel_stats}")

        return stats

    # -------------------------------------------------------------------------
    # 统计信息
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """返回数据库统计信息。"""
        try:
            node_rows = self._read("MATCH (n:Entity) RETURN count(n) AS count")
            rel_rows = self._read("MATCH ()-[r]->() RETURN count(r) AS count")
            node_count = node_rows[0]["count"] if node_rows else 0
            rel_count = rel_rows[0]["count"] if rel_rows else 0

            type_rows = self._read(
                "MATCH (n:Entity) RETURN n.entityType AS entityType, count(n) AS count"
            )
            type_counts = {r["entityType"]: r["count"] for r in type_rows}

            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "type_counts": type_counts,
                "connected": self.is_connected,
            }
        except Exception as exc:
            logger.error(f"get_stats failed: {exc}")
            return {"error": str(exc), "connected": self.is_connected}

    # -------------------------------------------------------------------------
    # JSON 文件处理
    # -------------------------------------------------------------------------

    def process_file(self, file_path: str) -> Optional[KnowledgeGraph]:
        """
        解析单个 JSON 文件为 KnowledgeGraph 并保存到 Neo4j。

        参数:
            file_path: JSON 文件路径

        返回:
            解析得到的 KnowledgeGraph 对象，失败时返回 None
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            kg = KnowledgeGraph.from_dict(raw)
            self.save_knowledge_graph(kg)
            logger.info(
                f"文件 {file_path} 处理完成"
                f"（{kg.entity_count} 实体, {kg.relationship_count} 关系）"
            )
            return kg

        except json.JSONDecodeError as exc:
            logger.error(f"JSON 解析失败 [{file_path}]: {exc}")
        except FileNotFoundError:
            logger.error(f"文件不存在 [{file_path}]")
        except Exception as exc:
            import traceback
            logger.error(f"处理文件 [{file_path}] 时出错: {exc}\n{traceback.format_exc()}")

        return None

    def process_directory(
        self,
        directory_path: str,
        pattern: str = "**/*.json",
        max_files: Optional[int] = None,
        ensure_schema: bool = True,
    ) -> None:
        """
        处理目录中的所有匹配文件。

        参数:
            directory_path: 目录路径
            pattern: 文件匹配模式
            max_files: 最大处理文件数（None 表示不限制）
            ensure_schema: 是否先创建 schema 约束和索引
        """
        if ensure_schema:
            self.ensure_schema()

        resolved_dir = os.path.join(PROJECT_ROOT, directory_path)
        file_paths = sorted(
            glob.glob(os.path.join(resolved_dir, pattern), recursive=True)
        )

        if not file_paths:
            logger.warning(
                f"在目录 {directory_path} 中没有找到匹配 {pattern} 的文件"
            )
            return

        if max_files:
            file_paths = file_paths[:max_files]

        logger.info(f"找到 {len(file_paths)} 个文件需要处理")

        for file_path in file_paths:
            self.process_file(file_path)

        logger.info(f"目录 {directory_path} 处理完成")


def main():
    """主函数。"""
    load_dotenv()

    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    data_dir = os.path.join("kg", "data_process", "extracted_json", "data", "result_fixed")


    saver = Neo4jGraphSaver(
        uri=neo4j_uri,
        username=neo4j_user,
        password=neo4j_password,
        database=neo4j_database,
    )

    try:
        saver.process_directory(data_dir)
    finally:
        saver.close()


if __name__ == "__main__":
    main()
