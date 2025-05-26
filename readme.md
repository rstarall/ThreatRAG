
## TreatRAG
ThreadRAG is a RAG(Retrieval-Augmented Generation) framework for CTI(Cyber Threat Intelligence).

## How to run?

首先安装依赖：
```shell
pip install -r requirements.txt
```

然后启动项目：
```shell
python ./main.py
```

**注意：** 从现在开始，启动main.py时会自动启动本地的Milvus服务器，无需手动启动。如果是第一次运行，系统会自动安装milvus。

please confirm the .env file is setup:
```yaml
#BASE_MODEL=gpt-4o-mini
BASE_MODEL=deepseek-ai/DeepSeek-V2.5
#siliconflow
API_BASE=https://api.siliconflow.cn/v1
API_KEY=your key of siliconflow
#OPENAI
OPENAI_API_KEY=sk-DGEoAotAgPZBovEm3rWjhHAd3plK6qaZjpi1vwwNFfWiQp6w
FASTAPI_ENV=development
```
## the chat frontend
you can get the frontend:
[https://github.com/rstarall/br-cti-chat](https://github.com/rstarall/br-cti-chat)

## the default database
### neo4J
username:neo4j
password:12345678

### milvus
Milvus会在启动main.py时自动安装和启动。

如果需要手动管理，可以使用以下命令：

安装milvus：
```shell
pip install milvus
```

手动启动milvus（通常不需要，因为会自动启动）：
```shell
milvus-server --data ./milvus_lite
```

配置选项（在config.yaml中）：
```yaml
milvus:
  auto_start: true          # 是否自动启动milvus
  data_dir: ./milvus_lite   # 数据存储目录
  host: 127.0.0.1          # 监听地址
  port: 19530              # 监听端口
```



