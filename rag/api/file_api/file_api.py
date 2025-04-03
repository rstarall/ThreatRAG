import hashlib
import os
import json
from datetime import datetime
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import List, Dict
from fastapi.responses import JSONResponse
import aiofiles
from rag.api.server import fastapi_server as app

UPLOAD_DIR = "../../data/file_uploads"
FILE_INFO = "../../data/file_info.json"
file_lock = asyncio.Lock()  # 异步文件操作锁

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

def generate_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    """生成文件的SHA256哈希值"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


async def update_file_info(file_hash: str, original_name: str) -> None:
    """异步更新文件信息到JSON文件"""
    try:
        # 使用异步锁保证线程安全
        async with file_lock:
            # 读取现有数据
            data: Dict = {}
            if os.path.exists(FILE_INFO):
                async with aiofiles.open(FILE_INFO, mode='r') as f:
                    content = await f.read()
                    if content:
                        data = json.loads(content)

            # 更新数据
            data[file_hash] = {
                "original_name": original_name,
                "upload_time": datetime.now().isoformat()
            }

            # 写入更新后的数据
            async with aiofiles.open(FILE_INFO, mode='w') as f:
                await f.write(json.dumps(data, indent=2))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update file info: {str(e)}"
        )



async def save_upload_file(file: UploadFile) -> dict:
    """保存上传文件并返回文件信息"""
    try:
        contents = await file.read()
        temp_path = os.path.join(UPLOAD_DIR, file.filename)
        
        # 保存临时文件
        with open(temp_path, "wb") as f:
            f.write(contents)
        
        # 生成哈希并重命名
        file_hash = generate_file_hash(temp_path)
        filename, ext = os.path.splitext(file.filename)
        new_filename = f"{file_hash}{ext}"
        new_path = os.path.join(UPLOAD_DIR, new_filename)
        os.rename(temp_path, new_path)

        # 异步更新文件信息
        await update_file_info(file_hash, file.filename)

        return {
            "original_name": file.filename,
            "saved_name": new_filename,
            "hash": file_hash,
            "path": new_path,
            "size": len(contents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await file.close()

@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    """批量上传文件接口"""
    results = []
    for file in files:
        try:
            file_info = await save_upload_file(file)
            results.append(file_info)
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
            
    return JSONResponse(content={"files": results})

