#!/bin/bash

# ThreatRAG 服务初始化脚本
# 等待各服务启动并进行初始化配置

set -e

echo "🚀 开始初始化 ThreatRAG 服务..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 等待服务健康检查函数
wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}等待 ${service_name} 服务启动...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z $host $port 2>/dev/null; then
            echo -e "${GREEN}✓ ${service_name} 服务已启动${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}等待 ${service_name} 服务启动 (${attempt}/${max_attempts})...${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}✗ ${service_name} 服务启动失败或超时${NC}"
    return 1
}

echo "📋 检查服务状态..."

# 等待各服务启动
wait_for_service "PostgreSQL" "postgres" "5432"
wait_for_service "Redis" "redis" "6379"
wait_for_service "Neo4j" "neo4j" "7687"
wait_for_service "Milvus" "milvus-standalone" "19530"

echo -e "${BLUE}🔧 开始服务配置...${NC}"

# 1. 检查 PostgreSQL 连接
echo "检查 PostgreSQL 连接..."
if PGPASSWORD=12345678 psql -h postgres -U postgres -d knowledge_db -c "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL 连接正常${NC}"
    
    # 检查表是否已创建
    table_count=$(PGPASSWORD=12345678 psql -h postgres -U postgres -d knowledge_db -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
    echo "数据库表数量: $(echo $table_count | tr -d ' ')"
else
    echo -e "${RED}✗ PostgreSQL 连接失败${NC}"
fi

# 2. 检查 Redis 连接
echo "检查 Redis 连接..."
if redis-cli -h redis ping | grep -q PONG; then
    echo -e "${GREEN}✓ Redis 连接正常${NC}"
else
    echo -e "${RED}✗ Redis 连接失败${NC}"
fi

# 3. 检查 Neo4j 连接
echo "检查 Neo4j 连接..."
if curl -s -f http://neo4j:7474/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Neo4j 连接正常${NC}"
else
    echo -e "${RED}✗ Neo4j 连接失败${NC}"
fi

# 4. 检查 Milvus 连接
echo "检查 Milvus 连接..."
if curl -f http://milvus-standalone:9091/healthz > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Milvus 服务正常${NC}"
else
    echo -e "${RED}✗ Milvus 服务异常${NC}"
fi

echo -e "${GREEN}🎉 依赖服务初始化完成！${NC}"
echo ""
echo -e "${BLUE}📍 服务连接信息:${NC}"
echo "• PostgreSQL: postgres:5432 (postgres/12345678)"
echo "• Redis: redis:6379"
echo "• Neo4j: neo4j:7687 (neo4j/12345678)"
echo "• Milvus: milvus-standalone:19530"
echo ""
echo -e "${YELLOW}💡 现在可以启动 ThreatRAG API 服务${NC}"
