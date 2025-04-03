from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationBufferMemory, ChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, AsyncGenerator, List, Optional, Union, Callable
from rag.vector.vector_database import VectorDatabase
from langchain_core.documents import Document
import os
import sys
import uuid
import json
from rag.structs.conversation import ConversationSchema

class StreamingAgentCallbackHandler(BaseCallbackHandler):
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
        self.stream_func(token)
    
    def on_llm_end(self, response, **kwargs) -> None:
        """LLM生成结束时的回调
        
        Args:
            response: LLM响应
            **kwargs: 其他参数
        """
        pass
    
    def on_llm_error(self, error, **kwargs) -> None:
        """LLM生成错误时的回调
        
        Args:
            error: 错误信息
            **kwargs: 其他参数
        """
        self.stream_func(f"\n生成过程中出错: {str(error)}")

    def on_chain_end(self, outputs, **kwargs) -> None:
        """链执行结束时的回调
        
        Args:
            outputs: 输出
            **kwargs: 其他参数
        """
        pass
        
    def on_tool_end(self, output, **kwargs) -> None:
        """工具执行结束时的回调
        
        Args:
            output: 工具输出
            **kwargs: 其他参数
        """
        pass
        
    def on_agent_action(self, action, **kwargs) -> None:
        """代理执行动作时的回调
        
        Args:
            action: 动作
            **kwargs: 其他参数
        """
        pass

    def on_agent_finish(self, finish, **kwargs) -> None:
        """代理执行完成时的回调
        
        Args:
            finish: 完成状态
            **kwargs: 其他参数
        """
        # 如果是Final Answer，可以在这里处理
        if hasattr(finish, "return_values") and "output" in finish.return_values:
            final_answer = finish.return_values["output"]
            # 如果最终答案与当前响应不同，可以流式输出最终答案
            if final_answer != self.current_response:
                self.stream_func(f"\n最终答案: {final_answer}")

class StreamingConversationalAgent:
    """流式会话代理类，实现与LLM的流式交互"""
    
    def __init__(
        self, 
        model_name: str = "deepseek-ai/DeepSeek-V2.5",
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        verbose: bool = False,
        use_rag: bool = False,
        vector_database: Optional[VectorDatabase] = None,
        use_ollama: bool = False
    ):
        """初始化流式会话代理
        
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

    def _query_vector_database(self, query: str)->List[Document]:
        """使用向量数据库查询
        
        Args:
            query: 查询文本
        """
        print(f"使用向量数据库查询: {query}")
        recall_docs = self.vector_database.query_vector_database(query)
        print(f"向量数据库召回文档数: {len(recall_docs)}")
        # if len(recall_docs) > 0:
        #     print(f"向量数据库召回文档: {recall_docs[0].page_content}")
        return recall_docs
    
    def _get_memory(self, conversation_id: str) -> ConversationBufferMemory:
        """获取或创建会话记忆
        
        Args:
            conversation_id: 会话ID
            
        Returns:
            ConversationBufferMemory: 会话记忆
        """
        if conversation_id not in self.conversations:
            # 直接创建ConversationBufferMemory实例
            self.conversations[conversation_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="output"
            )
        return self.conversations[conversation_id]
    

    def _create_llm(self, callback_handler):
        """创建LLM实例
        
        Args:
            callback_handler: 回调处理器
        """
        if self.use_ollama:
            return ChatOllama(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                streaming=True,  # 启用流式输出
                callbacks=[callback_handler],  # 设置回调处理器
            )
        else:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                streaming=True,  # 启用流式输出
                callbacks=[callback_handler],  # 设置回调处理器
                openai_api_base=self.api_base,
                openai_api_key=self.api_key
            )
        

    def _create_agent(self, conversation_id: str, callback_handler) -> Any:
        """创建Agent实例
        
        Args:
            conversation_id: 会话ID
            callback_handler: 回调处理器
            
        Returns:
            Agent: Agent实例
        """
        # 创建LLM实例
        llm = self._create_llm(callback_handler)
        
        # 获取记忆
        memory = self._get_memory(conversation_id)
                
        # 创建工具函数，确保上下文信息被传递
        def conversation_function(input_dict):
            # 简化输入处理
            user_input = ""
            if isinstance(input_dict, str):
                user_input = input_dict
            elif isinstance(input_dict, dict) and "input" in input_dict:
                user_input = input_dict["input"]
            else:
                user_input = str(input_dict)
            
            # 检索增强
            recall_docs = []
            if self.is_use_rag:
                recall_docs = self._query_vector_database(user_input)
            
            rag_contxt = ""
            if recall_docs:
                rag_contxt = "以下是相关文档信息：\n\n"
                for i, doc in enumerate(recall_docs, 1):
                    source = doc.metadata.get('source', '未知来源')
                    rag_contxt += f"[文档{i}] 来源: {source}\n内容: {doc.page_content}\n\n"
            else:   
                rag_contxt = "没有找到相关文档。"
            
            # 直接使用messages格式调用LLM
            from langchain_core.messages import HumanMessage, SystemMessage
            
            messages = [
                SystemMessage(content="""你是一个专业的AI助手。请根据历史对话和检索到的信息回答用户问题。
                遵循以下原则：
                1. 如果检索内容中包含问题的答案，请基于这些内容回答
                2. 对于引用的内容，请明确指出信息来源
                3. 如果检索内容不足以回答问题，可以使用你的知识补充，但请明确区分
                4. 保持响应友好、专业、有帮助"""),
                HumanMessage(content=f"""
                历史对话:
                {memory.buffer}
                
                检索召回内容:
                {rag_contxt}
                
                我的问题: {user_input}
                """)
            ]
            
            return llm.invoke(messages)
        
        # 创建会话工具
        conversation_tool = Tool(
            name='对话',
            func=conversation_function,
            description='基于历史对话和检索内容回答用户问题'
        )
        
        # 初始化Agent
        return initialize_agent(
            tools=[conversation_tool],
            llm=llm,
            agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory=memory,
            verbose=self.verbose,
            handle_parsing_errors=True
        )
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
        if conversation_id== None or conversation_id not in self.conversations:
            new_conversation_id = str(uuid.uuid4())
            self.conversations[new_conversation_id] = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="output"
            )
            return new_conversation_id
        return conversation_id
    

    async def astream(self, message: str, conversation_id: str = None) -> AsyncGenerator[str, None]:
        """异步流式生成响应
        
        Args:
            message: 用户消息
            conversation_id: 会话ID
            
        Yields:
            str: 响应片段
        """
        # 创建异步生成器
        async def token_generator():
            queue = []
           
            # 定义token处理函数
            def handle_token(token):
                queue.append(token)
            
            # 创建回调处理器
            callback_handler = StreamingAgentCallbackHandler(handle_token)

            

            # 创建Agent
            agent = self._create_agent(conversation_id, callback_handler)
            
            # 运行Agent
            try:
                # 非阻塞执行Agent
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                
                # 创建执行器
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    # 在线程池中运行同步代码
                    future = loop.run_in_executor(
                        executor,
                        lambda: agent.invoke({"input": message})
                    )
                    
                    # 等待队列中有token
                    while True:
                        # 检查队列中是否有token
                        if queue:
                            token = queue.pop(0)
                            yield token
                        
                        # 检查Agent是否已完成
                        if future.done():
                            # 确保所有剩余token都被处理
                            while queue:
                                yield queue.pop(0)
                            break
                        
                        # 短暂等待
                        await asyncio.sleep(0.01)
                    
                    # 确保future完成
                    await future
                    
            except Exception as e:
                yield f"\n生成过程中出错: {str(e)}"
        
        # 返回生成器
        async for token in token_generator():
            yield token
