"""
数据库工具模块

提供多种数据库管理功能:
- DatabaseServiceChecker: 数据库服务状态检查器
- PostgreSQLManager: PostgreSQL SQL 数据库管理器
- VectorDBManager: Milvus 向量数据库管理器
- LLMClient: 大语言模型客户端
- XMLParser: XML 解析工具

使用懒加载避免循环导入。
"""

from .logging_config import logger

__all__ = [
    # 日志
    "logger",
    # 文件处理
    "hashstr",
    "read_text_file",
    "chunk_text",
    "process_uploaded_file",
]


def __getattr__(name: str):
    """懒加载模块成员，避免循环导入"""
    
    # 数据库服务检查
    if name in ("DatabaseServiceChecker", "service_checker"):
        from .database_manager import DatabaseServiceChecker, service_checker
        if name == "DatabaseServiceChecker":
            return DatabaseServiceChecker
        return service_checker
    
    # PostgreSQL
    if name in ("PostgreSQLManager", "Base", "get_postgres_manager"):
        from .postgres_manager import PostgreSQLManager, Base, get_postgres_manager
        if name == "PostgreSQLManager":
            return PostgreSQLManager
        elif name == "Base":
            return Base
        return get_postgres_manager
    
    # 向量数据库
    if name in ("VectorDBManager", "get_vector_db_manager"):
        from .vector_db_manager import VectorDBManager, get_vector_db_manager
        if name == "VectorDBManager":
            return VectorDBManager
        return get_vector_db_manager
    
    # LLM 客户端
    if name in ("LLMClient", "LLMClientError", "get_llm_client", "clear_llm_client_cache"):
        from .llm_client import LLMClient, LLMClientError, get_llm_client, clear_llm_client_cache
        if name == "LLMClient":
            return LLMClient
        elif name == "LLMClientError":
            return LLMClientError
        elif name == "get_llm_client":
            return get_llm_client
        return clear_llm_client_cache
    
    # XML 解析 (注意：xml_parser 依赖 src.models，会导致循环导入，必须懒加载)
    if name in ("XMLParser", "XMLParseError", "parse_graph_xml", "validate_entities", "validate_relationships"):
        from .xml_parser import (
            XMLParser,
            XMLParseError,
            parse_graph_xml,
            validate_entities,
            validate_relationships,
        )
        if name == "XMLParser":
            return XMLParser
        elif name == "XMLParseError":
            return XMLParseError
        elif name == "parse_graph_xml":
            return parse_graph_xml
        elif name == "validate_entities":
            return validate_entities
        return validate_relationships

    # 文件处理
    if name in ("hashstr", "read_text_file", "chunk_text", "process_uploaded_file"):
        from .file_processor import hashstr, read_text_file, chunk_text, process_uploaded_file
        if name == "hashstr":
            return hashstr
        elif name == "read_text_file":
            return read_text_file
        elif name == "chunk_text":
            return chunk_text
        return process_uploaded_file

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
