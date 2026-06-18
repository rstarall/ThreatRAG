"""
模型管理模块

包含三大类模型：
- LLM / Embedding 模型（chat_model / embedding_model / rerank_model）
- SQLAlchemy ORM 模型（orm_models.py）
- 知识图谱数据结构模型（graph_model.py）
"""

from .chat_model import select_model
from .embedding_model import get_embedding_model
from .rerank_model import get_reranker

__all__ = ["select_model", "get_embedding_model", "get_reranker"]

# SQLAlchemy ORM 模型
from .orm_models import (
    Base,
    User,
    KnowledgeDatabase,
    Document,
    DocumentChunk,
    ChatSession,
    ChatMessage,
    VectorIndexTask,
    SystemConfig,
)

__all__ += [
    "User",
    "Base",
    "KnowledgeDatabase",
    "Document",
    "DocumentChunk",
    "ChatSession",
    "ChatMessage",
    "VectorIndexTask",
    "SystemConfig",
]

# 知识图谱数据结构模型
from .graph_model import (
    # 实体大类
    EntityType,
    # 实体细分子类
    AttackerSubType,
    VictimSubType,
    EventSubType,
    AssetSubType,
    VulSubType,
    IocSubType,
    ToolSubType,
    FileSubType,
    EnvSubType,
    # 关系类型
    RelationshipType,
    # ATT&CK 标签
    TTPLabel,
    # 核心数据模型
    Entity,
    Relationship,
    KnowledgeGraph,
    SubGraph,
    # 搜索参数
    SubGraphSearchParams,
    # 工具函数
    normalize_entity_type,
    build_subgraph_from_search,
)

__all__ += [
    "EntityType",
    "AttackerSubType",
    "VictimSubType",
    "EventSubType",
    "AssetSubType",
    "VulSubType",
    "IocSubType",
    "ToolSubType",
    "FileSubType",
    "EnvSubType",
    "RelationshipType",
    "TTPLabel",
    "Entity",
    "Relationship",
    "KnowledgeGraph",
    "SubGraph",
    "SubGraphSearchParams",
    "normalize_entity_type",
    "build_subgraph_from_search",
]
