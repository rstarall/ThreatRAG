# 聊天会话系统快速开始

## 🎯 概述

ThreatRAG 现在支持用户级别的多会话管理，所有聊天记录与用户绑定，并使用 MySQL + Redis 双层存储。

---

## ⚡ 快速开始（5分钟）

### 1️⃣ 初始化数据库表

```bash
cd /home/lxp/workspace/ThreatRAG

# 创建聊天相关的数据库表
python scripts/create_chat_tables.py create
```

**预期输出：**
```
✅ 聊天表创建成功！
已创建表:
  - chat_sessions (聊天会话表)
  - chat_messages (聊天消息表)
```

---

### 2️⃣ 启动服务

```bash
# 确保 Docker 容器正在运行
docker compose up -d

# 或者直接启动 FastAPI
python main.py
```

---

### 3️⃣ 开始聊天（两种方式）

#### 方式 A: 快捷方式（自动创建会话）

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好，我想了解APT攻击",
    "user_id": 1,
    "meta": {
      "title": "威胁情报讨论",
      "system_prompt": "你是一个专业的威胁情报分析师",
      "model_provider": "deepseek"
    }
  }'
```

**✨ 优点:** 一次调用即可开始聊天，无需预先创建会话

---

#### 方式 B: 标准方式（先创建会话）

**Step 1: 创建会话**
```bash
curl -X POST http://localhost:8006/chat/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "威胁情报讨论",
    "system_prompt": "你是一个专业的威胁情报分析师"
  }'
```

**响应:**
```json
{
  "success": true,
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "会话创建成功"
}
```

**Step 2: 发送消息**
```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好，我想了解APT攻击",
    "user_id": 1,
    "thread_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "meta": {
      "model_provider": "deepseek"
    }
  }'
```

**✨ 优点:** 更好的会话控制，可以批量创建会话

---

**响应示例（两种方式相同）：**
```json
{"response":"你好","status":"loading","thread_id":"a1b2c3d4-..."}
{"response":"！我是专业的威胁情报分析师...","status":"loading","thread_id":"a1b2c3d4-..."}
{"status":"finished","thread_id":"a1b2c3d4-...","history":[...]}
```

**📝 记住返回的 `thread_id`，用于后续聊天！**

---

### 4️⃣ 继续对话

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "APT攻击有哪些特征？",
    "user_id": 1,
    "thread_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }'
```

---

### 5️⃣ 查看所有会话

```bash
curl "http://localhost:8006/chat/sessions?user_id=1&limit=10"
```

**响应示例：**
```json
{
  "success": true,
  "sessions": [
    {
      "session_id": "a1b2c3d4-...",
      "title": "对话 2025-10-16 14:30",
      "created_at": "2025-10-16T14:30:00",
      "updated_at": "2025-10-16T14:35:00"
    }
  ],
  "total": 1
}
```

---

### 6️⃣ 查看会话详情（含消息历史）

```bash
curl "http://localhost:8006/chat/sessions/a1b2c3d4-...?user_id=1&include_messages=true"
```

---

## 🔥 核心功能

### ✅ 已实现功能

| 功能 | 说明 | API 端点 |
|------|------|----------|
| **创建会话** | 创建新的聊天会话 | `POST /chat/sessions/create` |
| **发送消息** | 在已有会话中发送消息并获取回复 | `POST /chat/stream` |
| **会话列表** | 查看用户的所有会话 | `GET /chat/sessions` |
| **会话详情** | 查看会话信息和消息历史 | `GET /chat/sessions/{id}` |
| **更新会话** | 修改会话标题或系统提示词 | `PUT /chat/sessions/{id}` |
| **删除会话** | 软删除或硬删除会话 | `DELETE /chat/sessions/{id}` |
| **删除消息** | 删除单条消息 | `DELETE /chat/sessions/{id}/messages/{msg_id}` |
| **权限控制** | 用户只能访问自己的会话 | 所有端点 |
| **双层存储** | MySQL 主存储 + Redis 缓存 | 自动 |

---

## 🗄️ 数据存储架构

```
┌─────────────┐
│   用户请求   │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│   Redis     │────▶│   MySQL     │
│   (缓存)     │◀────│  (主存储)   │
└─────────────┘     └─────────────┘
  1小时TTL         永久存储
  快速读取         持久化
```

**查询流程:**
1. 先查 Redis（缓存命中率高）
2. 未命中则查 MySQL
3. 写回 Redis 缓存

**写入流程:**
1. 先写 MySQL（确保持久化）
2. 再写 Redis（更新缓存）

---

## 📊 数据结构

### chat_sessions 表

```sql
CREATE TABLE chat_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(36) UNIQUE NOT NULL,  -- UUID
    user_id INT NOT NULL,                    -- 用户ID
    title VARCHAR(255),                      -- 会话标题
    system_prompt TEXT,                      -- 系统提示词
    created_at DATETIME,
    updated_at DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE         -- 软删除标记
);
```

### chat_messages 表

```sql
CREATE TABLE chat_messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(36) NOT NULL,         -- 关联会话
    role VARCHAR(20) NOT NULL,               -- user/assistant/system
    content TEXT NOT NULL,                   -- 消息内容
    created_at DATETIME,
    is_deleted BOOLEAN DEFAULT FALSE,
    meta TEXT                                -- 扩展字段(JSON)
);
```

---

## 🎨 前端集成示例

### JavaScript/TypeScript

```typescript
class ThreatRAGClient {
  private baseUrl = "http://localhost:8006";
  private userId: number;
  private currentThreadId: string | null = null;

  constructor(userId: number) {
    this.userId = userId;
  }

  // 创建新会话
  async createSession(
    title?: string,
    systemPrompt?: string
  ): Promise<string> {
    const response = await fetch(`${this.baseUrl}/chat/sessions/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: this.userId,
        title: title || `对话 ${new Date().toLocaleString()}`,
        system_prompt: systemPrompt
      })
    });

    const data = await response.json();
    this.currentThreadId = data.session_id;
    return data.session_id;
  }

  // 在会话中发送消息
  async sendMessage(
    query: string,
    threadId?: string,
    modelProvider = "deepseek"
  ) {
    const tid = threadId || this.currentThreadId;
    if (!tid) {
      throw new Error("请先创建会话（使用 createSession）");
    }

    const response = await fetch(`${this.baseUrl}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        thread_id: tid,
        user_id: this.userId,
        meta: {
          model_provider: modelProvider,
          model_name: "deepseek-chat"
        }
      })
    });

    // 处理流式响应
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n").filter(l => l.trim());

      for (const line of lines) {
        const data = JSON.parse(line);

        // 处理响应内容
        if (data.response) {
          fullResponse += data.response;
          console.log(data.response); // 实时显示
        }

        // 检查是否完成
        if (data.status === "finished") {
          return {
            threadId: tid,
            response: fullResponse,
            history: data.history
          };
        }
      }
    }
  }

  // 获取所有会话
  async getSessions(limit = 20) {
    const response = await fetch(
      `${this.baseUrl}/chat/sessions?user_id=${this.userId}&limit=${limit}`
    );
    return await response.json();
  }

  // 获取会话详情
  async getSessionDetails(threadId: string) {
    const response = await fetch(
      `${this.baseUrl}/chat/sessions/${threadId}?user_id=${this.userId}&include_messages=true`
    );
    return await response.json();
  }

  // 更新会话标题
  async updateSessionTitle(threadId: string, title: string) {
    const response = await fetch(
      `${this.baseUrl}/chat/sessions/${threadId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: this.userId, title })
      }
    );
    return await response.json();
  }

  // 删除会话
  async deleteSession(threadId: string, hardDelete = false) {
    const response = await fetch(
      `${this.baseUrl}/chat/sessions/${threadId}?user_id=${this.userId}&hard_delete=${hardDelete}`,
      { method: "DELETE" }
    );
    return await response.json();
  }
}

// 使用示例
const client = new ThreatRAGClient(1);

// 1. 创建新会话
const sessionId = await client.createSession(
  "APT攻击讨论",
  "你是一个专业的威胁情报分析师"
);
console.log("会话创建成功:", sessionId);

// 2. 发送第一条消息
const result1 = await client.sendMessage("什么是APT攻击？", sessionId);
console.log("回复:", result1.response);

// 3. 继续对话
const result2 = await client.sendMessage("APT攻击的特征是什么？", sessionId);
console.log("回复:", result2.response);

// 4. 查看所有会话
const sessions = await client.getSessions();
console.log("所有会话:", sessions);

// 5. 更新标题
await client.updateSessionTitle(sessionId, "APT攻击深度讨论");
```

---

## 🧪 完整测试脚本

创建 `test_chat_sessions.py`:

```python
import requests
import json
import time

BASE_URL = "http://localhost:8006"
USER_ID = 1

def test_chat_sessions():
    print("="*60)
    print("🧪 ThreatRAG 聊天会话系统测试")
    print("="*60)
    
    # 1. 创建新会话
    print("\n1️⃣  创建新会话...")
    response = requests.post(
        f"{BASE_URL}/chat/sessions/create",
        json={
            "user_id": USER_ID,
            "title": "APT攻击讨论",
            "system_prompt": "你是一个专业的威胁情报分析师"
        }
    )
    
    session_data = response.json()
    thread_id = session_data["session_id"]
    print(f"✅ 会话创建成功: {thread_id}")
    time.sleep(1)
    
    # 2. 发送第一条消息
    print("\n2️⃣  发送第一条消息...")
    response = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "query": "你好，我想了解APT攻击",
            "thread_id": thread_id,
            "user_id": USER_ID,
            "meta": {"model_provider": "deepseek"}
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if data.get("status") == "finished":
                break
    
    print(f"✅ 消息发送成功")
    time.sleep(1)
    
    # 3. 获取会话列表
    print("\n3️⃣  获取会话列表...")
    response = requests.get(
        f"{BASE_URL}/chat/sessions",
        params={"user_id": USER_ID, "limit": 10}
    )
    sessions = response.json()["sessions"]
    print(f"✅ 找到 {len(sessions)} 个会话")
    for s in sessions:
        print(f"   - {s['title']} ({s['session_id'][:8]}...)")
    time.sleep(1)
    
    # 4. 查看会话详情
    print("\n4️⃣  查看会话详情...")
    response = requests.get(
        f"{BASE_URL}/chat/sessions/{thread_id}",
        params={"user_id": USER_ID, "include_messages": True}
    )
    session = response.json()["session"]
    print(f"✅ 会话: {session['title']}")
    print(f"   消息数: {len(session.get('messages', []))}")
    for msg in session.get("messages", []):
        print(f"   [{msg['role']}]: {msg['content'][:50]}...")
    time.sleep(1)
    
    # 5. 继续对话
    print("\n5️⃣  继续对话...")
    response = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "query": "APT攻击有哪些特征？",
            "thread_id": thread_id,
            "user_id": USER_ID
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if data.get("status") == "finished":
                break
    
    print("✅ 对话继续成功")
    time.sleep(1)
    
    # 6. 更新会话标题
    print("\n6️⃣  更新会话标题...")
    response = requests.put(
        f"{BASE_URL}/chat/sessions/{thread_id}",
        json={
            "user_id": USER_ID,
            "title": "APT攻击深度讨论"
        }
    )
    print(f"✅ 标题更新成功")
    time.sleep(1)
    
    # 7. 获取消息历史
    print("\n7️⃣  获取消息历史...")
    response = requests.get(
        f"{BASE_URL}/chat/sessions/{thread_id}/messages",
        params={"user_id": USER_ID}
    )
    messages = response.json()["messages"]
    print(f"✅ 共有 {len(messages)} 条消息")
    time.sleep(1)
    
    # 8. 删除会话（软删除）
    print("\n8️⃣  删除会话...")
    response = requests.delete(
        f"{BASE_URL}/chat/sessions/{thread_id}",
        params={"user_id": USER_ID, "hard_delete": False}
    )
    print("✅ 会话已软删除")
    
    print("\n" + "="*60)
    print("🎉 所有测试通过！")
    print("="*60)

if __name__ == "__main__":
    test_chat_sessions()
```

运行测试：
```bash
python test_chat_sessions.py
```

---

## 📚 下一步

1. **集成用户认证**: 使用 JWT 或 Session 管理用户登录
2. **会话分享**: 允许用户分享会话给其他人
3. **会话导出**: 导出会话为 Markdown/PDF
4. **消息编辑**: 允许用户编辑已发送的消息
5. **会话搜索**: 在会话和消息中搜索关键词

---

## 🆘 常见问题

### Q: 如何重置所有会话？

```bash
python scripts/create_chat_tables.py recreate
```

### Q: 如何查看 MySQL 中的数据？

```bash
docker exec -it threatrag-mysql mysql -u mysql -p12345678 knowledge_db

# 查看会话
SELECT * FROM chat_sessions LIMIT 10;

# 查看消息
SELECT * FROM chat_messages LIMIT 10;
```

### Q: Redis 缓存如何清理？

```bash
docker exec -it threatrag-redis redis-cli

# 查看所有会话缓存
KEYS chat_session:*

# 删除特定会话缓存
DEL chat_session:uuid-xxx

# 清空所有缓存（谨慎！）
FLUSHDB
```

### Q: 如何备份会话数据？

```bash
# 导出 MySQL 数据
docker exec threatrag-mysql mysqldump -u mysql -p12345678 knowledge_db chat_sessions chat_messages > chat_backup.sql

# 恢复数据
docker exec -i threatrag-mysql mysql -u mysql -p12345678 knowledge_db < chat_backup.sql
```

---

## 📖 相关文档

- [完整 API 文档](chat-session-api.md)
- [模型使用指南](model-usage-examples.md)
- [项目结构说明](../project-structure.mdc)

