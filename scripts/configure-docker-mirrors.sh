#!/bin/bash

# Docker 中科院镜像源配置脚本
# 适用于 WSL 和 Linux 环境

set -e

echo "🐳 配置 Docker 中科院镜像源..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查是否在 WSL 环境中
if grep -q Microsoft /proc/version 2>/dev/null; then
    echo -e "${BLUE}检测到 WSL 环境${NC}"
    ENVIRONMENT="WSL"
else
    echo -e "${BLUE}检测到 Linux 环境${NC}"
    ENVIRONMENT="Linux"
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker 未安装，请先安装 Docker${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 已安装${NC}"

# 检查 Docker 服务状态
if ! systemctl is-active --quiet docker 2>/dev/null; then
    echo -e "${YELLOW}⚠ Docker 服务未运行，检测 Docker Desktop...${NC}"
    
    # 检查是否是 Docker Desktop
    if command -v docker &> /dev/null && docker version &> /dev/null; then
        echo -e "${GREEN}✓ 检测到 Docker Desktop，服务正在运行${NC}"
    else
        echo -e "${RED}✗ Docker Desktop 未运行，请启动 Docker Desktop${NC}"
        echo "请在 Windows 中启动 Docker Desktop 应用程序"
        exit 1
    fi
fi

# 创建 Docker 配置目录
echo -e "${YELLOW}创建 Docker 配置目录...${NC}"
sudo mkdir -p /etc/docker

# 备份现有配置
if [ -f /etc/docker/daemon.json ]; then
    echo -e "${YELLOW}备份现有配置...${NC}"
    sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# 创建新的 daemon.json 配置
echo -e "${YELLOW}配置镜像源...${NC}"
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://ccr.ccs.tencentyun.com",
    "https://registry.docker-cn.com"
  ],
  "insecure-registries": [],
  "debug": false,
  "experimental": false,
  "features": {
    "buildkit": true
  },
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF

echo -e "${GREEN}✓ 配置文件已创建${NC}"

# 针对 Docker Desktop 的额外说明
if ! systemctl is-active --quiet docker 2>/dev/null; then
    echo -e "${YELLOW}📋 Docker Desktop 用户请注意:${NC}"
    echo "1. 配置文件已创建在 /etc/docker/daemon.json"
    echo "2. 请重启 Docker Desktop 应用程序使配置生效"
    echo "3. 或者在 Docker Desktop 设置中手动添加镜像源配置"
    echo ""
fi

# 重启 Docker 服务
echo -e "${YELLOW}重启 Docker 服务...${NC}"
if [ "$ENVIRONMENT" = "WSL" ]; then
    # WSL 环境下的重启方式
    if systemctl is-active --quiet docker 2>/dev/null; then
        sudo systemctl restart docker
    else
        echo -e "${BLUE}使用 Docker Desktop，无需重启系统服务${NC}"
    fi
else
    # Linux 环境下的重启方式
    if systemctl is-active --quiet docker 2>/dev/null; then
        sudo systemctl restart docker
    else
        echo -e "${BLUE}使用 Docker Desktop，无需重启系统服务${NC}"
    fi
fi

# 等待服务启动
sleep 3

# 验证配置
echo -e "${YELLOW}验证配置...${NC}"
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker 服务运行正常${NC}"
    
    # 显示镜像源配置
    echo -e "${BLUE}📋 当前镜像源配置:${NC}"
    docker info | grep -A 10 "Registry Mirrors" || echo "未找到镜像源配置"
    
    # 测试镜像拉取
    echo -e "${YELLOW}测试镜像拉取...${NC}"
    if docker pull hello-world > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 镜像拉取测试成功${NC}"
        docker rmi hello-world > /dev/null 2>&1
    else
        echo -e "${RED}✗ 镜像拉取测试失败${NC}"
    fi
else
    echo -e "${RED}✗ Docker 服务启动失败${NC}"
    echo "请检查 Docker 安装和配置"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Docker 镜像源配置完成！${NC}"
echo ""
echo -e "${BLUE}📍 配置的镜像源:${NC}"
echo "• 中科院镜像: https://docker.mirrors.ustc.edu.cn"
echo "• 网易镜像: https://hub-mirror.c.163.com"
echo "• 百度镜像: https://mirror.baidubce.com"
echo "• 腾讯云镜像: https://ccr.ccs.tencentyun.com"
echo "• Docker 中国: https://registry.docker-cn.com"
echo ""
echo -e "${YELLOW}💡 使用提示:${NC}"
echo "• 如果配置不生效，请重启 WSL: wsl --shutdown"
echo "• 查看 Docker 信息: docker info"
echo "• 测试镜像拉取: docker pull hello-world"
echo "• 恢复原配置: sudo cp /etc/docker/daemon.json.backup.* /etc/docker/daemon.json"
