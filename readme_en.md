# ThreatRAG

ThreatRAG is a Retrieval-Augmented Generation (RAG) framework for Cyber Threat Intelligence (CTI), integrating knowledge graph and causal reasoning capabilities to provide security analysts with an intelligent threat intelligence analysis tool.

## Project Architecture

ThreatRAG consists of the following main modules:

- **RAG Module**: A retrieval-augmented generation system based on LangChain, supporting various document formats and vector databases
- **Knowledge Graph (KG) Module**: Entity relationship extraction, graph construction and storage
- **Causal Reasoning Module**: Threat intelligence graph relationship reasoning based on discrete-time topological Hawkes process
- **API Service**: Backend service implemented with FastAPI, providing conversation and retrieval interfaces

```
ThreatRAG/
├── rag/                # Retrieval-Augmented Generation module
│   ├── api/            # API interfaces
│   ├── agents/         # Intelligent agents
│   ├── chains/         # LLM chains
│   └── vector/         # Vector database
├── kg/                 # Knowledge Graph module
│   ├── data_process/   # Data processing
│   └── data_spider/    # Data crawling
├── experiment/         # Experiment module
│   └── rl_moldel/      # Reinforcement learning model
└── main.py             # Main program entry
```

## Features

- **Intelligent Retrieval**: Similarity-based retrieval using vector databases, supporting various document formats
- **Entity Relationship Extraction**: Extracting entities and relationships from unstructured threat intelligence reports
- **Knowledge Graph Construction**: Saving extracted entity relationships to Neo4j graph database
- **Causal Reasoning**: Graph relationship reasoning and completion based on reinforcement learning
- **Streaming Conversation**: Conversation interface with streaming output support

## Quick Start

### Environment Setup

1. Clone the project and install dependencies:

```bash
git clone https://github.com/yourusername/ThreatRAG.git
cd ThreatRAG
pip install -r requirements.txt
```

2. Configure environment variables (create .env file):

```
# Model configuration
BASE_MODEL=deepseek-ai/DeepSeek-V2.5
# SiliconFlow API
API_BASE=https://api.siliconflow.cn/v1
API_KEY=your_key_of_siliconflow
# OpenAI API (optional)
OPENAI_API_KEY=your_openai_api_key
# Environment configuration
FASTAPI_ENV=development
# Neo4j configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=12345678
NEO4J_DATABASE=neo4j
```

### Start Service

Start the project:

```bash
python ./main.py
```

### Database Configuration

#### Neo4j

- Username: neo4j
- Password: 12345678
- Access URL: http://localhost:7474/browser/

#### Milvus

Installation:

```bash
pip install milvus
```

Start Milvus:

```bash
milvus-server --data ./milvus_lite
```

## Module Description

### RAG Module

The RAG module is implemented based on LangChain, supporting various document formats and vector databases, providing intelligent retrieval and conversation capabilities.

Key features:
- Support for multiple document formats including PDF, TXT, DOCX, etc.
- Efficient retrieval using FAISS vector database
- Conversation interface with streaming output support
- Automatic detection and update of document changes

### Knowledge Graph Module

The Knowledge Graph module is responsible for extracting entities and relationships from unstructured threat intelligence reports and constructing knowledge graphs.

Main functions:
- Named entity recognition and relationship extraction using large language models
- Support for batch inference and processing
- Saving extracted entity relationships to Neo4j graph database
- Providing graph query and visualization interfaces

### Causal Reasoning Module

The Causal Reasoning module is based on discrete-time topological Hawkes process and reinforcement learning, implementing threat intelligence graph relationship reasoning and completion.

Key features:
- Causality-aware relationship prediction
- Counterfactual reasoning capability
- Graph completion capability
- Explainability guarantee

## Frontend Interface

Frontend project repository: [https://github.com/rstarall/br-cti-chat](https://github.com/rstarall/br-cti-chat)

## Contribution Guidelines

Contributions and issues are welcome! Please follow these steps:

1. Fork the project
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
