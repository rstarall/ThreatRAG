"""
聊天模型管理
整合packages/models/chat_model.py的功能
"""

import os
import requests
from typing import Optional, List, Dict, Any, Union
from openai import OpenAI

from ..config import get_config
from ..utils.logging_config import logger


class GeneralResponse:
    """通用响应类"""
    
    def __init__(self, content: Optional[str] = None, 
                 reasoning_content: Optional[str] = None, 
                 is_full: bool = False):
        self.content = content
        self.reasoning_content = reasoning_content
        self.is_full = is_full


class OpenAIBaseChatModel:
    """基于OpenAI API的聊天模型基类"""
    
    def __init__(self, api_key: str, base_url: str, model_name: str, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.info = kwargs
        
    def predict(self, message: Union[str, List[Dict[str, str]]], stream: bool = False) -> Union[GeneralResponse, Any]:
        """预测接口"""
        if isinstance(message, str):
            messages = [{"role": "user", "content": message}]
        else:
            messages = message
            
        if stream:
            return self._stream_response(messages)
        else:
            return self._get_response(messages)
            
    def _validate_messages(self, messages: List[Dict[str, str]]):
        """验证消息格式"""
        if not messages or not isinstance(messages, list):
            raise ValueError("Messages must be a non-empty list")
            
        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                raise ValueError(f"Message {i} must be a dict, got {type(msg)}")
            if "role" not in msg:
                raise ValueError(f"Message {i} missing 'role' field: {msg}")
            if "content" not in msg:
                raise ValueError(f"Message {i} missing 'content' field: {msg}")
            if not isinstance(msg["role"], str) or not msg["role"].strip():
                raise ValueError(f"Message {i} has invalid role: {msg['role']}")
                
    def _stream_response(self, messages: List[Dict[str, str]]):
        """流式响应"""
        self._validate_messages(messages)
        
        logger.debug(f"Sending {len(messages)} messages to API: {[m['role'] for m in messages]}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
            )
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content is not None:
                        yield GeneralResponse(content=delta.content)
                        
        except Exception as e:
            err = f"Error streaming response: {e}, URL: {self.base_url}, API Key: {self.api_key[:5]}***, Model: {self.model_name}"
            logger.error(err)
            raise Exception(err)
            
    def _get_response(self, messages: List[Dict[str, str]]) -> GeneralResponse:
        """获取完整响应"""
        self._validate_messages(messages)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=False,
            )
            return GeneralResponse(content=response.choices[0].message.content, is_full=True)
            
        except Exception as e:
            err = f"Error getting response: {e}, URL: {self.base_url}, API Key: {self.api_key[:5]}***, Model: {self.model_name}"
            logger.error(err)
            raise Exception(err)
            
    def get_models(self) -> List[str]:
        """获取可用模型列表"""
        try:
            response = self.client.models.list(extra_query={"type": "text"})
            return [model.id for model in response.data]
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return []


class DeepSeekChatModel(OpenAIBaseChatModel):
    """DeepSeek聊天模型"""
    
    def __init__(self, model_name: Optional[str] = None):
        model_name = model_name or "deepseek-chat"
        api_key = os.getenv("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
        
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
            
        logger.info(f"DeepSeek model: {model_name}, base_url: {base_url}")
        super().__init__(api_key=api_key, base_url=base_url, model_name=model_name)


class SiliconFlowChatModel(OpenAIBaseChatModel):
    """SiliconFlow聊天模型"""
    
    def __init__(self, model_name: Optional[str] = None):
        model_name = model_name or "deepseek-ai/DeepSeek-V3"
        api_key = os.getenv("SILICONFLOW_API_KEY")
        base_url = os.getenv("SILICONFLOW_API_BASE", "https://api.siliconflow.cn/v1")
        
        if not api_key:
            raise ValueError("SILICONFLOW_API_KEY environment variable is required")
            
        logger.info(f"SiliconFlow model: {model_name}, base_url: {base_url}")
        super().__init__(api_key=api_key, base_url=base_url, model_name=model_name)


def select_model(model_provider: Optional[str] = None, 
                model_name: Optional[str] = None) -> OpenAIBaseChatModel:
    """选择聊天模型
    
    Args:
        model_provider: 模型提供商，如不指定则使用配置中的默认值
        model_name: 模型名称，如不指定则使用配置中的默认值
        
    Returns:
        OpenAIBaseChatModel: 聊天模型实例
    """
    cfg = get_config()
    provider = model_provider or cfg.model_provider
    name = model_name or cfg.model_name
    
    # 检查提供商是否可用
    if provider not in cfg.available_providers:
        logger.warning(f"Model provider {provider} not available, using fallback")
        if cfg.available_providers:
            provider = cfg.available_providers[0]
        else:
            raise ValueError("No available model providers")
    
    # 检查模型名称是否在支持列表中
    provider_info = cfg.model_names.get(provider, {})
    if name not in provider_info.get("models", []):
        logger.warning(f"Model {name} not found in {provider}, using default")
        name = provider_info.get("default", "deepseek-chat")
    
    # 创建模型实例
    try:
        if provider == "deepseek":
            return DeepSeekChatModel(model_name=name)
        elif provider == "siliconflow":
            return SiliconFlowChatModel(model_name=name)
        else:
            raise ValueError(f"Unsupported model provider: {provider}")
            
    except Exception as e:
        logger.error(f"Failed to create model {provider}/{name}: {e}")
        raise


__all__ = ["GeneralResponse", "OpenAIBaseChatModel", "DeepSeekChatModel", 
           "SiliconFlowChatModel", "select_model"]
