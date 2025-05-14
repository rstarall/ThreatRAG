# 更新后的模块导入（基于网页2、网页3、网页16的架构调整）
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import RetrievalQA  # 使用RetrievalQA替代create_retrieval_chain
from langchain_openai import ChatOpenAI
# 如果用本地embedding模型（推荐）：
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
from rag.vector.faiss import FaissVectorDatabase

class RAGService:
    def __init__(self):
        self.vector_database = FaissVectorDatabase()
        self.embedding_model = HuggingFaceEmbeddings(model_name="../models/embedding_model/bge-m3")
        self.llm_model = self._init_llm()

    # 新增向量数据库初始化方法（网页11最佳实践）
    def _init_vector_db(self):
        return FAISS.from_documents(
            documents=self._load_documents(),
            embedding=self.embedding_model,
            distance_strategy="COSINE"  # 明确指定相似度算法
        )
    
    # 文档加载与处理流程（整合网页6、网页8的分割策略）
    def _load_documents(self):
        loader = DirectoryLoader("data/", glob="**/*.pdf", loader_cls=PyPDFLoader)
        raw_docs = loader.load()
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？"]  # 适配中文标点（网页6）
        )
        return splitter.split_documents(raw_docs)

    # 更新LLM初始化（网页20的千帆平台集成模式）
    def _init_llm(self):
        return ChatOpenAI(
            model=os.getenv("BASE_MODEL"),  # 推荐国产模型（网页3）
            api_base=os.getenv("API_BASE"),
            api_key=os.getenv("API_KEY"),
            temperature=0.3,  # 降低随机性
            max_tokens=2048,
            model_kwargs={"top_p": 0.9}
        )

    # 使用RetrievalQA重构检索链
    def init_rag_chain(self):
        # 创建提示模板（网页12的模板设计）
        prompt_template = """
        系统指令：你是一个专业的中文问答助手，请基于以下上下文用中文回答：
        <上下文>{context}</上下文>
        问题：{input}
        回答要求：
        1. 使用Markdown格式
        2. 包含至少3个相关数据点
        3. 若不确定请声明「根据现有资料」"""
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        # 构建检索器（网页10的检索策略）
        retriever = self.vector_database.as_retriever(
            search_type="mmr",  # 最大边际相关性（网页10）
            search_kwargs={
                "k": 5,
                "score_threshold": 0.7,
                "fetch_k": 20
            }
        )
        
        # 使用RetrievalQA创建检索问答链
        return RetrievalQA.from_chain_type(
            llm=self.llm_model,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt}
        )