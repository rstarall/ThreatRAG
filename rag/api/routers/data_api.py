import os
import asyncio
import traceback
from typing import List, Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Body, Form, Query
import shutil

from packages.utils import logger, hashstr
from packages import config
from packages import executor, retriever, knowledge_base, graph_base
from packages.core.graph_indexer import graph_indexer

data = APIRouter(prefix="/data")


@data.get("/")
async def get_databases():
    try:
        database = knowledge_base.get_databases()
    except Exception as e:
        logger.error(f"获取数据库列表失败 {e}, {traceback.format_exc()}")
        return {"message": f"获取数据库列表失败 {e}", "databases": []}
    return database

@data.post("/")
async def create_database(
    database_name: str = Body(...),
    description: str = Body(...),
    dimension: Optional[int] = Body(None)
):
    logger.debug(f"Create database {database_name}")
    try:
        database_info = knowledge_base.create_database(
            database_name,
            description,
            dimension=dimension
        )
    except Exception as e:
        logger.error(f"创建数据库失败 {e}, {traceback.format_exc()}")
        return {"message": f"创建数据库失败 {e}", "status": "failed"}
    return database_info

@data.delete("/")
async def delete_database(db_id):
    logger.debug(f"Delete database {db_id}")
    knowledge_base.delete_database(db_id)
    return {"message": "删除成功"}

@data.post("/query-test")
async def query_test(query: str = Body(...), meta: dict = Body(...)):
    logger.debug(f"Query test in {meta}: {query}")
    result = retriever.query_knowledgebase(query, history=None, refs={"meta": meta})
    return result

@data.post("/file-to-chunk")
async def file_to_chunk(files: List[str] = Body(...), params: dict = Body(...)):
    logger.debug(f"File to chunk: {files}")
    result = knowledge_base.file_to_chunk(files, params=params)
    return result

@data.post("/add-by-file")
async def create_document_by_file(db_id: str = Body(...), files: List[str] = Body(...)):
    logger.debug(f"Add document in {db_id} by file: {files}")
    try:
        # 使用线程池执行耗时操作
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,  # 使用与chat_router相同的线程池
            lambda: knowledge_base.add_files(db_id, files)
        )
        return {"message": "文件添加完成", "status": "success"}
    except Exception as e:
        logger.error(f"添加文件失败: {e}, {traceback.format_exc()}")
        return {"message": f"添加文件失败: {e}", "status": "failed"}

@data.post("/add-by-chunks")
async def add_by_chunks(db_id: str = Body(...), file_chunks: dict = Body(...)):
    # logger.debug(f"Add chunks in {db_id}: {len(file_chunks)} chunks")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,  # 使用与chat_router相同的线程池
            lambda: knowledge_base.add_chunks(db_id, file_chunks)
        )
        return {"message": "分块添加完成", "status": "success"}
    except Exception as e:
        logger.error(f"添加分块失败: {e}, {traceback.format_exc()}")
        return {"message": f"添加分块失败: {e}", "status": "failed"}

@data.get("/info")
async def get_database_info(db_id: str):
    # logger.debug(f"Get database {db_id} info")
    database = knowledge_base.get_database_info(db_id)
    return database

@data.delete("/document")
async def delete_document(db_id: str = Body(...), file_id: str = Body(...)):
    logger.debug(f"DELETE document {file_id} info in {db_id}")
    knowledge_base.delete_file(db_id, file_id)
    return {"message": "删除成功"}

@data.get("/document")
async def get_document_info(db_id: str, file_id: str):
    logger.debug(f"GET document {file_id} info in {db_id}")

    try:
        info = knowledge_base.get_file_info(db_id, file_id)
    except Exception as e:
        logger.error(f"Failed to get file info, {e}, {db_id=}, {file_id=}, {traceback.format_exc()}")
        info = {"message": "Failed to get file info", "status": "failed"}

    return info

@data.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db_id: Optional[str] = Query(None)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No selected file")

    # 根据db_id获取上传路径，如果db_id为None则使用默认路径
    if db_id:
        upload_dir = knowledge_base.get_db_upload_path(db_id)
    else:
        upload_dir = os.path.join(config.save_dir, "data", "uploads")

    basename, ext = os.path.splitext(file.filename)
    filename = f"{basename}_{hashstr(basename, 4, with_salt=True)}{ext}".lower()
    file_path = os.path.join(upload_dir, filename)
    os.makedirs(upload_dir, exist_ok=True)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # 返回文件路径，但使用相对路径而不是绝对路径，提高安全性
    relative_path = os.path.relpath(file_path, config.save_dir) if config.save_dir in file_path else filename
    return {"message": "File successfully uploaded", "file_path": relative_path, "db_id": db_id}



@data.get("/files")
async def get_files_list(db_id: str):
    """获取指定数据库中的所有文件列表"""
    logger.debug(f"GET files list in database {db_id}")
    
    try:
        # 获取文件列表
        files = knowledge_base.get_files_list(db_id)
        
        return {
            "message": "获取文件列表成功",
            "status": "success",
            "db_id": db_id,
            "files": files,
            "total_count": len(files)
        }
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}, {traceback.format_exc()}")
        return {"message": f"获取文件列表失败: {e}", "status": "failed", "files": []}

@data.delete("/file")
async def delete_file_by_id(db_id: str = Body(...), file_id: str = Body(...)):
    """删除指定数据库中的指定文件"""
    logger.debug(f"DELETE file {file_id} from database {db_id}")
    
    try:
        # 先检查数据库是否存在
        db = knowledge_base.get_kb_by_id(db_id)
        if db is None:
            return {"message": f"数据库不存在，db_id: {db_id}", "status": "failed"}
        
        # 根据file_id获取文件信息
        file_info = knowledge_base.get_file_by_id(file_id)
        if file_info is None:
            return {"message": f"文件不存在，file_id: {file_id}", "status": "failed"}
        
        # 验证文件是否属于指定的数据库
        file_db_id = file_info.get("database_id")
        if file_db_id != db_id:
            return {
                "message": f"文件不属于指定数据库。文件属于数据库: {file_db_id}，请求的数据库: {db_id}",
                "status": "failed"
            }
        
        # 执行删除操作
        knowledge_base.delete_file(db_id, file_id)
        
        return {
            "message": "文件删除成功",
            "status": "success",
            "file_id": file_id,
            "db_id": db_id,
            "filename": file_info.get("filename", "未知")
        }
    except Exception as e:
        logger.error(f"删除文件失败: {e}, {traceback.format_exc()}")
        return {"message": f"删除文件失败: {e}", "status": "failed"}



