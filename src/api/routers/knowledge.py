"""
知识库API路由
重构rag/api/routers/data_api.py
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Body, Query
from typing import List, Optional, Dict, Any
import os
import tempfile

from ...services.knowledge_service import KnowledgeService


# 创建路由
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# 初始化知识库服务
knowledge_service = KnowledgeService()


@knowledge_router.get("/")
async def get_databases():
    """获取数据库列表"""
    try:
        result = knowledge_service.get_databases()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库列表失败: {str(e)}")


@knowledge_router.get("/{db_id}/files")
async def get_database_files(db_id: str):
    """获取指定数据库的文件列表"""
    try:
        result = knowledge_service.get_documents(db_id)

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@knowledge_router.post("/")
async def create_database(
    database_name: str = Body(..., description="数据库名称"),
    description: str = Body(..., description="数据库描述"),
    dimension: Optional[int] = Body(None, description="向量维度"),
    user_id: Optional[str] = Body(None, description="创建者用户ID")
):
    """创建数据库"""
    try:
        result = knowledge_service.create_database(database_name, description, dimension, user_id)

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建数据库失败: {str(e)}")


@knowledge_router.delete("/{db_id}")
async def delete_database(db_id: str):
    """删除数据库"""
    try:
        result = knowledge_service.delete_database(db_id)

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除数据库失败: {str(e)}")


@knowledge_router.post("/query-test")
async def query_test(
    query: str = Body(..., description="查询文本"),
    meta: Dict[str, Any] = Body(..., description="查询参数")
):
    """查询测试"""
    try:
        result = await knowledge_service.query_test(query, meta)

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询测试失败: {str(e)}")


@knowledge_router.post("/{db_id}/upload")
async def upload_file(
    db_id: str,
    file: UploadFile = File(..., description="上传的文件"),
    chunk_size: int = Query(500, description="分块大小"),
    overlap: int = Query(50, description="重叠大小"),
    user_id: Optional[str] = Query(None, description="创建者用户ID")
):
    """上传文件到知识库"""
    try:
        # 检查文件类型
        if not file.filename.endswith(('.txt', '.md', '.doc', '.docx', '.pdf')):
            raise HTTPException(status_code=400, detail="不支持的文件类型")

        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        try:
            # 上传文件到知识库
            result = knowledge_service.upload_file(
                db_id, tmp_file_path, chunk_size, overlap, user_id
            )

            if result.get("status") == "failed":
                raise HTTPException(status_code=400, detail=result.get("message"))

            return result

        finally:
            # 删除临时文件
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@knowledge_router.post("/{db_id}/documents")
async def add_documents(
    db_id: str,
    documents: List[Dict[str, Any]] = Body(..., description="文档列表"),
    user_id: Optional[str] = Body(None, description="创建者用户ID")
):
    """添加文档到知识库"""
    try:
        # 验证文档格式
        for i, doc in enumerate(documents):
            if "text" not in doc:
                raise HTTPException(status_code=400, detail=f"文档 {i} 缺少 text 字段")
            if "id" not in doc:
                # 自动生成ID
                from ...utils.file_processor import hashstr
                doc["id"] = hashstr(doc["text"])

        result = knowledge_service.add_documents(db_id, documents, user_id)

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加文档失败: {str(e)}")


@knowledge_router.get("/{db_id}/stats")
async def get_database_stats(db_id: str):
    """获取数据库统计信息"""
    try:
        result = knowledge_service.get_database_stats(db_id)

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@knowledge_router.post("/{db_id}/query")
async def query_database(
    db_id: str,
    query: str = Body(..., description="查询文本"),
    distance_threshold: float = Body(0.5, description="距离阈值"),
    rerank_threshold: float = Body(0.1, description="重排序阈值"),
    max_query_count: int = Body(20, description="最大查询数量"),
    top_k: int = Body(10, description="返回结果数量")
):
    """查询数据库"""
    try:
        meta = {
            "db_id": db_id,
            "distanceThreshold": distance_threshold,
            "rerankThreshold": rerank_threshold,
            "maxQueryCount": max_query_count,
            "topK": top_k
        }

        result = await knowledge_service.query_test(query, meta)

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库查询失败: {str(e)}")


__all__ = ["knowledge_router"]
