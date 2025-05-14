from typing import List
from pydantic import BaseModel
from langchain_core.documents import Document
# 将VectorDatabase类定义放在最前面，避免循环导入
class VectorDatabase:
    def __init__(self, path = None):
        self.vector_database = {}
        self.path = path

    def query_vector_database(self, query: str, filter: dict = None) -> List[Document]:
        """query vector database"""
        pass
    def load_or_create_vector_store(self, split_docs: List, index_path: str):
        """create or load vector database"""
        pass
        
    def update_vector_store(self, new_docs_path: str, index_path: str):
        """update vector database"""
        pass

# 延迟导入FaissVectorDatabase，避免循环依赖
vector_database_instance = None

def create_vector_database_instance(path = None):
    global vector_database_instance
    if vector_database_instance is None:
        from rag.vector.faiss import FaissVectorDatabase
        vector_database_instance = FaissVectorDatabase()
    return vector_database_instance

def get_vector_database_instance():
    global vector_database_instance
    if vector_database_instance is None:
        vector_database_instance = create_vector_database_instance()
    return vector_database_instance
