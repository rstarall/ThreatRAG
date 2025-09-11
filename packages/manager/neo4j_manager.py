import os
import subprocess
import time
import psutil
import threading
from pathlib import Path
from ..utils import logger


class Neo4jManager:
    """Neo4j服务器管理器"""
    
    def __init__(self, data_dir="./neo4j_data", port=7687, http_port=7474, host="127.0.0.1"):
        self.data_dir = Path(data_dir).resolve()
        self.port = port
        self.http_port = http_port
        self.host = host
        self.process = None
        self.is_running = False
        
        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def _check_neo4j_installed(self):
        """检查Neo4j是否已安装"""
        try:
            # 检查neo4j命令是否可用
            result = subprocess.run(['neo4j', 'version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _is_port_in_use(self, port):
        """检查端口是否被占用"""
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False
    
    def _wait_for_neo4j_ready(self, timeout=60):
        """等待Neo4j服务器就绪"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_port_in_use(self.port):
                # 尝试连接测试
                try:
                    from neo4j import GraphDatabase
                    driver = GraphDatabase.driver(f"bolt://{self.host}:{self.port}", 
                                                auth=("neo4j", "1234567890"))
                    with driver.session() as session:
                        session.run("RETURN 1")
                    driver.close()
                    logger.info(f"Neo4j服务器已就绪，监听端口 {self.port}")
                    return True
                except Exception:
                    pass
            time.sleep(2)
        return False
    
    def start(self):
        """启动Neo4j服务器"""
        if self.is_running:
            logger.info("Neo4j服务器已在运行")
            return True
            
        # 检查端口是否被占用
        if self._is_port_in_use(self.port):
            logger.info(f"端口 {self.port} 已被占用，假设Neo4j已在运行")
            if self._wait_for_neo4j_ready(timeout=10):
                self.is_running = True
                return True
            else:
                logger.error(f"端口 {self.port} 被占用但无法连接到Neo4j服务")
                return False
        
        # 检查是否已安装Neo4j
        if not self._check_neo4j_installed():
            logger.warning("未检测到Neo4j安装，请手动安装Neo4j")
            logger.info("安装指南: https://neo4j.com/docs/operations-manual/current/installation/")
            return False
        
        try:
            logger.info(f"正在启动Neo4j服务器，数据目录: {self.data_dir}")
            
            # 设置Neo4j环境变量
            env = os.environ.copy()
            env['NEO4J_HOME'] = str(self.data_dir)
            env['NEO4J_CONF'] = str(self.data_dir / "conf")
            env['NEO4J_DATA'] = str(self.data_dir / "data")
            env['NEO4J_LOGS'] = str(self.data_dir / "logs")
            
            # 创建必要的目录
            (self.data_dir / "conf").mkdir(exist_ok=True)
            (self.data_dir / "data").mkdir(exist_ok=True)
            (self.data_dir / "logs").mkdir(exist_ok=True)
            
            # 启动Neo4j服务器
            cmd = ['neo4j', 'console']
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=str(self.data_dir)
            )
            
            # 等待服务器启动
            if self._wait_for_neo4j_ready():
                self.is_running = True
                logger.info("Neo4j服务器启动成功")
                
                # 启动日志监控线程
                self._start_log_monitor()
                return True
            else:
                logger.error("Neo4j服务器启动超时")
                self.stop()
                return False
                
        except Exception as e:
            logger.error(f"启动Neo4j服务器失败: {e}")
            return False
    
    def _start_log_monitor(self):
        """启动日志监控线程"""
        def monitor_logs():
            if self.process:
                for line in iter(self.process.stdout.readline, ''):
                    if line.strip():
                        logger.debug(f"Neo4j: {line.strip()}")
                    if not self.is_running:
                        break
        
        log_thread = threading.Thread(target=monitor_logs, daemon=True)
        log_thread.start()
    
    def stop(self):
        """停止Neo4j服务器"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        if self.process:
            try:
                # 优雅关闭
                self.process.terminate()
                
                # 等待进程结束
                try:
                    self.process.wait(timeout=15)
                    logger.info("Neo4j服务器已停止")
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
                    self.process.kill()
                    self.process.wait()
                    logger.info("Neo4j服务器已强制停止")
                    
            except Exception as e:
                logger.error(f"停止Neo4j服务器时出错: {e}")
            finally:
                self.process = None
    
    def restart(self):
        """重启Neo4j服务器"""
        logger.info("正在重启Neo4j服务器...")
        self.stop()
        time.sleep(3)
        return self.start()
    
    def get_status(self):
        """获取Neo4j服务器状态"""
        if not self.is_running:
            return {"status": "stopped", "port": self.port, "data_dir": str(self.data_dir)}
        
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(f"bolt://{self.host}:{self.port}", 
                                        auth=("neo4j", "1234567890"))
            with driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) as node_count")
                node_count = result.single()["node_count"]
            driver.close()
            
            return {
                "status": "running",
                "port": self.port,
                "http_port": self.http_port,
                "host": self.host,
                "data_dir": str(self.data_dir),
                "node_count": node_count
            }
        except Exception as e:
            return {
                "status": "error",
                "port": self.port,
                "data_dir": str(self.data_dir),
                "error": str(e)
            }


# 全局Neo4j管理器实例
neo4j_manager = None

def get_neo4j_manager(data_dir="./neo4j_data", port=7687, http_port=7474, host="127.0.0.1"):
    """获取Neo4j管理器实例"""
    global neo4j_manager
    if neo4j_manager is None:
        neo4j_manager = Neo4jManager(data_dir, port, http_port, host)
    return neo4j_manager

def start_neo4j_server(data_dir="./neo4j_data", port=7687, http_port=7474, host="127.0.0.1"):
    """启动Neo4j服务器的便捷函数"""
    manager = get_neo4j_manager(data_dir, port, http_port, host)
    return manager.start()

def stop_neo4j_server():
    """停止Neo4j服务器的便捷函数"""
    global neo4j_manager
    if neo4j_manager:
        neo4j_manager.stop()
