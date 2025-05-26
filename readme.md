
# ThreatRAG

ThreatRAG是一个面向网络威胁情报(CTI)的检索增强生成(RAG)框架，集成了知识图谱和因果推理能力，为安全分析师提供智能化的威胁情报分析工具。

## 项目架构

ThreatRAG由以下主要模块组成：

- **RAG模块**：基于LangChain实现的检索增强生成系统，支持多种文档格式和向量数据库
- **知识图谱(KG)模块**：实体关系抽取、图谱构建与存储
- **因果推理模块**：基于离散时间拓扑霍克斯过程的威胁情报图谱关系推理
- **API服务**：FastAPI实现的后端服务，提供对话和检索接口

```
ThreatRAG/
├── rag/                # 检索增强生成模块
│   ├── api/            # API接口
│   ├── agents/         # 智能代理
│   ├── chains/         # LLM链
│   └── vector/         # 向量数据库
├── kg/                 # 知识图谱模块
│   ├── data_process/   # 数据处理
│   └── data_spider/    # 数据爬取
├── experiment/         # 实验模块
│   └── rl_moldel/      # 强化学习模型
└── main.py             # 主程序入口
```

## 功能特点

- **智能检索**：基于向量数据库的相似度检索，支持多种文档格式
- **实体关系抽取**：从非结构化威胁情报报告中提取实体和关系
- **知识图谱构建**：将提取的实体关系保存到Neo4j图数据库
- **因果推理**：基于强化学习的图谱关系推理与补全
- **流式对话**：支持流式输出的对话接口

## 快速开始

### 环境配置

1. 克隆项目并安装依赖：

```bash
git clone https://github.com/yourusername/ThreatRAG.git
cd ThreatRAG
pip install -r requirements.txt
```

2. 配置环境变量（创建.env文件）：

```
# 模型配置
BASE_MODEL=deepseek-ai/DeepSeek-V2.5
# SiliconFlow API
API_BASE=https://api.siliconflow.cn/v1
API_KEY=your_key_of_siliconflow
# OpenAI API (可选)
OPENAI_API_KEY=your_openai_api_key
# 环境配置
FASTAPI_ENV=development
# Neo4j配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678
NEO4J_DATABASE=neo4j
```

### 启动服务

启动项目：

```bash
python ./main.py
```

### 数据库配置

#### Neo4j

- 用户名：neo4j
- 密码：12345678
- 访问地址：http://localhost:7474/browser/

#### Milvus

安装：

```bash
pip install milvus
```

启动Milvus：

```bash
milvus-server --data ./milvus_lite
```

## 模块说明

### RAG模块

RAG模块基于LangChain实现，支持多种文档格式和向量数据库，提供智能检索和对话功能。

主要特点：
- 支持PDF、TXT、DOCX等多种文档格式
- 使用FAISS向量数据库进行高效检索
- 支持流式输出的对话接口
- 自动检测和更新文档变化

### 知识图谱模块

知识图谱模块负责从非结构化威胁情报报告中提取实体和关系，并构建知识图谱。

主要功能：
- 使用大语言模型进行命名实体识别和关系抽取
- 支持批量推理和处理
- 将提取的实体关系保存到Neo4j图数据库
- 提供图谱查询和可视化接口

### 因果推理模块

因果推理模块基于离散时间拓扑霍克斯过程和强化学习，实现威胁情报图谱关系推理与补全。

主要特点：
- 因果感知的关系预测
- 反事实推理能力
- 图谱补全能力
- 可解释性保障

## 前端界面

前端项目仓库：[https://github.com/rstarall/br-cti-chat](https://github.com/rstarall/br-cti-chat)

## 贡献指南

欢迎贡献代码或提出问题！请遵循以下步骤：

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。
