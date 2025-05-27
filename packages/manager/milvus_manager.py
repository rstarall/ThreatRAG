import os
import subprocess
import time
import signal
import psutil
import threading
from pathlib import Path
from ..utils import logger


class MilvusManager:
    """Milvus服务器管理器"""

    def __init__(self, data_dir="./milvus_lite", port=19530, host="127.0.0.1"):
        self.port = port
        self.host = host
        self.is_running = False

    def _check_milvus_available(self):
        """检查Milvus服务是否可用"""
        try:
            from pymilvus import MilvusClient
            client = MilvusClient(uri=f"http://{self.host}:{self.port}")
            client.list_collections()
            return True
        except Exception:
            return False

    def start(self):
        """检查Milvus服务是否可用"""
        if self.is_running:
            logger.info("Milvus服务已在运行")
            return True

        if self._check_milvus_available():
            self.is_running = True
            logger.info(f"Milvus服务可用，监听 {self.host}:{self.port}")
            return True
        else:
            logger.error(f"无法连接到Milvus服务 {self.host}:{self.port}")
            logger.error("请确保已启动Milvus服务，可以使用以下命令：")
            logger.error("docker run -d --name milvus_standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:latest")
            return False

    def stop(self):
        """停止Milvus服务检查"""
        self.is_running = False
        logger.info("Milvus服务检查已停止")

    def restart(self):
        """重启Milvus服务检查"""
        logger.info("正在重启Milvus服务检查...")
        self.stop()
        return self.start()

    def get_status(self):
        """获取Milvus服务状态"""
        if not self.is_running:
            return {"status": "stopped", "port": self.port, "host": self.host}

        try:
            from pymilvus import MilvusClient
            client = MilvusClient(uri=f"http://{self.host}:{self.port}")
            collections = client.list_collections()
            return {
                "status": "running",
                "port": self.port,
                "host": self.host,
                "collections_count": len(collections)
            }
        except Exception as e:
            return {
                "status": "error",
                "port": self.port,
                "host": self.host,
                "error": str(e)
            }


# 全局milvus管理器实例
milvus_manager = None

def get_milvus_manager(data_dir="./milvus_lite", port=19530, host="127.0.0.1"):
    """获取milvus管理器实例"""
    global milvus_manager
    if milvus_manager is None:
        milvus_manager = MilvusManager(data_dir, port, host)
    return milvus_manager

def start_milvus_server(data_dir="./milvus_lite", port=19530, host="127.0.0.1"):
    """启动milvus服务器的便捷函数"""
    manager = get_milvus_manager(data_dir, port, host)
    return manager.start()

def stop_milvus_server():
    """停止milvus服务器的便捷函数"""
    global milvus_manager
    if milvus_manager:
        milvus_manager.stop()
