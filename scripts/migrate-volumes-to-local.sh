#!/bin/bash
# ThreatRAG - 将 Docker Volumes 数据迁移到本地目录
# 用途：将现有的 Docker volume 数据复制到本地 ./data 目录

set -e

echo "========================================"
echo "ThreatRAG Volume 数据迁移工具"
echo "========================================"
echo ""

# 检查是否以 root 或 sudo 运行
if [ "$EUID" -ne 0 ] && [ -z "$SUDO_USER" ]; then 
    echo "⚠️  建议使用 sudo 运行此脚本以避免权限问题"
    echo "   sudo bash $0"
    echo ""
    read -p "是否继续? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data"

echo "📁 项目目录: $PROJECT_ROOT"
echo "📁 数据目录: $DATA_DIR"
echo ""

# 定义要迁移的 volumes
declare -A VOLUMES=(
    ["threatrag_mysql_data"]="mysql"
    ["threatrag_redis_data"]="redis"
    ["threatrag_neo4j_data"]="neo4j/data"
    ["threatrag_neo4j_logs"]="neo4j/logs"
    ["threatrag_etcd_data"]="etcd"
    ["threatrag_minio_data"]="minio"
    ["threatrag_milvus_data"]="milvus"
    ["threatrag_ollama_data"]="ollama"
)

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi

echo "🔍 检查现有 Docker volumes..."
echo ""

# 检查哪些 volumes 存在
existing_volumes=()
for volume in "${!VOLUMES[@]}"; do
    if docker volume inspect "$volume" > /dev/null 2>&1; then
        existing_volumes+=("$volume")
        size=$(docker system df -v | grep "$volume" | awk '{print $3}')
        echo -e "  ✓ ${GREEN}$volume${NC} (大小: ${size:-未知})"
    fi
done

if [ ${#existing_volumes[@]} -eq 0 ]; then
    echo -e "${YELLOW}⚠️  未找到任何现有的 Docker volumes${NC}"
    echo "   可能的原因："
    echo "   1. 这是首次部署"
    echo "   2. Volume 名称不匹配（请检查 docker volume ls）"
    echo ""
    docker volume ls
    echo ""
    read -p "是否继续创建目录结构? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  警告：此操作将会：${NC}"
    echo "   1. 停止所有 ThreatRAG 容器"
    echo "   2. 将 volume 数据复制到 $DATA_DIR"
    echo "   3. 使用新的本地挂载重启容器"
    echo "   4. 原有的 Docker volumes 将被保留（不会删除）"
    echo ""
    read -p "是否继续? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "取消操作"
        exit 0
    fi
fi

echo ""
echo "=================================="
echo "开始迁移..."
echo "=================================="
echo ""

# 1. 停止容器
echo "🛑 停止 ThreatRAG 容器..."
cd "$PROJECT_ROOT"
docker compose down || true
echo ""

# 2. 创建本地数据目录结构
echo "📁 创建本地目录结构..."
for target_dir in "${VOLUMES[@]}"; do
    mkdir -p "$DATA_DIR/$target_dir"
    echo "   创建: $DATA_DIR/$target_dir"
done
echo ""

# 3. 复制 volume 数据到本地
if [ ${#existing_volumes[@]} -gt 0 ]; then
    echo "📦 开始复制数据..."
    for volume in "${existing_volumes[@]}"; do
        target_dir="${VOLUMES[$volume]}"
        echo ""
        echo "  处理: $volume -> $target_dir"
        
        # 使用临时容器复制数据
        # 这是最安全的方法，不需要直接访问 Docker 的内部存储
        # 使用项目配置的镜像源
        docker run --rm \
            -v "$volume:/source:ro" \
            -v "$DATA_DIR/$target_dir:/target" \
            docker1.aeko.cn/library/alpine:latest \
            sh -c "cp -av /source/. /target/" 2>&1 | sed 's/^/    /'
        
        if [ $? -eq 0 ]; then
            echo -e "  ${GREEN}✓ 完成${NC}"
        else
            echo -e "  ${RED}✗ 失败${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠️  没有数据需要复制${NC}"
fi

echo ""
echo "=================================="
echo "设置权限..."
echo "=================================="
echo ""

# 4. 调整权限（重要！）
echo "🔐 调整目录权限..."

# MySQL 需要特定权限
if [ -d "$DATA_DIR/mysql" ]; then
    echo "  MySQL: 设置权限为 999:999 (mysql用户)"
    chown -R 999:999 "$DATA_DIR/mysql" 2>/dev/null || \
        echo -e "    ${YELLOW}⚠️  无法更改权限，可能需要 sudo${NC}"
fi

# Neo4j 需要特定权限
if [ -d "$DATA_DIR/neo4j" ]; then
    echo "  Neo4j: 设置权限为 7474:7474 (neo4j用户)"
    chown -R 7474:7474 "$DATA_DIR/neo4j" 2>/dev/null || \
        echo -e "    ${YELLOW}⚠️  无法更改权限，可能需要 sudo${NC}"
fi

# Redis
if [ -d "$DATA_DIR/redis" ]; then
    echo "  Redis: 设置权限为 999:999"
    chown -R 999:999 "$DATA_DIR/redis" 2>/dev/null || \
        echo -e "    ${YELLOW}⚠️  无法更改权限，可能需要 sudo${NC}"
fi

# 其他目录使用当前用户
echo "  其他: 设置权限为当前用户"
if [ -n "$SUDO_USER" ]; then
    # 如果通过 sudo 运行，使用原始用户
    REAL_USER="$SUDO_USER"
    REAL_GROUP=$(id -gn "$SUDO_USER")
else
    REAL_USER="$USER"
    REAL_GROUP=$(id -gn)
fi

for dir in etcd minio milvus ollama; do
    if [ -d "$DATA_DIR/$dir" ]; then
        chown -R "$REAL_USER:$REAL_GROUP" "$DATA_DIR/$dir" 2>/dev/null || true
    fi
done

echo ""
echo "=================================="
echo "验证迁移结果"
echo "=================================="
echo ""

# 5. 显示数据目录大小
echo "📊 数据目录大小统计："
for dir in "${VOLUMES[@]}"; do
    if [ -d "$DATA_DIR/$dir" ]; then
        size=$(du -sh "$DATA_DIR/$dir" 2>/dev/null | cut -f1)
        echo "  $dir: $size"
    fi
done

echo ""
echo "=================================="
echo "完成！"
echo "=================================="
echo ""

echo -e "${GREEN}✓ 数据迁移完成${NC}"
echo ""
echo "下一步："
echo "  1. 检查 $DATA_DIR 目录确认数据已复制"
echo "  2. 使用新配置启动服务："
echo "     ${GREEN}docker compose up -d${NC}"
echo ""
echo "  3. 验证服务正常运行："
echo "     ${GREEN}docker compose ps${NC}"
echo ""
echo "备注："
echo "  • 原有的 Docker volumes 已保留（未删除）"
echo "  • 如果需要，可以手动删除："
echo "    ${YELLOW}docker volume rm ${existing_volumes[*]}${NC}"
echo ""
echo "  • 如果遇到权限问题，运行："
echo "    ${YELLOW}sudo chown -R \$USER:\$USER $DATA_DIR${NC}"
echo ""

