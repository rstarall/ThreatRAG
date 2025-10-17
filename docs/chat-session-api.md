# 聊天会话 API 文档

## 📚 概述

ThreatRAG 的聊天系统采用 **MySQL + Redis** 双层存储架构：
- **MySQL**: 主存储，持久化所有会话和消息数据
- **Redis**: 缓存层，加速查询，提高响应速度

所有聊天记录与用户绑定，支持多会话管理。

---

## 🗄️ 数据库表结构

### 1. chat_sessions (聊天会话表)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT | 主键，自增 |
| `session_id` | VARCHAR(36) | UUID，唯一会话标识 |
| `user_id` | INT | 用户ID（外键关联 users.id） |
| `title` | VARCHAR(255) | 会话标题 |
| `system_prompt` | TEXT | 系统提示词 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |
| `is_deleted` | BOOLEAN | 软删除标记 |

**索引:**
- `session_id`: 唯一索引
- `user_id`: 普通索引

---

### 2. chat_messages (聊天消息表)

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INT | 主键，自增 |
| `session_id` | VARCHAR(36) | 会话ID（外键关联 chat_sessions.session_id） |
| `role` | VARCHAR(20) | 角色：user, assistant, system |
| `content` | TEXT | 消息内容 |
| `created_at` | DATETIME | 创建时间 |
| `is_deleted` | BOOLEAN | 软删除标记 |
| `meta` | TEXT | 扩展元数据（JSON格式） |

**索引:**
- `session_id`: 普通索引

---

## 🚀 API 端点

### 1. 创建新会话

**端点:** `POST /chat/sessions/create`

**描述:** 创建一个新的聊天会话

**请求参数:**

```json
{
  "user_id": 1,
  "title": "威胁情报讨论",
  "system_prompt": "你是一个专业的威胁情报分析师"
}
```

**参数说明:**
- `user_id` (必需): 用户ID
- `title` (可选): 会话标题，如不提供则自动生成
- `system_prompt` (可选): 系统提示词

**响应:**

```json
{
  "success": true,
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "会话创建成功"
}
```

**curl 示例:**

```bash
curl -X POST http://localhost:8006/chat/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "APT攻击分析",
    "system_prompt": "你是一个威胁情报专家"
  }'
```

---

### 2. 在会话中聊天

**端点:** `POST /chat/stream`

**描述:** 在会话中发送消息并获取流式响应（支持自动创建会话）

**请求参数:**

```json
{
  "query": "分析这个威胁情报",
  "user_id": 1,
  "thread_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "meta": {
    "model_provider": "deepseek",
    "model_name": "deepseek-chat",
    "db_id": "kb_threat_intel",
    "use_graph": true
  }
}
```

**参数说明:**
- `query` (必需): 用户的输入查询文本
- `user_id` (必需): 用户ID
- `thread_id` (可选): 会话ID
  - **提供了** `thread_id`: 使用已有会话
  - **未提供** `thread_id`: 自动创建新会话
- `meta` (可选): 请求元数据
  - `title`: 会话标题（自动创建时使用）
  - `system_prompt`: 系统提示词（自动创建时使用）
  - 其他检索相关参数...

**响应:** 流式JSON

```json
{"response": "分析中...", "status": "loading", "thread_id": "uuid-xxx"}
{"response": "完整回复", "status": "finished", "thread_id": "uuid-xxx"}
```

---

#### 📌 使用方式 1: 继续已有会话（推荐）

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是APT攻击？",
    "user_id": 1,
    "thread_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "meta": {
      "model_provider": "deepseek"
    }
  }'
```

---

#### 📌 使用方式 2: 自动创建新会话（快捷方式）

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好，我想了解威胁情报",
    "user_id": 1,
    "meta": {
      "title": "威胁情报咨询",
      "system_prompt": "你是一个专业的威胁情报分析师",
      "model_provider": "deepseek"
    }
  }'
```

**💡 提示:** 
- 方式 1：更好的控制，可以提前设置会话
- 方式 2：更便捷，一次调用即可开始聊天

---

### 3. 获取用户的所有会话

**端点:** `GET /chat/sessions`

**描述:** 获取指定用户的所有会话列表

**查询参数:**
- `user_id` (必需): 用户ID
- `limit` (可选): 返回数量，默认50
- `offset` (可选): 偏移量，默认0

**响应:**

```json
{
  "success": true,
  "sessions": [
    {
      "id": 1,
      "session_id": "uuid-xxx",
      "user_id": 1,
      "title": "对话 2025-10-16 14:30",
      "system_prompt": "你是一个助手",
      "created_at": "2025-10-16T14:30:00",
      "updated_at": "2025-10-16T15:00:00",
      "is_deleted": false
    }
  ],
  "total": 1
}
```

**curl 示例:**

```bash
curl "http://localhost:8006/chat/sessions?user_id=1&limit=20"
```

---

### 4. 获取会话详情

**端点:** `GET /chat/sessions/{thread_id}`

**描述:** 获取指定会话的详细信息（包含消息历史）

**查询参数:**
- `user_id` (必需): 用户ID
- `include_messages` (可选): 是否包含消息列表，默认true

**响应:**

```json
{
  "success": true,
  "session": {
    "id": 1,
    "session_id": "uuid-xxx",
    "user_id": 1,
    "title": "对话 2025-10-16 14:30",
    "system_prompt": "你是一个助手",
    "created_at": "2025-10-16T14:30:00",
    "updated_at": "2025-10-16T15:00:00",
    "is_deleted": false,
    "messages": [
      {
        "id": 1,
        "role": "user",
        "content": "什么是APT攻击？",
        "created_at": "2025-10-16T14:30:00",
        "is_deleted": false
      },
      {
        "id": 2,
        "role": "assistant",
        "content": "APT是高级持续性威胁...",
        "created_at": "2025-10-16T14:30:05",
        "is_deleted": false
      }
    ]
  }
}
```

**curl 示例:**

```bash
curl "http://localhost:8006/chat/sessions/uuid-xxx?user_id=1&include_messages=true"
```

---

### 5. 获取会话的消息历史

**端点:** `GET /chat/sessions/{thread_id}/messages`

**描述:** 获取指定会话的所有消息

**查询参数:**
- `user_id` (必需): 用户ID
- `limit` (可选): 限制返回消息数量

**响应:**

```json
{
  "success": true,
  "messages": [
    {
      "role": "user",
      "content": "什么是APT攻击？",
      "timestamp": "2025-10-16T14:30:00"
    },
    {
      "role": "assistant",
      "content": "APT是高级持续性威胁...",
      "timestamp": "2025-10-16T14:30:05"
    }
  ],
  "total": 2
}
```

**curl 示例:**

```bash
curl "http://localhost:8006/chat/sessions/uuid-xxx/messages?user_id=1&limit=50"
```

---

### 6. 更新会话信息

**端点:** `PUT /chat/sessions/{thread_id}`

**描述:** 更新会话的标题或系统提示词

**请求参数:**

```json
{
  "user_id": 1,
  "title": "威胁情报分析对话",
  "system_prompt": "你是一个专业的威胁情报分析师"
}
```

**响应:**

```json
{
  "success": true,
  "message": "会话更新成功"
}
```

**curl 示例:**

```bash
curl -X PUT http://localhost:8006/chat/sessions/uuid-xxx \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "APT分析讨论"
  }'
```

---

### 7. 删除会话

**端点:** `DELETE /chat/sessions/{thread_id}`

**描述:** 删除指定会话（默认软删除）

**查询参数:**
- `user_id` (必需): 用户ID
- `hard_delete` (可选): 是否物理删除，默认false

**响应:**

```json
{
  "success": true,
  "message": "会话删除成功"
}
```

**curl 示例:**

```bash
# 软删除（推荐）
curl -X DELETE "http://localhost:8006/chat/sessions/uuid-xxx?user_id=1"

# 物理删除（谨慎使用）
curl -X DELETE "http://localhost:8006/chat/sessions/uuid-xxx?user_id=1&hard_delete=true"
```

---

### 8. 删除单条消息

**端点:** `DELETE /chat/sessions/{thread_id}/messages/{message_id}`

**描述:** 删除会话中的某条消息（软删除）

**查询参数:**
- `user_id` (必需): 用户ID

**响应:**

```json
{
  "success": true,
  "message": "消息删除成功"
}
```

**curl 示例:**

```bash
curl -X DELETE "http://localhost:8006/chat/sessions/uuid-xxx/messages/123?user_id=1"
```

---

## 🔐 权限控制

所有 API 都进行了用户权限校验：
- ✅ 用户只能访问自己的会话
- ✅ 用户只能修改/删除自己的会话和消息
- ❌ 未授权访问返回 404 错误

---

## 💾 缓存策略

### Redis 缓存逻辑

**写入顺序（双写）:**
1. 先写入 MySQL（持久化）
2. 再写入 Redis（缓存）

**查询顺序（读穿）:**
1. 先从 Redis 读取
2. 如果 Redis 未命中，从 MySQL 读取
3. 读取成功后写入 Redis

**缓存失效:**
- 会话更新/删除时：清除 Redis 缓存
- 消息删除时：清除整个会话缓存
- TTL: 3600秒（1小时）

---

## 🛠️ 数据库初始化

### 方法 1: 使用迁移脚本（推荐）

```bash
cd /home/lxp/workspace/ThreatRAG

# 创建表
python scripts/create_chat_tables.py create

# 重建表（会删除所有数据！）
python scripts/create_chat_tables.py recreate

# 删除表
python scripts/create_chat_tables.py drop
```

### 方法 2: 手动SQL

```sql
-- 创建会话表
CREATE TABLE chat_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    title VARCHAR(255),
    system_prompt TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 创建消息表
CREATE TABLE chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    meta TEXT,
    INDEX idx_session_id (session_id),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
);
```

---

## 📊 使用示例

### Python 客户端示例

```python
import requests
import json

BASE_URL = "http://localhost:8006"
USER_ID = 1

# 1. 创建新会话并开始聊天
def start_chat(query, model_provider="deepseek"):
    response = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "query": query,
            "user_id": USER_ID,
            "meta": {
                "model_provider": model_provider,
                "model_name": "deepseek-chat"
            }
        },
        stream=True
    )
    
    thread_id = None
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            thread_id = data.get("thread_id")
            if data.get("status") == "finished":
                print(f"✅ 会话创建成功: {thread_id}")
                break
    
    return thread_id

# 2. 获取用户的所有会话
def list_sessions():
    response = requests.get(
        f"{BASE_URL}/chat/sessions",
        params={"user_id": USER_ID, "limit": 10}
    )
    sessions = response.json()["sessions"]
    print(f"📋 共有 {len(sessions)} 个会话:")
    for s in sessions:
        print(f"  - {s['title']} ({s['session_id']})")
    return sessions

# 3. 查看会话详情
def get_session_details(thread_id):
    response = requests.get(
        f"{BASE_URL}/chat/sessions/{thread_id}",
        params={"user_id": USER_ID, "include_messages": True}
    )
    session = response.json()["session"]
    print(f"📝 会话: {session['title']}")
    print(f"消息数: {len(session.get('messages', []))}")
    for msg in session.get("messages", []):
        print(f"  [{msg['role']}]: {msg['content'][:50]}...")

# 4. 继续已有会话
def continue_chat(thread_id, query):
    response = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "query": query,
            "user_id": USER_ID,
            "thread_id": thread_id
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if data.get("response"):
                print(data["response"], end="", flush=True)
    print()

# 5. 更新会话标题
def update_session_title(thread_id, new_title):
    response = requests.put(
        f"{BASE_URL}/chat/sessions/{thread_id}",
        json={
            "user_id": USER_ID,
            "title": new_title
        }
    )
    print(f"✅ 标题更新为: {new_title}")

# 6. 删除会话
def delete_session(thread_id):
    response = requests.delete(
        f"{BASE_URL}/chat/sessions/{thread_id}",
        params={"user_id": USER_ID}
    )
    print(f"✅ 会话已删除")

# 完整流程示例
if __name__ == "__main__":
    # 创建新会话
    thread_id = start_chat("什么是APT攻击？")
    
    # 查看所有会话
    list_sessions()
    
    # 查看会话详情
    get_session_details(thread_id)
    
    # 继续对话
    continue_chat(thread_id, "APT攻击有哪些特征？")
    
    # 更新标题
    update_session_title(thread_id, "APT攻击讨论")
    
    # 删除会话
    # delete_session(thread_id)
```

---

## 🧪 测试流程

### 1. 初始化数据库

```bash
python scripts/create_chat_tables.py create
```

### 2. 测试创建会话

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好",
    "user_id": 1
  }'
```

### 3. 查看会话列表

```bash
curl "http://localhost:8006/chat/sessions?user_id=1"
```

### 4. 查看会话详情

```bash
# 使用上一步返回的 session_id
curl "http://localhost:8006/chat/sessions/<session_id>?user_id=1"
```

### 5. 继续对话

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "再说一遍",
    "user_id": 1,
    "thread_id": "<session_id>"
  }'
```

---

## 📝 注意事项

1. **user_id 是必需的**: 所有聊天操作都必须提供用户ID
2. **软删除优先**: 默认使用软删除，可恢复数据
3. **Redis 缓存**: 查询优先走缓存，提升性能
4. **权限隔离**: 用户之间的会话严格隔离
5. **级联删除**: 删除会话时，关联的消息也会被删除（软删除）

---

## 🔧 故障排查

### 问题 1: "会话不存在或无权访问"

**原因:** 
- user_id 不匹配
- session_id 错误
- 会话已被删除

**解决:**
```bash
# 检查用户的所有会话
curl "http://localhost:8006/chat/sessions?user_id=1"
```

### 问题 2: Redis 连接失败

**原因:** Redis 服务未启动或连接配置错误

**解决:**
```bash
# 检查 Redis 状态
docker ps | grep redis

# 检查环境变量
echo $REDIS_URL
```

### 问题 3: MySQL 表不存在

**原因:** 未执行数据库迁移

**解决:**
```bash
# 运行迁移脚本
python scripts/create_chat_tables.py create
```

---

## 📚 相关文档

- [模型使用指南](model-usage-examples.md)
- [API 测试示例](api-test-examples.md)
- [Ollama 设置指南](ollama-setup.md)

