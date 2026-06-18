"""
知识库业务服务
整合rag/service/data_service.py的业务逻辑
"""

from typing import Dict, List, Any, Optional
import traceback

from ..core.knowledge.knowledge_base import KnowledgeBase
from ..utils.logging_config import logger


class KnowledgeService:
    """知识库业务服务类"""

    def __init__(self):
        """初始化知识库服务"""
        self.knowledge_base = KnowledgeBase()

    def get_databases(self) -> Dict[str, Any]:
        """获取数据库列表

        Returns:
            Dict[str, Any]: 数据库列表信息
        """
        try:
            result = self.knowledge_base.get_databases()
            return result

        except Exception as e:
            logger.error(f"获取数据库列表失败: {e}\n{traceback.format_exc()}")
            return {"message": f"获取数据库列表失败: {e}", "databases": []}

    def get_documents(self, db_id: str) -> Dict[str, Any]:
        """获取指定数据库的所有文档

        Args:
            db_id: 数据库ID

        Returns:
            Dict[str, Any]: 文档列表
        """
        try:
            result = self.knowledge_base.get_documents(db_id)
            return result
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}\n{traceback.format_exc()}")
            return {"documents": [], "total": 0, "message": f"获取文档列表失败: {e}"}

    def create_database(self, database_name: str, description: str,
                       dimension: Optional[int] = None,
                       user_id: Optional[str] = None) -> Dict[str, Any]:
        """创建数据库

        Args:
            database_name: 数据库名称
            description: 数据库描述
            dimension: 向量维度
            user_id: 创建者用户ID

        Returns:
            Dict[str, Any]: 创建结果
        """
        logger.debug(f"Create database {database_name} by user {user_id}")

        try:
            database_info = self.knowledge_base.create_database(
                database_name=database_name,
                description=description,
                dimension=dimension,
                creator_id=user_id
            )

            logger.info(f"Created database {database_name} successfully by user {user_id}")
            return {"status": "success", **database_info}

        except Exception as e:
            logger.error(f"创建数据库失败: {e}\n{traceback.format_exc()}")
            return {"message": f"创建数据库失败: {e}", "status": "failed"}

    def delete_database(self, db_id: str) -> Dict[str, Any]:
        """删除数据库

        Args:
            db_id: 数据库ID

        Returns:
            Dict[str, Any]: 删除结果
        """
        logger.debug(f"Delete database {db_id}")

        try:
            success = self.knowledge_base.delete_database(db_id)

            if success:
                logger.info(f"Deleted database {db_id} successfully")
                return {"status": "success", "message": "数据库删除成功"}
            else:
                return {"status": "failed", "message": "数据库不存在或删除失败"}

        except Exception as e:
            logger.error(f"删除数据库失败: {e}\n{traceback.format_exc()}")
            return {"message": f"删除数据库失败: {e}", "status": "failed"}

    def upload_file(self, db_id: str, file_path: str,
                   chunk_size: int = 500, overlap: int = 50,
                   user_id: Optional[str] = None) -> Dict[str, Any]:
        """上传文件到知识库

        Args:
            db_id: 数据库ID
            file_path: 文件路径
            chunk_size: 分块大小
            overlap: 重叠大小
            user_id: 创建者用户ID

        Returns:
            Dict[str, Any]: 上传结果
        """
        logger.debug(f"Upload file {file_path} to database {db_id} by user {user_id}")

        try:
            success = self.knowledge_base.upload_file(
                db_id=db_id,
                file_path=file_path,
                chunk_size=chunk_size,
                overlap=overlap,
                creator_id=user_id
            )

            if success:
                logger.info(f"Uploaded file {file_path} to {db_id} successfully")
                return {"status": "success", "message": "文件上传成功"}
            else:
                return {"status": "failed", "message": "文件上传失败"}

        except Exception as e:
            logger.error(f"上传文件失败: {e}\n{traceback.format_exc()}")
            return {"message": f"上传文件失败: {e}", "status": "failed"}

    def add_documents(self, db_id: str, documents: List[Dict[str, Any]],
                     user_id: Optional[str] = None) -> Dict[str, Any]:
        """添加文档到知识库

        Args:
            db_id: 数据库ID
            documents: 文档列表
            user_id: 创建者用户ID

        Returns:
            Dict[str, Any]: 添加结果
        """
        logger.debug(f"Add {len(documents)} documents to database {db_id} by user {user_id}")

        try:
            success = self.knowledge_base.add_documents(db_id, documents, creator_id=user_id)

            if success:
                logger.info(f"Added {len(documents)} documents to {db_id} successfully")
                return {"status": "success", "message": f"成功添加 {len(documents)} 个文档"}
            else:
                return {"status": "failed", "message": "文档添加失败"}

        except Exception as e:
            logger.error(f"添加文档失败: {e}\n{traceback.format_exc()}")
            return {"message": f"添加文档失败: {e}", "status": "failed"}

    async def query_test(self, query: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """查询测试

        Args:
            query: 查询文本
            meta: 查询参数

        Returns:
            Dict[str, Any]: 查询结果
        """
        logger.debug(f"Query test: {query}")

        try:
            db_id = meta.get("db_id")
            if not db_id:
                return {"status": "failed", "message": "缺少数据库ID"}

            result = self.knowledge_base.query(
                query=query,
                db_id=db_id,
                distance_threshold=meta.get("distanceThreshold", 0.5),
                rerank_threshold=meta.get("rerankThreshold", 0.1),
                max_query_count=meta.get("maxQueryCount", 20),
                top_k=meta.get("topK", 10)
            )

            return {"status": "success", **result}

        except Exception as e:
            logger.error(f"查询测试失败: {e}\n{traceback.format_exc()}")
            return {"message": f"查询测试失败: {e}", "status": "failed"}

    def get_database_stats(self, db_id: str) -> Dict[str, Any]:
        """获取数据库统计信息

        Args:
            db_id: 数据库ID

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            stats = self.knowledge_base.vector_store.get_collection_stats(db_id)
            return {"status": "success", **stats}

        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {"message": f"获取数据库统计失败: {e}", "status": "failed"}


__all__ = ["KnowledgeService"]
