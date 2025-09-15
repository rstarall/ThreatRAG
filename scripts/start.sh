#!/bin/bash
set -euo pipefail

echo "🚀 启动 ThreatRAG 服务..."

if [ -x /app/scripts/init-services.sh ]; then
  echo "🧩 运行依赖服务初始化脚本 scripts/init-services.sh"
  /app/scripts/init-services.sh || true
fi

echo "🎯 启动ThreatRAG API..."
exec python /app/main.py


