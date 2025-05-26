from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, AsyncGenerator, List, Optional, Callable
from rag.vector.vector_database import VectorDatabase
from langchain_core.documents import Document
import os
import json
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

class StreamingCallbackHandler(BaseCallbackHandler):
    """自定义流式回调处理器，用于捕获和处理LLM生成的内容"""
    
    def __init__(self, stream_func: Callable[[str], None]):
        """初始化回调处理器
        
        Args:
            stream_func: 用于处理每个token的回调函数
        """
        super().__init__()
        self.stream_func = stream_func
        self.tokens = []
        self.current_response = ""
        
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """处理LLM生成的新token
        
        Args:
            token: 生成的token
            **kwargs: 其他参数
        """
        self.tokens.append(token)
        self.current_response += token
        # 使用JSON格式化token
        try:
            token_json = json.dumps({"type": "conversation", "data": token})
            self.stream_func(token_json)
        except:
            self.stream_func(token)
    
    def on_llm_error(self, error, **kwargs) -> None:
        """LLM生成错误时的回调
        
        Args:
            error: 错误信息
            **kwargs: 其他参数
        """
        error_json = json.dumps({"error": f"生成过程中出错: {str(error)}"})
        self.stream_func(error_json)

class StreamingConversationChain:
    """使用Chain实现流式会话，替代Agent实现"""
    
    def __init__(
        self, 
        model_name: str = "deepseek-chat",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        verbose: bool = False,
        use_rag: bool = False,
        vector_database: Optional[VectorDatabase] = None,
        use_ollama: bool = False
    ):
        """初始化流式会话链
        
        Args:
            model_name: 模型名称
            api_base: API基础URL
            api_key: API密钥
            temperature: 温度参数
            max_tokens: 最大token数
            verbose: 是否显示详细日志
            use_rag: 是否使用RAG
            vector_database: 向量数据库
            use_ollama: 是否使用ollama
        """
        self.model_name = model_name
        self.api_base = api_base 
        self.api_key = api_key 
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.verbose = verbose
        
        # 会话存储
        self.conversations = {}
        self.is_use_rag = use_rag
        self.vector_database = vector_database
        self.use_ollama = use_ollama
    
    def _query_vector_database(self, query: str) -> List[Document]:
        """使用向量数据库查询
        
        Args:
            query: 查询文本
            
        Returns:
            List[Document]: 召回的文档列表
        """
        if not self.is_use_rag or not self.vector_database:
            return []
            
        print(f"使用向量数据库查询: {query}")
        recall_docs = self.vector_database.query_vector_database(query)
        print(f"向量数据库召回文档数: {len(recall_docs)}")
        return recall_docs
    
    def _get_memory(self, conversation_id: str) -> ConversationBufferMemory:
        """获取或创建会话记忆
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            ConversationBufferMemory: 会话记忆
        """
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                input_key="question",
                output_key="output"
            )
        return self.conversations[conversation_id]
    
    def _create_llm(self, callback_handler):
        """创建LLM实例
        
        Args:
            callback_handler: 回调处理器
            
        Returns:
            ChatOpenAI or ChatOllama: LLM实例
        """
        if self.use_ollama:
            return ChatOllama(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                streaming=True,
                callbacks=[callback_handler]
            )
        else:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                streaming=True,
                callbacks=[callback_handler],
                openai_api_base=self.api_base,
                openai_api_key=self.api_key
            )
    
    def _create_chain(self, conversation_id: str, callback_handler, use_rag: bool = True):
        """创建对话链
        
        Args:
            conversation_id: 会话ID
            callback_handler: 回调处理器
            use_rag: 是否使用RAG
            
        Returns:
            LLMChain: 对话链实例
        """
        # 创建LLM实例
        llm = self._create_llm(callback_handler)
        
        # 获取会话记忆
        memory = self._get_memory(conversation_id)
        
        # 根据是否使用RAG选择不同的提示模板
        if use_rag:
            # 创建带RAG的对话提示模板
            prompt = ChatPromptTemplate.from_template("""
                你是一个专业的AI助手。请根据历史对话和检索到的信息回答用户问题。
                
                遵循以下原则：
                1. 如果检索内容中包含问题的答案，请基于这些内容回答
                2. 对于引用的内容，请明确指出信息来源
                3. 如果检索内容不足以回答问题，可以使用你的知识补充，但请明确区分
                4. 保持响应友好、专业、有帮助
                5. 直接回答问题，不要重复问题
                
                历史对话:
                {chat_history}
                                                                   
                检索召回内容:
                {rag_context}

                人类: {question}
                
                助手:
            """)
        else:
            # 创建不使用RAG的简化对话提示模板
            prompt = ChatPromptTemplate.from_template("""
                你是一个专业的AI助手。请根据历史对话回答用户问题。
                
                保持响应友好、专业、有帮助，直接回答问题，不要重复问题。
                
                历史对话:
                {chat_history}
                
                人类: {question}
                
                助手:
            """)
        
        # 创建LLMChain
        return LLMChain(
            llm=llm,
            prompt=prompt,
            verbose=self.verbose,
            memory=memory,
            output_key="output"
        )
    
    def _parse_user_input(self, message: str) -> str:
        """解析用户输入，提取实际问题
        
        Args:
            message: 用户输入
            
        Returns:
            str: 实际问题
        """
        # 尝试解析JSON
        try:
            # 尝试解析JSON字符串
            message_data = json.loads(message)
            
            # 处理不同的JSON格式
            if isinstance(message_data, dict):
                if "action" in message_data and "action_input" in message_data:
                    return message_data["action_input"]
                elif "data" in message_data:
                    data = message_data["data"]
                    if isinstance(data, dict) and "action_input" in data:
                        return data["action_input"]
                    elif isinstance(data, str):
                        return data
        except:
            # 如果不是JSON或解析失败，直接返回原始消息
            pass
        
        return message
    
    async def get_title_from_conversation(self, conversation_id: str) -> str:
        """从会话中生成标题
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            str: 生成的会话标题
        """
        # 获取会话历史
        if conversation_id not in self.conversations:
            return conversation_id
            
        memory = self.conversations[conversation_id]
        chat_history = memory.buffer
        
        if not chat_history:
            return conversation_id
            
        # 创建LLM实例（非流式）
        if self.use_ollama:
            llm = ChatOllama(
                model=self.model_name,
                temperature=0.3,
                max_tokens=50
            )
        else:
            llm = ChatOpenAI(
                model=self.model_name,
                temperature=0.3,
                max_tokens=50,
                openai_api_base=self.api_base,
                openai_api_key=self.api_key
            )
            
        # 创建提示词
        prompt = ChatPromptTemplate.from_template("""
        根据以下对话历史，生成一个简短的会话标题（不超过10个字）。标题应该概括对话的主要内容。
        请直接返回标题文本，不要包含任何其他内容。
        
        对话历史:
        {chat_history}
        
        标题:
        """)
        
        try:
            # 调用LLM生成标题
            response = llm.invoke(prompt.format(chat_history=chat_history))
            title = response.content.strip()
            
            # 尝试解析JSON格式（如果返回的是JSON）
            try:
                title_data = json.loads(title)
                if isinstance(title_data, dict) and "title" in title_data:
                    return title_data["title"]
            except:
                pass
                
            return title if title else conversation_id
        except Exception as e:
            print(f"生成标题时出错: {str(e)}")
            return conversation_id
    
    async def get_or_create_conversation(self, conversation_id: str) -> str:
        """获取或创建会话
        
        Args:
            conversation_id: 会话ID
        """
        if conversation_id not in self.conversations:
            new_conversation_id = str(uuid.uuid4())
            self.conversations[new_conversation_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                input_key="question",
                output_key="output"
            )
            return new_conversation_id
        return conversation_id
    
    async def astream(self, message: str, conversation_id: str = None, use_rag: bool = True, file_ids: list = None) -> AsyncGenerator[str, None]:
        """异步流式生成响应
        
        Args:
            message: 用户消息
            conversation_id: 会话ID
            use_rag: 是否使用RAG
            file_ids: 文件ID列表，用于针对特定文件进行检索
            
        Yields:
            str: JSON格式的响应片段
        """
        # 解析用户输入
        user_query = self._parse_user_input(message)
        
        # 创建异步生成器
        async def token_generator():
            queue = []
            
            # 定义token处理函数
            def handle_token(token):
                queue.append(token)
            
            # 创建回调处理器
            callback_handler = StreamingCallbackHandler(handle_token)
            
            # 根据是否使用RAG选择不同的处理逻辑
            if use_rag and self.is_use_rag and self.vector_database:
                # 使用RAG功能
                # 创建带RAG的对话链
                chain = self._create_chain(conversation_id, callback_handler, use_rag=True)
                
                # 获取RAG上下文
                rag_docs = []
                
                # 如果提供了文件ID，优先对这些文件进行检索
                if file_ids and len(file_ids) > 0:
                    try:
                        # 获取文件信息
                        file_info_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/file_info.json")
                        if os.path.exists(file_info_path):
                            with open(file_info_path, 'r') as f:
                                file_info = json.load(f)
                                
                            # 遍历文件ID
                            for file_id in file_ids:
                                if file_id in file_info:
                                    # 获取文件信息
                                    original_name = file_info[file_id].get("original_name", "未知文件")
                                    file_ext = os.path.splitext(original_name)[1]
                                    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../data/file_uploads")
                                    file_path = os.path.join(upload_dir, f"{file_id}{file_ext}")
                                    
                                    if os.path.exists(file_path):
                                        # 直接从向量数据库中查询
                                        docs = self.vector_database.query_vector_database(
                                            query=user_query,
                                            filter={"source": f"{file_id}{file_ext}"}
                                        )
                                        if docs:
                                            # 添加文件元数据
                                            for doc in docs:
                                                if "filename" not in doc.metadata:
                                                    doc.metadata["filename"] = original_name
                                                if "file_id" not in doc.metadata:
                                                    doc.metadata["file_id"] = file_id
                                            rag_docs.extend(docs)
                    except Exception as e:
                        print(f"处理文件ID时出错: {str(e)}")
                
                # 如果没有通过文件ID获取到文档，则使用常规向量检索
                if not rag_docs:
                    rag_docs = self._query_vector_database(user_query)
                
                rag_context = ""
                if rag_docs:
                    rag_context = "以下是相关文档信息：\n\n"
                    for i, doc in enumerate(rag_docs, 1):
                        source = doc.metadata.get('source', '未知来源')
                        filename = doc.metadata.get('filename', os.path.basename(source) if source else '未知文件')
                        rag_context += f"[文档{i}] 来源: {filename}\n内容: {doc.page_content}\n\n"
                else:
                    rag_context = "没有找到相关文档。"
            else:
                # 不使用RAG功能，使用简化的对话链
                chain = self._create_chain(conversation_id, callback_handler, use_rag=False)
                
                # 空RAG上下文
                rag_context = ""

            try:
                # 非阻塞执行链
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    # 在线程池中运行同步代码
                    future = loop.run_in_executor(
                        executor,
                        lambda: chain.invoke({
                            "question": user_query,
                            "rag_context": rag_context
                        })
                    )
                    
                    # 等待队列中有token
                    while True:
                        # 检查队列中是否有token
                        if queue:
                            token = queue.pop(0)
                            try:
                                # 尝试解析JSON
                                token_data = json.loads(token)
                                if isinstance(token_data, dict) and "data" in token_data:
                                    yield token_data["data"]
                                else:
                                    yield token
                            except:
                                yield token
                        
                        # 检查链是否已完成
                        if future.done():
                            # 确保所有剩余token都被处理
                            while queue:
                                token = queue.pop(0)
                                try:
                                    token_data = json.loads(token)
                                    if isinstance(token_data, dict) and "data" in token_data:
                                        yield token_data["data"]
                                    else:
                                        yield token
                                except:
                                    yield token
                            break
                        
                        # 短暂等待
                        await asyncio.sleep(0.01)
                    
                    # 确保future完成
                    await future
                    
            except Exception as e:
                error_json = json.dumps({"error": f"生成过程中出错: {str(e)}"})
                yield error_json
        
        # 返回生成器
        async for token in token_generator():
            yield token
