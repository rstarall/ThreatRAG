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
        self.data_dir = Path(data_dir).resolve()
        self.port = port
        self.host = host
        self.process = None
        self.is_running = False
        
        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def _check_milvus_installed(self):
        """检查milvus是否已安装"""
        try:
            result = subprocess.run(['milvus-server', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _install_milvus(self):
        """安装milvus"""
        logger.info("正在安装milvus...")
        try:
            subprocess.run(['pip', 'install', 'milvus'], check=True)
            logger.info("milvus安装成功")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"milvus安装失败: {e}")
            return False
    
    def _is_port_in_use(self, port):
        """检查端口是否被占用"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
    
    def _wait_for_milvus_ready(self, timeout=30):
        """等待milvus服务器就绪"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_port_in_use(self.port):
                # 尝试连接测试
                try:
                    from pymilvus import MilvusClient
                    client = MilvusClient(uri=f"http://{self.host}:{self.port}")
                    client.list_collections()
                    logger.info(f"Milvus服务器已就绪，监听端口 {self.port}")
                    return True
                except Exception:
                    pass
            time.sleep(1)
        return False
    
    def start(self):
        """启动milvus服务器"""
        if self.is_running:
            logger.info("Milvus服务器已在运行")
            return True
            
        # 检查是否已安装milvus
        if not self._check_milvus_installed():
            logger.info("未检测到milvus，正在安装...")
            if not self._install_milvus():
                logger.error("无法安装milvus，请手动安装: pip install milvus")
                return False
        
        # 检查端口是否被占用
        if self._is_port_in_use(self.port):
            logger.info(f"端口 {self.port} 已被占用，假设milvus已在运行")
            if self._wait_for_milvus_ready(timeout=5):
                self.is_running = True
                return True
            else:
                logger.error(f"端口 {self.port} 被占用但无法连接到milvus服务")
                return False
        
        try:
            logger.info(f"正在启动milvus服务器，数据目录: {self.data_dir}")
            
            # 启动milvus服务器
            cmd = ['milvus-server', '--data', str(self.data_dir)]
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 等待服务器启动
            if self._wait_for_milvus_ready():
                self.is_running = True
                logger.info("Milvus服务器启动成功")
                
                # 启动日志监控线程
                self._start_log_monitor()
                return True
            else:
                logger.error("Milvus服务器启动超时")
                self.stop()
                return False
                
        except Exception as e:
            logger.error(f"启动milvus服务器失败: {e}")
            return False
    
    def _start_log_monitor(self):
        """启动日志监控线程"""
        def monitor_logs():
            if self.process:
                for line in iter(self.process.stdout.readline, ''):
                    if line.strip():
                        logger.debug(f"Milvus: {line.strip()}")
                    if not self.is_running:
                        break
        
        log_thread = threading.Thread(target=monitor_logs, daemon=True)
        log_thread.start()
    
    def stop(self):
        """停止milvus服务器"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        if self.process:
            try:
                # 优雅关闭
                self.process.terminate()
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=10)
                    logger.info("Milvus服务器已停止")
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
                    self.process.kill()
                    self.process.wait()
                    logger.info("Milvus服务器已强制停止")
                    
            except Exception as e:
                logger.error(f"停止milvus服务器时出错: {e}")
            finally:
                self.process = None
    
    def restart(self):
        """重启milvus服务器"""
        logger.info("正在重启milvus服务器...")
        self.stop()
        time.sleep(2)
        return self.start()
    
    def get_status(self):
        """获取milvus服务器状态"""
        if not self.is_running:
            return {"status": "stopped", "port": self.port, "data_dir": str(self.data_dir)}
        
        try:
            from pymilvus import MilvusClient
            client = MilvusClient(uri=f"http://{self.host}:{self.port}")
            collections = client.list_collections()
            return {
                "status": "running",
                "port": self.port,
                "host": self.host,
                "data_dir": str(self.data_dir),
                "collections_count": len(collections)
            }
        except Exception as e:
            return {
                "status": "error",
                "port": self.port,
                "data_dir": str(self.data_dir),
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
