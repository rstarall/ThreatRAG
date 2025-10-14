import imp
import time
import random
import os
from pathlib import Path
from .logging_config import logger
from .bm25 import AbstractBM25
from .query_preprocessor import QueryPreprocessor

def is_text_pdf(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    if total_pages == 0:
        return False

    text_pages = 0
    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        text = page.get_text()
        if text.strip():  # 检查是否有文本内容
            text_pages += 1

    # 计算有文本内容的页面比例
    text_ratio = text_pages / total_pages
    # 如果超过50%的页面有文本内容，则认为是文本PDF
    return text_ratio > 0.5

def hashstr(input_string, length=8, with_salt=False):
    import hashlib
    # 添加时间戳作为干扰
    if with_salt:
        input_string += str(time.time() + random.random())

    hash = hashlib.md5(str(input_string).encode()).hexdigest()
    return hash[:length]


def get_project_root():
    """
    获取项目根目录路径
    通过查找包含特定标识文件的目录来确定项目根目录
    """
    current_path = Path(__file__).resolve()

    # 从当前文件向上查找，直到找到项目根目录的标识
    # 项目根目录应该包含这些文件之一：.git, requirements.txt, pyproject.toml, setup.py
    root_indicators = ['.git', 'requirements.txt', 'pyproject.toml', 'setup.py', 'README.md']

    for parent in current_path.parents:
        if any((parent / indicator).exists() for indicator in root_indicators):
            return str(parent)

    # 如果没有找到标识文件，返回当前文件的上两级目录（packages的父目录）
    return str(current_path.parent.parent.parent)


def get_docker_safe_url(base_url):
    if os.getenv("RUNNING_IN_DOCKER") == "true":
        # 替换所有可能的本地地址形式
        base_url = base_url.replace("http://localhost", "http://host.docker.internal")
        base_url = base_url.replace("http://127.0.0.1", "http://host.docker.internal")
        logger.info(f"Running in docker, using {base_url} as base url")
    return base_url