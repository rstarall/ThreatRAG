import uvicorn
import threading
from rag.vector.vector_database import create_vector_database_instance
import yaml
import signal
import sys
import atexit
from packages.core.milvus_manager import get_milvus_manager

config = None
milvus_manager = None

def load_config():
    with open("./config.yaml", "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)  # 添加Loader参数以避免TypeError
    return config

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

# def start_vector_database(path = "/rag/data/vector_db"):
#     """start the vector database"""
#     create_vector_database_instance(path=path)

# def start_rag_service():
#     """start the rag service"""
#     pass

def signal_handler(sig, frame):
    """处理信号，确保主进程结束时终止所有线程"""
    print("接收到终止信号，正在关闭服务...")
    stop_milvus()
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 注册退出时的清理函数
    atexit.register(stop_milvus)

    config = load_config()

    # 启动Milvus服务器
    if not start_milvus():
        print("Milvus服务器启动失败，程序退出")
        sys.exit(1)

    # 将向量数据库线程设置为守护线程，这样主进程结束时它会自动终止
    thread = threading.Thread(
        #target=start_vector_database,
        args=(config["vector_database"]["path"],),
        daemon=True  # 设置为守护线程
    )
    thread.start()

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
