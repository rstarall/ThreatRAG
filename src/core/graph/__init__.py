"""
知识图谱核心模块

三层结构：
- Neo4jClient：Neo4j 连接 + read/write 原语（不包含任何业务 Cypher）
- GraphStore：所有写操作（Cypher 内联）+ get_entity / get_stats 必要读
- GraphSearcher：所有查询操作（子图/路径/关系），持有 GraphStore
"""

from .graph_store import GraphStore
from .neo4j_client import Neo4jClient
from .graph_extract import (
    GraphExtractor,
    ExtractionTask,
    ExtractionResult,
    get_graph_extractor,
    extract_graph_from_text,
)
from .graph_search import GraphSearcher

__all__ = [
    # 存储相关
    "GraphStore",
    "Neo4jClient",
    # 实体关系抽取
    "GraphExtractor",
    "ExtractionTask",
    "ExtractionResult",
    "get_graph_extractor",
    "extract_graph_from_text",
    # 图搜索
    "GraphSearcher",
]
