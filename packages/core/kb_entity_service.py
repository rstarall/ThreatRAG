import asyncio
from typing import List, Dict, Optional, Any

from .. import config, executor
from ..utils import logger
from .entity_extractor import entity_extractor
from .. import knowledge_base

class KnowledgeBaseEntityService:
    """知识库实体服务
    
    提供从知识库文件中提取实体的功能
    """
    
    @staticmethod
    async def extract_entities_from_file(db_id: str, 
                                        file_id: str, 
                                        language: str = "chinese",
                                        entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """从知识库中的文件提取实体
        
        Args:
            db_id: 知识库ID
            file_id: 文件ID
            language: 提取语言，默认为chinese
            entity_types: 要提取的实体类型列表，为空则提取所有类型
            
        Returns:
            包含实体和关系的字典
        """
        # 验证知识库和文件
        validation_result = await KnowledgeBaseEntityService._validate_db_and_file(db_id, file_id)
        if validation_result["status"] == "failed":
            return validation_result
            
        file_info = validation_result["file_info"]
        
        # 获取文件的文本分块
        chunks_result = await KnowledgeBaseEntityService._get_file_chunks(db_id, file_id)
        if chunks_result["status"] == "failed":
            return chunks_result
            
        combined_text = chunks_result["combined_text"]
        
        # 提取实体
        extraction_result = await entity_extractor.extract_entities(
            text=combined_text,
            language=language,
            entity_types=entity_types
        )
        
        # 合并结果
        return {
            **extraction_result,
            "db_id": db_id,
            "file_id": file_id,
            "file_name": file_info.get("filename", "未知")
        }
    
    @staticmethod
    async def _validate_db_and_file(db_id: str, file_id: str) -> Dict[str, Any]:
        """验证知识库和文件是否存在及关联
        
        Args:
            db_id: 知识库ID
            file_id: 文件ID
            
        Returns:
            验证结果，包含状态和文件信息
        """
        loop = asyncio.get_event_loop()
        
        # 验证知识库是否存在
        db_info = await loop.run_in_executor(
            executor,
            lambda: knowledge_base.get_kb_by_id(db_id)
        )
        
        if not db_info:
            return {"status": "failed", "message": f"知识库不存在: {db_id}"}
        
        # 验证文件是否存在
        file_info = await loop.run_in_executor(
            executor,
            lambda: knowledge_base.get_file_by_id(file_id)
        )
        
        if not file_info:
            return {"status": "failed", "message": f"文件不存在: {file_id}"}
        
        # 验证文件是否属于该知识库
        if file_info.get("database_id") != db_id:
            return {"status": "failed", "message": "文件不属于指定知识库"}
        
        return {"status": "success", "file_info": file_info}
    
    @staticmethod
    async def _get_file_chunks(db_id: str, file_id: str) -> Dict[str, Any]:
        """从Milvus获取文件的文本分块
        
        Args:
            db_id: 知识库ID
            file_id: 文件ID
            
        Returns:
            包含合并文本的字典
        """
        loop = asyncio.get_event_loop()
        
        # 查询该文件的所有分块
        chunks = await loop.run_in_executor(
            executor,
            lambda: knowledge_base.client.query(
                collection_name=db_id,
                filter=f"file_id == '{file_id}'",
                output_fields=["text", "start_char_idx"]
            )
        )
        
        if not chunks:
            return {"status": "failed", "message": f"文件 {file_id} 在Milvus中未找到分块"}
        
        # 按照start_char_idx排序分块
        chunks.sort(key=lambda x: x.get("start_char_idx") or 0)
        
        # 合并全部文本分块
        chunks_sorted = sorted(chunks, key=lambda x: x.get("start_char_idx") or 0)
        combined_text = " ".join([chunk["text"] for chunk in chunks_sorted]).strip()
        
        return {
            "status": "success", 
            "combined_text": combined_text, 
            "chunks_count": len(chunks)
        }

# 创建全局实例
kb_entity_service = KnowledgeBaseEntityService()
