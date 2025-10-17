# Ollama 本地模型集成指南

## 概述
Ollama 已集成到 ThreatRAG 系统中，您可以使用本地运行的开源模型进行威胁情报分析。

## 快速启动

### 1. 启动 Ollama 容器
```bash
docker-compose up -d ollama
```

### 2. 下载模型
进入 Ollama 容器并下载您需要的模型：

```bash
# 进入容器
docker exec -it threatrag-ollama bash

# 下载模型（示例）
ollama pull llama3.2:3b          # 3B 参数，适合快速推理
ollama pull qwen2.5:7b           # 7B 参数，中文友好
ollama pull deepseek-r1:7b       # DeepSeek R1 模型
ollama pull mistral:7b           # Mistral 模型

# 查看已下载的模型
ollama list

# 退出容器
exit
```

### 3. 配置 ThreatRAG 使用 Ollama

在 `config.yaml` 中添加 Ollama 配置：

```yaml
# 方式1：作为自定义模型
custom_models:
  - custom_id: "ollama-llama3"
    base_url: "http://ollama:11434/v1"
    api_key: "ollama"  # Ollama 不需要真实 API Key，随便填
    model_name: "llama3.2:3b"
  
  - custom_id: "ollama-qwen"
    base_url: "http://ollama:11434/v1"
    api_key: "ollama"
    model_name: "qwen2.5:7b"

# 方式2：作为独立提供商
model_names:
  ollama:
    base_url: "http://ollama:11434/v1"
    default: "llama3.2:3b"
    models: ["llama3.2:3b", "qwen2.5:7b", "deepseek-r1:7b"]
    env: ["OLLAMA_API_KEY"]  # 可以设为任意值
```

## API 使用示例

### 方式1：使用自定义模型配置
```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分析这个IP的威胁等级",
    "meta": {
      "db_id": "kb_xxx",
      "model_provider": "custom",
      "model_name": "ollama-qwen"
    }
  }'
```

### 方式2：使用独立提供商配置
```bash
curl -X POST http://localhost:8006/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "分析这个IP的威胁等级",
    "meta": {
      "db_id": "kb_xxx",
      "model_provider": "ollama",
      "model_name": "qwen2.5:7b"
    }
  }'
```

## 推荐模型

### 快速推理（适合实时分析）
- **llama3.2:3b** - Meta 的 Llama 3.2，3B 参数，速度快
- **phi3:3.8b** - Microsoft Phi-3，专为效率优化

### 中文友好（适合中文威胁情报）
- **qwen2.5:7b** - 阿里千问 2.5，中文理解优秀
- **glm4:9b** - 智谱 GLM-4，中文推理能力强

### 推理能力强（适合复杂分析）
- **deepseek-r1:7b** - DeepSeek R1，推理链能力强
- **llama3.1:8b** - Meta Llama 3.1，平衡性能

### 专业模型
- **codellama:7b** - 代码分析（适合恶意代码分析）
- **sqlcoder:7b** - SQL 生成（适合 Cypher 查询生成）

## GPU 加速

如果您有 NVIDIA GPU，可以启用 GPU 加速：

### 1. 安装 NVIDIA Container Toolkit
```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 2. 修改 docker-compose.yml
取消 Ollama 服务中的 GPU 配置注释：
```yaml
ollama:
  # ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 3. 重启服务
```bash
docker-compose up -d ollama
```

## 性能优化

### 1. 设置并发数
在启动 Ollama 时设置并发参数：
```bash
docker exec -it threatrag-ollama bash
export OLLAMA_NUM_PARALLEL=4  # 允许4个并发请求
```

### 2. 内存限制
在 docker-compose.yml 中为 Ollama 设置内存限制：
```yaml
ollama:
  # ...
  deploy:
    resources:
      limits:
        memory: 16G  # 根据您的硬件调整
```

### 3. 模型量化
使用量化模型减少内存占用：
```bash
# Q4_0 量化（推荐，质量损失小）
ollama pull qwen2.5:7b-q4_0

# Q8_0 量化（质量更好，但体积大）
ollama pull qwen2.5:7b-q8_0
```

## 常见问题

### Q: Ollama 容器启动后无法访问？
A: 检查健康检查状态：
```bash
docker ps | grep ollama
docker logs threatrag-ollama
```

### Q: 模型下载很慢？
A: 可以使用国内镜像：
```bash
# 设置镜像
export OLLAMA_HOST=https://ollama.mirror.cn  # 示例
ollama pull qwen2.5:7b
```

### Q: 如何查看模型占用的资源？
A: 使用 docker stats：
```bash
docker stats threatrag-ollama
```

### Q: 如何删除不用的模型？
A: 
```bash
docker exec -it threatrag-ollama bash
ollama rm model-name
```

## 监控和日志

### 查看 Ollama 日志
```bash
docker logs -f threatrag-ollama
```

### 查看模型加载情况
```bash
docker exec threatrag-ollama ollama ps
```

### 测试模型
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b",
  "prompt": "什么是网络威胁情报？",
  "stream": false
}'
```

## 最佳实践

1. **模型选择**: 根据任务复杂度选择合适大小的模型
2. **批处理**: 对于批量分析任务，使用较小的模型提高吞吐量
3. **缓存**: 启用 Ollama 的 KV 缓存以提高重复查询的速度
4. **监控**: 定期检查模型的响应时间和资源占用
5. **更新**: 定期更新模型以获得更好的性能

## 相关链接

- [Ollama 官方文档](https://github.com/ollama/ollama)
- [Ollama 模型库](https://ollama.com/library)
- [ThreatRAG 模型集成指南](.cursor/rules/model-integration.mdc)

