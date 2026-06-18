# 使用Python 3.10作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    netcat-openbsd \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/data /app/models /app/saves/log

# 设置脚本执行权限
RUN chmod +x /app/scripts/init-services.sh

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
sleep 30\n\
\n\
# 运行初始化脚本\n\
echo "🔧 运行服务初始化..."\n\
/app/scripts/init-services.sh\n\
\n\
# 启动主应用\n\
echo "🎯 启动 ThreatRAG API..."\n\
exec python main.py' > /app/start.sh && chmod +x /app/start.sh

# 启动命令
CMD ["/app/start.sh"]
