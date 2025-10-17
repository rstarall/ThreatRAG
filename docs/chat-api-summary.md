# 聊天 API 总结

## 🎯 核心特性

ThreatRAG 聊天系统提供 **两种灵活的使用方式**：

### 方式 1: 快捷方式 ⚡
**一步到位，自动创建会话**

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好",
    "user_id": 1
  }'
```

- ✅ 无需预先创建会话
- ✅ 系统自动创建并返回 `thread_id`
- ✅ 适合快速开始聊天

---

### 方式 2: 标准方式 🎛️
**完全控制，显式管理会话**

```bash
# 1. 创建会话
curl -X POST http://localhost:8006/chat/sessions/create \
  -d '{"user_id": 1, "title": "我的会话"}'

# 2. 发送消息
curl -X POST http://localhost:8006/chat/stream \
  -d '{"query": "你好", "user_id": 1, "thread_id": "abc123..."}'
```

- ✅ 完全控制会话创建
- ✅ 可以批量预创建会话
- ✅ 适合需要精确控制的场景

---

## 📊 对比表格

| 特性 | 快捷方式 | 标准方式 |
|------|---------|---------|
| **API 调用次数** | 1 次（直接聊天） | 2 次（创建+聊天） |
| **会话控制** | 自动创建 | 手动控制 |
| **适用场景** | 快速测试、简单对话 | 生产环境、批量创建 |
| **会话标题** | 通过 `meta.title` 设置 | 显式设置 |
| **系统提示词** | 通过 `meta.system_prompt` | 显式设置 |

---

## 🚀 快速开始

### 第一次聊天（快捷方式）

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是APT攻击？",
    "user_id": 1,
    "meta": {
      "title": "威胁情报咨询",
      "system_prompt": "你是一个专业的威胁情报分析师",
      "model_provider": "deepseek"
    }
  }'
```

**响应：**
```json
{
  "response": "APT是...",
  "status": "loading",
  "thread_id": "a1b2c3d4-..."  ← 保存这个ID！
}
```

---

### 继续对话

```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何防御？",
    "user_id": 1,
    "thread_id": "a1b2c3d4-..."
  }'
```

---

## 🔑 关键要点

### ✅ 推荐做法

1. **快速测试**: 不提供 `thread_id`，让系统自动创建
2. **生产环境**: 使用 `POST /chat/sessions/create` 创建会话
3. **保存 thread_id**: 客户端必须保存返回的 `thread_id` 用于后续对话
4. **会话管理**: 定期清理或归档旧会话

### ⚠️ 注意事项

1. **user_id 必需**: 所有操作都需要提供用户ID
2. **权限隔离**: 用户只能访问自己的会话
3. **thread_id 持久化**: 客户端需要保存 `thread_id`（localStorage/数据库）
4. **会话验证**: 提供 `thread_id` 时会验证会话存在和权限

---

## 📝 完整 API 列表

| 端点 | 方法 | 功能 |
|------|------|------|
| `/chat/sessions/create` | POST | 创建新会话 |
| `/chat/stream` | POST | 发送消息（可自动创建会话） |
| `/chat/sessions` | GET | 获取用户所有会话 |
| `/chat/sessions/{id}` | GET | 获取会话详情 |
| `/chat/sessions/{id}` | PUT | 更新会话 |
| `/chat/sessions/{id}` | DELETE | 删除会话 |
| `/chat/sessions/{id}/messages` | GET | 获取消息历史 |
| `/chat/sessions/{id}/messages/{msg_id}` | DELETE | 删除消息 |

---

## 💡 使用建议

### 场景 1: 移动端 App
**推荐：快捷方式**

```typescript
// 简单调用，自动创建会话
async function sendMessage(query: string) {
  const response = await fetch('/chat/stream', {
    method: 'POST',
    body: JSON.stringify({
      query,
      user_id: currentUserId
    })
  });
  
  // 从响应中提取 thread_id 并保存
  // ...
}
```

---

### 场景 2: Web 管理后台
**推荐：标准方式**

```typescript
class SessionManager {
  // 批量预创建会话
  async createMultipleSessions(topics: string[]) {
    const sessions = [];
    for (const topic of topics) {
      const session = await fetch('/chat/sessions/create', {
        method: 'POST',
        body: JSON.stringify({
          user_id: currentUserId,
          title: topic
        })
      });
      sessions.push(await session.json());
    }
    return sessions;
  }
  
  // 在特定会话中聊天
  async chatInSession(sessionId: string, query: string) {
    return await fetch('/chat/stream', {
      method: 'POST',
      body: JSON.stringify({
        query,
        user_id: currentUserId,
        thread_id: sessionId
      })
    });
  }
}
```

---

### 场景 3: 自动化脚本
**推荐：快捷方式**

```python
import requests

def analyze_threat(query):
    # 一次调用即可
    response = requests.post(
        'http://localhost:8006/chat/stream',
        json={
            'query': query,
            'user_id': 1,
            'meta': {
                'model_provider': 'deepseek',
                'db_id': 'kb_threats'
            }
        },
        stream=True
    )
    
    # 处理流式响应...
```

---

## 🔄 迁移指南

### 从旧版本迁移

**旧代码（假设）:**
```python
# 必须先创建会话
session_id = create_session(user_id, title)
# 然后聊天
send_message(session_id, query)
```

**新代码（两种方式都支持）:**

**选项 A: 保持原有逻辑**
```python
# 仍然可以用旧方式
session_id = create_session(user_id, title)
send_message(session_id, query)
```

**选项 B: 简化为一步**
```python
# 或使用新的快捷方式
send_message_auto(query, user_id, title=title)
```

---

## 📚 相关文档

- [完整 API 文档](chat-session-api.md) - 详细的API参数说明
- [快速开始指南](chat-session-quickstart.md) - 5分钟上手教程
- [工作流程图](chat-api-workflow.md) - 详细的使用场景
- [模型使用指南](model-usage-examples.md) - 多模型切换

---

## 🎉 总结

ThreatRAG 聊天系统提供了 **灵活且强大** 的 API：

- ✅ **快捷模式**: 一步到位，自动创建会话
- ✅ **标准模式**: 完全控制，显式管理会话
- ✅ **兼容性强**: 新旧代码都能正常工作
- ✅ **文档完善**: 详细的使用示例和最佳实践

选择适合您场景的方式，开始使用吧！🚀

