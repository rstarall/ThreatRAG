import json
import os
import threading
import time
import uuid
from typing import Dict, Any
import pika
from rag.mq.rabbitmq_manager import RabbitMQManager
from rag.vector.vector_database import get_vector_database_instance
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorSearchWorker:
    """向量检索工作器，处理异步检索请求"""
    
    def __init__(self, num_workers: int = 3):
        """初始化向量检索工作器
        
        Args:
            num_workers: 工作线程数量
        """
        self.mq_manager = RabbitMQManager()
        self.vector_db = get_vector_database_instance()
        self.search_queue = "vector_search_queue"
        self.result_queue = "vector_search_result_queue"
        self.num_workers = num_workers
        self.workers = []
        
        # 声明队列
        self.mq_manager.declare_queue(self.search_queue)
        self.mq_manager.declare_queue(self.result_queue)
    
    def start_workers(self):
        """启动工作线程"""
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                args=(i,),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            logger.info(f"向量检索工作线程 {i} 已启动")
    
    def _worker_thread(self, worker_id: int):
        """工作线程函数
        
        Args:
            worker_id: 工作线程ID
        """
        logger.info(f"向量检索工作线程 {worker_id} 开始运行")
        
        # 创建独立的RabbitMQ连接
        mq = RabbitMQManager()
        
        def callback(ch, method, properties, body):
            """消息处理回调函数"""
            try:
                # 解析消息
                message = json.loads(body)
                logger.info(f"工作线程 {worker_id} 收到检索请求: {message.get('request_id')}")
                
                # 提取查询参数
                query = message.get("query", "")
                k = message.get("k", 5)
                request_id = message.get("request_id", "")
                conversation_id = message.get("conversation_id", "")
                
                # 执行向量检索
                start_time = time.time()
                results = self.vector_db.query_vector_database(query)
                search_time = time.time() - start_time
                
                # 格式化结果
                formatted_results = []
                for doc in results:
                    formatted_results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    })
                
                # 发送结果
                result_message = {
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "results": formatted_results,
                    "search_time": search_time,
                    "timestamp": time.time()
                }
                
                mq.publish_message(self.result_queue, result_message)
                logger.info(f"工作线程 {worker_id} 完成检索请求: {request_id}, 耗时: {search_time:.2f}秒")
                
                # 确认消息
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"工作线程 {worker_id} 处理消息失败: {str(e)}")
                # 拒绝消息并重新入队
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # 设置QoS，每次只处理一条消息
        mq.channel.basic_qos(prefetch_count=1)
        
        # 开始消费消息
        mq.consume_messages(self.search_queue, callback, auto_ack=False)
    
    def submit_search_task(self, query: str, conversation_id: str = None, k: int = 5) -> str:
        """提交检索任务
        
        Args:
            query: 查询文本
            conversation_id: 会话ID
            k: 返回结果数量
            
        Returns:
            str: 请求ID
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 创建消息
        message = {
            "request_id": request_id,
            "conversation_id": conversation_id,
            "query": query,
            "k": k,
            "timestamp": time.time()
        }
        
        # 发布消息
        self.mq_manager.publish_message(self.search_queue, message)
        logger.info(f"已提交检索任务: {request_id}")
        
        return request_id