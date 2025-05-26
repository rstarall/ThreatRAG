import json
import os
import threading
import time
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Callable
import pika
from rag.mq.rabbitmq_manager import RabbitMQManager
from rag.chains.conversation_chain import StreamingConversationChain
from rag.vector.vector_database import get_vector_database_instance
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConversationWorker:
    """会话处理工作器，处理异步会话请求"""
    
    def __init__(self, num_workers: int = 3):
        """初始化会话处理工作器
        
        Args:
            num_workers: 工作线程数量
        """
        self.mq_manager = RabbitMQManager()
        self.conversation_queue = "conversation_queue"
        self.conversation_result_queue = "conversation_result_queue"
        self.num_workers = num_workers
        self.workers = []
        
        # 声明队列
        self.mq_manager.declare_queue(self.conversation_queue)
        self.mq_manager.declare_queue(self.conversation_result_queue)
        
        # 结果回调注册表
        self.result_callbacks = {}
        self.result_lock = threading.Lock()
        
        # 启动结果监听线程
        self.result_thread = threading.Thread(
            target=self._listen_for_results,
            daemon=True
        )
        self.result_thread.start()
    
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
            logger.info(f"会话处理工作线程 {i} 已启动")
    
    def _worker_thread(self, worker_id: int):
        """工作线程函数
        
        Args:
            worker_id: 工作线程ID
        """
        logger.info(f"会话处理工作线程 {worker_id} 开始运行")
        
        # 创建独立的RabbitMQ连接
        mq = RabbitMQManager()
        
        # 创建会话链实例
        conversation_chain = StreamingConversationChain(
            verbose=False,
            model_name=os.getenv("BASE_MODEL"),
            api_base=os.getenv("API_BASE"),
            api_key=os.getenv("API_KEY"),
            use_rag=True,
            vector_database=get_vector_database_instance()
        )
        
        def callback(ch, method, properties, body):
            """消息处理回调函数"""
            try:
                # 解析消息
                message = json.loads(body)
                logger.info(f"工作线程 {worker_id} 收到会话请求: {message.get('request_id')}")
                
                # 提取参数
                request_id = message.get("request_id", "")
                conversation_id = message.get("conversation_id", "")
                user_message = message.get("message", "")
                temperature = message.get("temperature", 0.7)
                
                # 获取或创建会话ID
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                conversation_id = loop.run_until_complete(
                    conversation_chain.get_or_create_conversation(conversation_id)
                )
                
                # 处理会话
                full_response = ""
                rag_context = []
                
                # 创建异步生成器包装器
                async def process_stream():
                    nonlocal full_response
                    async for token in conversation_chain.astream(
                        message=user_message,
                        conversation_id=conversation_id
                    ):
                        if token:
                            # 检查是否为RAG上下文
                            if token.startswith("[rag_context]:"):
                                try:
                                    rag_data = json.loads(token[14:])
                                    rag_context.extend(rag_data)
                                except:
                                    pass
                            else:
                                full_response += token
                
                # 运行异步生成器
                loop.run_until_complete(process_stream())
                
                # 获取会话标题
                conversation_title = loop.run_until_complete(
                    conversation_chain.get_title_from_conversation(conversation_id)
                )
                
                # 关闭事件循环
                loop.close()
                
                # 发送结果
                result_message = {
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "response": full_response,
                    "conversation_title": conversation_title,
                    "rag_context": rag_context,
                    "timestamp": time.time()
                }
                
                mq.publish_message(self.conversation_result_queue, result_message)
                logger.info(f"工作线程 {worker_id} 完成会话请求: {request_id}")
                
                # 确认消息
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"工作线程 {worker_id} 处理消息失败: {str(e)}")
                # 拒绝消息并重新入队
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        # 设置QoS，每次只处理一条消息
        mq.channel.basic_qos(prefetch_count=1)
        
        # 开始消费消息
        mq.consume_messages(self.conversation_queue, callback, auto_ack=False)
    
    def _listen_for_results(self):
        """监听结果队列的线程函数"""
        logger.info("开始监听会话结果队列")
        
        # 创建独立的RabbitMQ连接
        mq = RabbitMQManager()
        
        def callback(ch, method, properties, body):
            """结果处理回调函数"""
            try:
                # 解析消息
                result = json.loads(body)
                request_id = result.get("request_id", "")
                
                # 查找并调用回调函数
                with self.result_lock:
                    if request_id in self.result_callbacks:
                        callback_func = self.result_callbacks[request_id]
                        # 从注册表中移除
                        del self.result_callbacks[request_id]
                        # 调用回调
                        callback_func(result)
                
                # 确认消息
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error(f"处理结果消息失败: {str(e)}")
                # 拒绝消息
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        # 设置QoS
        mq.channel.basic_qos(prefetch_count=10)
        
        # 开始消费消息
        mq.consume_messages(self.conversation_result_queue, callback, auto_ack=False)
    
    def submit_conversation_task(self, message: str, conversation_id: str = None, 
                                temperature: float = 0.7, callback: Callable = None) -> str:
        """提交会话任务
        
        Args:
            message: 用户消息
            conversation_id: 会话ID
            temperature: 温度参数
            callback: 结果回调函数
            
        Returns:
            str: 请求ID
        """
        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 注册回调函数
        if callback:
            with self.result_lock:
                self.result_callbacks[request_id] = callback
        
        # 创建消息
        message_data = {
            "request_id": request_id,
            "conversation_id": conversation_id,
            "message": message,
            "temperature": temperature,
            "timestamp": time.time()
        }
        
        # 发布消息
        self.mq_manager.publish_message(self.conversation_queue, message_data)
        logger.info(f"已提交会话任务: {request_id}")
        
        return request_id