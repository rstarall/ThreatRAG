# 使用Python 3.10作为基础镜像
FROM docker1.aeko.cn/library/python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    default-libmysqlclient-dev \
    default-mysql-client \
    curl \
    netcat-openbsd \
    redis-tools \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    antiword \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install  -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p /app/data /app/models /app/saves/log

# 设置Python路径
ENV PYTHONPATH=/app

# 设置默认环境变量
ENV FASTAPI_ENV=production

# 暴露端口
EXPOSE 8006

# 复制启动脚本
COPY scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh || true
RUN sed -i 's/\r$//' /app/start.sh || true

# 启动命令
CMD ["bash", "/app/start.sh"]