#!/bin/bash
# NVIDIA Container Toolkit 安装脚本
# 用于为 Docker 启用 GPU 支持

set -e

echo "=========================================="
echo "NVIDIA Container Toolkit 安装脚本"
echo "=========================================="
echo ""

# 检查是否有 NVIDIA GPU
echo "步骤 1/6: 检查 NVIDIA GPU..."
if ! lspci | grep -i nvidia > /dev/null; then
    echo "❌ 错误：未检测到 NVIDIA GPU"
    echo "请确保您的系统有 NVIDIA 显卡"
    exit 1
fi
echo "✓ 检测到 NVIDIA GPU"
echo ""

# 检查 NVIDIA 驱动
echo "步骤 2/6: 检查 NVIDIA 驱动..."
if ! nvidia-smi > /dev/null 2>&1; then
    echo "❌ 错误：NVIDIA 驱动未安装或未正确配置"
    echo "请先安装 NVIDIA 驱动：https://www.nvidia.com/Download/index.aspx"
    exit 1
fi
echo "✓ NVIDIA 驱动已安装"
nvidia-smi
echo ""

# 检测系统类型
echo "步骤 3/6: 检测系统类型..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION_ID=$VERSION_ID
    echo "✓ 检测到系统: $OS $VERSION_ID"
else
    echo "❌ 错误：无法检测系统类型"
    exit 1
fi
echo ""

# 添加 NVIDIA Container Toolkit 仓库
echo "步骤 4/6: 添加 NVIDIA Container Toolkit 仓库..."
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)

# 添加 GPG key
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 添加仓库
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

echo "✓ 仓库添加成功"
echo ""

# 安装 NVIDIA Container Toolkit
echo "步骤 5/6: 安装 NVIDIA Container Toolkit..."
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
echo "✓ NVIDIA Container Toolkit 安装成功"
echo ""

# 配置 Docker
echo "步骤 6/6: 配置 Docker 以使用 NVIDIA Runtime..."
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
echo "✓ Docker 配置完成"
echo ""

# 验证安装
echo "=========================================="
echo "验证 GPU 支持..."
echo "=========================================="
if docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi > /dev/null 2>&1; then
    echo "✓ GPU 支持验证成功！"
    echo ""
    echo "Docker 现在可以使用 GPU 了"
    docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
else
    echo "❌ GPU 支持验证失败"
    echo "请检查日志并重试"
    exit 1
fi

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 启动 Ollama GPU 版本："
echo "   docker-compose up -d ollama"
echo ""
echo "2. 下载模型："
echo "   docker exec -it threatrag-ollama ollama pull qwen2.5:7b"
echo ""
echo "3. 验证 GPU 使用："
echo "   docker exec threatrag-ollama nvidia-smi"
echo ""

