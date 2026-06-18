# ThreatRAG API 接口文档

> **Base URL**: `http://<host>:<port>` （默认 `http://localhost:8000`）  
> **版本**: v2.0.0  
> **在线文档**: Swagger UI (`/docs`) | ReDoc (`/redoc`)

---

## 目录

1. [通用说明](#通用说明)
2. [系统接口](#系统接口)
3. [聊天接口 (Chat)](#聊天接口-chat)
4. [知识库接口 (Knowledge)](#知识库接口-knowledge)
5. [知识图谱接口 (Graph)](#知识图谱接口-graph)
6. [用户认证接口 (Auth)](#用户认证接口-auth)

---

## 通用说明

### 请求与响应规范

- 所有 API 均返回 JSON 格式数据（流式接口除外）。
- 成功时响应体中包含 `"status": "success"` 或 `"success": true`。
- 失败时返回 HTTP 错误状态码或响应体中包含 `"status": "failed"` / `"success": false`，并附带 `message` 或 `error` 说明。
- 所有 HTTP 错误统一返回以下格式：

```json
{
  "detail": "错误描述信息"
}
```

### 全局错误响应

```json
{
  "error": "Internal Server Error",
  "message": "服务器内部错误，请稍后重试",
  "detail": null
}
```

### CORS

本 API 已开启全局 CORS，`allow_origins: ["*"]`，生产环境请在 `src/api/server.py` 中指定具体前端域名。

---

## 系统接口

### 健康检查

#### `GET /`

根路径健康检查，返回服务基本信息。

**响应示例**

```json
{
  "message": "ThreatRAG API Server",
  "status": "ok",
  "version": "2.0.0"
}
```

---

#### `GET /health`

详细健康检查，返回各依赖服务和功能模块状态。

**响应示例**

```json
{
  "status": "ok",
  "version": "2.0.0",
  "services": {
    "milvus": true,
    "neo4j": true,
    "redis": true
  },
  "features": {
    "knowledge_base": true,
    "knowledge_graph": true,
    "reranker": true,
    "web_search": false
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 整体状态：`ok` / `warning` |
| `services` | object | 各后端服务可用性 |
| `features` | object | 各功能模块开关状态 |

---

## 聊天接口 (Chat)

**路由前缀**: `/chat`

---

### 聊天接口 GET 测试

#### `GET /chat/`

**说明**: 聊天接口健康检查。

**响应示例**

```json
{
  "message": "Chat API is working",
  "status": "ok"
}
```

---

### 发送聊天消息（流式）

#### `POST /chat/`

**说明**: 发送聊天消息，返回 SSE（Server-Sent Events）流式响应。前端应使用 `EventSource` 或 `fetch` + `ReadableStream` 接收数据。

**请求体** (JSON，FormData 格式提交)

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 用户输入的查询文本 |
| `meta` | object | ❌ | 请求元数据（见下表） |
| `history` | array | ❌ | 对话历史，格式为 `[{role, content}]` |
| `session_id` | string | ❌ | 会话 ID，用于关联多轮对话 |
| `user_id` | string | ❌ | 用户 ID |

**`meta` 对象字段**

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `use_web` | bool | false | 是否启用网络搜索 |
| `use_graph` | bool | false | 是否启用知识图谱检索 |
| `db_id` | string | - | 指定查询的知识库 ID |
| `history_round` | int | - | 历史对话轮数限制 |
| `system_prompt` | string | - | 自定义系统提示词 |
| `distanceThreshold` | float | 0.5 | 向量搜索距离阈值 |
| `rerankThreshold` | float | 0.1 | 重排序得分阈值 |
| `maxQueryCount` | int | 20 | 最大查询数量 |
| `topK` | int | 10 | 返回结果数量 |

**SSE 流数据块格式**

每个 `data:` 行是一个 JSON 对象，根据 `status` 不同，字段有所差异。

> **性能优化说明**: 为减少冗余传输，所有中间状态块（`searching`、`generating`、`reasoning`、`loading`、`title_generating`、`title_generated`、`error`）的 `meta` 字段为空对象 `{}`，仅在最终 `finished` 状态块中返回完整元数据（含 `server_model_name`）。

**1. 检索阶段状态**

```json
// 开始检索
{"response": "", "meta": {}, "session_id": "xxx", "status": "searching"}

// 检索完成，进入生成阶段（携带检索结果）
{
  "response": "",
  "meta": {},
  "session_id": "xxx",
  "status": "generating",
  "retrieved_docs": [
    {
      "type": "document",
      "id": "doc_xxx",
      "filename": "威胁情报报告.pdf",
      "content": "文档内容片段（最多200字符）...",
      "score": 0.12
    },
    {
      "type": "graph_node",
      "entity_id": "node_xxx",
      "entity_name": "APT29",
      "entity_type": "ThreatActor",
      "entity_sub_type": "",
      "labels": ["ThreatActor"],
      "times": [],
      "entity_variant_names": ["Cozy Bear", "The Dukes"],
      "properties": {"country": "Russia"}
    }
  ]
}

// 不使用检索时
{"response": "", "meta": {}, "session_id": "xxx", "status": "generating"}
```

**2. AI推理阶段状态**（部分模型支持）

```json
{
  "response": "",
  "meta": {},
  "session_id": "xxx",
  "status": "reasoning",
  "reasoning_content": "AI正在分析思考..."
}
```

**3. 生成阶段状态**

```json
// 流式输出中
{"response": "部分回复...", "meta": {}, "session_id": "xxx", "status": "loading"}

// 回复完成
{
  "response": "完整回复内容...",
  "content": "完整回复内容...",
  "meta": {"server_model_name": "deepseek-ai/DeepSeek-V3"},
  "session_id": "xxx",
  "status": "finished",
  "history": [
    {"role": "user", "content": "用户问题"},
    {"role": "assistant", "content": "完整回复内容"}
  ],
  "refs": {"knowledge_base": {...}, "graph_base": {...}}
}
```

**4. 标题生成阶段状态**

```json
// 正在生成标题
{"response": "", "meta": {}, "session_id": "xxx", "status": "title_generating"}

// 标题生成完成
{
  "response": "",
  "meta": {},
  "session_id": "xxx",
  "status": "title_generated",
  "title": "APT29攻击手法分析"
}
```

**5. 错误状态**

```json
// 检索错误
{"message": "检索出错: xxx", "meta": {}, "session_id": "xxx", "status": "error"}

// 生成错误
{"message": "对话处理出错: xxx", "meta": {}, "session_id": "xxx", "status": "error"}
```

**`status` 状态值说明**

| status 值 | 说明 | 伴随字段 |
|-----------|------|----------|
| `searching` | 正在检索知识库/图谱 | - |
| `generating` | 检索完成，开始生成回答 | `retrieved_docs`（如有） |
| `reasoning` | AI模型推理中（部分模型） | `reasoning_content` |
| `loading` | 流式输出中，逐块返回增量内容 | `response` |
| `finished` | 回复生成完毕 | `content`, `history`, `refs`, `meta`（含 `server_model_name`） |
| `title_generating` | 正在生成会话标题 | - |
| `title_generated` | 会话标题已生成 | `title` |
| `error` | 发生错误 | `message` |

**`retrieved_docs` 字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 数据类型：`document`（知识库文档）或 `graph_node`（图谱节点） |
| `id` / `entity_id` | string | 文档/节点ID |
| `filename` / `entity_name` | string | 文档名或实体名称 |
| `content` | string | 文档内容片段（最多200字符） |
| `score` | float | 检索相关度得分 |
| `entity_type` | string | 实体类型（如 ThreatActor、Malware 等） |
| `entity_sub_type` | string | 实体子类型 |
| `labels` | array | 标签列表 |
| `times` | array | 时间信息 |
| `entity_variant_names` | array | 实体别名 |
| `properties` | object | 实体属性 |

**注意**: `finished` 状态的 chunk 中同时包含 `response`（默认字段名）和 `content`（显式传入字段名）两个 key，值相同，都是完整回复内容。

**HTTP 响应头**

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

**错误响应**

```
HTTP 500
{"detail": "聊天处理失败: <错误信息>"}
```

---

### 获取会话信息

#### `GET /chat/session/{session_id}`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 会话 ID |

**成功响应**

```json
{
  "status": "success",
  "session": {
    "session_id": "xxx",
    "user_id": "xxx",
    "title": "会话标题",
    "messages": [...],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}
```

**错误响应**

```
HTTP 404
{"status": 404}
```

---

### 删除会话

#### `DELETE /chat/session/{session_id}`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 会话 ID |

**成功响应**

```json
{
  "status": "success",
  "message": "会话删除成功"
}
```

**错误响应**

```
HTTP 404
{"detail": "会话不存在或删除失败"}
```

---

### 获取会话列表

#### `GET /chat/sessions`

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `user_id` | string | null | 按用户 ID 过滤（可选） |
| `limit` | int | 50 | 返回结果数量上限 |

**成功响应**

```json
{
  "status": "success",
  "sessions": [
    {
      "session_id": "xxx",
      "user_id": "xxx",
      "title": "会话标题",
      "created_at": "2026-01-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### 更新会话标题

#### `PUT /chat/session/{session_id}/title`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `session_id` | string | 会话 ID |

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | ✅ | 新的会话标题 |

**成功响应**

```json
{
  "status": "success",
  "message": "标题更新成功"
}
```

**错误响应**

```
HTTP 404
{"detail": "会话不存在或更新失败"}
```

---

### 获取模型列表

#### `GET /chat/models/{model_provider}`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `model_provider` | string | 模型提供商名称（如 `deepseek`、`siliconflow`） |

**成功响应**

```json
{
  "status": "success",
  "models": ["deepseek-chat", "deepseek-coder"]
}
```

**错误响应**

```
HTTP 500
{"detail": "获取模型列表失败: <错误信息>"}
```

---

## 知识库接口 (Knowledge)

**路由前缀**: `/knowledge`

> 支持的文件格式：`.txt`、`.md`、`.doc`、`.docx`、`.pdf`

---

### 获取数据库列表

#### `GET /knowledge/`

**成功响应**

```json
{
  "status": "success",
  "databases": [
    {
      "db_id": "db_xxx",
      "name": "威胁情报库",
      "description": "用于存储威胁情报",
      "dimension": 1024,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### 创建数据库

#### `POST /knowledge/`

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `database_name` | string | ✅ | 数据库名称 |
| `description` | string | ✅ | 数据库描述 |
| `dimension` | int | ❌ | 向量维度（默认由配置决定） |
| `user_id` | string | ❌ | 创建者用户 ID |

**成功响应**

```json
{
  "status": "success",
  "db_id": "db_xxx",
  "message": "数据库创建成功"
}
```

**错误响应**

```
HTTP 400
{"detail": "数据库名称已存在"}
```

---

### 删除数据库

#### `DELETE /knowledge/{db_id}`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_id` | string | 数据库 ID |

**成功响应**

```json
{
  "status": "success",
  "message": "数据库删除成功"
}
```

---

### 上传文件

#### `POST /knowledge/{db_id}/upload`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_id` | string | 数据库 ID |

**表单参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `file` | file | ✅ | 上传的文件（.txt/.md/.doc/.docx/.pdf） |
| `chunk_size` | int | 500 | 文本分块大小（字符数） |
| `overlap` | int | 50 | 相邻块重叠字符数 |
| `user_id` | string | null | 创建者用户 ID |

**成功响应**

```json
{
  "status": "success",
  "message": "文件上传成功"
}
```

**错误响应**

```
HTTP 400
{"detail": "不支持的文件类型"}
```

---

### 获取文件列表

#### `GET /knowledge/{db_id}/files`

**说明**: 获取指定数据库中已上传的所有文件列表。

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_id` | string | 数据库 ID |

**成功响应**

```json
{
  "documents": [
    {
      "id": "uuid",
      "db_id": "kb_xxx",
      "document_id": "doc_xxx",
      "title": "威胁情报报告.md",
      "file_path": "/tmp/xxx.md",
      "file_type": "markdown",
      "file_size": 4096,
      "chunk_count": 8,
      "creator_id": "user_xxx",
      "created_at": "2026-04-04T10:00:00Z",
      "updated_at": "2026-04-04T10:00:00Z",
      "metadata": {
        "original_filename": "威胁情报报告.md"
      }
    }
  ],
  "total": 1
}
```

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| `documents` | array | 文件列表 |
| `total` | int | 文件总数 |
| `documents[].title` | string | 文件标题（默认等于文件名） |
| `documents[].file_type` | string | 文件类型：`text`/`markdown`/`word`/`pdf`/`unknown` |
| `documents[].chunk_count` | int | 该文件被分成的块数量 |

**错误响应**

```
HTTP 500
{"detail": "获取文件列表失败: <错误信息>"}
```

---

### 批量添加文档

#### `POST /knowledge/{db_id}/documents`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_id` | string | 数据库 ID |

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `documents` | array | ✅ | 文档列表 |
| `user_id` | string | ❌ | 创建者用户 ID |

**`documents` 数组中每个元素的格式**

```json
[
  {
    "id": "可选，若不提供则自动生成",
    "text": "文档文本内容",
    "metadata": {
      "source": "可选，来源信息",
      "extra_field": "其他元数据"
    }
  }
]
```

**成功响应**

```json
{
  "status": "success",
  "message": "成功添加 10 个文档"
}
```

---

### 获取数据库统计信息

#### `GET /knowledge/{db_id}/stats`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_id` | string | 数据库 ID |

**成功响应**

```json
{
  "status": "success",
  "entity_count": 1000,
  "total_vector_count": 5000,
  "index_type": "IP"
}
```

---

### 查询数据库

#### `POST /knowledge/{db_id}/query`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `db_id` | string | 数据库 ID |

**请求体**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | string | ✅ | 查询文本 |
| `distance_threshold` | float | 0.5 | 向量搜索距离阈值 |
| `rerank_threshold` | float | 0.1 | 重排序得分阈值 |
| `max_query_count` | int | 20 | 最大查询数量 |
| `top_k` | int | 10 | 返回结果数量 |

**成功响应**

```json
{
  "status": "success",
  "results": [
    {
      "text": "文档片段内容...",
      "distance": 0.12,
      "rerank_score": 0.85,
      "metadata": {
        "source": "xxx",
        "id": "xxx"
      }
    }
  ]
}
```

---

### 查询测试

#### `POST /knowledge/query-test`

**说明**: 跨库查询测试（不指定 db_id 时使用默认配置）。

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 查询文本 |
| `meta` | object | ✅ | 查询参数（包含 `db_id` 等） |

**成功响应** 同 `POST /knowledge/{db_id}/query`

---

## 知识图谱接口 (Graph)

**路由前缀**: `/graph`

---

### 获取图数据库信息

#### `GET /graph/`

**成功响应**

```json
{
  "status": "success",
  "node_count": 1000,
  "relationship_count": 2500,
  "label_counts": {
    "IP": 200,
    "Domain": 150,
    "Vulnerability": 300,
    "Malware": 100,
    "ThreatActor": 50,
    "Campaign": 200
  }
}
```

---

### 获取图数据库统计

#### `GET /graph/stats`

**成功响应**

```json
{
  "status": "success",
  "stats": {
    "node_count": 1000,
    "relationship_count": 2500,
    "label_counts": {
      "IP": 200,
      "Domain": 150
    },
    "status": "success"
  }
}
```

---

### 获取图节点信息

#### `GET /graph/node`

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `entity_name` | string | ✅ | 实体名称 |

**成功响应**

```json
{
  "status": "success",
  "nodes": [
    {
      "id": "node_xxx",
      "name": "APT29",
      "label": "ThreatActor",
      "labels": ["ThreatActor"],
      "properties": {
        "aliases": ["Cozy Bear", "The Dukes"],
        "country": "Russia"
      }
    }
  ],
  "edges": [
    {
      "id": "edge_xxx",
      "source": "apt29_id",
      "target": "campaign_id",
      "source_name": "APT29",
      "target_name": "SolarWinds Attack",
      "type": "ATTRIBUTED_TO",
      "properties": {}
    }
  ],
  "stats": {
    "node_count": 1,
    "edge_count": 3
  }
}
```

---

### 获取图节点列表

#### `GET /graph/nodes`

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `num` | int | 50 | 节点数量限制 |

**成功响应**

```json
{
  "status": "success",
  "nodes": [
    {
      "id": "node_xxx",
      "name": "APT29",
      "label": "ThreatActor"
    }
  ]
}
```

---

### 批量查询图谱实体

#### `POST /graph/query`

**说明**: 传入多个实体名称，返回合并去重后的子图。

**请求体**

| 参数 | 类型 | 说明 |
|------|------|------|
| `entities` | array[string] | 实体名称列表（必填，不能为空） |

**成功响应**

```json
{
  "status": "success",
  "nodes": [...],
  "edges": [...],
  "stats": {
    "node_count": 10,
    "edge_count": 15
  }
}
```

**错误响应**

```
HTTP 400
{"detail": "实体列表不能为空"}
```

---

### 同步抽取实体关系

#### `POST /graph/extract`

**说明**: 对输入文本进行实体关系抽取，**不存储到图数据库**，直接返回抽取结果。

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | ✅ | 输入情报文本 |
| `source` | string | ❌ | 文本来源 |
| `metadata` | object | ❌ | 额外元数据 |

**成功响应**

```json
{
  "status": "success",
  "task_id": "task_abc12345",
  "entity_count": 5,
  "relationship_count": 3,
  "entities": [
    {
      "entity_id": "e_xxx",
      "entity_name": "APT29",
      "entity_type": "ThreatActor",
      "properties": {},
      "source": "user_input",
      "confidence": 0.95
    }
  ],
  "relationships": [
    {
      "relationship_id": "r_xxx",
      "source": "e_xxx",
      "target": "e_yyy",
      "relationship_type": "ATTRIBUTED_TO",
      "properties": {},
      "source_name": "APT29",
      "target_name": "SolarWinds",
      "confidence": 0.90
    }
  ],
  "raw_xml": "<?xml ...",
  "processing_time_ms": 1234,
  "errors": []
}
```

**支持的实体类型**: `IP`, `Domain`, `Vulnerability`, `Malware`, `ThreatActor`, `Campaign`, `AttackPattern`, `Tool`, `Software`, `Industry`, `Region`, `Organization`, `Person`, `Event`, `Weakness`, `CourseOfAction`, `Identity`, `Location`, `Tool`

---

### 异步抽取并存储实体关系

#### `POST /graph/extract-and-save`

**说明**: 将文本抽取的实体关系**异步存储到图数据库**，立即返回任务接收确认，**不等待执行完成**。

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | ✅ | 输入情报文本 |
| `source` | string | ❌ | 文本来源 |
| `metadata` | object | ❌ | 额外元数据 |

**成功响应**

```json
{
  "status": "success",
  "task_id": "task_abc12345",
  "message": "任务已接收，正在后台执行抽取并存储"
}
```

---

## 用户认证接口 (Auth)

**路由前缀**: `/auth`

---

### 用户注册

#### `POST /auth/register`

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | ✅ | 用户名（3-32字符，字母/数字/下划线） |
| `password` | string | ✅ | 密码（至少6个字符） |
| `email` | string | ❌ | 邮箱地址 |
| `display_name` | string | ❌ | 显示名称（默认同用户名） |

**成功响应**

```json
{
  "success": true,
  "user": {
    "user_id": "user_xxx",
    "username": "john",
    "email": "john@example.com",
    "display_name": "John",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

**失败响应**

```json
{
  "success": false,
  "error": "用户名已存在"
}
```

---

### 用户登录

#### `POST /auth/login`

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `username` | string | ✅ | 用户名 |
| `password` | string | ✅ | 密码 |

**成功响应**

```json
{
  "success": true,
  "user": {
    "user_id": "user_xxx",
    "username": "john",
    "email": "john@example.com",
    "display_name": "John"
  }
}
```

**失败响应**

```json
{
  "success": false,
  "error": "用户名或密码错误"
}
```

---

### 获取用户信息

#### `GET /auth/user/{user_id}`

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户 ID |

**成功响应**

```json
{
  "success": true,
  "user": {
    "user_id": "user_xxx",
    "username": "john",
    "email": "john@example.com",
    "display_name": "John",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

**错误响应**

```
HTTP 404
{"detail": "用户不存在"}
```

---

### 修改密码

#### `POST /auth/change-password`

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_id` | string | ✅ | 用户 ID |
| `old_password` | string | ✅ | 旧密码 |
| `new_password` | string | ✅ | 新密码（至少6个字符） |

**成功响应**

```json
{
  "success": true,
  "message": "密码修改成功"
}
```

---

### 验证用户名格式

#### `GET /auth/validate/username`

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `username` | string | 待验证的用户名 |

**响应示例**

```json
{
  "valid": true,
  "message": "用户名格式正确"
}
```

或

```json
{
  "valid": false,
  "message": "用户名只能包含字母、数字和下划线"
}
```

---

### 验证密码格式

#### `GET /auth/validate/password`

**查询参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `password` | string | 待验证的密码 |

**响应示例**

```json
{
  "valid": true,
  "message": "密码格式正确"
}
```

或

```json
{
  "valid": false,
  "message": "密码长度至少为6个字符"
}
```

---

## 附录

### SSE 流式响应处理示例

**JavaScript (fetch)**

```javascript
const response = await fetch("/chat/", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query: "APT29使用了哪些攻击手法？",
    session_id: "sess_abc123",
    meta: { use_graph: true, topK: 5 }
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

let retrievedDocs = [];

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split("\n");

  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const data = JSON.parse(line.slice(6));
      const status = data.status;
      
      switch (status) {
        case "searching":
          console.log("正在检索知识库...");
          break;
        case "generating":
          // 检索完成，收到检索结果
          if (data.retrieved_docs && data.retrieved_docs.length > 0) {
            retrievedDocs = data.retrieved_docs;
            retrievedDocs.forEach(doc => {
              if (doc.type === "document") {
                console.log(`[文档] ${doc.filename}: ${doc.content.substring(0, 50)}...`);
              } else if (doc.type === "graph_node") {
                console.log(`[图谱] ${doc.entity_name} (${doc.entity_type})`);
              }
            });
          }
          console.log("开始生成回答...");
          break;
        case "reasoning":
          // AI推理过程（部分模型）
          process.stdout.write(`推理中: ${data.reasoning_content || ""}`);
          break;
        case "loading":
          process.stdout.write(data.response || "");
          break;
        case "finished":
          console.log("\n[finished] 完整回复:", data.content);
          console.log("[finished] 对话历史:", data.history?.length, "条");
          console.log("[finished] 检索引用:", data.refs);
          break;
        case "title_generating":
          console.log("正在生成会话标题...");
          break;
        case "title_generated":
          console.log("会话标题:", data.title);
          break;
        case "error":
          console.error("[error]", data.message);
          break;
      }
    }
  }
}
```

**Python (requests)**

```python
import requests

with requests.post(
    "http://localhost:8000/chat/",
    json={"query": "APT29使用了哪些攻击手法？", "meta": {"use_graph": True, "topK": 5}},
    stream=True
) as r:
    retrieved_docs = []
    for line in r.iter_lines():
        if line.startswith("data: "):
            import json
            data = json.loads(line[6:])
            status = data.get("status")
            
            if status == "searching":
                print("正在检索知识库...")
            elif status == "generating":
                # 检索完成，收到检索结果
                if "retrieved_docs" in data:
                    retrieved_docs = data["retrieved_docs"]
                    for doc in retrieved_docs:
                        if doc.get("type") == "document":
                            print(f"[文档] {doc['filename']}: {doc['content'][:50]}...")
                        elif doc.get("type") == "graph_node":
                            print(f"[图谱] {doc['entity_name']} ({doc['entity_type']})")
                print("开始生成回答...")
            elif status == "reasoning":
                # AI推理过程（部分模型）
                print(f"推理中: {data.get('reasoning_content', '')}")
            elif status == "loading":
                print(data.get("response", ""), end="", flush=True)
            elif status == "finished":
                print(f"\n[finished] 完整回复: {data.get('content', '')}")
                print(f"[finished] 对话历史: {len(data.get('history', []))} 条")
                print(f"[finished] 检索引用: {data.get('refs')}")
            elif status == "title_generating":
                print("正在生成会话标题...")
            elif status == "title_generated":
                print(f"会话标题: {data.get('title', '')}")
            elif status == "error":
                print(f"\n[error] {data.get('message', '未知错误')}")
                break
```

### 实体关系类型参考

| 关系类型 | 说明 | 实体类型组合 |
|----------|------|--------------|
| `ATTRIBUTED_TO` | 归因于 | ThreatActor → Campaign |
| `USES` | 使用（工具/战术） | ThreatActor → Tool |
| `TARGETS` | 攻击目标 | ThreatActor → Industry/Region |
| `EXPLOITS` | 利用漏洞 | ThreatActor → Vulnerability |
| `ASSOCIATED_WITH` | 与…关联 | Malware → ThreatActor |
| `RELATED_TO` | 与…相关 | Generic |
| `LOCATED_IN` | 位于 | Domain/IP → Location |
| `RESOLVES_TO` | 解析到 | Domain → IP |
| `CAMPAIGN_OF` | …的活动 | Campaign → ThreatActor |
| `MENTIONS` | 提及 | Document → Entity |

> 实际关系类型由 LLM 抽取结果决定，上表仅供参考。
