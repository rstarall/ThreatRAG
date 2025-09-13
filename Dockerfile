# 使用Python 3.10作为基础镜像
FROM docker1.aeko.cn/library/python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    default-libmysqlclient-dev \
    curl \
    netcat-openbsd \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/data /app/models /app/saves/log

# 设置Python路径
ENV PYTHONPATH=/app

# 设置默认环境变量
ENV FASTAPI_ENV=production

# 暴露端口
EXPOSE 8000

# 创建启动脚本
RUN echo '#!/bin/bash\n\
    set -e\n\
    echo "🚀 启动 ThreatRAG 服务..."\n\
    \n\
    # 等待依赖服务启动\n\
    echo "⏳ 等待依赖服务启动..."\n\
    \n\
    # 等待MySQL启动\n\
    echo "⏳ 等待MySQL启动..."\n\
    until nc -z -v -w30 mysql 3306\n\
    do\n\
    echo "等待MySQL启动..."\n\
    sleep 5\n\
    done\n\
    echo "✅ MySQL已启动"\n\
    \n\
    # 等待Redis启动\n\
    echo "⏳ 等待Redis启动..."\n\
    until nc -z -v -w30 redis 6379\n\
    do\n\
    echo "等待Redis启动..."\n\
    sleep 5\n\
    done\n\
    echo "✅ Redis已启动"\n\
    \n\
    # 等待RabbitMQ启动\n\
    echo "⏳ 等待RabbitMQ启动..."\n\
    until nc -z -v -w30 rabbitmq 5672\n\
    do\n\
    echo "等待RabbitMQ启动..."\n\
    sleep 5\n\
    done\n\
    echo "✅ RabbitMQ已启动"\n\
    \n\
    # 等待Neo4j启动\n\
    echo "⏳ 等待Neo4j启动..."\n\
    until nc -z -v -w30 neo4j 7687\n\
    do\n\
    echo "等待Neo4j启动..."\n\
    sleep 5\n\
    done\n\
    echo "✅ Neo4j已启动"\n\
    \n\
    # 等待Milvus启动\n\
    echo "⏳ 等待Milvus启动..."\n\
    until nc -z -v -w30 milvus-standalone 19530\n\
    do\n\
    echo "等待Milvus启动..."\n\
    sleep 5\n\
    done\n\
    echo "✅ Milvus已启动"\n\
    \n\
    # 启动主应用\n\
    echo "🎯 启动ThreatRAG API..."\n\
    exec python main.py' > /app/start.sh && chmod +x /app/start.sh

# 启动命令
CMD ["/app/start.sh"]