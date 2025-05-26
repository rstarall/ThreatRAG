from fastapi import UploadFile, File, APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import hashlib
from datetime import datetime
import aiofiles
import json
from typing import List, Dict
from rag.vector.faiss import FaissVectorDatabase  # 你已有的类
import asyncio

upload_router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "../../data/file_uploads")
FILE_INFO = os.path.join(BASE_DIR, "../../data/file_info.json")


file_lock = asyncio.Lock()

os.makedirs(UPLOAD_DIR, exist_ok=True)

# 初始化向量数据库（只初始化一次，避免多线程重复加载模型）
vector_db = FaissVectorDatabase()

# 生成文件哈希
def generate_file_hash(file_path: str, chunk_size: int = 8192) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()

# 更新 file_info.json
async def update_file_info(file_hash: str, original_name: str) -> None:
    async with file_lock:
        data: Dict = {}
        if os.path.exists(FILE_INFO):
            async with aiofiles.open(FILE_INFO, 'r') as f:
                content = await f.read()
                if content:
                    data = json.loads(content)

        data[file_hash] = {
            "original_name": original_name,
            "upload_time": datetime.now().isoformat()
        }

        async with aiofiles.open(FILE_INFO, 'w') as f:
            await f.write(json.dumps(data, indent=2))

# 主上传接口
@upload_router.post("/upload/with_embedding")
async def upload_files_with_embedding(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
        try:
            contents = await file.read()
            temp_path = os.path.join(UPLOAD_DIR, file.filename)

            # 写入临时文件
            with open(temp_path, "wb") as f:
                f.write(contents)

            # 生成哈希并重命名
            file_hash = generate_file_hash(temp_path)
            filename, ext = os.path.splitext(file.filename)
            new_filename = f"{file_hash}{ext}"
            new_path = os.path.join(UPLOAD_DIR, new_filename)
            os.rename(temp_path, new_path)

            # 更新文件记录
            await update_file_info(file_hash, file.filename)

            # 添加到向量库
            vector_db.process_and_update_documents(
                update_files=[new_filename],
                data_path=vector_db.file_uploads_dir,
                chunk_path=vector_db.file_chunks_dir,
                index_path=vector_db.index_path
            )

            results.append({
                "filename": file.filename,
                "hash": file_hash,
                "saved_as": new_filename,
                "status": "✅ 已上传并入库"
            })

        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e),
                "status": "❌ 失败"
            })
        finally:
            await file.close()

    return JSONResponse(content={"files": results})
