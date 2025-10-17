# 聊天 API 使用流程

## 📋 完整工作流程

### 方式 A: 快捷流程（自动创建会话）

```
┌─────────────────────────────────────────────────────────────┐
│              1. 发送消息（自动创建会话）                      │
│   POST /chat/stream                                          │
│   { "query": "...", "user_id": 1,                           │
│     "meta": {"title": "...", "system_prompt": "..."} }      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  流式响应       │  ← 实时显示
              │  + thread_id   │  ← 保存这个ID！
              └────────┬───────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    2. 继续对话                               │
│   POST /chat/stream                                          │
│   { "query": "...", "thread_id": "...", "user_id": 1 }      │
└─────────────────────────────────────────────────────────────┘
```

### 方式 B: 标准流程（显式创建会话）

```
┌─────────────────────────────────────────────────────────────┐
│                    1. 创建新会话                             │
│   POST /chat/sessions/create                                │
│   { "user_id": 1, "title": "...", "system_prompt": "..." }  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  session_id    │  ← 保存这个ID！
              └────────┬───────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    2. 发送消息                               │
│   POST /chat/stream                                          │
│   { "query": "...", "thread_id": "...", "user_id": 1 }      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  流式响应       │  ← 实时显示
              └────────┬───────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    3. 继续对话                               │
│   POST /chat/stream (相同的 thread_id)                       │
│   { "query": "...", "thread_id": "...", "user_id": 1 }      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  流式响应       │
              └────────┬───────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              4. 管理会话（可选）                             │
│   - 查看所有会话: GET /chat/sessions?user_id=1              │
│   - 查看详情: GET /chat/sessions/{id}?user_id=1             │
│   - 更新标题: PUT /chat/sessions/{id}                        │
│   - 删除会话: DELETE /chat/sessions/{id}?user_id=1          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 典型使用场景

### 场景 1: 新用户首次使用（快捷方式）

```bash
# Step 1: 直接开始聊天（自动创建会话）
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是APT攻击？",
    "user_id": 1,
    "meta": {
      "title": "威胁情报咨询",
      "system_prompt": "你是一个专业的威胁情报分析师"
    }
  }'

# 响应中包含 thread_id: "abc123..."

# Step 2: 继续对话（使用返回的 thread_id）
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何防御？",
    "user_id": 1,
    "thread_id": "abc123..."
  }'
```

---

### 场景 1B: 新用户首次使用（标准方式）

```bash
# Step 1: 创建会话
curl -X POST http://localhost:8006/chat/sessions/create \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "title": "威胁情报咨询"
  }'

# 响应: {"success": true, "session_id": "abc123..."}

# Step 2: 开始聊天
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是APT攻击？",
    "user_id": 1,
    "thread_id": "abc123..."
  }'

# Step 3: 继续对话
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何防御？",
    "user_id": 1,
    "thread_id": "abc123..."
  }'
```

---

### 场景 2: 用户恢复之前的会话

```bash
# Step 1: 查看所有会话
curl "http://localhost:8006/chat/sessions?user_id=1"

# 响应: 返回会话列表，选择一个 session_id

# Step 2: 查看历史消息
curl "http://localhost:8006/chat/sessions/abc123.../messages?user_id=1"

# Step 3: 继续对话
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "继续之前的话题",
    "thread_id": "abc123...",
    "user_id": 1
  }'
```

---

### 场景 3: 多会话管理

```bash
# 创建多个不同主题的会话

# 会话1: APT分析
curl -X POST http://localhost:8006/chat/sessions/create \
  -d '{"user_id": 1, "title": "APT分析"}'
# → session_id: "sess-apt-001"

# 会话2: 恶意软件分析
curl -X POST http://localhost:8006/chat/sessions/create \
  -d '{"user_id": 1, "title": "恶意软件分析"}'
# → session_id: "sess-malware-001"

# 会话3: 漏洞研究
curl -X POST http://localhost:8006/chat/sessions/create \
  -d '{"user_id": 1, "title": "漏洞研究"}'
# → session_id: "sess-vuln-001"

# 在不同会话中分别对话
curl -X POST http://localhost:8006/chat/stream \
  -d '{"query": "APT相关问题", "thread_id": "sess-apt-001", "user_id": 1}'

curl -X POST http://localhost:8006/chat/stream \
  -d '{"query": "恶意软件问题", "thread_id": "sess-malware-001", "user_id": 1}'
```

---

## ⚠️ 重要注意事项

### ✅ 正确的流程

1. **先创建会话** → `POST /chat/sessions/create`
2. **获取 session_id** → 保存在客户端（localStorage/内存/数据库）
3. **发送消息** → `POST /chat/stream` 带上 `thread_id`
4. **所有后续消息** → 使用相同的 `thread_id`

### ❌ 错误的用法

```bash
# ✅ 正确：不提供 thread_id 会自动创建会话
curl -X POST http://localhost:8006/chat/stream \
  -d '{"query": "你好", "user_id": 1}'
# 正确！会自动创建新会话

# ❌ 错误：使用不存在的 session_id
curl -X POST http://localhost:8006/chat/stream \
  -d '{"query": "你好", "user_id": 1, "thread_id": "fake-id"}'
# 错误: 404 会话不存在或无权访问

# ❌ 错误：user_id 不匹配
curl -X POST http://localhost:8006/chat/stream \
  -d '{"query": "你好", "user_id": 2, "thread_id": "user1-session"}'
# 错误: 404 会话不存在或无权访问
```

---

## 🎯 最佳实践

### 1. 客户端会话管理

```typescript
class SessionManager {
  private currentSessionId: string | null = null;
  
  async startNewSession(title?: string) {
    const response = await fetch('/chat/sessions/create', {
      method: 'POST',
      body: JSON.stringify({
        user_id: this.userId,
        title: title || `对话 ${new Date().toLocaleString()}`
      })
    });
    
    const data = await response.json();
    this.currentSessionId = data.session_id;
    
    // 保存到 localStorage
    localStorage.setItem('current_session_id', this.currentSessionId);
    
    return this.currentSessionId;
  }
  
  getCurrentSessionId() {
    if (!this.currentSessionId) {
      // 尝试从 localStorage 恢复
      this.currentSessionId = localStorage.getItem('current_session_id');
    }
    return this.currentSessionId;
  }
  
  async sendMessage(query: string) {
    const sessionId = this.getCurrentSessionId();
    if (!sessionId) {
      throw new Error('请先创建会话');
    }
    
    // 发送消息...
  }
}
```

### 2. 错误处理

```typescript
async function sendMessage(query: string, threadId: string, userId: number) {
  try {
    const response = await fetch('/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, thread_id: threadId, user_id: userId })
    });
    
    if (response.status === 404) {
      // 会话不存在，创建新会话
      console.log('会话已过期，创建新会话...');
      const newSessionId = await createSession(userId);
      return await sendMessage(query, newSessionId, userId);
    }
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    
    // 处理流式响应...
  } catch (error) {
    console.error('发送消息失败:', error);
    throw error;
  }
}
```

### 3. 会话生命周期

```typescript
class ChatApp {
  // 应用启动时
  async onAppStart() {
    // 尝试恢复上次的会话
    const lastSessionId = localStorage.getItem('last_session_id');
    
    if (lastSessionId) {
      // 验证会话是否仍然有效
      const isValid = await this.validateSession(lastSessionId);
      if (isValid) {
        this.currentSessionId = lastSessionId;
        await this.loadSessionHistory(lastSessionId);
      } else {
        // 会话已失效，创建新会话
        this.currentSessionId = await this.createSession();
      }
    } else {
      // 没有历史会话，创建新会话
      this.currentSessionId = await this.createSession();
    }
  }
  
  // 用户切换会话
  async switchSession(sessionId: string) {
    this.currentSessionId = sessionId;
    localStorage.setItem('last_session_id', sessionId);
    await this.loadSessionHistory(sessionId);
  }
  
  // 用户创建新会话
  async createNewSession(title?: string) {
    const sessionId = await this.createSession(title);
    this.currentSessionId = sessionId;
    localStorage.setItem('last_session_id', sessionId);
    return sessionId;
  }
}
```

---

## 📊 数据流图

```
用户操作                API 调用                     数据库操作
    │                      │                            │
    │                      │                            │
    ▼                      ▼                            ▼
┌─────────┐         ┌──────────┐              ┌──────────────┐
│ 创建会话 │────────▶│  POST    │─────────────▶│ MySQL INSERT │
│         │         │ /sessions│              │ chat_sessions│
└─────────┘         │ /create  │              └──────┬───────┘
                    └──────────┘                     │
                         │                           │
                         │◀──────────────────────────┘
                         │ (返回 session_id)
                         │
    ┌────────────────────┘
    │
    ▼
┌─────────┐         ┌──────────┐              ┌──────────────┐
│ 发送消息 │────────▶│  POST    │──┬──────────▶│ MySQL INSERT │
│         │         │ /stream  │  │           │ chat_messages│
└─────────┘         └──────────┘  │           └──────────────┘
                         │         │
                         │         └──────────▶ Redis SET
                         │                     (缓存消息)
                         │
                         ▼
                    (流式响应)
                         │
    ┌────────────────────┘
    │
    ▼
┌─────────┐         ┌──────────┐              ┌──────────────┐
│ 查询历史 │────────▶│   GET    │──┬──────────▶│ Redis GET    │
│         │         │ /sessions│  │           │ (缓存命中)   │
└─────────┘         │/{id}     │  │           └──────┬───────┘
                    └──────────┘  │                  │
                         │         │ (未命中)         │ (命中)
                         │         └─────────▶MySQL  │
                         │           SELECT          │
                         │                            │
                         │◀───────────────────────────┘
                         │
                         ▼
                    (返回历史)
```

---

## 🔍 调试技巧

### 查看会话是否存在

```bash
curl "http://localhost:8006/chat/sessions/<session_id>?user_id=1"
```

### 查看所有会话

```bash
curl "http://localhost:8006/chat/sessions?user_id=1"
```

### 测试权限控制

```bash
# 尝试访问其他用户的会话（应该失败）
curl "http://localhost:8006/chat/sessions/<user1-session-id>?user_id=2"
# 预期: 404 会话不存在或无权访问
```

### 检查 Redis 缓存

```bash
docker exec -it threatrag-redis redis-cli

# 查看所有会话缓存
KEYS chat_session:*

# 查看特定会话
GET chat_session:<session_id>
```

### 检查 MySQL 数据

```bash
docker exec -it threatrag-mysql mysql -u mysql -p12345678 knowledge_db

# 查看会话表
SELECT * FROM chat_sessions WHERE user_id = 1 ORDER BY updated_at DESC;

# 查看消息表
SELECT * FROM chat_messages WHERE session_id = '<session_id>' ORDER BY created_at;
```

---

## 📚 相关文档

- [完整 API 文档](chat-session-api.md)
- [快速开始指南](chat-session-quickstart.md)
- [模型使用指南](model-usage-examples.md)

