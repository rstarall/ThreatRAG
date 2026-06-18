# ThreatRAG

ThreatRAG 是一个面向网络威胁情报（CTI）的检索增强生成（RAG）框架，结合向量知识库与 Neo4j 知识图谱，为安全分析师提供智能化的威胁情报分析与问答能力。

![前端界面](docs/imgs/frontend.png)

## 功能特点

- **智能检索**：基于 BAAI/bge-m3 嵌入的向量相似度检索，可选 bge-m3 重排序模型，并支持基于对话历史的查询改写
- **混合 RAG**：同时从向量知识库与知识图谱中检索，自动合并并排序结果后送给大模型
- **文档管理**：支持 TXT、MD、DOC、DOCX、PDF 等多种格式文档上传，自动分块、向量化，元数据存入 PostgreSQL
- **知识图谱构建**：基于大模型从非结构化威胁情报报告中抽取实体与关系，使用 XML 提示词约束，最终持久化到 Neo4j
- **图谱查询与增强**：实体搜索、BFS 子图扩展、最短路径查询，并在对话中基于图谱结果增强回答
- **流式对话**：基于 SSE 的流式输出，原生支持带推理内容（如 DeepSeek-R1）的模型
- **会话与认证**：基于 Redis 的会话管理，配合 bcrypt 实现的用户注册与登录
- **多模型支持**：内置 DeepSeek、SiliconFlow 等多家 LLM 提供商（DeepSeek-V3、DeepSeek-R1、Qwen2.5 等）
- **健康检查**：`/health` 端点实时报告 Milvus、Neo4j、Redis、PostgreSQL 等依赖服务的状态
- **一键部署**：通过 Docker Compose 一键拉起 PostgreSQL、Redis、Neo4j、Milvus、etcd、MinIO 及 API 服务

## 项目架构

```
ThreatRAG/
├── main.py                       # 服务启动入口
├── config.yaml                   # 统一配置（模型、数据库、服务、KG、KB 等）
├── requirements.txt
├── docker-compose.yml            # 生产部署
├── docker-compose.dev.yml        # 开发部署（支持热重载）
├── Dockerfile
├── data/                         # 运行时数据（图谱数据、知识库、上传文件）
├── docs/                         # API 文档、CTI 样本、架构说明
├── kg/
│   └── data_process/             # 离线知识图谱抽取流水线
│       ├── batch_inference/      # 批量 LLM 推理脚本
│       ├── extracted_entities/   # 抽取出的原始实体
│       ├── extracted_json/       # 抽取出的 JSON、约束修正与导入脚本
│       ├── ner/                  # NER / 图谱模型定义
│       ├── prompts/              # XML 抽取提示词（中文 / 英文）
│       └── save_to_neo4J/        # 写入 Neo4j 的脚本
├── models/                       # 本地模型权重（bge-m3 等）
├── scripts/                      # SQL / Shell 辅助脚本（init-postgres.sql、init-services.sh 等）
├── src/
│   ├── api/                      # FastAPI 服务与路由
│   │   ├── server.py
│   │   └── routers/              # chat / knowledge / graph / user
│   ├── config/                   # 配置加载
│   ├── core/
│   │   ├── chat/                 # ChatEngine、SessionManager
│   │   ├── graph/                # GraphStore、GraphSearcher、GraphExtractor、Neo4jClient
│   │   ├── knowledge/            # KnowledgeBase、VectorStore
│   │   ├── retrieval/            # Retriever、QueryProcessor、ResultMerger
│   │   └── user/                 # 用户管理
│   ├── models/                   # chat_model、embedding_model、rerank_model、graph_model、orm_models
│   ├── prompts/                  # 图谱抽取提示词（中文）
│   ├── services/                 # chat / knowledge / graph / user 业务服务
│   └── utils/                    # database_manager、postgres_manager、vector_db_manager、llm_client、xml_parser 等
└── tests/                        # 单元、集成、端到端测试
```

## 快速开始

### 1. 环境准备

```bash
git clone https://github.com/yourusername/ThreatRAG.git
cd ThreatRAG
pip install -r requirements.txt
```

### 2. 配置环境变量

复制并按需修改环境变量文件：

```bash
cp .env.example .env
```

`.env` 中的关键配置：

```
# 基础模型
BASE_MODEL=deepseek-ai/DeepSeek-V3

# Neo4j
NEO4J_URL=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=12345678
NEO4J_DATABASE=neo4j

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=knowledge_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=12345678

# Redis
REDIS_URL=redis://localhost:6379

# 大模型服务商
SILICONFLOW_API_KEY=sk-xxxxxxxx
SILICONFLOW_API_BASE=https://api.siliconflow.cn/v1
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

`config.yaml` 中还提供了更多运行时开关（知识库 / 知识图谱 / 重排 / 查询改写 / 模型提供方等）。

### 3. 启动服务

#### 方式一：Docker Compose（推荐）

```bash
docker-compose up -d
```

将自动拉起 PostgreSQL、Redis、Neo4j、Milvus（etcd + MinIO）以及 ThreatRAG API 服务。

API 默认监听 `http://localhost:8000`，交互式文档：

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

#### 方式二：本地直接运行

自行启动 PostgreSQL、Redis、Neo4j、Milvus 等依赖后执行：

```bash
python main.py
```

### 4. 数据库连接信息

| 服务       | 端口  | 访问方式                          | 默认账号 / 密码          |
| ---------- | ----- | --------------------------------- | ----------------------- |
| Neo4j      | 7474  | http://localhost:7474/browser/    | `neo4j` / `12345678`    |
| Milvus     | 19530 | pymilvus / Attu                   | （依实际配置）           |
| PostgreSQL | 5432  | `psql -h localhost -U postgres`   | `postgres` / `12345678` |
| Redis      | 6379  | `redis-cli`                       | （无密码）               |

## 模块说明

### API 服务（`src/api`）

基于 FastAPI 实现的接口，主要包括：

- `POST /chat/` —— 支持流式输出的聊天接口（SSE），可按需启用知识库 / 知识图谱检索
- `GET /chat/session/{id}`、`DELETE /chat/session/{id}`、`GET /chat/sessions`、`PUT /chat/session/{id}/title` —— 会话管理
- `GET /chat/models/{provider}` —— 列出指定提供方可用模型
- `GET /knowledge/`、`POST /knowledge/`、`DELETE /knowledge/{db_id}` —— 知识库增删查
- `POST /knowledge/{db_id}/upload` —— 上传文档（TXT、MD、DOC、DOCX、PDF）
- `POST /knowledge/{db_id}/documents` —— 直接添加文本块
- `POST /knowledge/{db_id}/query`、`POST /knowledge/query-test` —— 向量检索 / 查询测试
- `GET /graph/`、`GET /graph/node`、`GET /graph/nodes`、`GET /graph/stats` —— 图谱概览
- `POST /graph/query` —— 按实体列表检索子图
- `POST /graph/extract` —— 同步从原始文本中抽取实体与关系
- `POST /graph/extract-and-save` —— 异步抽取并写入图谱
- `POST /auth/register`、`POST /auth/login`、`GET /auth/user/{id}`、`POST /auth/change-password` —— 用户认证

### 对话引擎（`src/core/chat`）

- `ChatEngine`：负责检索增强、提示词组装、流式生成、会话历史管理
- `SessionManager`：基于 Redis 的会话持久化，支持自动生成会话标题

### 检索模块（`src/core/retrieval`）

- `Retriever`：并发调度实体抽取、知识库查询、知识图谱查询，并拼接增强后的提示
- `QueryProcessor`：关键词提取、查询清洗、查询扩展、意图分析
- `ResultMerger`：合并知识库与图谱结果，去重、按相关度排序并生成摘要

### 知识库（`src/core/knowledge`）

- `KnowledgeBase`：知识库的创建、删除、文档上传 / 添加、向量检索
- `VectorStore`：Milvus 客户端封装，负责集合管理与向量搜索
- 文档元数据（知识库、文档、文档块、会话、消息、向量索引任务等）通过 SQLAlchemy ORM 存入 PostgreSQL

### 知识图谱（`src/core/graph`）

- `GraphStore`：Neo4j 驱动封装，负责实体与关系的读写
- `GraphSearcher`：实体搜索、BFS 子图扩展、最短路径、统计信息
- `GraphExtractor`：调用大模型结合 XML 提示词（`xml_prompt_cn.md` / `xml_prompt_en.md`）从威胁情报文本中抽取实体和关系
- `Neo4jClient`：底层 Neo4j 读写辅助

### 知识图谱数据处理（`kg/data_process`）

将原始 CTI 报告离线转换为 Neo4j 中可用的图数据：

1. `batch_inference/`：准备 / 提交 / 处理 LLM 批处理任务
2. `extracted_json/`：存放抽取结果；`fix_relationship_constraints.py` 用于约束实体类型与关系类型的一致性
3. `save_to_neo4J/save_to_neo4j.py`：将修正后的 JSON 批量导入 Neo4j

XML 提示词定义了 9 类实体（attacker、victim、event、asset、vul、ioc、tool、file、env）、9 类关系、MITRE ATT&CK 战术标签以及每个实体在攻击链中的时序。

## 前端界面

前端项目仓库：[https://github.com/rstarall/br-cti-chat](https://github.com/rstarall/br-cti-chat)

## 文档

- `docs/API/api.md` —— REST API 接口文档
- `docs/database-architecture.md` —— 多数据库架构说明
- `docs/neo4j-node-label-design.md` —— Neo4j 节点标签设计
- `docs/CTI/` —— 示例威胁情报报告

## 贡献指南

欢迎贡献代码或提出问题。请遵循以下步骤：

1. Fork 项目
2. 创建特性分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add some amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证，详情请参阅 [LICENSE](LICENSE) 文件。
