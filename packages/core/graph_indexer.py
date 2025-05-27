import time
import threading
import traceback
from datetime import datetime

from .. import config
from ..utils import logger
from .graphbase import graph_base

class GraphIndexer:
    """图数据库索引器，定时扫描并为没有嵌入向量的实体创建索引"""
    
    def __init__(self, interval=3600, batch_size=100, kgdb_name='neo4j'):
        """
        初始化图数据库索引器
        
        Args:
            interval: 扫描间隔，单位为秒，默认1小时
            batch_size: 每次处理的实体数量，默认100
            kgdb_name: 图数据库名称，默认'neo4j'
        """
        self.interval = interval
        self.batch_size = batch_size
        self.kgdb_name = kgdb_name
        self.running = False
        self.thread = None
        self.last_run_time = None
        self.total_indexed = 0
    
    def start(self):
        """启动索引器"""
        if self.running:
            logger.warning("图数据库索引器已在运行中")
            return False
        
        if not config.enable_knowledge_graph:
            logger.warning("知识图谱未启用，索引器不会启动")
            return False
        
        if not graph_base.is_running():
            logger.warning("图数据库未启动，索引器不会启动")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"图数据库索引器已启动，扫描间隔: {self.interval}秒")
        return True
    
    def stop(self):
        """停止索引器"""
        if not self.running:
            return
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
        logger.info("图数据库索引器已停止")
    
    def _run(self):
        """索引器主循环"""
        while self.running:
            try:
                self._index_nodes()
                self.last_run_time = datetime.now()
                # 等待下一次扫描
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"图数据库索引过程出错: {e}, {traceback.format_exc()}")
                # 出错后等待一段时间再重试
                time.sleep(60)
    
    def _index_nodes(self):
        """索引没有嵌入向量的节点"""
        if not graph_base.is_running():
            logger.warning("图数据库未启动，跳过本次索引")
            return 0
        
        # 查询没有嵌入向量的节点
        nodes_without_embedding = graph_base.query_nodes_without_embedding(self.kgdb_name)
        total_nodes = len(nodes_without_embedding)
        
        if total_nodes == 0:
            logger.info("没有需要索引的节点")
            return 0
        
        logger.info(f"发现 {total_nodes} 个没有嵌入向量的节点，开始索引")
        
        # 分批处理节点
        indexed_count = 0
        for i in range(0, total_nodes, self.batch_size):
            if not self.running:
                break
                
            batch = nodes_without_embedding[i:i+self.batch_size]
            logger.info(f"正在处理第 {i//self.batch_size + 1}/{(total_nodes-1)//self.batch_size + 1} 批 ({len(batch)} 个节点)")
            
            try:
                count = graph_base.add_embedding_to_nodes(batch, self.kgdb_name)
                indexed_count += count
                logger.info(f"已为 {count} 个节点添加嵌入向量")
            except Exception as e:
                logger.error(f"为节点批次添加嵌入向量失败: {e}, {traceback.format_exc()}")
        
        self.total_indexed += indexed_count
        logger.info(f"索引完成，共为 {indexed_count} 个节点添加了嵌入向量")
        return indexed_count
    
    def get_status(self):
        """获取索引器状态"""
        return {
            "running": self.running,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "total_indexed": self.total_indexed,
            "interval": self.interval,
            "batch_size": self.batch_size,
            "kgdb_name": self.kgdb_name
        }

# 创建全局索引器实例
graph_indexer = GraphIndexer()

def get_graph_indexer():
    """获取图数据库索引器实例"""
    return graph_indexer