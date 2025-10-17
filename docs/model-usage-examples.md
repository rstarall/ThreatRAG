# ThreatRAG 多模型使用指南

## 概述

ThreatRAG 支持多种 LLM 提供商，可以根据不同场景选择最合适的模型：

| 模型提供商 | 优势 | 适用场景 |
|-----------|------|---------|
| **OpenAI** | 强大的推理能力 | 复杂分析、多步推理 |
| **Ollama** | 本地部署、隐私保护 | 敏感数据、离线环境 |
| **DeepSeek** | 中文优化、成本低 | 中文对话、代码生成 |

## 一、OpenAI 模型配置

### 1. 环境变量配置

在 `.env` 文件中添加：
```bash
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 2. 可用模型列表

| 模型名称 | 说明 | 上下文长度 | 适用场景 |
|---------|------|-----------|---------|
| `gpt-4o` | 最新多模态模型 | 128K | 复杂推理、图像分析 |
| `gpt-4o-mini` | 轻量版 GPT-4o | 128K | 日常对话、快速响应 |
| `gpt-4-turbo` | GPT-4 Turbo | 128K | 长文本分析 |
| `gpt-3.5-turbo` | 经济实惠 | 16K | 简单任务、批量处理 |

### 3. API 使用示例

#### 流式聊天
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分析这个 APT 组织的攻击手法",
    "meta": {
      "model_provider": "openai",
      "model_name": "gpt-4o",
      "db_id": "kb_threat_intel",
      "use_graph": true
    }
  }'
```

#### 四阶段混合检索
```bash
curl -X POST http://localhost:8000/chat/hybrid-retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "query": "综合分析 2025年1月6日的攻击事件",
    "meta": {
      "model_provider": "openai",
      "model_name": "gpt-4o-mini",
      "db_id": "kb_daily_reports",
      "vector_top_k": 20,
      "graph_top_k": 15
    },
    "response_mode": "simple"
  }'
```

## 二、Ollama 本地模型配置

### 1. 启动 Ollama 服务

Ollama 已在 `docker-compose.yml` 中配置，启动时会自动运行：
```bash
docker compose up -d ollama
```

验证服务状态：
```bash
docker ps | grep ollama
curl http://localhost:11434/api/tags
```

### 2. 下载推荐模型

#### 中文场景推荐
```bash
# 阿里千问 2.5 (7B) - 中文能力强
docker exec -it threatrag-ollama ollama pull qwen2.5:7b

# 阿里千问 2.5 (14B) - 更强推理
docker exec -it threatrag-ollama ollama pull qwen2.5:14b

# DeepSeek R1 (7B) - 推理优化
docker exec -it threatrag-ollama ollama pull deepseek-r1:7b
```

#### 英文场景推荐
```bash
# Meta Llama 3.2 (3B) - 轻量快速
docker exec -it threatrag-ollama ollama pull llama3.2:3b

# Google Gemma 2 (9B) - 平衡性能
docker exec -it threatrag-ollama ollama pull gemma2:9b

# Mistral (7B) - 高质量输出
docker exec -it threatrag-ollama ollama pull mistral:7b
```

#### 查看已下载的模型
```bash
docker exec -it threatrag-ollama ollama list
```

### 3. GPU 加速配置

系统已自动配置 GPU 支持，验证 GPU 是否被识别：
```bash
docker exec -it threatrag-ollama nvidia-smi
```

### 4. API 使用示例

#### 使用千问模型（中文优化）
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分析 IP 194.48.251.18 的攻击行为特征",
    "meta": {
      "model_provider": "ollama",
      "model_name": "qwen2.5:7b",
      "db_id": "kb_security_logs",
      "use_graph": true
    }
  }'
```

#### 使用 Llama 模型（英文优化）
```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze the attack pattern of APT41",
    "meta": {
      "model_provider": "ollama",
      "model_name": "llama3.2:3b",
      "db_id": "kb_apt_reports",
      "use_graph": true
    }
  }'
```

#### 本地推理任务
```bash
curl -X POST http://localhost:8000/chat/hybrid-retrieval \
  -H "Content-Type: application/json" \
  -d '{
    "query": "总结近期的 DDoS 攻击趋势",
    "meta": {
      "model_provider": "ollama",
      "model_name": "deepseek-r1:7b",
      "db_id": "kb_threat_trends"
    }
  }'
```

## 三、DeepSeek 模型配置

### 1. 环境变量配置

在 `.env` 文件中添加：
```bash
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### 2. API 使用示例

```bash
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "生成这个攻击场景的 Python 检测脚本",
    "meta": {
      "model_provider": "deepseek",
      "model_name": "deepseek-chat",
      "db_id": "kb_malware_samples"
    }
  }'
```

## 四、模型选择策略

### 场景 1：复杂 APT 分析
**推荐**: OpenAI GPT-4o
```json
{
  "model_provider": "openai",
  "model_name": "gpt-4o"
}
```

### 场景 2：敏感情报分析（本地）
**推荐**: Ollama Qwen 2.5 (14B)
```json
{
  "model_provider": "ollama",
  "model_name": "qwen2.5:14b"
}
```

### 场景 3：批量日志分析（成本敏感）
**推荐**: Ollama Llama 3.2 (3B) 或 OpenAI GPT-3.5-turbo
```json
{
  "model_provider": "ollama",
  "model_name": "llama3.2:3b"
}
```

### 场景 4：代码生成和分析
**推荐**: DeepSeek Chat
```json
{
  "model_provider": "deepseek",
  "model_name": "deepseek-chat"
}
```

### 场景 5：中文报告生成
**推荐**: Ollama Qwen 2.5 (7B)
```json
{
  "model_provider": "ollama",
  "model_name": "qwen2.5:7b"
}
```

## 五、性能对比

### 响应速度（参考）
| 模型 | 首 Token 延迟 | 吞吐量 | 适用并发 |
|------|-------------|--------|---------|
| `ollama/qwen2.5:7b` (GPU) | ~50ms | 高 | 10+ |
| `ollama/llama3.2:3b` (GPU) | ~30ms | 很高 | 20+ |
| `openai/gpt-4o-mini` | ~200ms | 中 | 50+ |
| `openai/gpt-4o` | ~300ms | 中 | 20+ |
| `deepseek/deepseek-chat` | ~150ms | 高 | 30+ |

### 成本对比（参考）
| 模型 | 输入价格 | 输出价格 | 适用场景 |
|------|---------|---------|---------|
| Ollama (本地) | ¥0 | ¥0 | 任何场景 |
| DeepSeek | ¥0.001/1K tokens | ¥0.002/1K tokens | 高频调用 |
| GPT-3.5-turbo | ¥0.007/1K tokens | ¥0.014/1K tokens | 简单任务 |
| GPT-4o-mini | ¥0.01/1K tokens | ¥0.03/1K tokens | 平衡性能 |
| GPT-4o | ¥0.35/1K tokens | ¥1.05/1K tokens | 复杂推理 |

## 六、故障排查

### OpenAI 连接问题
```bash
# 测试连接
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 检查环境变量
echo $OPENAI_API_KEY
```

### Ollama 无响应
```bash
# 检查容器状态
docker ps | grep ollama

# 查看日志
docker logs threatrag-ollama

# 重启服务
docker compose restart ollama
```

### GPU 未识别
```bash
# 检查 NVIDIA 驱动
nvidia-smi

# 检查 Docker GPU 支持
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# 重新配置 NVIDIA Container Toolkit
sudo bash scripts/setup-nvidia-docker.sh
```

### 模型下载慢
```bash
# 使用镜像加速（中国大陆）
export OLLAMA_MIRROR=https://ollama.aeko.cn
docker compose restart ollama

# 手动下载模型
docker exec -it threatrag-ollama ollama pull qwen2.5:7b
```

## 七、最佳实践

### 1. 环境隔离
- 生产环境使用 OpenAI/DeepSeek API
- 测试环境使用 Ollama 本地模型

### 2. 模型缓存
```python
# 复用模型实例，避免重复初始化
model = select_model("ollama", "qwen2.5:7b")
```

### 3. 降级策略
```python
try:
    model = select_model("openai", "gpt-4o")
except:
    model = select_model("ollama", "qwen2.5:7b")  # 降级到本地模型
```

### 4. 并发控制
```python
# API 中已实现协程池，限制并发
coroutine_pool = CoroutinePool(max_workers=20)
```

### 5. 超时设置
在生产环境中为 API 调用设置超时：
```bash
curl --max-time 30 http://localhost:8000/chat/stream ...
```

## 八、Python SDK 示例

```python
import requests
import json

class ThreatRAGClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def chat(self, query, model_provider="ollama", model_name="qwen2.5:7b", **kwargs):
        """发送聊天请求"""
        url = f"{self.base_url}/chat/stream"
        payload = {
            "query": query,
            "meta": {
                "model_provider": model_provider,
                "model_name": model_name,
                **kwargs
            }
        }
        
        response = requests.post(url, json=payload, stream=True)
        for line in response.iter_lines():
            if line:
                yield json.loads(line)
    
    def hybrid_retrieval(self, query, model_provider="openai", model_name="gpt-4o-mini", **kwargs):
        """四阶段混合检索"""
        url = f"{self.base_url}/chat/hybrid-retrieval"
        payload = {
            "query": query,
            "meta": {
                "model_provider": model_provider,
                "model_name": model_name,
                **kwargs
            },
            "response_mode": "simple"
        }
        
        response = requests.post(url, json=payload)
        return response.json()

# 使用示例
client = ThreatRAGClient()

# 使用 Ollama 本地模型
for chunk in client.chat(
    "分析这个 IP 的攻击行为",
    model_provider="ollama",
    model_name="qwen2.5:7b",
    db_id="kb_security_logs"
):
    print(chunk)

# 使用 OpenAI 进行深度分析
result = client.hybrid_retrieval(
    "综合分析 APT41 的攻击手法",
    model_provider="openai",
    model_name="gpt-4o",
    db_id="kb_apt_reports"
)
print(result['generated_answer']['content'])
```

## 九、常见问题

### Q: 如何选择合适的模型？
A: 
- 复杂推理 → OpenAI GPT-4o
- 中文对话 → Ollama Qwen 2.5
- 成本敏感 → Ollama 本地模型
- 代码生成 → DeepSeek

### Q: Ollama 模型可以使用 CPU 吗？
A: 可以，但性能会显著降低。推荐使用 GPU（NVIDIA）。

### Q: 如何提高 Ollama 响应速度？
A: 
1. 使用 GPU 加速
2. 选择更小的模型（3B vs 7B）
3. 调整 `num_gpu` 和 `num_thread` 参数

### Q: 可以同时使用多个模型吗？
A: 可以！每个 API 请求可以独立指定 `model_provider` 和 `model_name`。

### Q: 如何监控模型使用情况？
A: 查看应用日志：
```bash
docker logs -f threatrag-threatrag | grep "Selecting model"
```

