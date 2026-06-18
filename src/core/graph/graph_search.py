"""
图搜索封装

基于 GraphStore 提供统一的图搜索接口。
所有搜索结果均以 `SubGraph` / `Entity` / `Relationship` 数据结构返回，
与 src/models/graph_model.py 完全对齐。
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Any, Optional

from ...models.graph_model import (
    Entity,
    Relationship,
    SubGraph,
    SubGraphSearchParams,
)
from .graph_store import GraphStore


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _row_to_entity(row: Dict[str, Any]) -> Entity:
    """将数据库行字典转换为 Entity 对象。"""
    row = dict(row)
    row["entity_id"] = row.pop("entityId", "")
    row["entity_name"] = row.pop("entityName", "")
    row["entity_type"] = row.pop("entityType", "")
    row["entity_sub_type"] = row.pop("entitySubType", "")
    row["labels"] = row.pop("labels", [])
    row["times"] = row.pop("times", [])
    row["properties"] = row.pop("properties", {})
    row["neo4j_id"] = row.pop("neo4j_id", None)
    return Entity.from_dict(row)


def _row_to_relationship(
    row: Dict[str, Any], entity_map: Optional[Dict[str, Entity]] = None
) -> Relationship:
    """将数据库行字典转换为 Relationship 对象。"""
    source_name = row.get("source_name", row.get("source", ""))
    target_name = row.get("target_name", row.get("target", ""))
    return Relationship(
        relationship_id=row.get("relationship_id", ""),
        relationship_type=row["relationship_type"],
        source=source_name,
        target=target_name,
        source_id=entity_map.get(source_name).entity_id
        if entity_map and entity_map.get(source_name) else None,
        target_id=entity_map.get(target_name).entity_id
        if entity_map and entity_map.get(target_name) else None,
    )


class GraphSearcher:
    """
    图搜索封装，对外提供统一的搜索接口。

    内部持有 GraphStore，所有查询直接调用 store.client.read / store.get_entity / store.get_stats。
    """

    def __init__(self, store: Optional[GraphStore] = None) -> None:
        self.store = store

    @property
    def is_running(self) -> bool:
        """检查图数据库是否正常运行。"""
        return self.store is not None and self.store.is_running()

    # -------------------------------------------------------------------------
    # 底层 Cypher 查询（直接调用 client.read）
    # -------------------------------------------------------------------------

    def _search_entities(
        self,
        name_contains: str,
        entity_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """按 entityName 子串模糊搜索节点（裸字典）。"""
        if not self.store or not self.store.client:
            return []
        params: Dict[str, Any] = {"name_contains": name_contains, "limit": limit}
        type_clause = "AND n.entityType = $entity_type" if entity_type else ""
        query = f"""
        MATCH (n:Entity)
        WHERE n.entityName CONTAINS $name_contains {type_clause}
        RETURN elementId(n) AS neo4j_id,
               n.entityId         AS entityId,
               n.entityName       AS entityName,
               n.entityType       AS entityType,
               n.entitySubType    AS entitySubType,
               n.labels           AS labels,
               n.times            AS times,
               n.entityVariantNames AS entityVariantNames,
               n.properties       AS properties
        ORDER BY n.entityName
        LIMIT $limit
        """
        if entity_type:
            params["entity_type"] = entity_type
        rows = self.store.client.read(query, params)
        for row in rows:
            row["entityVariantNames"] = json.loads(row.get("entityVariantNames", "[]"))
            row["labels"] = row.get("labels") or []
            row["times"] = row.get("times") or []
            row["properties"] = row.get("properties") or {}
        return rows

    def _get_relationships(
        self,
        entity_name: str,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取指定实体的所有关系（裸字典）。"""
        if not self.store or not self.store.client:
            return []
        dir_map = {
            "outgoing": "(s)-[r]->(t)",
            "incoming": "(s)<-[r]-(t)",
            "both": "(s)-[r]-(t)",
        }
        cypher_dir = dir_map.get(direction, "(s)-[r]-(t)")
        where_clause = (
            "AND type(r) IN $relationship_types" if relationship_types else ""
        )
        query = f"""
        MATCH (s {{entityName: $entity_name}}){cypher_dir}(t)
        WHERE s.entityName IS NOT NULL AND t.entityName IS NOT NULL {where_clause}
        RETURN type(r)       AS relationshipType,
               r.relationshipId AS relationshipId,
               s.entityName     AS sourceName,
               t.entityName     AS targetName
        LIMIT $limit
        """
        params: Dict[str, Any] = {"entity_name": entity_name, "limit": limit}
        if relationship_types:
            params["relationship_types"] = relationship_types
        return self.store.client.read(query, params)

    def _get_subgraph(
        self,
        start_entity_name: str,
        max_depth: int = 2,
        direction: str = "both",
        entity_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None,
        limit_per_depth: int = 50,
    ) -> Dict[str, Any]:
        """
        BFS 扩展子图查询，返回路径中所有节点和关系（裸字典）。
        """
        if not self.store or not self.store.client:
            return {"nodes": [], "relationships": [], "query_time_ms": 0.0}

        client = self.store.client
        t0 = time.time()
        dir_map = {
            "outgoing": "-[r]->",
            "incoming": "<-[r]-",
            "both": "-[r]-",
        }
        cypher_dir = dir_map.get(direction, "-[r]-")

        rel_filter = (
            f"AND type(r) IN $relationship_types" if relationship_types else ""
        )
        et_params = {f"et{i}": t for i, t in enumerate(entity_types or [])}
        type_where = (
            "AND n.entityType IN $entity_types" if entity_types else ""
        )

        nodes_query = f"""
        MATCH (start {{entityName: $start_name}})
        CALL {{
            WITH start
            MATCH p = (start){cypher_dir}{{0..{max_depth}}} (n)
            WHERE n.entityName IS NOT NULL {type_where}
            RETURN nodes(p) AS ns
            LIMIT $limit
        }}
        UNWIND ns AS node
        WITH collect(DISTINCT node) AS unique_nodes
        UNWIND unique_nodes AS n
        RETURN elementId(n) AS neo4j_id,
               n.entityId         AS entityId,
               n.entityName       AS entityName,
               n.entityType       AS entityType,
               n.entitySubType    AS entitySubType,
               n.labels           AS labels,
               n.times            AS times,
               n.entityVariantNames AS entityVariantNames,
               n.properties       AS properties
        """
        rels_query = f"""
        MATCH (s {{entityName: $start_name}}){cypher_dir}{{0..{max_depth}}}(t)
        WHERE s.entityName IS NOT NULL AND t.entityName IS NOT NULL
        {rel_filter}
        RETURN s.entityName AS sourceName,
               t.entityName AS targetName,
               type(r)       AS relationshipType,
               r.relationshipId AS relationshipId
        LIMIT $limit
        """
        node_params = {
            "start_name": start_entity_name,
            "limit": limit_per_depth,
            "entity_types": entity_types,
            "relationship_types": relationship_types,
            **et_params,
        }
        rel_params = {
            "start_name": start_entity_name,
            "limit": limit_per_depth,
            "relationship_types": relationship_types,
            **et_params,
        }

        try:
            nodes_rows = client.read(nodes_query, node_params)
            rels_rows = client.read(rels_query, rel_params)
        except Exception:
            nodes_rows = client.read(
                """
                MATCH (start {entityName: $start_name})
                MATCH p = (start)-[*0..$max_depth]-(n)
                WHERE n.entityName IS NOT NULL
                WITH start, nodes(p) AS ns
                UNWIND ns AS node
                WITH collect(DISTINCT node) AS unique_nodes
                UNWIND unique_nodes AS n
                RETURN elementId(n) AS neo4j_id,
                       n.entityId         AS entityId,
                       n.entityName       AS entityName,
                       n.entityType       AS entityType,
                       n.entitySubType    AS entitySubType,
                       n.labels           AS labels,
                       n.times            AS times,
                       n.entityVariantNames AS entityVariantNames,
                       n.properties       AS properties
                LIMIT $limit
                """,
                {
                    "start_name": start_entity_name,
                    "max_depth": max_depth,
                    "limit": limit_per_depth,
                },
            )
            rels_rows = client.read(
                """
                MATCH (s {entityName: $start_name})
                MATCH p = (s)-[*0..$max_depth]-(t)
                UNWIND relationships(p) AS rel
                WHERE s.entityName IS NOT NULL AND t.entityName IS NOT NULL
                RETURN startNode(rel).entityName AS sourceName,
                       endNode(rel).entityName AS targetName,
                       type(rel)               AS relationshipType,
                       rel.relationshipId      AS relationshipId
                LIMIT $limit
                """,
                {
                    "start_name": start_entity_name,
                    "max_depth": max_depth,
                    "limit": limit_per_depth,
                },
            )

        nodes: List[Dict[str, Any]] = []
        for row in nodes_rows:
            row["entityVariantNames"] = json.loads(row.get("entityVariantNames", "[]"))
            row["labels"] = row.get("labels") or []
            row["times"] = row.get("times") or []
            row["properties"] = row.get("properties") or {}
            nodes.append(row)

        relationships: List[Dict[str, Any]] = [
            {
                "relationship_id": r.get("relationship_id", ""),
                "relationship_type": r["relationship_type"],
                "source": r["source_name"],
                "target": r["target_name"],
            }
            for r in rels_rows
        ]

        elapsed_ms = (time.time() - t0) * 1000
        return {
            "nodes": nodes,
            "relationships": relationships,
            "query_time_ms": elapsed_ms,
        }

    def _find_shortest_paths(
        self,
        source_name: str,
        target_name: str,
        max_hops: int = 3,
    ) -> List[List[Dict[str, Any]]]:
        """查找两个实体之间的最短路径，返回裸字典列表。"""
        if not self.store or not self.store.client:
            return []

        try:
            rows = self.store.client.read(
                """
                MATCH path = shortestPath(
                    (s:Entity {entityName: $source})-[*1..$max_hops]-(t:Entity {entityName: $target})
                )
                WITH path
                UNWIND nodes(path) AS node
                WITH path, collect({
                    entityId: node.entityId,
                    entityName: node.entityName,
                    entityType: node.entityType,
                    entitySubType: node.entitySubType,
                    labels: node.labels,
                    times: node.times,
                    properties: node.properties,
                    entityVariantNames: node.entityVariantNames
                }) AS nodes
                RETURN nodes
                """,
                {"source": source_name, "target": target_name, "max_hops": max_hops},
            )
            if not rows:
                return []

            paths: List[List[Dict[str, Any]]] = []
            for row in rows:
                nodes = row.get("nodes", [])
                path_nodes = []
                for n in nodes:
                    n["entityVariantNames"] = json.loads(n.get("entityVariantNames", "[]"))
                    n["labels"] = n.get("labels") or []
                    n["times"] = n.get("times") or []
                    n["properties"] = n.get("properties") or {}
                    path_nodes.append(n)
                paths.append(path_nodes)
            return paths

        except Exception:
            return []

    # -------------------------------------------------------------------------
    # 实体搜索
    # -------------------------------------------------------------------------

    def search_entities(
        self,
        name_contains: str,
        entity_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Entity]:
        """按 entityName 子串搜索 Entity 列表。"""
        if not self.is_running:
            return []
        rows = self._search_entities(name_contains, entity_type, limit)
        return [_row_to_entity(row) for row in rows]

    def get_entity(self, entity_name: str) -> Optional[Entity]:
        """按名称精确获取单个 Entity。"""
        if not self.store:
            return None
        row = self.store.get_entity(entity_name)
        if not row:
            return None
        return _row_to_entity(row)

    # -------------------------------------------------------------------------
    # 子图搜索
    # -------------------------------------------------------------------------

    def query_subgraph(self, params: SubGraphSearchParams) -> SubGraph:
        """BFS 扩展子图查询。"""
        if not self.is_running:
            return SubGraph(start_entity_name=params.start_entity_name, max_depth=params.max_depth)
        params.validate()

        raw = self._get_subgraph(
            start_entity_name=params.start_entity_name,
            max_depth=params.max_depth,
            direction=params.direction,
            entity_types=params.entity_types,
            relationship_types=params.relationship_types,
            limit_per_depth=params.limit_per_depth or 50,
        )

        entity_map: Dict[str, Entity] = {}
        for n in raw["nodes"]:
            entity = _row_to_entity(n)
            entity_map[entity.entity_name] = entity

        start_entity = entity_map.get(params.start_entity_name)
        if start_entity is None:
            start_row = self.store.get_entity(params.start_entity_name)
            if start_row:
                start_entity = _row_to_entity(start_row)
                entity_map[start_entity.entity_name] = start_entity

        relationships = [
            _row_to_relationship(r, entity_map)
            for r in raw["relationships"]
        ]

        return SubGraph(
            entities=list(entity_map.values()),
            relationships=relationships,
            start_entity_name=params.start_entity_name,
            max_depth=params.max_depth,
            query_time_ms=raw.get("query_time_ms"),
        )

    def get_subgraph(
        self,
        start_entity_name: str,
        max_depth: int = 2,
        direction: str = "both",
        entity_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None,
        limit_per_depth: int = 50,
    ) -> SubGraph:
        """BFS 子图扩展查询。"""
        params = SubGraphSearchParams(
            start_entity_name=start_entity_name,
            max_depth=max_depth,
            direction=direction,
            entity_types=entity_types,
            relationship_types=relationship_types,
            limit_per_depth=limit_per_depth,
        )
        return self.query_subgraph(params)

    def query_node(self, entity_name: str, limit: int = 10) -> SubGraph:
        """查询单个节点及其关联子图（depth=1）。"""
        params = SubGraphSearchParams(
            start_entity_name=entity_name,
            max_depth=1,
            direction="both",
            limit_per_depth=limit,
        )
        return self.query_subgraph(params)

    def get_neighbors(
        self,
        entity_name: str,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> SubGraph:
        """获取实体的直接邻居（depth=1）。"""
        return self.get_subgraph(
            start_entity_name=entity_name,
            max_depth=1,
            direction=direction,
            relationship_types=relationship_types,
            limit_per_depth=limit,
        )

    # -------------------------------------------------------------------------
    # 关系搜索
    # -------------------------------------------------------------------------

    def get_relationships(
        self,
        entity_name: str,
        direction: str = "both",
        relationship_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Relationship]:
        """获取指定实体的所有关系。"""
        if not self.store:
            return []
        rows = self._get_relationships(entity_name, direction, relationship_types, limit)
        return [_row_to_relationship(r) for r in rows]

    # -------------------------------------------------------------------------
    # 路径查询
    # -------------------------------------------------------------------------

    def find_paths(
        self,
        source_name: str,
        target_name: str,
        max_hops: int = 3,
    ) -> List[List[Entity]]:
        """查找两个实体之间的最短路径（多条）。"""
        if not self.is_running:
            return []
        paths = self._find_shortest_paths(source_name, target_name, max_hops)
        if not paths:
            return []
        result: List[List[Entity]] = []
        for path_nodes in paths:
            entities = [_row_to_entity(row) for row in path_nodes]
            result.append(entities)
        return result

    # -------------------------------------------------------------------------
    # 统计
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """返回图数据库统计信息。"""
        if not self.store:
            return {"error": "GraphStore not initialized"}
        return self.store.get_stats()

    def get_graph_nodes(self, num: int = 50) -> Dict[str, Any]:
        """获取图节点列表（nodes + edges），用于可视化。"""
        if not self.store or not self.store.client:
            return {"message": "Graph database not running", "status": "failed"}

        rows = self.store.client.read(
            """
            MATCH (n:Entity)-[r]-(m:Entity)
            RETURN n, r, m
            LIMIT $limit
            """,
            {"limit": num},
        )

        nodes_dict: Dict[str, Dict[str, Any]] = {}
        edges: List[Dict[str, Any]] = []

        for record in rows:
            node_n = record["n"]
            node_n_id = str(node_n.get("elementId", ""))
            if node_n_id not in nodes_dict:
                nodes_dict[node_n_id] = {
                    "id": node_n_id,
                    "name": node_n.get("entityName", ""),
                    "label": node_n.get("entityType", "Entity"),
                    "properties": dict(node_n),
                }

            node_m = record["m"]
            node_m_id = str(node_m.get("elementId", ""))
            if node_m_id not in nodes_dict:
                nodes_dict[node_m_id] = {
                    "id": node_m_id,
                    "name": node_m.get("entityName", ""),
                    "label": node_m.get("entityType", "Entity"),
                    "properties": dict(node_m),
                }

            relationship = record["r"]
            rel_id = str(relationship.get("elementId", ""))
            edges.append({
                "id": rel_id,
                "source": node_n_id,
                "target": node_m_id,
                "source_name": node_n.get("entityName", ""),
                "target_name": node_m.get("entityName", ""),
                "type": relationship.type if hasattr(relationship, "type") else "RELATED",
                "properties": dict(relationship),
            })

        return {
            "status": "success",
            "nodes": list(nodes_dict.values()),
            "edges": edges,
            "stats": {
                "node_count": len(nodes_dict),
                "edge_count": len(edges),
            },
        }


__all__ = ["GraphSearcher"]
