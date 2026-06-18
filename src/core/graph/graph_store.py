"""
知识图谱存储管理

只负责写操作（增删改）：
- Entity / Relationship 的 upsert / delete
- Schema 约束和索引
- 批量导入 KnowledgeGraph / SubGraph

读操作（子图查询/路径/统计）由 GraphSearcher 提供。
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, List, Any, Optional

from ...config import get_config
from ...utils.logging_config import logger
from ...models.graph_model import (
    Entity,
    Relationship,
    SubGraph,
)
from .neo4j_client import Neo4jClient


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

_VALID_RELATIONSHIP_TYPES: List[str] = [
    "use", "trigger", "involve", "target", "has",
    "exploit", "affect", "related_to", "belong_to",
]

_DEFAULT_LABELS: List[str] = ["TA0001"]


# ---------------------------------------------------------------------------
# GraphStore
# ---------------------------------------------------------------------------

class GraphStore:
    """
    知识图谱存储管理类。

    负责：
    - 连接 / 关闭 Neo4j
    - Entity / Relationship 的增删改（Cypher 写逻辑）

    读操作（子图查询 / 路径 / 统计）由 GraphSearcher 提供。
    """

    def __init__(self, database_name: str = "neo4j") -> None:
        self.database_name = database_name
        self.work_dir = os.path.join(get_config().save_dir, "graph_data", database_name)
        os.makedirs(self.work_dir, exist_ok=True)

        self.client: Optional[Neo4jClient] = None
        self.status: str = "closed"

        self._load_graph_info()
        self._start()

    # -------------------------------------------------------------------------
    # 生命周期
    # -------------------------------------------------------------------------

    def _load_graph_info(self) -> None:
        """加载本地图数据库元信息文件。"""
        info_file = os.path.join(self.work_dir, "graph_info.json")
        try:
            if os.path.exists(info_file):
                with open(info_file, "r", encoding="utf-8") as f:
                    self.graph_info: Dict[str, Any] = json.load(f)
            else:
                self.graph_info = {
                    "database_name": self.database_name,
                    "created_at": None,
                    "node_count": 0,
                    "relationship_count": 0,
                }
        except Exception as exc:
            logger.error(f"Failed to load graph info: {exc}")
            self.graph_info = {}

    def _save_graph_info(self) -> None:
        """持久化图数据库元信息文件。"""
        info_file = os.path.join(self.work_dir, "graph_info.json")
        try:
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(self.graph_info, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error(f"Failed to save graph info: {exc}")

    def _start(self) -> None:
        """启动连接、加载配置、创建索引。"""
        cfg = get_config()
        if not cfg.enable_knowledge_graph:
            logger.info("Knowledge graph is disabled")
            return

        try:
            self.client = Neo4jClient(database=self.database_name)
            self.status = "open"

            if not self.graph_info.get("created_at"):
                self.graph_info["created_at"] = int(time.time())
                self._save_graph_info()

            try:
                self._ensure_constraints_and_indexes()
            except Exception as exc:
                logger.warning(f"Schema setup warning (non-fatal): {exc}")

            logger.info(f"Graph database {self.database_name} started successfully")

        except Exception as exc:
            logger.error(f"Failed to start graph database: {exc}")
            self.status = "closed"
            cfg.enable_knowledge_graph = False

    def _ensure_constraints_and_indexes(self) -> None:
        """创建 schema 约束和索引。"""
        if not self.client:
            return

        # entityName 全局唯一性约束
        try:
            self.client.write(
                "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                "FOR (n:Entity) REQUIRE n.entityName IS NOT NULL"
            )
        except Exception as exc:
            if "already exists" in str(exc).lower() or "EquivalentSchemaRuleAlreadyExists" in str(exc):
                logger.info("Constraint entity_name_unique already exists")
            else:
                try:
                    self.client.write(
                        "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
                        "FOR (n:Entity) REQUIRE n.entityName IS UNIQUE"
                    )
                    logger.info("Constraint entity_name_unique (Entity label) ensured")
                except Exception as exc2:
                    if "already exists" in str(exc2).lower() or "EquivalentSchemaRuleAlreadyExists" in str(exc2):
                        logger.info("Constraint entity_name_unique already exists")
                    else:
                        logger.warning(f"Failed to create entityName constraint: {exc2}")

    def is_running(self) -> bool:
        """检查图数据库是否正常运行。"""
        return self.status == "open" and self.client is not None

    def close(self) -> None:
        """关闭连接。"""
        if self.client:
            self.client.close()
            self.status = "closed"

    # -------------------------------------------------------------------------
    # Entity 写操作（Cypher 直接内联）
    # -------------------------------------------------------------------------

    def upsert_entity(self, entity: Entity) -> bool:
        """创建或更新单个 Entity 节点。"""
        if not self.is_running():
            logger.error("Graph database is not running")
            return False

        labels = entity.labels or _DEFAULT_LABELS
        times = entity.times or []
        entity_variant_names = entity.entity_variant_names or []
        properties = entity.properties or {}
        variant_names_json = json.dumps(entity_variant_names, ensure_ascii=False)

        query = """
        MERGE (n:Entity {entityName: $entity_name})
        ON MATCH SET
            n.entityId           = $entity_id,
            n.entityType         = $entity_type,
            n.entitySubType      = $entity_sub_type,
            n.labels             = $labels,
            n.times              = $times,
            n.entityVariantNames = $variant_names_json,
            n.properties         = $properties
        ON CREATE SET
            n.entityId           = $entity_id,
            n.entityType         = $entity_type,
            n.entitySubType      = $entity_sub_type,
            n.labels             = $labels,
            n.times              = $times,
            n.entityVariantNames = $variant_names_json,
            n.properties         = $properties
        RETURN elementId(n) AS neo4j_id,
               n.entityId     AS entityId,
               n.entityName   AS entityName,
               n.entityType   AS entityType,
               n.entitySubType AS entitySubType
        """
        try:
            self.client.write(query, {
                "entity_name": entity.entity_name,
                "entity_id": entity.entity_id,
                "entity_type": entity.entity_type,
                "entity_sub_type": entity.entity_sub_type,
                "labels": labels,
                "times": times,
                "variant_names_json": variant_names_json,
                "properties": properties,
            })
            logger.debug(f"Upserted entity '{entity.entity_name}' (type={entity.entity_type})")
            return True
        except Exception as exc:
            logger.error(f"Failed to upsert entity {entity.entity_name}: {exc}")
            return False

    def upsert_entities(self, entities: List[Entity]) -> Dict[str, Any]:
        """批量创建或更新 Entity 节点。"""
        if not self.is_running():
            return {"error": "Graph database is not running"}
        if not entities:
            return {"nodes_created": 0}

        def _prep(e: Entity) -> Dict[str, Any]:
            return {
                "entity_id": e.entity_id,
                "entity_name": e.entity_name,
                "entity_type": e.entity_type,
                "entity_sub_type": e.entity_sub_type,
                "labels": e.labels or _DEFAULT_LABELS,
                "times": e.times or [],
                "entity_variant_names": e.entity_variant_names or [],
                "properties": e.properties or {},
                "variant_names_json": json.dumps(e.entity_variant_names or [], ensure_ascii=False),
            }

        prepared = [_prep(e) for e in entities]
        query = """
        UNWIND $entities AS row
        MERGE (n:Entity {entityName: row.entity_name})
        ON CREATE SET
            n.entityId           = row.entity_id,
            n.entityType         = row.entity_type,
            n.entitySubType      = row.entity_sub_type,
            n.labels             = row.labels,
            n.times              = row.times,
            n.entityVariantNames = row.variant_names_json,
            n.properties         = row.properties
        ON MATCH SET
            n.entityId           = row.entity_id,
            n.entityType         = row.entity_type,
            n.entitySubType      = row.entity_sub_type,
            n.labels             = row.labels,
            n.times              = row.times,
            n.entityVariantNames = row.variant_names_json,
            n.properties         = row.properties
        RETURN count(n) AS total
        """
        try:
            return self.client.write(query, {"entities": prepared})
        except Exception as exc:
            logger.error(f"Failed to upsert entities batch: {exc}")
            return {"error": str(exc)}

    def delete_entity(self, entity_name: str) -> bool:
        """删除指定 entityName 的节点及其所有关系。"""
        if not self.is_running():
            return False
        query = """
        MATCH (n:Entity {entityName: $entity_name})
        DETACH DELETE n
        """
        try:
            result = self.client.write(query, {"entity_name": entity_name})
            return result.get("nodes_deleted", 0) > 0
        except Exception as exc:
            logger.error(f"Failed to delete entity '{entity_name}': {exc}")
            return False

    def get_entity(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """按 entityName 精确查找单个 Entity 节点。"""
        if not self.is_running():
            return None
        query = """
        MATCH (n:Entity {entityName: $entity_name})
        RETURN elementId(n) AS neo4j_id,
               n.entityId         AS entityId,
               n.entityName       AS entityName,
               n.entityType       AS entityType,
               n.entitySubType    AS entitySubType,
               n.labels           AS labels,
               n.times            AS times,
               n.entityVariantNames AS entityVariantNames,
               n.properties       AS properties
        LIMIT 1
        """
        try:
            rows = self.client.read(query, {"entity_name": entity_name})
            if not rows:
                return None
            row = rows[0]
            row["entityVariantNames"] = json.loads(row.get("entityVariantNames", "[]"))
            row["labels"] = row.get("labels") or []
            row["times"] = row.get("times") or []
            row["properties"] = row.get("properties") or {}
            return row
        except Exception as exc:
            logger.error(f"Failed to get entity '{entity_name}': {exc}")
            return None

    # -------------------------------------------------------------------------
    # Relationship 写操作（Cypher 直接内联）
    # -------------------------------------------------------------------------

    def upsert_relationship(self, relationship: Relationship) -> bool:
        """创建或更新单个 Relationship。"""
        if not self.is_running():
            logger.error("Graph database is not running")
            return False

        source_entity_type = "asset"
        target_entity_type = "asset"
        if relationship.source_id and "_" in relationship.source_id:
            source_entity_type = relationship.source_id.split("_")[0]
        if relationship.target_id and "_" in relationship.target_id:
            target_entity_type = relationship.target_id.split("_")[0]

        query = f"""
        MERGE (s:Entity {{entityName: $source_name}})
        ON MATCH SET s.entityType = $source_entity_type
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
        ON MATCH SET t.entityType = $target_entity_type
        ON CREATE SET
            t.entityId           = $target_name,
            t.entityType         = $target_entity_type,
            t.entitySubType      = '',
            t.labels             = [],
            t.times              = [],
            t.entityVariantNames = '[]',
            t.properties         = {{}}
        WITH s, t
        MERGE (s)-[r:`{relationship.relationship_type}`]->(t)
        SET r.relationshipId = $relationship_id
        RETURN count(r) AS total
        """
        try:
            self.client.write(query, {
                "source_name": relationship.source,
                "target_name": relationship.target,
                "source_entity_type": source_entity_type,
                "target_entity_type": target_entity_type,
                "relationship_id": relationship.relationship_id,
            })
            return True
        except Exception as exc:
            logger.error(
                f"Failed to upsert relationship "
                f"'{relationship.source}'-[{relationship.relationship_type}]->'{relationship.target}': {exc}"
            )
            return False

    def upsert_relationships(
        self,
        relationships: List[Relationship],
        entity_name_to_type: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """批量创建或更新 Relationship。"""
        if not self.is_running():
            return {"error": "Graph database is not running"}
        if not relationships:
            return {"relationships_created": 0}

        entity_name_to_type = entity_name_to_type or {}
        total = 0

        for r in relationships:
            source_et = entity_name_to_type.get(r.source, "asset")
            target_et = entity_name_to_type.get(r.target, "asset")
            rt = r.relationship_type.lower() if r.relationship_type else r.relationship_type
            if rt not in _VALID_RELATIONSHIP_TYPES:
                rt = "related_to"

            query = f"""
            MERGE (s:Entity {{entityName: $source_name}})
            ON MATCH SET s.entityType = $source_entity_type
            ON CREATE SET
                s.entityId = $source_name, s.entityType = $source_entity_type,
                s.entitySubType = '', s.labels = [], s.times = [],
                s.entityVariantNames = '[]', s.properties = {{}}
            WITH s
            MERGE (t:Entity {{entityName: $target_name}})
            ON MATCH SET t.entityType = $target_entity_type
            ON CREATE SET
                t.entityId = $target_name, t.entityType = $target_entity_type,
                t.entitySubType = '', t.labels = [], t.times = [],
                t.entityVariantNames = '[]', t.properties = {{}}
            WITH s, t
            MERGE (s)-[r:`{rt}`]->(t)
            SET r.relationshipId = $relationship_id
            RETURN count(r) AS total
            """
            try:
                result = self.client.write(query, {
                    "source_name": r.source,
                    "target_name": r.target,
                    "source_entity_type": source_et,
                    "target_entity_type": target_et,
                    "relationship_id": r.relationship_id,
                })
                total += result.get("relationships_created", 0)
            except Exception as exc:
                logger.warning(
                    f"Failed to upsert relationship "
                    f"'{r.source}'-[{rt}]->'{r.target}': {exc}"
                )

        return {"relationships_created": total}

    # -------------------------------------------------------------------------
    # 批量导入
    # -------------------------------------------------------------------------

    def save_knowledge_graph(self, kg: KnowledgeGraph) -> Dict[str, Any]:
        """将 KnowledgeGraph 整体写入 Neo4j。"""
        if not self.is_running():
            return {"error": "Graph database is not running"}

        if not kg.entities and not kg.relationships:
            return {"message": "Nothing to save (empty graph)"}

        stats: Dict[str, Any] = {}

        if kg.entities:
            entity_stats = self.upsert_entities(kg.entities)
            stats["entity_stats"] = entity_stats
            logger.info(f"Saved {len(kg.entities)} entities: {entity_stats}")

        name_to_id = {}
        name_to_type = {}
        for e in kg.entities:
            name_to_id[e.entity_name] = e.entity_id
            name_to_type[e.entity_name] = e.entity_type

        for rel in kg.relationships:
            rel.source_id = name_to_id.get(rel.source)
            rel.target_id = name_to_id.get(rel.target)

        if kg.relationships:
            rel_stats = self.upsert_relationships(kg.relationships, name_to_type)
            stats["relationship_stats"] = rel_stats
            logger.info(f"Saved {len(kg.relationships)} relationships: {rel_stats}")

        return stats

    def save_subgraph(self, subgraph: SubGraph) -> Dict[str, Any]:
        """将 SubGraph 整体写入。"""
        kg = subgraph.to_knowledge_graph()
        return self.save_knowledge_graph(kg)

    # -------------------------------------------------------------------------
    # 统计 / 元信息
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """返回图数据库统计信息。"""
        if not self.is_running():
            return {"error": "Graph database is not running"}
        try:
            node_count = self.client.read(
                "MATCH (n:Entity) RETURN count(n) AS count"
            )[0]["count"]
            rel_count = self.client.read(
                "MATCH ()-[r]->() RETURN count(r) AS count"
            )[0]["count"]
            type_rows = self.client.read(
                "MATCH (n:Entity) RETURN n.entityType AS entityType, count(n) AS count"
            )
            type_counts = {r["entityType"]: r["count"] for r in type_rows}
            return {
                "node_count": node_count,
                "relationship_count": rel_count,
                "type_counts": type_counts,
                "connected": True,
            }
        except Exception as exc:
            logger.error(f"get_stats failed: {exc}")
            return {"error": str(exc), "connected": False}

    def get_graph_info(self) -> Dict[str, Any]:
        """返回图数据库运行时统计和元信息。"""
        if not self.is_running():
            return {"status": "closed", "message": "Graph database is not running"}

        try:
            stats = self.get_stats()
            self.graph_info.update({
                "node_count": stats.get("node_count", 0),
                "relationship_count": stats.get("relationship_count", 0),
                "type_counts": stats.get("type_counts", {}),
                "status": "running",
            })
            self._save_graph_info()
            return {
                **self.graph_info,
                "database_name": self.database_name,
                "work_dir": self.work_dir,
            }
        except Exception as exc:
            logger.error(f"Failed to get graph info: {exc}")
            return {"status": "error", "message": str(exc)}


# ---------------------------------------------------------------------------
# 内部导入避免循环
# ---------------------------------------------------------------------------
from ...models.graph_model import KnowledgeGraph

__all__ = [
    "GraphStore",
    "KnowledgeGraph",
]
