# ThreatRAG 数据库架构说明

## 概述

本项目采用**多数据库架构**，分离 SQL 数据库和向量数据库的职责，实现清晰的分层和解耦。

## 数据库类型

| 数据库 | 用途 | 技术栈 |
|--------|------|--------|
| **PostgreSQL** | 结构化数据存储 | SQLAlchemy ORM |
| **Milvus** | 向量数据存储 | 向量检索 |
| **Neo4j** | 知识图谱存储 | 图数据库 |
| **Redis** | 会话缓存 | Key-Value 缓存 |

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        ThreatRAG 应用层                          │
├─────────────────────────────────────────────────────────────────┤
│  services/         │  core/knowledge/  │  core/graph/           │
│  - chat_service    │  - knowledge_base │  - graph_store         │
│  - knowledge_svc   │  - vector_store   │  - neo4j_client       │
└─────────┬─────────┴────────┬──────────┴────────┬────────────────┘
          │                  │                   │
          ▼                  ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │     Milvus       │  │     Neo4j       │
│  (元数据存储)    │  │  (向量存储)       │  │  (图谱存储)      │
│                 │  │                  │  │                  │
│ - knowledge_db  │  │ - Collection     │  │ - Entity        │
│ - documents     │  │ - Vector         │  │ - Relationship  │
│ - chat_sessions │  │                  │  │                  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │
          ▼
┌─────────────────┐
│     Redis       │
│  (会话缓存)      │
│                 │
│ - session:*     │
└─────────────────┘
```

## 文件结构

```
src/
├── config/
│   └── config.py              # 配置管理 (包含 PostgreSQL 配置)
├── models/
│   ├── __init__.py           # 模型导出
│   ├── orm_models.py         # SQLAlchemy ORM 模型定义
│   ├── embedding_model.py    # 嵌入模型
│   └── rerank_model.py       # 重排序模型
└── utils/
    ├── __init__.py           # 工具模块导出
    ├── database_manager.py   # 服务状态检查器
    ├── postgres_manager.py   # PostgreSQL 管理器
    └── vector_db_manager.py  # Milvus 向量数据库管理器
```

## 核心组件

### 1. PostgreSQL 管理器 (`src/utils/postgres_manager.py`)

```python
PostgreSQLManager
├── engine: SQLAlchemy Engine
├── SessionLocal: Session 工厂
├── create_tables(): 创建所有表
├── drop_tables(): 删除所有表
├── get_session(): 获取会话上下文管理器
└── test_connection(): 测试连接
```

### 2. 向量数据库管理器 (`src/utils/vector_db_manager.py`)

```python
VectorDBManager (Milvus)
├── client: MilvusClient
├── create_collection(): 创建集合
├── insert_vectors(): 插入向量
├── search_vectors(): 搜索向量
├── delete_collection(): 删除集合
└── get_collection_stats(): 获取统计
```

### 3. 服务状态检查器 (`src/utils/database_manager.py`)

```python
DatabaseServiceChecker
├── check_milvus(): 检查 Milvus
├── check_neo4j(): 检查 Neo4j
├── check_redis(): 检查 Redis
├── check_postgres(): 检查 PostgreSQL
└── check_all_services(): 检查所有服务
```

### 4. ORM 模型 (`src/models/orm_models.py`)

| 模型 | 表名 | 说明 |
|------|------|------|
| `KnowledgeDatabase` | knowledge_databases | 知识库信息 |
| `Document` | documents | 文档信息 |
| `DocumentChunk` | document_chunks | 文档块 |
| `ChatSession` | chat_sessions | 会话 |
| `ChatMessage` | chat_messages | 消息 |
| `VectorIndexTask` | vector_index_tasks | 向量索引任务 |
| `SystemConfig` | system_config | 系统配置 |

## 配置

### PostgreSQL 配置 (`config.yaml`)

```yaml
postgres:
  host: "127.0.0.1"
  port: 5432
  username: "postgres"
  password: "postgres"
  database: "knowledge_db"
  pool_size: 5
  max_overflow: 10
```

### 环境变量覆盖

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_HOST` | 主机地址 | 127.0.0.1 |
| `POSTGRES_PORT` | 端口 | 5432 |
| `POSTGRES_USER` | 用户名 | postgres |
| `POSTGRES_PASSWORD` | 密码 | postgres |
| `POSTGRES_DB` | 数据库名 | knowledge_db |

## 使用示例

### 1. 初始化数据库

```bash
# 使用 Docker 启动 PostgreSQL
docker-compose up -d postgres

# 初始化表结构
python scripts/init_database.py
```

### 2. 在代码中使用

```python
# 方式 1: 直接使用 PostgreSQL 管理器
from src.utils.postgres_manager import get_postgres_manager

pg_manager = get_postgres_manager()
with pg_manager.get_session() as session:
    # 执行数据库操作
    pass

# 方式 2: 使用 ORM 模型
from src.models.orm_models import KnowledgeDatabase

pg_manager = get_postgres_manager()
with pg_manager.get_session() as session:
    db = KnowledgeDatabase(
        db_id="test",
        name="Test DB",
        description="Test"
    )
    session.add(db)

# 方式 3: 使用知识库核心类
from src.core.knowledge.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
kb.create_database("my_db", "My Database")
```

## 数据库初始化 SQL

参考 `scripts/init-postgres.sql` 文件，该文件定义了完整的表结构、索引和触发器。

### 主要表结构

- `knowledge_databases`: 知识库表
- `documents`: 文档表
- `document_chunks`: 文档块表
- `chat_sessions`: 会话表
- `chat_messages`: 消息表
- `vector_index_tasks`: 向量索引任务表
- `system_config`: 系统配置表

## 迁移说明

如果从旧版本的基于文件的数据库迁移，请注意：

1. 旧代码使用 `knowledge_base.py` 中的 `DatabaseManager` 类管理文件存储
2. 新代码使用 PostgreSQL 存储元数据，Milvus 存储向量
3. 需要运行 `scripts/init_database.py` 初始化新的数据库表
4. 旧数据需要迁移到新的数据库中

## 常见问题

### Q: 如何查看 PostgreSQL 数据库？
```bash
# 使用 psql 连接
psql -h localhost -U postgres -d knowledge_db

# 使用 Docker
docker exec -it threatrag-postgres psql -U postgres -d knowledge_db
```

### Q: 如何重置数据库？
```bash
python scripts/init_database.py --drop
python scripts/init_database.py
```
