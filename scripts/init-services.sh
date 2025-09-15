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

# 读取环境变量并设置候选端口（容器网络优先）
MYSQL_HOST=${MYSQL_HOST:-mysql}
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD:-12345678}
# 优先尝试容器端口 3306，然后尝试环境端口，最后兼容宿主映射端口 3309
MYSQL_PORT_CANDIDATES="3306 ${MYSQL_PORT:-3306} 3309"

NEO4J_HOST=${NEO4J_HOST:-neo4j}
# 优先尝试容器端口 7687，然后尝试环境端口，最后兼容宿主映射端口 7688
NEO4J_BOLT_PORT_CANDIDATES="7687 ${NEO4J_BOLT_PORT:-7687} 7688"

# 选择可用端口的小工具
choose_port() {
    local host=$1
    shift
    local ports=("$@")
    for p in "${ports[@]}"; do
        if nc -z "$host" "$p" 2>/dev/null; then
            echo "$p"
            return 0
        fi
    done
    # 若都不可用，返回第一个作为默认
    echo "${ports[0]}"
}

MYSQL_PORT=$(choose_port "$MYSQL_HOST" $MYSQL_PORT_CANDIDATES)
NEO4J_BOLT_PORT=$(choose_port "$NEO4J_HOST" $NEO4J_BOLT_PORT_CANDIDATES)

# 等待各服务启动（按已选端口）
wait_for_service "MySQL" "$MYSQL_HOST" "$MYSQL_PORT"
wait_for_service "Redis" "redis" "6379"
wait_for_service "Neo4j" "$NEO4J_HOST" "$NEO4J_BOLT_PORT"
wait_for_service "Milvus" "milvus-standalone" "19530"

echo -e "${BLUE}🔧 开始服务配置...${NC}"

# 1. 检查 MySQL 连接
echo "检查 MySQL 连接..."
if mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u root -p"$MYSQL_ROOT_PASSWORD" -e "SELECT version();" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MySQL 连接正常${NC}"
    
    # 检查表是否已创建
    table_count=$(mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u root -p"$MYSQL_ROOT_PASSWORD" knowledge_db -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='knowledge_db';" -s -N 2>/dev/null || echo "0")
    echo "数据库表数量: $table_count"
else
    echo -e "${RED}✗ MySQL 连接失败${NC}"
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
if echo 'RETURN "Neo4j is running" as status;' | cypher-shell -a bolt://$NEO4J_HOST:$NEO4J_BOLT_PORT -u neo4j -p 12345678 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Neo4j 连接正常${NC}"
    
    # 创建初始索引
    echo "创建 Neo4j 索引..."
    echo "
        CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name);
        CREATE INDEX relationship_type IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.type);
    " | cypher-shell -a bolt://$NEO4J_HOST:$NEO4J_BOLT_PORT -u neo4j -p 12345678 > /dev/null 2>&1 || true
    echo -e "${GREEN}✓ Neo4j 索引创建完成${NC}"
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
echo "• MySQL: $MYSQL_HOST:$MYSQL_PORT (root/$MYSQL_ROOT_PASSWORD)"
echo "• Redis: redis:6379"
echo "• Neo4j: $NEO4J_HOST:$NEO4J_BOLT_PORT (neo4j/12345678)"
echo "• Milvus: milvus-standalone:19530"
echo ""
echo -e "${YELLOW}💡 现在可以启动 ThreatRAG API 服务${NC}"