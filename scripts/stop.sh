#!/bin/bash

# ThreatRAG 停止脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 停止 ThreatRAG 服务...${NC}"

# 检查是否有运行的服务
if ! docker-compose ps | grep -q "Up\|healthy"; then
    echo -e "${YELLOW}⚠️  没有运行中的服务${NC}"
    exit 0
fi

# 停止服务
if [ "$1" = "--remove" ] || [ "$1" = "-r" ]; then
    echo -e "${YELLOW}🗑️  停止服务并删除容器...${NC}"
    docker-compose down
elif [ "$1" = "--clean" ] || [ "$1" = "-c" ]; then
    echo -e "${RED}🧹 停止服务、删除容器和数据卷 (⚠️  这将删除所有数据！)${NC}"
    read -p "确认删除所有数据？(y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        echo -e "${GREEN}✓ 所有服务和数据已清除${NC}"
    else
        echo -e "${YELLOW}操作已取消${NC}"
    fi
else
    echo -e "${YELLOW}🔄 停止服务...${NC}"
    docker-compose stop
fi

echo -e "${GREEN}✓ ThreatRAG 服务已停止${NC}"

echo -e "${BLUE}💡 使用提示:${NC}"
echo "• 重新启动: ./scripts/start.sh"
echo "• 停止并删除容器: ./scripts/stop.sh --remove"
echo "• 完全清除(包括数据): ./scripts/stop.sh --clean"
