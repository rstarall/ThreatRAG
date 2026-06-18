"""
配置管理系统
整合packages/config和根目录配置
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..utils.logging_config import logger


class SimpleConfig(dict):
    """简单配置类，支持点语法访问"""

    def __key(self, key):
        return "" if key is None else key

    def __str__(self):
        return json.dumps(self, ensure_ascii=False, indent=2)

    def __setattr__(self, key, value):
        self[self.__key(key)] = value

    def __getattr__(self, key):
        return self.get(self.__key(key))

    def __getitem__(self, key):
        return self.get(self.__key(key))

    def __setitem__(self, key, value):
        return super().__setitem__(self.__key(key), value)


class Config(SimpleConfig):
    """主配置类"""

    def __init__(self, config_file: Optional[str] = None):
        super().__init__()
        self._config_items = {}
        
        # 获取项目根目录
        self.project_root = self._get_project_root()
        
        # 配置文件路径
        if config_file:
            self.config_file = config_file
        else:
            self.config_file = os.path.join(self.project_root, "config.yaml")
            
        # 数据目录
        self.save_dir = os.path.join(self.project_root, "data")
        
        # 加载用户配置
        self.load()
        
        # 初始化模型配置（从config.yaml读取，必须在_set_defaults之前）
        self._init_model_configs()
        
        # 设置默认配置
        self._set_defaults()
        
        # 处理配置
        self._handle_config()
        
        # 从环境变量覆盖关键配置（优先级高于config.yaml）
        self._apply_env_overrides()

    def _get_project_root(self) -> str:
        """获取项目根目录"""
        current_path = Path(__file__).resolve()
        root_indicators = ['.git', 'requirements.txt', 'config.yaml', 'main.py']
        
        for parent in current_path.parents:
            if any((parent / indicator).exists() for indicator in root_indicators):
                return str(parent)
        
        return str(current_path.parent.parent.parent)

    def _init_model_configs(self):
        """初始化模型配置（从config.yaml读取）"""
        self.model_names = self.get("model_names", {})
        self.embed_model_names = self.get("embed_model_info", {})
        self.reranker_names = self.get("reranker_list", {})
        
        if not self.model_names:
            logger.warning("model_names not found in config, using defaults")
            self._set_default_models()
        if not self.embed_model_names:
            logger.warning("embed_model_info not found in config")
        if not self.reranker_names:
            logger.warning("reranker_list not found in config")

    def _set_default_models(self):
        """设置默认模型配置"""
        self.model_names = {
            "deepseek": {
                "models": ["deepseek-chat"],
                "default": "deepseek-chat",
                "env": ["DEEPSEEK_API_KEY"]
            },
            "siliconflow": {
                "models": ["deepseek-ai/DeepSeek-V3"],
                "default": "deepseek-ai/DeepSeek-V3",
                "env": ["SILICONFLOW_API_KEY"]
            }
        }
        
        self.embed_model_names = {
            "siliconflow/BAAI/bge-m3": "BAAI/bge-m3",
            "local/BAAI/bge-m3": "BAAI/bge-m3"
        }
        
        self.reranker_names = {
            "siliconflow/BAAI/bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3",
            "local/BAAI/bge-m3": "BAAI/bge-m3"
        }

    def _set_defaults(self):
        """设置默认配置项"""
        # 功能开关
        self.add_item("enable_reranker", default=True, des="是否开启重排序")
        self.add_item("enable_knowledge_base", default=True, des="是否开启知识库")
        self.add_item("enable_knowledge_graph", default=True, des="是否开启知识图谱")
        self.add_item("enable_web_search", default=False, des="是否开启网页搜索")
        
        # 查询配置
        self.add_item("use_rewrite_query", default="on", des="重写查询", choices=["off", "on", "hyde"])
        
        # 模型配置（model_names在load后由_init_model_configs初始化）
        model_providers = list(self.model_names.keys()) if self.model_names else ["siliconflow", "deepseek"]
        self.add_item("model_provider", default="siliconflow", des="模型提供商", 
                     choices=model_providers)
        self.add_item("model_name", default="deepseek-ai/DeepSeek-V3", des="模型名称")
        
        # 嵌入模型配置
        self.add_item("embed_model", default="local/BAAI/bge-m3", des="嵌入模型")
        self.add_item("reranker", default="local/BAAI/bge-m3", des="重排序模型")
        self.add_item("model_local_paths", default={}, des="本地模型路径")
        
        # 设备配置
        self.add_item("device", default="cuda", des="设备", choices=["cpu", "cuda"])
        
        # 服务器配置
        self.add_item("fastapi_server", default={
            "host": "localhost",
            "port": 8000
        }, des="FastAPI服务器配置")
        
        # 数据库配置
        self.add_item("milvus", default={
            "auto_start": True,
            "host": "127.0.0.1",
            "port": 19530,
            "data_dir": "./milvus_lite"
        }, des="Milvus配置")
        
        self.add_item("neo4j", default={
            "auto_start": False,
            "host": "127.0.0.1",
            "port": 7687,
            "http_port": 7474,
            "data_dir": "./neo4j_data",
            "index_interval": 600,
            "index_batch_size": 200,
            "auto_index": True
        }, des="Neo4j配置")

        self.add_item("postgres", default={
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "12345678",
            "database": "knowledge_db"
        }, des="PostgreSQL配置")

    def add_item(self, key: str, default: Any, des: str = None, choices: List[str] = None):
        """添加配置项"""
        self.__setattr__(key, default)
        self._config_items[key] = {
            "default": default,
            "des": des,
            "choices": choices
        }

    def load(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            logger.warning(f"Config file {self.config_file} not found, using defaults")
            return
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            if config_data:
                self.update(config_data)
                logger.info(f"Loaded config from {self.config_file}")
            else:
                logger.warning(f"Config file {self.config_file} is empty")
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def _apply_env_overrides(self):
        """从环境变量覆盖关键配置（优先级高于config.yaml）"""
        try:
            milvus_host = os.getenv("MILVUS_HOST")
            milvus_port = os.getenv("MILVUS_PORT")
            if milvus_host:
                self.milvus["host"] = milvus_host
            if milvus_port:
                self.milvus["port"] = int(milvus_port)

            neo4j_url = os.getenv("NEO4J_URL")
            neo4j_host = os.getenv("NEO4J_HOST")
            neo4j_port = os.getenv("NEO4J_PORT")
            if neo4j_url:
                try:
                    # bolt://host:port
                    url_no_scheme = neo4j_url.split("//", 1)[1]
                    host_part, port_part = url_no_scheme.rsplit(":", 1)
                    self.neo4j["host"] = host_part
                    self.neo4j["port"] = int(port_part)
                except Exception:
                    pass
            if neo4j_host:
                self.neo4j["host"] = neo4j_host
            if neo4j_port:
                self.neo4j["port"] = int(neo4j_port)

            # PostgreSQL 环境变量覆盖
            pg_host = os.getenv("POSTGRES_HOST")
            pg_port = os.getenv("POSTGRES_PORT")
            pg_user = os.getenv("POSTGRES_USER")
            pg_password = os.getenv("POSTGRES_PASSWORD")
            pg_database = os.getenv("POSTGRES_DB")
            if pg_host:
                self.postgres["host"] = pg_host
            if pg_port:
                self.postgres["port"] = int(pg_port)
            if pg_user:
                self.postgres["user"] = pg_user
            if pg_password:
                self.postgres["password"] = pg_password
            if pg_database:
                self.postgres["database"] = pg_database
        except Exception as e:
            logger.warning(f"Failed to apply env overrides: {e}")

    def save(self):
        """保存配置文件"""
        try:
            config_dict = {k: v for k, v in self.items() 
                          if not k.startswith('_') and k not in ['model_names', 'embed_model_names', 'reranker_names']}
                          
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True, indent=2)
                
            logger.info(f"Saved config to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def _handle_config(self):
        """处理配置后的逻辑"""
        # 检查模型提供商
        if self.model_provider not in self.model_names:
            logger.warning(f"Model provider {self.model_provider} not supported, using siliconflow")
            self.model_provider = "siliconflow"
            
        # 检查模型名称
        provider_info = self.model_names.get(self.model_provider, {})
        if self.model_name not in provider_info.get("models", []):
            logger.warning(f"Model {self.model_name} not found, using default")
            self.model_name = provider_info.get("default", "deepseek-ai/DeepSeek-V3")
        
        # 检查环境变量
        self.model_provider_status = {}
        for provider in self.model_names:
            env_vars = self.model_names[provider].get("env", [])
            self.model_provider_status[provider] = all(os.getenv(var) for var in env_vars)
        
        # 检查可用的模型提供商
        self.available_providers = [k for k, v in self.model_provider_status.items() if v]
        
        if not self.available_providers:
            logger.error("No available model providers! Please check your environment variables.")
        
        # 检查Web搜索
        if os.getenv("TAVILY_API_KEY"):
            self.enable_web_search = True

    def __dict__(self):
        """返回配置字典，排除内部属性"""
        blocklist = [
            "_config_items", "model_names", "embed_model_names", "reranker_names",
            "model_provider_status", "available_providers", "project_root", "config_file"
        ]
        return {k: v for k, v in self.items() if k not in blocklist}


# 全局配置实例（延迟初始化）
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例（单例模式）
    
    Returns:
        Config: 全局配置实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


# 为了兼容旧代码，提供模块级 config（实际调用 get_config()）
class _ConfigWrapper:
    """配置包装器，将所有属性访问代理到实际的 Config 实例"""
    
    def __getattr__(self, name):
        return getattr(get_config(), name)
    
    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            setattr(get_config(), name, value)
    
    def __getitem__(self, key):
        return get_config()[key]
    
    def __setitem__(self, key, value):
        get_config()[key] = value


config = _ConfigWrapper()

__all__ = ["Config", "config", "get_config"]
