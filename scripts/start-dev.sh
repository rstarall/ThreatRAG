#!/bin/bash

# ThreatRAG 开发环境启动脚本
# 支持源代码热重载的开发模式

set -e

echo "🚀 启动 ThreatRAG 开发环境..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi

# 检查 Docker Compose 是否可用
if ! docker-compose --version > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker Compose 不可用${NC}"
    exit 1
fi

echo -e "${BLUE}📋 开发环境特性:${NC}"
echo "• 源代码热重载 - 修改 src/ 目录下的文件会自动重启服务"
echo "• 配置热重载 - 修改 .env 文件后重启服务即可生效"
echo "• 开发模式配置 - 使用开发环境特定的配置"
echo "• 详细日志输出 - 便于调试和开发"
echo ""

# 停止现有服务
echo -e "${YELLOW}停止现有服务...${NC}"
docker-compose -f docker-compose.dev.yml down 2>/dev/null || true

# 启动开发环境
echo -e "${YELLOW}启动开发环境服务...${NC}"
docker-compose -f docker-compose.dev.yml up -d

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 10

# 显示服务状态
echo -e "${BLUE}📊 服务状态:${NC}"
docker-compose -f docker-compose.dev.yml ps

echo ""
echo -e "${GREEN}🎉 开发环境启动完成！${NC}"
echo ""
echo -e "${BLUE}📍 服务访问地址:${NC}"
echo "• ThreatRAG API: http://localhost:8000"
echo "• API 文档: http://localhost:8000/docs"
echo "• Neo4j Browser: http://localhost:7474 (neo4j/12345678)"
echo "• MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo -e "${YELLOW}💡 开发提示:${NC}"
echo "• 修改 src/ 目录下的 Python 文件会自动重启服务"
echo "• 修改 .env 文件后需要重启服务: docker-compose -f docker-compose.dev.yml restart threatrag"
echo "• 查看实时日志: docker-compose -f docker-compose.dev.yml logs -f threatrag"
echo "• 重启服务: docker-compose -f docker-compose.dev.yml restart threatrag"
echo "• 停止服务: docker-compose -f docker-compose.dev.yml down"
echo ""
echo -e "${BLUE}🔧 热重载说明:${NC}"
echo "• 支持热重载的文件: src/ 目录下的所有 .py 文件"
echo "• 配置热重载: .env 文件修改后重启服务即可生效"
echo "• 不支持热重载的文件: requirements.txt, config.yaml 等配置文件"
echo "• 修改不支持热重载的文件后需要重启容器"
