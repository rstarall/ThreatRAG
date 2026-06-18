"""
重排序模型管理
整合packages/models/rerank_model.py的功能
"""

import os
import json
import requests
import numpy as np
from typing import List, Tuple, Union, Optional
from FlagEmbedding import FlagReranker

from ..config import get_config
from ..utils.logging_config import logger


def sigmoid(x: float) -> float:
    """Sigmoid激活函数"""
    return 1 / (1 + np.exp(-x))


class BaseReranker:
    """重排序器基类"""
    
    def compute_score(self, sentence_pairs: Tuple[str, List[str]], 
                     batch_size: int = 256, max_length: int = 512, 
                     normalize: bool = False) -> List[float]:
        """计算重排序分数
        
        Args:
            sentence_pairs: (查询, 文档列表) 元组
            batch_size: 批次大小
            max_length: 最大长度
            normalize: 是否归一化
            
        Returns:
            List[float]: 重排序分数列表
        """
        raise NotImplementedError


class LocalReranker(FlagReranker, BaseReranker):
    """本地重排序模型"""
    
    def __init__(self, config_obj, **kwargs):
        """初始化本地重排序模型
        
        Args:
            config_obj: 配置对象
            **kwargs: 其他参数
        """
        model_info = config_obj.reranker_names[config_obj.reranker]
        
        # 确定模型路径
        model_name_or_path = config_obj.model_local_paths.get(
            model_info["name"], 
            model_info.get("local_path")
        )
        model_name_or_path = model_name_or_path or model_info["name"]
        
        # 检查本地路径
        if os.getenv("MODEL_DIR"):
            local_path = os.path.join(os.getenv("MODEL_DIR"), model_name_or_path)
            if os.path.exists(local_path):
                model_name_or_path = local_path
        
        logger.info(f"Loading local reranker model {config_obj.reranker} from {model_name_or_path}")
        
        # 初始化FlagReranker
        FlagReranker.__init__(
            self, 
            model_name_or_path, 
            use_fp16=True, 
            device=config_obj.device, 
            **kwargs
        )
        
        logger.info(f"Reranker model {config_obj.reranker} loaded successfully")


class SiliconFlowReranker(BaseReranker):
    """SiliconFlow重排序模型"""
    
    def __init__(self, config_obj, **kwargs):
        """初始化SiliconFlow重排序模型
        
        Args:
            config_obj: 配置对象
            **kwargs: 其他参数
        """
        self.url = "https://api.siliconflow.cn/v1/rerank"
        self.model = config_obj.reranker_names[config_obj.reranker]["name"]
        
        # 获取API密钥
        api_key = os.getenv("SILICONFLOW_API_KEY")
        if not api_key:
            raise ValueError("SILICONFLOW_API_KEY environment variable is required")
            
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"SiliconFlow reranker initialized with model: {self.model}")
    
    def compute_score(self, sentence_pairs: Tuple[str, List[str]], 
                     batch_size: int = 256, max_length: int = 512, 
                     normalize: bool = False) -> List[float]:
        """计算重排序分数"""
        query, sentences = sentence_pairs[0], sentence_pairs[1]
        
        # 构建请求载荷
        payload = self._build_payload(query, sentences, max_length)
        
        try:
            # 发送请求
            response = requests.post(self.url, json=payload, headers=self.headers)
            response.raise_for_status()
            
            response_data = response.json()
            
            # 解析结果
            results = sorted(response_data["results"], key=lambda x: x["index"])
            all_scores = [result["relevance_score"] for result in results]
            
            # 归一化处理
            if normalize:
                all_scores = [sigmoid(score) for score in all_scores]
                
            return all_scores
            
        except Exception as e:
            logger.error(f"SiliconFlow reranker error: {e}")
            # 返回默认分数
            return [0.0] * len(sentences)
    
    def _build_payload(self, query: str, sentences: List[str], 
                      max_length: int = 512) -> dict:
        """构建API请求载荷"""
        return {
            "model": self.model,
            "query": query,
            "documents": sentences,
            "max_chunks_per_doc": max_length,
        }


def get_reranker(config_obj: Optional[object] = None) -> Optional[BaseReranker]:
    """获取重排序模型实例
    
    Args:
        config_obj: 配置对象，如不指定则使用全局配置
        
    Returns:
        BaseReranker: 重排序模型实例，如果重排序未启用则返回None
    """
    cfg = config_obj or get_config()
    
    if not cfg.enable_reranker:
        return None
        
    # 检查模型是否支持
    if cfg.reranker not in cfg.reranker_names.keys():
        logger.error(f"Unsupported reranker: {cfg.reranker}, "
                    f"supported rerankers: {list(cfg.reranker_names.keys())}")
        return None
    
    # 解析提供商和模型名称
    try:
        provider, model_name = cfg.reranker.split('/', 1)
    except ValueError:
        logger.error(f"Invalid reranker format: {cfg.reranker}")
        return None
    
    try:
        if provider == "local":
            return LocalReranker(cfg)
        elif provider == "siliconflow":
            return SiliconFlowReranker(cfg)
        else:
            logger.error(f"Unsupported reranker provider: {provider}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to load reranker {cfg.reranker}: {e}")
        return None


__all__ = ["BaseReranker", "LocalReranker", "SiliconFlowReranker", "get_reranker"]
