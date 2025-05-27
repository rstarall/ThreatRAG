import os
import subprocess
import sys
import time
import signal
import argparse

def check_redis():
    """检查Redis是否已启动"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=1)
        r.ping()
        print("✅ Redis已启动")
        return True
    except:
        print("❌ Redis未启动")
        return False

def start_redis():
    """启动Redis服务"""
    try:
        # 检查是否已安装Redis
        if sys.platform == 'win32':
            # Windows
            redis_server = subprocess.Popen(
                ['redis-server'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        else:
            # Linux/Mac
            redis_server = subprocess.Popen(
                ['redis-server'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
        
        # 等待Redis启动
        time.sleep(2)
        
        # 检查是否成功启动
        if check_redis():
            print("✅ Redis服务已成功启动")
            return redis_server
        else:
            print("❌ Redis服务启动失败")
            return None
    except Exception as e:
        print(f"❌ 启动Redis时出错: {e}")
        return None

def start_app():
    """启动FastAPI应用"""
    try:
        # 启动FastAPI应用
        app_process = subprocess.Popen(
            ['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("✅ FastAPI应用已启动")
        return app_process
    except Exception as e:
        print(f"❌ 启动FastAPI应用时出错: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='启动服务')
    parser.add_argument('--no-redis', action='store_true', help='不启动Redis')
    parser.add_argument('--no-app', action='store_true', help='不启动FastAPI应用')
    args = parser.parse_args()
    
    processes = []
    
    # 启动Redis
    if not args.no_redis:
        if not check_redis():
            redis_process = start_redis()
            if redis_process:
                processes.append(redis_process)
    
    # 启动FastAPI应用
    if not args.no_app:
        app_process = start_app()
        if app_process:
            processes.append(app_process)
    
    # 注册信号处理
    def signal_handler(sig, frame):
        print("\n正在关闭服务...")
        for process in processes:
            process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 保持主进程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
        for process in processes:
            process.terminate()

if __name__ == "__main__":
    main()