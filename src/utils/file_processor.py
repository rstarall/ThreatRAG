"""
文件处理工具
整合文件读取和分块功能
"""

import os
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path

from .logging_config import logger


def hashstr(text: str, with_salt: bool = False) -> str:
    """生成文本的哈希值
    
    Args:
        text: 输入文本
        with_salt: 是否添加时间戳盐值
        
    Returns:
        str: 哈希值
    """
    if with_salt:
        import time
        text = f"{text}_{int(time.time())}"
        
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def read_text_file(file_path: str) -> Optional[str]:
    """读取文本文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[str]: 文件内容，读取失败返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return None


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    """文本分块
    
    Args:
        text: 输入文本
        chunk_size: 分块大小
        overlap: 重叠大小
        
    Returns:
        List[Dict[str, Any]]: 分块结果列表
    """
    if not text or len(text) <= chunk_size:
        return [{
            "id": hashstr(text),
            "text": text,
            "metadata": {"chunk_index": 0, "total_chunks": 1}
        }]
    
    chunks = []
    start = 0
    chunk_index = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]
        
        # 尝试在句号、问号、感叹号处切分
        if end < len(text) and chunk_text.rfind('.') > chunk_size * 0.8:
            end = start + chunk_text.rfind('.') + 1
            chunk_text = text[start:end]
        elif end < len(text) and chunk_text.rfind('。') > chunk_size * 0.8:
            end = start + chunk_text.rfind('。') + 1
            chunk_text = text[start:end]
        
        chunks.append({
            "id": hashstr(f"{chunk_text}_{chunk_index}"),
            "text": chunk_text.strip(),
            "metadata": {
                "chunk_index": chunk_index,
                "start_pos": start,
                "end_pos": end
            }
        })
        
        # 计算下一个开始位置（考虑重叠）
        start = max(end - overlap, start + 1)
        chunk_index += 1
    
    # 更新总块数
    for chunk in chunks:
        chunk["metadata"]["total_chunks"] = len(chunks)
    
    return chunks


def process_uploaded_file(file_path: str, chunk_size: int = 500, 
                         overlap: int = 50) -> List[Dict[str, Any]]:
    """处理上传的文件
    
    Args:
        file_path: 文件路径
        chunk_size: 分块大小
        overlap: 重叠大小
        
    Returns:
        List[Dict[str, Any]]: 处理后的文档块列表
    """
    # 读取文件内容
    content = read_text_file(file_path)
    if not content:
        return []
    
    # 分块处理
    chunks = chunk_text(content, chunk_size, overlap)
    
    # 添加文件元数据
    file_name = Path(file_path).name
    for chunk in chunks:
        chunk["metadata"].update({
            "filename": file_name,
            "file_path": file_path,
            "file_size": len(content)
        })
    
    return chunks


__all__ = ["hashstr", "read_text_file", "chunk_text", "process_uploaded_file"]
