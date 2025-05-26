from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, JSONLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate

# 如果用本地embedding模型（推荐）：
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import time
import threading
from typing import List, Tuple
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
    def query_vector_database(self, query: str, filter: dict = None) -> List[Document]:
        """查询向量数据库
           使用相似度搜索获取文档列表
           默认的嵌入模型是bge-m3
        参数:
            query: 查询文本
            filter: 过滤条件，如 {"source": "filename.pdf"}
        返回:
            docs: 文档列表
        """
        if filter:
            # 检索并过滤
            docs = self.vector_store.similarity_search(query, k=10)  # 获取较多结果，以便过滤后仍有足够的文档
            filtered_docs = []
            for doc in docs:
                match = True
                for key, value in filter.items():
                    if key not in doc.metadata or doc.metadata[key] != value:
                        match = False
                        break
                
                if match:
                    filtered_docs.append(doc)
            
            # 如果过滤后的结果少于3个，返回前3个，否则返回过滤后的结果
            return filtered_docs[:3] if len(filtered_docs) > 3 else filtered_docs
        else:
            # 常规检索
            return self.vector_store.similarity_search(query)
    # 自动更新向量库的线程函数
    def _auto_update_vector_store(self):
        """每分钟自动检查并更新向量数据库"""
        while not self.stop_update_thread:
            try:
                print("自动检查新文档...")
                has_update, update_files = self.has_update_files(self.data_dir)
                if has_update:
                    print("检测到有更新文档，开始更新向量数据库...")
                    self.process_and_update_documents(update_files, self.file_uploads_dir, self.file_chunks_dir, self.index_path)
                # 等待1分钟
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
    
    # 判断是否有更新的文件
    def has_update_files(self, data_path: str) -> Tuple[bool, List]:
        """判断是否有更新的文件"""
        # 检查file_update.json文件
        update_file_path = os.path.join(data_path, "file_update.json")
        if os.path.exists(update_file_path):
            try:
                with open(update_file_path, 'r', encoding='utf-8') as f:
                    update_files = json.load(f)
                    # 如果数组不为空，表示有更新
                    return len(update_files) > 0, update_files
            except Exception as e:
                return False, []
        return False, []
    
    #更新的文档在列表中移除并添加到已存在的文档列表中
    def remove_update_files(self, new_update_files: List):
        """从更新列表中移除并添加到已存在的文档列表中"""
        update_file_path = os.path.join(self.data_dir, "file_update.json")
        exist_file_path = os.path.join(self.data_dir, "file_exist.json")
        exist_files = []
        update_files = []
        if os.path.exists(exist_file_path) and os.path.exists(update_file_path):
            with open(exist_file_path, 'r', encoding='utf-8') as f:
                exist_files = json.load(f)
            with open(update_file_path, 'r', encoding='utf-8') as f:
                update_files = json.load(f)
        for file in new_update_files:
            if file in update_files:
                update_files.remove(file)
                exist_files.append(file)
                print(f"移除更新文件: {file}")
            else:
                exist_files.append(file)
                print(f"添加新文件: {file}")
        #去重
        update_files = list(set(update_files))
        exist_files = list(set(exist_files))
        # 保存更新文件列表
        with open(exist_file_path, 'w', encoding='utf-8') as f:
            json.dump(exist_files, f)
        with open(update_file_path, 'w', encoding='utf-8') as f:
            json.dump(update_files, f)
        return exist_files, update_files
                
    
    # 处理文档
    def process_documents(self,update_files: List, data_path: str) -> Tuple[List, List]:
        """加载文件夹中的文档，进行文本分割，并保存分割后的文本
        
        param:
            update_files: 更新文件列表
            data_path: 文件夹路径
        return:
            update_file_list: 更新文件列表
            split_docs: 分割后的文本列表
        """
        
        documents = []
        update_file_list = []
        # 遍历data_path中的文件，检查是否在update_files列表中
        supported_extensions = [".pdf", ".json", ".txt", ".docx"]
        for root, _, files in os.walk(data_path):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                
                # 检查文件是否在更新列表中且扩展名受支持
                if file in update_files and file_ext in supported_extensions:
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
                        update_file_list.append(file)
                        print(f"已加载更新文件: {file}")
                    except Exception as e:
                        print(f"加载文件 {file} 时出错: {str(e)}")
        
        if not documents:
            print(f"在更新列表中未找到有效文档")
            return update_file_list, []

        # 分割文本
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            length_function=len,
            is_separator_regex=False,
        )
        split_docs = text_splitter.split_documents(documents)
        
        return update_file_list, split_docs
    
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
    def process_and_update_documents(self,update_files: List, data_path: str, chunk_path: str, index_path: str):
        """处理新文档，保存分块，并更新向量数据库"""

        
        # 处理文档
        update_file_list, new_split_docs = self.process_documents(update_files, data_path)
        print(f"更新的文件队列:{update_file_list}")
        # 保存分块
        self.save_split_docs(new_split_docs, chunk_path)
        
        self.remove_update_files(update_file_list)
        
        # 更新向量数据库
        if new_split_docs:
            print(f"正在添加 {len(new_split_docs)} 个新文档块到向量数据库...")
            self.vector_store.add_documents(new_split_docs)
            self.vector_store.save_local(index_path)
            print("数据库更新完成！")
        else:
            print("未检测到新文档，无需更新")
        
        return new_split_docs

    # 修改后的向量数据库创建/加载函数
    def process_and_save_split_texts(self, data_path: str = "../data/file_uploads", chunk_path: str = "../data/file_chunks"):
        """加载文件夹，进行文本分割，并保存分割后的文本"""
        update_file_list, split_docs = self.process_documents(data_path)
        self.save_split_docs(split_docs, chunk_path)
        self.remove_update_files(update_file_list)
        return split_docs

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
            new_file_list = self.load_documents()
            
            # 检查文档是否为空
            if not new_file_list:
                print("警告：没有找到任何文档！请确保目录中有PDF、TXT、JSON或DOCX文件。")
                return vector_store
                            
            #分割文本
            update_file_list, split_docs = self.process_documents(new_file_list,self.file_uploads_dir)
            #保存分块
            self.save_split_docs(split_docs, self.file_chunks_dir)
            #移除更新文件
            self.remove_update_files(update_file_list)
            


            print(f"创建向量数据库，包含 {len(split_docs)} 个文档块...")           
            # 创建向量数据库
            vector_store = FAISS.from_documents(
                documents=split_docs,
                embedding=self.embeddings
            )
            vector_store.save_local(index_path)
            return vector_store

    # 新增动态更新函数
    def update_vector_store(self, new_docs_path: str, index_path: str = "../data/faiss_index"):
        """动态更新现有向量数据库"""
        return self.process_and_update_documents(new_docs_path, self.file_chunks_dir, index_path)
