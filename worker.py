import os
import sys
import time
import logging
from dotenv import load_dotenv
from rag.mq.conversation_worker import ConversationWorker
from rag.mq.vector_search_worker import VectorSearchWorker

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """工作器主函数"""
    # 获取工作器类型和数量
    worker_type = os.getenv("WORKER_TYPE", "all").lower()
    worker_count = int(os.getenv("WORKER_COUNT", "3"))
    
    logger.info(f"启动工作器: 类型={worker_type}, 数量={worker_count}")
    
    # 启动会话工作器
    if worker_type in ["conversation", "all"]:
        conversation_worker = ConversationWorker(num_workers=worker_count)
        conversation_worker.start_workers()
        logger.info(f"已启动 {worker_count} 个会话工作器")
    
    # 启动向量检索工作器
    if worker_type in ["vector", "all"]:
        vector_worker = VectorSearchWorker(num_workers=worker_count)
        vector_worker.start_workers()
        logger.info(f"已启动 {worker_count} 个向量检索工作器")
    
    # 保持进程运行
    try:
        while True:
            time.sleep(60)
            logger.info("工作器正在运行...")
    except KeyboardInterrupt:
        logger.info("收到中断信号，工作器退出")
    except Exception as e:
        logger.error(f"工作器运行出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()