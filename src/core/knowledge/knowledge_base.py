"""
知识库管理核心
使用 PostgreSQL 存储元数据，Milvus 存储向量
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ...config import get_config
from ...utils.logging_config import logger
from ...utils.file_processor import hashstr, process_uploaded_file
from ...utils.vector_db_manager import get_vector_db_manager
from ...utils.postgres_manager import get_postgres_manager
from ...models.embedding_model import get_embedding_model
from ...models.rerank_model import get_reranker
from ...models.orm_models import KnowledgeDatabase, Document, DocumentChunk


@dataclass
class KnowledgeDocument:
    """知识库文档数据类"""
    id: str
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class KnowledgeBaseRepository:
    """知识库数据库仓储层 - 使用 PostgreSQL 存储元数据"""

    def __init__(self):
        self.pg_manager = get_postgres_manager()

    def create_database(self, db_id: str, name: str, description: str,
                       embed_model: str, dimension: int,
                       creator_id: Optional[str] = None) -> Dict[str, Any]:
        """创建知识库数据库记录"""
        try:
            with self.pg_manager.get_session() as session:
                db_record = KnowledgeDatabase(
                    db_id=db_id,
                    name=name,
                    description=description,
                    creator_id=creator_id,
                    metadata_={
                        "embed_model": embed_model,
                        "dimension": dimension,
                        "status": "active"
                    }
                )
                session.add(db_record)
                session.commit()
                return db_record.to_dict()
        except Exception as e:
            logger.error(f"Failed to create database record: {e}")
            raise

    def get_database_by_id(self, db_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取数据库信息"""
        try:
            with self.pg_manager.get_session() as session:
                db_record = session.query(KnowledgeDatabase).filter(
                    KnowledgeDatabase.db_id == db_id
                ).first()
                if db_record:
                    return db_record.to_dict()
                return None
        except Exception as e:
            logger.error(f"Failed to get database: {e}")
            return None

    def get_all_databases(self) -> List[Dict[str, Any]]:
        """获取所有数据库"""
        try:
            with self.pg_manager.get_session() as session:
                db_records = session.query(KnowledgeDatabase).all()
                return [db.to_dict() for db in db_records]
        except Exception as e:
            logger.error(f"Failed to get all databases: {e}")
            return []

    def delete_database(self, db_id: str) -> bool:
        """删除数据库"""
        try:
            with self.pg_manager.get_session() as session:
                db_record = session.query(KnowledgeDatabase).filter(
                    KnowledgeDatabase.db_id == db_id
                ).first()
                if db_record:
                    session.delete(db_record)
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete database: {e}")
            return False

    def get_documents_by_db_id(self, db_id: str) -> List[Dict[str, Any]]:
        """获取指定数据库的所有文档"""
        try:
            with self.pg_manager.get_session() as session:
                docs = session.query(Document).filter(
                    Document.db_id == db_id
                ).order_by(Document.created_at.desc()).all()
                return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Failed to get documents for db {db_id}: {e}")
            return []

    def get_document_by_id(self, db_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档信息"""
        try:
            with self.pg_manager.get_session() as session:
                doc = session.query(Document).filter(
                    Document.db_id == db_id,
                    Document.document_id == document_id
                ).first()
                if doc:
                    return doc.to_dict()
                return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None

    def create_document(self, db_id: str, document_id: str, title: str,
                       content: str, file_path: str = None, file_type: str = None,
                       file_size: int = None, chunk_count: int = 0,
                       metadata: Dict = None,
                       creator_id: Optional[str] = None) -> Dict[str, Any]:
        """创建文档记录"""
        try:
            with self.pg_manager.get_session() as session:
                doc = Document(
                    db_id=db_id,
                    document_id=document_id,
                    title=title,
                    content=content,
                    file_path=file_path,
                    file_type=file_type,
                    file_size=file_size,
                    chunk_count=chunk_count,
                    metadata_=metadata or {},
                    creator_id=creator_id
                )
                session.add(doc)
                session.commit()
                return doc.to_dict()
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise

    def create_document_chunk(self, document_id: str, chunk_id: str,
                              content: str, chunk_index: int = None,
                              token_count: int = None,
                              metadata: Dict = None,
                              creator_id: Optional[str] = None) -> Dict[str, Any]:
        """创建文档块记录"""
        try:
            with self.pg_manager.get_session() as session:
                chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_id=chunk_id,
                    content=content,
                    chunk_index=chunk_index,
                    token_count=token_count,
                    metadata_=metadata or {},
                    creator_id=creator_id
                )
                session.add(chunk)
                session.commit()
                return chunk.to_dict()
        except Exception as e:
            logger.error(f"Failed to create document chunk: {e}")
            raise


class KnowledgeBase:
    """知识库核心管理类"""

    def __init__(self):
        self.vector_store = get_vector_db_manager()
        self.db_repository = KnowledgeBaseRepository()

        # 默认配置
        self.default_distance_threshold = 0.5
        self.default_rerank_threshold = 0.1
        self.default_max_query_count = 20

        # 加载模型
        self._load_models()

    def _load_models(self):
        """加载相关模型"""
        cfg = get_config()
        if not cfg.enable_knowledge_base:
            return

        # 加载嵌入模型
        self.embed_model = get_embedding_model(cfg)
        if not self.embed_model:
            logger.error("Failed to load embedding model")
            return

        # 加载重排序模型
        if cfg.enable_reranker:
            self.reranker = get_reranker(cfg)
        else:
            self.reranker = None

        logger.info("Knowledge base models loaded successfully")

    def create_database(self, database_name: str, description: str,
                       dimension: Optional[int] = None,
                       creator_id: Optional[str] = None) -> Dict[str, Any]:
        """创建知识库

        Args:
            database_name: 数据库名称
            description: 描述
            dimension: 向量维度
            creator_id: 创建者用户ID

        Returns:
            Dict[str, Any]: 数据库信息
        """
        if not self.embed_model:
            raise ValueError("Embedding model not loaded")

        dimension = dimension or self.embed_model.get_dimension()
        db_id = f"kb_{hashstr(database_name, with_salt=True)}"

        # 创建数据库记录 (PostgreSQL)
        db_info = self.db_repository.create_database(
            db_id=db_id,
            name=database_name,
            description=description,
            embed_model=get_config().embed_model,
            dimension=dimension,
            creator_id=creator_id
        )

        # 在向量数据库中创建集合 (Milvus)
        if not self.vector_store.create_collection(db_id, dimension):
            raise ValueError(f"Failed to create vector collection for {db_id}")

        logger.info(f"Created knowledge base: {database_name} (ID: {db_id}, creator: {creator_id})")
        return db_info

    def get_databases(self) -> Dict[str, Any]:
        """获取所有数据库"""
        if not get_config().enable_knowledge_base:
            return {"message": "知识库未启用", "databases": []}

        databases = self.db_repository.get_all_databases()

        # 添加向量库统计信息
        for db in databases:
            try:
                stats = self.vector_store.get_collection_stats(db["db_id"])
                db["vector_stats"] = stats
            except Exception as e:
                logger.warning(f"Failed to get stats for {db['name']}: {e}")
                db["vector_stats"] = {"error": str(e)}

        return {"databases": databases}

    def get_documents(self, db_id: str) -> Dict[str, Any]:
        """获取指定数据库的所有文档

        Args:
            db_id: 数据库ID

        Returns:
            Dict[str, Any]: 文档列表
        """
        try:
            documents = self.db_repository.get_documents_by_db_id(db_id)
            return {"documents": documents, "total": len(documents)}
        except Exception as e:
            logger.error(f"获取数据库文档失败: {e}")
            return {"documents": [], "total": 0, "message": str(e)}

    def delete_database(self, db_id: str) -> bool:
        """删除数据库"""
        # 删除向量集合 (Milvus)
        self.vector_store.delete_collection(db_id)

        # 删除数据库记录 (PostgreSQL)
        success = self.db_repository.delete_database(db_id)

        if success:
            logger.info(f"Deleted knowledge base: {db_id}")

        return success

    def add_documents(self, db_id: str, documents: List[Dict[str, Any]],
                     creator_id: Optional[str] = None) -> bool:
        """添加文档到知识库

        Args:
            db_id: 数据库ID
            documents: 文档列表
            creator_id: 创建者用户ID

        Returns:
            bool: 是否成功
        """
        if not self.embed_model:
            logger.error("Embedding model not loaded")
            return False

        try:
            # 提取文本进行向量化
            texts = [doc["text"] for doc in documents]
            embeddings = self.embed_model.batch_encode(texts)

            # 准备插入数据
            insert_data = []
            for i, doc in enumerate(documents):
                insert_data.append({
                    "id": doc["id"],
                    "vector": embeddings[i],
                    "text": doc["text"],
                    "metadata": doc.get("metadata", {})
                })

            # 插入向量数据库 (Milvus)
            success = self.vector_store.insert_vectors(db_id, insert_data)

            if success:
                logger.info(f"Added {len(documents)} documents to {db_id} by user {creator_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to add documents to {db_id}: {e}")
            return False

    def upload_file(self, db_id: str, file_path: str,
                   chunk_size: int = 500, overlap: int = 50,
                   creator_id: Optional[str] = None) -> bool:
        """上传文件到知识库

        Args:
            db_id: 数据库ID
            file_path: 文件路径
            chunk_size: 分块大小
            overlap: 重叠大小
            creator_id: 创建者用户ID

        Returns:
            bool: 是否成功
        """
        import os
        from pathlib import Path

        # 处理文件
        documents = process_uploaded_file(file_path, chunk_size, overlap)

        if not documents:
            logger.error(f"Failed to process file: {file_path}")
            return False

        # 提取文件元数据
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix.lower()
        try:
            file_size = os.path.getsize(file_path)
        except Exception:
            file_size = None

        # 文件类型映射
        file_type_map = {
            ".txt": "text",
            ".md": "markdown",
            ".doc": "word",
            ".docx": "word",
            ".pdf": "pdf"
        }
        file_type = file_type_map.get(file_ext, "unknown")

        # 为整个文件生成一个 document_id（基于文件名+大小+内容首尾）
        first_chunk = documents[0]["text"][:200] if documents else ""
        last_chunk = documents[-1]["text"][:200] if len(documents) > 1 else first_chunk
        doc_sig = f"{file_name}_{file_size}_{first_chunk}_{last_chunk}"
        document_id = hashstr(doc_sig)

        try:
            # 写入 Document 记录（PostgreSQL）
            self.db_repository.create_document(
                db_id=db_id,
                document_id=document_id,
                title=file_name,
                content="",  # 内容存在 chunks 中，按需从 Milvus 查询
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
                chunk_count=len(documents),
                metadata={"original_filename": file_name},
                creator_id=creator_id
            )
        except Exception as e:
            # 如果文档记录已存在（同一文件重复上传），忽略即可
            logger.warning(f"Document record may already exist: {e}")

        # 添加到向量库（Milvus）
        return self.add_documents(db_id, documents, creator_id=creator_id)

    def query(self, query: str, db_id: str, distance_threshold: float = None,
             rerank_threshold: float = None, max_query_count: int = None,
             top_k: int = 10) -> Dict[str, Any]:
        """查询知识库

        Args:
            query: 查询文本
            db_id: 数据库ID
            distance_threshold: 距离阈值
            rerank_threshold: 重排序阈值
            max_query_count: 最大查询数量
            top_k: 返回结果数量

        Returns:
            Dict[str, Any]: 查询结果
        """
        distance_threshold = distance_threshold or self.default_distance_threshold
        rerank_threshold = rerank_threshold or self.default_rerank_threshold
        max_query_count = max_query_count or self.default_max_query_count

        if not self.embed_model:
            return {"results": [], "all_results": [], "message": "Embedding model not loaded"}

        try:
            # 向量化查询
            query_embedding = self.embed_model.encode([query])[0]

            # 向量搜索 (Milvus)
            search_results = self.vector_store.search_vectors(
                collection_name=db_id,
                query_vector=query_embedding,
                top_k=max_query_count,
                threshold=distance_threshold
            )

            # 准备结果
            all_results = []
            for result in search_results:
                all_results.append({
                    "id": result["id"],
                    "distance": result["distance"],
                    "entity": {
                        "text": result["text"],
                        "metadata": result["metadata"]
                    }
                })

            # 重排序
            final_results = all_results[:top_k]
            if self.reranker and len(all_results) > 1:
                try:
                    # 提取文本用于重排序
                    texts = [r["entity"]["text"] for r in all_results]
                    scores = self.reranker.compute_score((query, texts))

                    # 根据重排序分数过滤和排序
                    scored_results = []
                    for i, result in enumerate(all_results):
                        if i < len(scores) and scores[i] >= rerank_threshold:
                            result["rerank_score"] = scores[i]
                            scored_results.append(result)

                    # 按重排序分数排序
                    final_results = sorted(scored_results,
                                         key=lambda x: x["rerank_score"],
                                         reverse=True)[:top_k]

                except Exception as e:
                    logger.warning(f"Reranking failed: {e}")

            return {
                "results": final_results,
                "all_results": all_results,
                "total_count": len(search_results)
            }

        except Exception as e:
            logger.error(f"Query failed for {db_id}: {e}")
            return {"results": [], "all_results": [], "message": str(e)}


__all__ = ["KnowledgeDocument", "KnowledgeBase", "KnowledgeBaseRepository"]
