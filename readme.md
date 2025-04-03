
## TreatRAG
ThreadRAG is a RAG(Retrieval-Augmented Generation) framework for CTI(Cyber Threat Intelligence).

## How to run?

start the project with:
```shell
python ./main.py
```
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
install
```shell
pip install milvus
```
start milvus
```shell
milvus-server --data ./milvus_lite

```



