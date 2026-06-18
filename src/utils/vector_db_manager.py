"""
向量数据库管理器
专门处理 Milvus 向量数据库的连接和操作
"""

import os
from typing import List, Dict, Any, Optional

from pymilvus import MilvusClient, MilvusException

from .logging_config import logger


class VectorDBManager:
    """向量数据库管理器 (Milvus)"""

    def __init__(self, host: str = None, port: int = None):
        """初始化向量数据库管理器

        Args:
            host: Milvus 主机地址
            port: Milvus 端口
        """
        from ..config import get_config
        milvus_config = get_config().milvus
        self.host = host or milvus_config.get("host", "127.0.0.1")
        self.port = port or milvus_config.get("port", 19530)
        self.client: Optional[MilvusClient] = None
        self._connect()

    def _connect(self):
        """连接到 Milvus"""
        try:
            uri = f"http://{self.host}:{self.port}"
            self.client = MilvusClient(uri=uri)
            logger.info(f"Connected to Milvus at {uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise ConnectionError(f"Failed to connect to Milvus: {e}")

    def create_collection(self, collection_name: str, dimension: int, metric_type: str = "IP") -> bool:
        """创建集合

        Args:
            collection_name: 集合名称
            dimension: 向量维度
            metric_type: 距离度量类型

        Returns:
            bool: 创建是否成功
        """
        try:
            if self.client.has_collection(collection_name):
                logger.warning(f"Collection {collection_name} already exists")
                return True

            self.client.create_collection(
                collection_name=collection_name,
                dimension=dimension,
                metric_type=metric_type,
                consistency_level="Strong"
            )

            logger.info(f"Created collection {collection_name} with dimension {dimension}")
            return True

        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            return False

    def insert_vectors(self, collection_name: str, data: List[Dict[str, Any]]) -> bool:
        """插入向量数据

        Args:
            collection_name: 集合名称
            data: 数据列表，每个元素包含 id, vector, 和其他字段

        Returns:
            bool: 插入是否成功
        """
        try:
            if not data:
                return True

            insert_data = []
            for item in data:
                raw_id = item["id"]
                if isinstance(raw_id, str):
                    int_id = int.from_bytes(bytes.fromhex(raw_id[:16].ljust(16, '0')), 'big')
                    int_id = int_id % (2**63)  # 有符号 int64 最大值
                else:
                    int_id = raw_id
                insert_data.append({
                    "id": int_id,
                    "vector": item["vector"],
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {})
                })

            self.client.insert(collection_name=collection_name, data=insert_data)

            logger.info(f"Inserted {len(insert_data)} vectors to {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to insert vectors to {collection_name}: {e}")
            return False

    def search_vectors(self, collection_name: str, query_vector: List[float],
                      top_k: int = 10, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """搜索向量

        Args:
            collection_name: 集合名称
            query_vector: 查询向量
            top_k: 返回结果数量
            threshold: 相似度阈值

        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        try:
            search_results = self.client.search(
                collection_name=collection_name,
                data=[query_vector],
                limit=top_k,
                output_fields=["text", "metadata"]
            )

            results = []
            for hit in search_results[0]:
                if hit["distance"] >= threshold:
                    results.append({
                        "id": hit["id"],
                        "distance": hit["distance"],
                        "text": hit["entity"].get("text", ""),
                        "metadata": hit["entity"].get("metadata", {})
                    })

            logger.debug(f"Found {len(results)} results in {collection_name}")
            return results

        except Exception as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            return []

    def delete_collection(self, collection_name: str) -> bool:
        """删除集合

        Args:
            collection_name: 集合名称

        Returns:
            bool: 删除是否成功
        """
        try:
            if self.client.has_collection(collection_name):
                self.client.drop_collection(collection_name)
                logger.info(f"Deleted collection {collection_name}")
            else:
                logger.warning(f"Collection {collection_name} does not exist")

            return True

        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False

    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """获取集合统计信息

        Args:
            collection_name: 集合名称

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            if not self.client.has_collection(collection_name):
                return {"error": "Collection does not exist"}

            stats = self.client.get_collection_stats(collection_name)
            return {
                "collection_name": collection_name,
                "row_count": stats["row_count"],
                "data_size": stats.get("data_size", 0)
            }

        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            return {"error": str(e)}

    def list_collections(self) -> List[str]:
        """列出所有集合

        Returns:
            List[str]: 集合名称列表
        """
        try:
            return self.client.list_collections()
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def close(self):
        """关闭连接"""
        self.client = None
        logger.info("Milvus connection closed")


# 全局单例向量数据库管理器实例
vector_db_manager: Optional[VectorDBManager] = None


def get_vector_db_manager() -> VectorDBManager:
    """获取向量数据库管理器实例"""
    global vector_db_manager
    if vector_db_manager is None:
        vector_db_manager = VectorDBManager()
    return vector_db_manager


__all__ = ["VectorDBManager", "get_vector_db_manager", "vector_db_manager"]
