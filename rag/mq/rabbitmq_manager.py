import pika
import json
import os
from typing import Dict, Any, Callable, Optional
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class RabbitMQManager:
    """RabbitMQ连接和通道管理器"""
    
    def __init__(self):
        """初始化RabbitMQ连接"""
        self.host = os.getenv("RABBITMQ_HOST", "localhost")
        self.port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.username = os.getenv("RABBITMQ_USERNAME", "guest")
        self.password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.vhost = os.getenv("RABBITMQ_VHOST", "/")
        
        self.connection = None
        self.channel = None
        self.connect()
        
    def connect(self):
        """建立到RabbitMQ的连接"""
        try:
            # 创建连接参数
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            # 建立连接
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info("成功连接到RabbitMQ服务器")
        except Exception as e:
            logger.error(f"连接RabbitMQ失败: {str(e)}")
            raise
    
    def declare_queue(self, queue_name: str, durable: bool = True):
        """声明队列
        
        Args:
            queue_name: 队列名称
            durable: 是否持久化
        """
        try:
            self.channel.queue_declare(queue=queue_name, durable=durable)
            logger.info(f"声明队列 {queue_name} 成功")
        except Exception as e:
            logger.error(f"声明队列 {queue_name} 失败: {str(e)}")
            # 尝试重新连接
            self.reconnect()
            self.channel.queue_declare(queue=queue_name, durable=durable)
    
    def publish_message(self, queue_name: str, message: Dict[str, Any]):
        """发布消息到队列
        
        Args:
            queue_name: 队列名称
            message: 消息内容（字典）
        """
        try:
            # 确保队列存在
            self.declare_queue(queue_name)
            
            # 发布消息
            self.channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # 持久化消息
                    content_type='application/json'
                )
            )
            logger.info(f"消息已发布到队列 {queue_name}")
        except Exception as e:
            logger.error(f"发布消息到队列 {queue_name} 失败: {str(e)}")
            # 尝试重新连接
            self.reconnect()
            self.publish_message(queue_name, message)
    
    def consume_messages(self, queue_name: str, callback: Callable, auto_ack: bool = False):
        """从队列消费消息
        
        Args:
            queue_name: 队列名称
            callback: 回调函数，处理消息
            auto_ack: 是否自动确认
        """
        try:
            # 确保队列存在
            self.declare_queue(queue_name)
            
            # 设置消费者
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack
            )
            
            logger.info(f"开始从队列 {queue_name} 消费消息")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"从队列 {queue_name} 消费消息失败: {str(e)}")
            # 尝试重新连接
            self.reconnect()
            self.consume_messages(queue_name, callback, auto_ack)
    
    def reconnect(self):
        """重新连接到RabbitMQ"""
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
            self.connect()
            logger.info("已重新连接到RabbitMQ服务器")
        except Exception as e:
            logger.error(f"重新连接RabbitMQ失败: {str(e)}")
            raise
    
    def close(self):
        """关闭连接"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("RabbitMQ连接已关闭")