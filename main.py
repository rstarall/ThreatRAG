import uvicorn
import threading
from rag.vector.vector_database import create_vector_database_instance
import yaml
import signal
import sys
import atexit
from packages.manager.milvus_manager import get_milvus_manager
# 导入图数据库索引器
from packages.core.graph_indexer import graph_indexer
from rag.cache.redis_session import RedisSessionManager
import redis

config = None
milvus_manager = None

def load_config():
    """加载配置文件，使用UTF-8编码"""
    try:
        with open("./config.yaml", "r", encoding='utf-8') as f:
            config = yaml.safe_load(f)  # 使用safe_load更安全
        return config
    except UnicodeDecodeError as e:
        print(f"配置文件编码错误: {e}")
        print("尝试使用其他编码加载...")
        try:
            with open("./config.yaml", "r", encoding='gbk') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e2:
            print(f"使用GBK编码也失败: {e2}")
            raise
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        raise

def start_milvus():
    """启动milvus服务器"""
    global milvus_manager
    if config.get("milvus", {}).get("auto_start", True):
        print("正在启动Milvus服务器...")
        milvus_config = config.get("milvus", {})
        data_dir = milvus_config.get("data_dir", "./milvus_lite")
        host = milvus_config.get("host", "127.0.0.1")
        port = milvus_config.get("port", 19530)

        milvus_manager = get_milvus_manager(data_dir, port, host)
        if milvus_manager.start():
            print(f"✓ Milvus服务器启动成功，监听 {host}:{port}")
            return True
        else:
            print("✗ Milvus服务器启动失败")
            return False
    else:
        print("Milvus自动启动已禁用，请手动启动milvus服务器")
        return True

def stop_milvus():
    """停止milvus服务器"""
    global milvus_manager
    if milvus_manager:
        print("正在停止Milvus服务器...")
        milvus_manager.stop()
        print("✓ Milvus服务器已停止")

def start_server(host = "0.0.0.0", port = 8000):
    """start the fastapi server"""
    # 延迟导入，确保在Milvus启动后再导入
    from rag.api.server import fastapi_server
    uvicorn.run(fastapi_server, host=host, port=port)


def signal_handler(sig, frame):
    """处理信号，确保主进程结束时终止所有线程"""
    print("接收到终止信号，正在关闭服务...")
    stop_milvus()
    sys.exit(0)

def check_redis():
    """检查Redis是否已启动"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=1)
        r.ping()
        print("Redis服务器已在运行")
        return True
    except:
        print("Redis服务器未启动")
        return False

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 注册退出时的清理函数
    atexit.register(stop_milvus)

    config = load_config()

    # 检查Redis是否已启动
    if not check_redis():
        print("警告: Redis服务器未启动，会话缓存将不可用")
        print("请安装并启动Redis服务器以启用会话缓存功能")
        print("安装指南: https://redis.io/docs/getting-started/")

    # 启动Milvus服务器
    if not start_milvus():
        print("Milvus服务器启动失败，程序退出")
        sys.exit(1)

    # 启动Neo4j服务器（如果配置了自动启动）
    if config.get("neo4j", {}).get("auto_start", False):
        from packages.manager.neo4j_manager import start_neo4j_server
        start_neo4j_server(
            data_dir=config.get("neo4j", {}).get("data_dir", "./neo4j_data"),
            port=config.get("neo4j", {}).get("port", 7687),
            http_port=config.get("neo4j", {}).get("http_port", 7474),
            host=config.get("neo4j", {}).get("host", "127.0.0.1")
        )

    # 启动图数据库索引器（如果启用了知识图谱）
    if config.get("enable_knowledge_graph", False):
        # 设置索引间隔（默认1小时）
        index_interval = config.get("neo4j", {}).get("index_interval", 3600)
        graph_indexer.interval = index_interval
        graph_indexer.start()


    # 启动服务器（主线程）
    try:
        print(f"正在启动FastAPI服务器，监听 {config['fastapi_server']['host']}:{config['fastapi_server']['port']}")
        start_server(host=config["fastapi_server"]["host"], port=config["fastapi_server"]["port"])
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"服务器启动失败: {e}")
    finally:
        stop_milvus()
