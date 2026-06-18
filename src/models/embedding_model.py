"""
嵌入模型管理
整合packages/models/embedding.py的功能
"""

import os
import asyncio
from typing import List, Union, Optional, Dict, Any
from FlagEmbedding import FlagModel

from ..config import get_config
from ..utils.logging_config import logger


class BaseEmbeddingModel:
    """嵌入模型基类"""
    
    def __init__(self):
        self.embed_state = {}
        
    def get_dimension(self) -> Optional[int]:
        """获取向量维度"""
        if hasattr(self, "dimension"):
            return self.dimension
            
        if hasattr(self, "embed_model_fullname"):
            return get_config().embed_model_names[self.embed_model_fullname].get("dimension", None)
            
        return get_config().embed_model_names.get(self.model, {}).get("dimension", None)
        
    def encode(self, message: Union[str, List[str]]) -> List[List[float]]:
        """编码文本"""
        return self.predict(message)
        
    def encode_queries(self, queries: Union[str, List[str]]) -> List[List[float]]:
        """编码查询"""
        return self.predict(queries)
        
    async def aencode(self, message: Union[str, List[str]]) -> List[List[float]]:
        """异步编码文本"""
        return await asyncio.to_thread(self.encode, message)
        
    async def aencode_queries(self, queries: Union[str, List[str]]) -> List[List[float]]:
        """异步编码查询"""
        return await asyncio.to_thread(self.encode_queries, queries)
        
    async def abatch_encode(self, messages: List[str], batch_size: int = 20) -> List[List[float]]:
        """异步批量编码"""
        return await asyncio.to_thread(self.batch_encode, messages, batch_size)
        
    def batch_encode(self, messages: List[str], batch_size: int = 20) -> List[List[float]]:
        """批量编码"""
        logger.info(f"Batch encoding {len(messages)} messages")
        data = []
        
        # 处理进度跟踪
        if len(messages) > batch_size:
            from ..utils import hashstr
            task_id = hashstr(str(messages))
            self.embed_state[task_id] = {
                'status': 'in-progress',
                'total': len(messages),
                'progress': 0
            }
        
        # 分批处理
        for i in range(0, len(messages), batch_size):
            group_msg = messages[i:i+batch_size]
            logger.debug(f"Encoding batch {i // batch_size + 1}: {len(group_msg)} messages")
            response = self.encode(group_msg)
            data.extend(response)
            
            # 更新进度
            if len(messages) > batch_size:
                task_id = hashstr(str(messages))
                self.embed_state[task_id]['progress'] = min(i + batch_size, len(messages))
        
        # 完成处理
        if len(messages) > batch_size:
            task_id = hashstr(str(messages))
            self.embed_state[task_id]['status'] = 'completed'
            
        return data
        
    def predict(self, message: Union[str, List[str]]) -> List[List[float]]:
        """预测接口，子类需要实现"""
        raise NotImplementedError


class LocalEmbeddingModel(FlagModel, BaseEmbeddingModel):
    """本地嵌入模型"""
    
    def __init__(self, config_obj: Any, **kwargs):
        """初始化本地嵌入模型
        
        Args:
            config_obj: 配置对象
            **kwargs: 其他参数
        """
        BaseEmbeddingModel.__init__(self)
        
        # 获取模型信息
        info = config_obj.embed_model_names[config_obj.embed_model]
        
        # 确定模型路径
        self.model = config_obj.model_local_paths.get(info["name"], info.get("local_path"))
        self.model = self.model or info["name"]
        self.dimension = info["dimension"]
        self.embed_model_fullname = config_obj.embed_model
        
        # 检查本地路径
        if os.getenv("MODEL_DIR"):
            model_path = os.path.join(os.getenv("MODEL_DIR"), self.model)
            if os.path.exists(model_path):
                self.model = model_path
            else:
                logger.warning(f"Local model `{info['name']}` not found in `{model_path}`, using `{info['name']}`")
        
        logger.info(f"Loading local embedding model `{info['name']}` from `{self.model}` with device `{config_obj.device}`")
        
        # 初始化FlagModel
        FlagModel.__init__(
            self,
            self.model,
            query_instruction_for_retrieval=info.get("query_instruction", None),
            use_fp16=False,
            device=config_obj.device,
            **kwargs,
        )
        
        logger.info(f"Embedding model {info['name']} loaded successfully")


def get_embedding_model(config_obj: Optional[Any] = None) -> Optional[BaseEmbeddingModel]:
    """获取嵌入模型实例
    
    Args:
        config_obj: 配置对象，如不指定则使用全局配置
        
    Returns:
        BaseEmbeddingModel: 嵌入模型实例，如果知识库未启用则返回None
    """
    cfg = config_obj or get_config()
    
    if not cfg.enable_knowledge_base:
        return None
        
    # 解析模型提供商和名称
    try:
        provider, model_name = cfg.embed_model.split('/', 1)
    except ValueError:
        logger.error(f"Invalid embed model format: {cfg.embed_model}")
        return None
        
    # 检查模型是否支持
    if cfg.embed_model not in cfg.embed_model_names.keys():
        logger.error(f"Unsupported embed model: {cfg.embed_model}, "
                    f"supported models: {list(cfg.embed_model_names.keys())}")
        return None
        
    logger.debug(f"Loading embedding model {cfg.embed_model}")
    
    try:
        if provider == "local":
            return LocalEmbeddingModel(cfg)
        else:
            logger.error(f"Unsupported embedding model provider: {provider}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to load embedding model {cfg.embed_model}: {e}")
        return None


__all__ = ["BaseEmbeddingModel", "LocalEmbeddingModel", "get_embedding_model"]
