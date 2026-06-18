#!/bin/bash

# ThreatRAG 快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
cat << "EOF"
 _____ _                    _   ____    _    ____ 
|_   _| |__  _ __ ___  __ _| |_|  _ \  / \  / ___|
  | | | '_ \| '__/ _ \/ _` | __| |_) |/ _ \| |  _ 
  | | | | | | | |  __/ (_| | |_|  _ </ ___ \ |_| |
  |_| |_| |_|_|  \___|\__,_|\__|_| \_\_/   \____|
                                                 
EOF
echo -e "${NC}"

echo -e "${BLUE}🚀 ThreatRAG 威胁情报检索增强生成系统${NC}"
echo -e "${BLUE}================================================${NC}"

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装，请先安装 Docker Compose${NC}"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env 文件不存在，从 .env.example 创建...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
        echo -e "${YELLOW}请根据需要修改 .env 文件中的配置${NC}"
    else
        echo -e "${RED}❌ .env.example 文件不存在${NC}"
        exit 1
    fi
fi

# 创建必要的目录
echo -e "${YELLOW}📁 创建必要的目录...${NC}"
mkdir -p data models saves/log

# 检查端口占用
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  端口 $port ($service) 已被占用${NC}"
        read -p "是否继续？(y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

echo -e "${YELLOW}🔍 检查端口占用...${NC}"
check_port 8000 "ThreatRAG API"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 7474 "Neo4j HTTP"
check_port 7687 "Neo4j Bolt"
check_port 19530 "Milvus"
check_port 9000 "MinIO"
check_port 9001 "MinIO Console"

echo -e "${BLUE}🔄 启动服务...${NC}"

# 构建并启动服务
if [ "$1" = "--build" ] || [ "$1" = "-b" ]; then
    echo -e "${YELLOW}🔨 重新构建镜像...${NC}"
    docker-compose build --no-cache
fi

# 启动服务
docker-compose up -d

echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 10

# 运行初始化脚本
if [ -f scripts/init-services.sh ]; then
    echo -e "${BLUE}🔧 运行服务初始化...${NC}"
    chmod +x scripts/init-services.sh
    ./scripts/init-services.sh
else
    echo -e "${YELLOW}⚠️  初始化脚本不存在，跳过自动初始化${NC}"
fi

echo -e "${GREEN}"
cat << "EOF"
🎉 ThreatRAG 启动完成！

📍 服务访问地址:
• ThreatRAG API: http://localhost:8000
• API 文档: http://localhost:8000/docs
• Neo4j Browser: http://localhost:7474 (neo4j/12345678)
• MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

💡 常用命令:
• 查看服务状态: docker-compose ps
• 查看日志: docker-compose logs -f [service_name]
• 停止服务: docker-compose down
• 重启服务: docker-compose restart [service_name]

🔧 开发模式:
• 实时查看 API 日志: docker-compose logs -f threatrag
• 进入 API 容器: docker-compose exec threatrag bash

EOF
echo -e "${NC}"
