# 数据存储说明（可添加到主 README）

## 📦 数据持久化

ThreatRAG 使用本地目录挂载来存储所有数据，便于备份、迁移和管理：

```
ThreatRAG/
└── data/                   # 所有持久化数据
    ├── mysql/             # MySQL 数据库
    ├── redis/             # Redis 缓存
    ├── neo4j/             # 知识图谱
    ├── milvus/            # 向量数据库
    ├── ollama/            # 本地 LLM 模型
    └── kb_*/              # 用户知识库
```

### 优势
- ✅ 数据可直接访问和查看
- ✅ 备份只需复制 `data` 目录
- ✅ 迁移服务器更简单
- ✅ 易于监控磁盘使用

### 首次启动
```bash
docker compose up -d
```
数据目录会自动创建。

### 从旧版本迁移
如果您之前使用 Docker volumes：
```bash
sudo bash scripts/migrate-volumes-to-local.sh
```

详见：[Volume 迁移指南](docs/volume-migration-guide.md)

---

## 🔒 数据安全

### 备份
```bash
# 创建备份
tar -czf threatrag-backup-$(date +%Y%m%d).tar.gz data/

# 恢复
tar -xzf threatrag-backup-20250116.tar.gz
```

### 自动备份
```bash
# 添加到 crontab（每天凌晨 2 点）
0 2 * * * cd /path/to/ThreatRAG && tar -czf /backups/threatrag-$(date +\%Y\%m\%d).tar.gz data/
```

### .gitignore
数据目录已自动排除在版本控制之外：
```gitignore
data/mysql/
data/redis/
data/neo4j/
data/etcd/
data/minio/
data/milvus/
data/ollama/
```

---

## 💾 磁盘空间管理

### 查看占用
```bash
du -sh data/*
```

### 预估空间需求
| 组件 | 最小 | 推荐 | 说明 |
|------|------|------|------|
| MySQL | 1 GB | 5 GB | 元数据 |
| Redis | 100 MB | 500 MB | 缓存 |
| Neo4j | 1 GB | 10 GB | 知识图谱 |
| Milvus | 5 GB | 50 GB | 向量数据 |
| Ollama | 5 GB | 30 GB | 本地模型 |
| **总计** | **12 GB** | **95 GB** | |

### 清理空间
```bash
# 删除不用的 Ollama 模型
docker exec -it threatrag-ollama ollama rm <model-name>

# 清理旧日志
find data/neo4j/logs -name "*.log" -mtime +7 -delete

# 清理 Docker 缓存
docker system prune -a
```

---

