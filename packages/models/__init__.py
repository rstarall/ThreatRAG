import os
import traceback
from .. import config
from ..utils.logging_config import logger
from .chat_model import OpenAIBase


def select_model(model_provider=None, model_name=None):
    """根据模型提供者选择模型"""
    model_provider = model_provider or config.model_provider
    model_info = config.model_names.get(model_provider, {})
    model_name = model_name or config.model_name or model_info.get("default", "")


    logger.info(f"Selecting model from `{model_provider}` with `{model_name}`")


    if model_provider is None:
        raise ValueError("Model provider not specified, please modify `model_provider` in `src/config/base.yaml`")

    # OpenAI 官方
    if model_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        model = OpenAIBase(
            api_key=api_key,
            base_url="https://api.openai.com/v1",
            model_name=model_name or "gpt-4o-mini",
        )
        return model
    
    # Ollama 本地模型
    if model_provider == "ollama":
        ollama_base = os.getenv("OLLAMA_API_BASE", "http://ollama:11434")
        model = OpenAIBase(
            api_key="ollama",  # Ollama 不需要真实 API Key
            base_url=f"{ollama_base}/v1",
            model_name=model_name or "llama3.1:8b",  # 默认使用 Llama 3.1
        )
        return model

    # DeepSeek
    if model_provider == "deepseek":
        from .chat_model import DeepSeek
        return DeepSeek(model_name)

    # 自定义模型
    if model_provider == "custom":
        model_info = next((x for x in config.custom_models if x["custom_id"] == model_name), None)
        if model_info is None:
            raise ValueError(f"Model {model_name} not found in custom models")

        from .chat_model import CustomModel
        return CustomModel(model_info)

    # 其他模型，默认使用OpenAIBase（兼容 OpenAI API 格式的提供商）
    try:
        model = OpenAIBase(
            api_key=os.getenv(model_info["env"][0]),
            base_url=model_info["base_url"],
            model_name=model_name,
        )
        return model
    except Exception as e:
        raise ValueError(f"Model provider {model_provider} load failed, {e} \n {traceback.format_exc()}")
