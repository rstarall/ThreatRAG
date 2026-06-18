"""
LLM 客户端封装
支持多种 LLM 提供商（SiliconFlow、DeepSeek 等），用于调用大语言模型 API。
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps

from .logging_config import logger


class LLMClientError(Exception):
    """LLM 客户端异常"""
    pass


class LLMClient:
    """LLM 客户端，支持多种提供商"""
    
    # 支持的提供商及其默认端点
    PROVIDER_ENDPOINTS = {
        "siliconflow": "https://api.siliconflow.cn/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "openai": "https://api.openai.com/v1/chat/completions",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    }
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        stream_callback: Optional[Callable[[str], None]] = None,
    ):
        """初始化 LLM 客户端
        
        Args:
            provider: 提供商名称 (siliconflow/deepseek/openai/zhipu/qwen)
            api_key: API 密钥，默认从环境变量获取
            model_name: 模型名称
            base_url: 自定义 API 端点
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            stream_callback: 流式输出的回调函数
        """
        from ..config import get_config
        cfg = get_config()
        
        self.provider = provider or cfg.model_provider
        self.api_key = api_key or self._get_api_key()
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.stream_callback = stream_callback
        
        # 设置 base_url
        if base_url:
            self.base_url = base_url.rstrip("/")
        elif hasattr(cfg, "model_names") and self.provider in cfg.model_names:
            # 如果配置中有自定义端点，使用配置的端点
            provider_info = cfg.model_names[self.provider]
            if "base_url" in provider_info:
                self.base_url = provider_info["base_url"].rstrip("/")
            else:
                self.base_url = self.PROVIDER_ENDPOINTS.get(self.provider, "")
        else:
            self.base_url = self.PROVIDER_ENDPOINTS.get(self.provider, "")
        
        # 设置模型名称
        if model_name:
            self.model_name = model_name
        elif hasattr(cfg, "model_names") and self.provider in cfg.model_names:
            self.model_name = cfg.model_names[self.provider].get("default", "gpt-4")
        else:
            self.model_name = "gpt-4"
        
        self._session = None
        
        if not self.api_key:
            logger.warning(f"No API key found for provider '{self.provider}', LLM calls may fail")
    
    def _get_api_key(self) -> Optional[str]:
        """获取 API 密钥"""
        from ..config import get_config
        cfg = get_config()
        
        # 按优先级尝试不同的环境变量
        env_vars = [
            f"{self.provider.upper()}_API_KEY",
            "API_KEY",
            "SILICONFLOW_API_KEY",
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
        ]
        
        for var in env_vars:
            key = os.getenv(var)
            if key:
                return key
        
        # 尝试从配置获取
        try:
            if hasattr(cfg, "model_names") and self.provider in cfg.model_names:
                env_list = cfg.model_names[self.provider].get("env", [])
                for env_var in env_list:
                    key = os.getenv(env_var)
                    if key:
                        return key
        except Exception:
            pass
        
        return None
    
    def _get_session(self):
        """获取 HTTP 会话"""
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })
        return self._session
    
    def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """发送请求到 LLM API
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            top_p: top_p 参数
            stop: 停止词列表
            stream: 是否使用流式输出
            **kwargs: 其他参数
            
        Returns:
            str 或 Dict: 如果 stream=False 返回完整响应文本，否则返回完整响应字典
            
        Raises:
            LLMClientError: 请求失败时抛出
        """
        import requests
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if top_p is not None:
            payload["top_p"] = top_p
        if stop is not None:
            payload["stop"] = stop
        
        # 添加其他参数
        payload.update(kwargs)
        
        url = f"{self.base_url}/chat/completions"
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                session = self._get_session()
                
                if stream and self.stream_callback:
                    response = session.post(
                        url,
                        json=payload,
                        timeout=self.timeout,
                        stream=True
                    )
                    response.raise_for_status()
                    
                    full_content = ""
                    for line in response.iter_lines():
                        if line:
                            line_text = line.decode('utf-8')
                            if line_text.startswith("data: "):
                                if line_text == "data: [DONE]":
                                    break
                                try:
                                    data = json.loads(line_text[6:])
                                    delta = data.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_content += content
                                        self.stream_callback(content)
                                except json.JSONDecodeError:
                                    continue
                    
                    return full_content
                else:
                    response = session.post(url, json=payload, timeout=self.timeout)
                    response.raise_for_status()
                    result = response.json()
                    
                    if "error" in result:
                        raise LLMClientError(f"API Error: {result['error']}")
                    
                    if stream:
                        # 非流式请求但要求流式，返回完整内容
                        choices = result.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
                        return ""
                    else:
                        return result
                        
            except requests.exceptions.Timeout:
                last_error = LLMClientError(f"Request timeout after {self.timeout}s")
                logger.warning(f"LLM request timeout (attempt {attempt + 1}/{self.max_retries})")
            except requests.exceptions.RequestException as e:
                last_error = LLMClientError(f"Request failed: {e}")
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
            except json.JSONDecodeError as e:
                last_error = LLMClientError(f"Failed to parse response: {e}")
                logger.warning(f"Failed to parse LLM response (attempt {attempt + 1}/{self.max_retries})")
            except Exception as e:
                last_error = LLMClientError(f"Unexpected error: {e}")
                logger.error(f"Unexpected error in LLM request: {e}")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))
        
        raise last_error or LLMClientError("Max retries exceeded")
    
    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """发送聊天请求
        
        Args:
            message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            history: 历史消息列表 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            **kwargs: 其他参数
            
        Returns:
            str: 助手回复文本
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": message})
        
        result = self._make_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs
        )
        
        if isinstance(result, dict):
            choices = result.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        
        return str(result)
    
    def chat_stream(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        history: Optional[List[Dict[str, str]]] = None,
        callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> str:
        """发送流式聊天请求
        
        Args:
            message: 用户消息
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            history: 历史消息列表
            callback: 流式输出的回调函数
            **kwargs: 其他参数
            
        Returns:
            str: 完整回复文本
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": message})
        
        if callback:
            def stream_callback(content: str):
                callback(content)
            self.stream_callback = stream_callback
        
        return self._make_request(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs
        )
    
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """补全请求（兼容旧接口）
        
        Args:
            prompt: 提示词
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数
            
        Returns:
            str: 生成的文本
        """
        return self.chat(
            message=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @staticmethod
    def load_prompt_from_file(file_path: str, **kwargs) -> str:
        """从文件加载提示词模板
        
        Args:
            file_path: 提示词文件路径
            **kwargs: 模板变量
            
        Returns:
            str: 格式化后的提示词
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template = f.read()
            
            if kwargs:
                return template.format(**kwargs)
            return template
            
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load prompt from {file_path}: {e}")
            raise


# 全局 LLM 客户端实例缓存
_llm_clients: Dict[str, LLMClient] = {}


def get_llm_client(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs
) -> LLMClient:
    """获取或创建 LLM 客户端实例
    
    Args:
    provider: 提供商名称
    model_name: 模型名称
    **kwargs: 其他参数
    
    Returns:
        LLMClient: LLM 客户端实例
    """
    from ..config import get_config
    cfg = get_config()
    
    provider = provider or cfg.model_provider
    model_name = model_name or getattr(cfg, "model_name", None)
    
    cache_key = f"{provider}:{model_name}"
    
    if cache_key not in _llm_clients:
        _llm_clients[cache_key] = LLMClient(
            provider=provider,
            model_name=model_name,
            **kwargs
        )
    
    return _llm_clients[cache_key]


def clear_llm_client_cache():
    """清除 LLM 客户端缓存"""
    global _llm_clients
    _llm_clients.clear()


__all__ = ["LLMClient", "LLMClientError", "get_llm_client", "clear_llm_client_cache"]
