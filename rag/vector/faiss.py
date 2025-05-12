from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, JSONLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate

# 如果用本地embedding模型（推荐）：
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import time
import threading
from typing import List, Tuple, Set
from rag.vector.vector_database import VectorDatabase
import json
from langchain_core.documents import Document
class FaissVectorDatabase(VectorDatabase):
    def __init__(self, path: str = "../data/faiss_index"):
        super().__init__(path)
        
        # 设置路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.abspath(os.path.join(base_dir, "../data"))
        self.file_uploads_dir = os.path.join(self.data_dir, "file_uploads")
        self.file_chunks_dir = os.path.join(self.data_dir, "file_chunks")
        self.index_path = os.path.join(self.data_dir, "faiss_index")
        self.exist_file_path = os.path.join(self.data_dir, "file_exist.json")
        
        # 确保目录存在
        os.makedirs(self.file_uploads_dir, exist_ok=True)
        os.makedirs(self.file_chunks_dir, exist_ok=True)
        os.makedirs(self.index_path, exist_ok=True)
        
        # 设置模型
        model_path = os.path.abspath(os.path.join(base_dir, "../../models/embedding_model/bge-m3"))
        print(f"尝试加载嵌入模型：{model_path}")
        
        # 测试嵌入模型
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_path
            )
            
            # 测试嵌入生成
            test_text = "这是一个测试文本，用于验证嵌入模型是否工作正常。"
            test_embedding = self.embeddings.embed_query(test_text)
            print(f"嵌入模型测试成功，生成了长度为 {len(test_embedding)} 的向量。")
        except Exception as e:
            print(f"嵌入模型加载失败: {str(e)}")
            print("尝试使用在线模型...")
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name="BAAI/bge-m3"
                )
                test_embedding = self.embeddings.embed_query(test_text)
                print(f"在线嵌入模型测试成功。")
            except Exception as e:
                print(f"在线嵌入模型也失败: {str(e)}")
                raise ValueError("无法初始化嵌入模型，请检查网络连接和模型安装。")
        
        # 创建或加载向量存储
        self.vector_store = self.load_or_create_vector_store(self.index_path)
        
        # 启动自动更新线程
        self.stop_update_thread = False
        self.update_thread = threading.Thread(target=self._auto_update_vector_store)
        self.update_thread.daemon = True
        self.update_thread.start()
        print("已启动自动更新线程，每分钟检查一次新文档")
    def query_vector_database(self, query: str)->List[Document]:
        """查询向量数据库
           使用相似度搜索获取文档列表
           默认的嵌入模型是bge-m3
        参数:
            query: 查询文本
        返回:
            docs: 文档列表
        """
        return self.vector_store.similarity_search(query)
    # 自动更新向量库的线程函数
    def _auto_update_vector_store(self):
        """每分钟自动检查并更新向量数据库"""
        while not self.stop_update_thread:
            try:
                print("自动检查新文档...")
                new_files, deleted_files = self.check_file_changes()
                if new_files or deleted_files:
                    print(f"检测到文件变化，新增: {len(new_files)}个，删除: {len(deleted_files)}个")
                    if new_files:
                        self.process_and_update_documents(new_files)
                    # TODO: 处理已删除文件的向量数据
                # 等待60s
                time.sleep(60)
            except Exception as e:
                print(f"自动更新过程中出错: {str(e)}")
                # 出错后等待10秒再重试
                time.sleep(10)
    
    # 停止更新线程的方法
    def stop_auto_update(self):
        """停止自动更新线程"""
        self.stop_update_thread = True
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=2)
            print("自动更新线程已停止")

    # 1. 扫描本地文档
    def load_documents(self):
        """扫描本地文档
        
        返回：文件名字符串数组
        """
        # 检查目录是否存在并包含文件
        if not os.path.exists(self.file_uploads_dir) or not os.listdir(self.file_uploads_dir):
            print(f"目录 {self.file_uploads_dir} 不存在或为空")
            return []
        
        file_list = []
        for file in os.listdir(self.file_uploads_dir):
            file_path = os.path.join(self.file_uploads_dir, file)
            if os.path.isfile(file_path):
                file_list.append(file)
        
        print(f"加载了 {len(file_list)} 个文档")
        return file_list

    # 辅助函数：检查FAISS索引是否存在
    def faiss_index_exists(self, index_path: str = "../data/faiss_index") -> bool:
        """检查本地是否存在FAISS索引文件"""
        required_files = ["index.faiss", "index.pkl"]
        return all(os.path.exists(os.path.join(index_path, f)) for f in required_files)
    
    # 检查文件变化
    def check_file_changes(self) -> Tuple[List[str], List[str]]:
        """检查文件变化，返回新文件和已删除文件列表"""
        # 获取当前文件列表
        current_files = set(self.load_documents())
        
        # 读取已存在文件列表
        exist_files = set()
        if os.path.exists(self.exist_file_path):
            try:
                with open(self.exist_file_path, 'r', encoding='utf-8') as f:
                    exist_files = set(json.load(f))
            except Exception as e:
                print(f"读取已存在文件列表出错: {str(e)}")
        
        # 计算新文件和已删除文件
        new_files = list(current_files - exist_files)
        deleted_files = list(exist_files - current_files)
        
        # 更新已存在文件列表
        if new_files or deleted_files:
            updated_exist_files = list(current_files)
            with open(self.exist_file_path, 'w', encoding='utf-8') as f:
                json.dump(updated_exist_files, f, ensure_ascii=False)
            print(f"已更新文件列表: 总计{len(updated_exist_files)}个文件")
        
        return new_files, deleted_files
    
    # 处理文档
    def process_documents(self, file_list: List[str], data_path: str) -> Tuple[List, List]:
        """加载文件夹中的文档，进行文本分割，并保存分割后的文本
        
        param:
            file_list: 文件列表
            data_path: 文件夹路径
        return:
            processed_files: 处理成功的文件列表
            split_docs: 分割后的文本列表
        """
        
        documents = []
        processed_files = []
        # 遍历data_path中的文件，检查是否在file_list列表中
        supported_extensions = [".pdf", ".json", ".txt", ".docx"]
        for root, _, files in os.walk(data_path):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                
                # 检查文件是否在列表中且扩展名受支持
                if file in file_list and file_ext in supported_extensions:
                    try:
                        file_path = os.path.join(root, file)
                        # 根据文件类型选择合适的加载器
                        if file_ext == ".pdf":
                            loader = PyPDFLoader(file_path)
                        elif file_ext == ".json":
                            loader = JSONLoader(file_path,encoding="utf-8")
                        elif file_ext == ".txt":
                            loader = TextLoader(file_path,encoding="utf-8")
                        elif file_ext == ".docx":
                            loader = Docx2txtLoader(file_path)
                            
                        # 加载文档
                        doc = loader.load()
                        documents.extend(doc)
                        processed_files.append(file)
                        print(f"已加载文件: {file}")
                    except Exception as e:
                        print(f"加载文件 {file} 时出错: {str(e)}")
        
        if not documents:
            print(f"未找到有效文档")
            return processed_files, []

        # 分割文本
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,           # 每个文本块的最大字符数
            chunk_overlap=1000,          # 相邻文本块之间重叠的字符数
            length_function=len,       # 用于计算文本长度的函数，这里用的是内置的len函数
            is_separator_regex=False,  # 分隔符是否为正则表达式，False表示不是
        )
        split_docs = text_splitter.split_documents(documents)
        
        return processed_files, split_docs
    
    #保存分块
    def save_split_docs(self, split_docs: List, chunk_path: str):
        """保存分割后的文本"""
        os.makedirs(chunk_path, exist_ok=True)
        for i, doc in enumerate(split_docs):
            base_filename = os.path.splitext(os.path.basename(doc.metadata["source"]))[0]
            chunk_filename = f"{chunk_path}/{base_filename}_chunk_{i}.txt"
            with open(chunk_filename, "w", encoding="utf-8") as f:
                f.write(doc.page_content)
            
        print(f"已保存 {len(split_docs)} 个文本块")
    
    # 处理并更新文档的统一函数
    def process_and_update_documents(self, file_list: List[str]):
        """处理新文档，保存分块，并更新向量数据库"""
        
        # 处理文档
        processed_files, new_split_docs = self.process_documents(file_list, self.file_uploads_dir)
        print(f"处理的文件: {processed_files}")
        
        # 保存分块
        if new_split_docs:
            self.save_split_docs(new_split_docs, self.file_chunks_dir)
            
            # 更新向量数据库
            print(f"正在添加 {len(new_split_docs)} 个新文档块到向量数据库...")
            self.vector_store.add_documents(new_split_docs)
            self.vector_store.save_local(self.index_path)
            print("数据库更新完成！")
        else:
            print("未处理到有效文档，无需更新")
        
        return new_split_docs

    # 修改后的向量数据库创建/加载函数
    def load_or_create_vector_store(self, index_path: str = "../data/faiss_index"):
        """智能创建或加载向量数据库"""

        if self.faiss_index_exists(index_path):
            print("检测到已有向量数据库，正在加载...")
            return FAISS.load_local(
                folder_path=index_path,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            print("创建新向量数据库...")
            # 加载文档
            file_list = self.load_documents()
            
            # 检查文档是否为空
            if not file_list:
                print("警告：没有找到任何文档！请确保目录中有PDF、TXT、JSON或DOCX文件。")
                # 创建空的向量存储
                vector_store = FAISS.from_documents(
                    documents=[Document(page_content="初始化", metadata={"source": "faiss数据库初始化"})],
                    embedding=self.embeddings
                )
                vector_store.save_local(index_path)
                return vector_store
                            
            # 分割文本
            processed_files, split_docs = self.process_documents(file_list, self.file_uploads_dir)
            
            # 保存分块
            self.save_split_docs(split_docs, self.file_chunks_dir)
            
            # 更新已存在文件列表
            with open(self.exist_file_path, 'w', encoding='utf-8') as f:
                json.dump(processed_files, f, ensure_ascii=False)
            print(f"已初始化文件列表，包含 {len(processed_files)} 个文件")

            print(f"创建向量数据库，包含 {len(split_docs)} 个文档块...")           
            # 创建向量数据库
            vector_store = FAISS.from_documents(
                documents=split_docs,
                embedding=self.embeddings
            )
            vector_store.save_local(index_path)
            return vector_store

    # 更新向量数据库
    def update_vector_store(self, file_list: List[str]):
        """动态更新现有向量数据库"""
        return self.process_and_update_documents(file_list)
