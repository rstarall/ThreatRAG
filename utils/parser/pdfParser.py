from typing import Union, Dict, Any
import json
import os
from pathlib import Path

from pypdf import PdfReader
import asyncio
from concurrent.futures import ThreadPoolExecutor

from utils.parser.baseParser import BaseParser

class PDFParser(BaseParser[str]):
    def __init__(self):
        self.executor = ThreadPoolExecutor()
    
    def parse(self, pdf_path: str) -> str:
        """同步解析PDF文件，返回包含标题和内容的JSON字符串"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        result = self._extract_pdf_content(pdf_path)
        return json.dumps(result, ensure_ascii=False)
    
    async def getAndParseAsync(self, pdf_url: str) -> str:
        """
        从pdf_url下载pdf文件，并解析为包含标题和内容的JSON字符串
        """
        import aiohttp
        import tempfile
        
        # 创建临时文件来保存PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # 异步下载PDF文件
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    if response.status != 200:
                        raise Exception(f"下载PDF失败,状态码: {response.status}")
                    
                    # 将内容写入临时文件
                    content = await response.read()
                    with open(temp_path, 'wb') as f:
                        f.write(content)            
            # 解析下载的PDF文件
            result = await self.parse_async(temp_path)
            return result
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def parse_async(self, pdf_path: str) -> str:
        """异步解析PDF文件，返回包含标题和内容的JSON字符串"""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._extract_pdf_content, pdf_path)
        return json.dumps(result, ensure_ascii=False)
    
    def _extract_pdf_content(self, pdf_path: str) -> Dict[str, Any]:
        """提取PDF文件的标题和内容"""
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            
            # 尝试从文档信息中获取标题，如果不存在则使用文件名
            title = None
            if reader.metadata and hasattr(reader.metadata, 'title') and reader.metadata.title:
                title = reader.metadata.title
            
            if not title:
                title = Path(pdf_path).stem
            
            # 提取所有页面的文本内容
            content = ""
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                content += page.extract_text() + "\n"
            
            return {
                "title": title,
                "content": content.strip()
            }
