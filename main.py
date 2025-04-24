import uvicorn
from rag.api.server import fastapi_server
import threading
from rag.vector.vector_database import create_vector_database_instance
import yaml
import signal
import sys

config = None

def load_config():
    with open("config.yaml", "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)  # 添加Loader参数以避免TypeError
    return config

def start_server(host = "0.0.0.0", port = 8000):
    """start the fastapi server"""
    uvicorn.run(fastapi_server, host=host, port=port)

def start_vector_database(path = "/rag/data/vector_db"):
    """start the vector database"""
    create_vector_database_instance(path=path)

def start_rag_service():
    """start the rag service"""
    pass

def signal_handler(sig, frame):
    """处理信号，确保主进程结束时终止所有线程"""
    print("接收到终止信号，正在关闭服务...")
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    config = load_config()
    
    # 将向量数据库线程设置为守护线程，这样主进程结束时它会自动终止
    thread = threading.Thread(
        target=start_vector_database, 
        args=(config["vector_database"]["path"],),
        daemon=True  # 设置为守护线程
    )
    thread.start()
    
    # 启动服务器（主线程）
    start_server(host=config["fastapi_server"]["host"], port=config["fastapi_server"]["port"])
