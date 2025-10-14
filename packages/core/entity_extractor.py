import json
import asyncio
import os
import traceback
from typing import List, Dict, Optional, Tuple, Any

from .. import config
from ..core.constant import STIX_ENTITY_TYPES
from ..utils import logger
from ..models.chat_model import CustomModel
from .prompt import PROMPTS
from dotenv import load_dotenv

load_dotenv()


class EntityExtractor:
    """STIX实体提取器
    
    用于从文本中提取STIX格式的实体和关系
    """
    
    def __init__(self, model_config: Optional[Dict] = None):
        """初始化实体提取器
        
        Args:
            model_config: 模型配置，包括name, api_base, api_key
        """
        self.model_config = model_config or {
            "name": os.getenv("MODEL_NAME"),
            "api_base": os.getenv("DASHSCOPE_BASE_URL"),
            "api_key": os.getenv("DASHSCOPE_API_KEY")
        }
        logger.info(f"实体提取模型配置: {self.model_config}")
        self.model = CustomModel(self.model_config)
        
        # 加载提示词模板
        self.system_prompt_template = PROMPTS["entity_extraction_system_prompt"]
        self.user_prompt_template = PROMPTS["entity_extraction_user_prompt"]
        self.examples = PROMPTS["entity_extraction_examples"]
        
        # 定义分隔符
        self.tuple_delimiter = PROMPTS["DEFAULT_TUPLE_DELIMITER"]
        self.record_delimiter = PROMPTS["DEFAULT_RECORD_DELIMITER"]
        self.completion_delimiter = PROMPTS["DEFAULT_COMPLETION_DELIMITER"]
    
    def prepare_prompt(self, 
                       text: str, 
                       language: str = "chinese",
                       entity_types: Optional[List[str]] = None) -> List[Dict[str, str]]:
        """准备实体提取的提示词
        
        Args:
            text: 要提取实体的文本
            language: 提取语言，默认为chinese
            entity_types: 要提取的实体类型列表，为空则提取所有类型
        
        Returns:
            格式化的提示词列表，包含系统提示词和用户提示词
        """
        # 设置实体类型过滤
        entity_types_str = ",".join(entity_types or list(STIX_ENTITY_TYPES.keys()))
        
        # 使用字符串替换而不是format，避免格式化问题
        system_prompt = self.system_prompt_template
        
        # 替换所有占位符
        system_prompt = system_prompt.replace("{examples}", "\n".join(self.examples))
        system_prompt = system_prompt.replace("{entity_types}", entity_types_str)
        system_prompt = system_prompt.replace("{input_text}", text)
        system_prompt = system_prompt.replace("{language}", language)
        system_prompt = system_prompt.replace("{tuple_delimiter}", self.tuple_delimiter)
        system_prompt = system_prompt.replace("{record_delimiter}", self.record_delimiter)
        system_prompt = system_prompt.replace("{completion_delimiter}", self.completion_delimiter)
        
        # 处理用户提示词
        user_prompt = self.user_prompt_template
        user_prompt = user_prompt.replace("{completion_delimiter}", self.completion_delimiter)
        user_prompt = user_prompt.replace("{language}", language)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    async def extract_entities(self, 
                              text: str, 
                              language: str = "chinese",
                              entity_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """从文本中提取STIX格式的实体和关系
        
        Args:
            text: 要提取实体的文本
            language: 提取语言，默认为chinese
            entity_types: 要提取的实体类型列表，为空则提取所有类型
        
        Returns:
            包含实体和关系的字典
        """
        try:
            # 准备提示词
            messages = self.prepare_prompt(text, language, entity_types)
            
            # 调用LLM进行实体提取
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,  # 使用默认执行器
                lambda: self.model.predict(messages)
            )
            
            # 添加调试日志
            logger.info(f"LLM响应内容: {response.content[:500]}...")  # 只显示前500字符
            logger.info(f"文本长度: {len(text)}, 实体类型: {entity_types}")
            
            # 解析结果
            entities, relationships = self.parse_result(response.content)
            
            return {
                "status": "success",
                "entities": entities,
                "relationships": relationships,
                "entities_count": len(entities),
                "relationships_count": len(relationships)
            }
        except Exception as e:
            logger.error(f"实体提取失败: {e}, {traceback.format_exc()}")
            return {
                "status": "failed",
                "message": f"实体提取失败: {str(e)}",
                "entities": [],
                "relationships": [],
                "entities_count": 0,
                "relationships_count": 0
            }
    
    def parse_result(self, result_text: str) -> Tuple[List[Dict], List[Dict]]:
        """解析LLM返回的结果文本，提取实体和关系
        
        Args:
            result_text: LLM返回的结果文本
            
        Returns:
            包含实体和关系的元组 (entities, relationships)
        """
        entities = []
        relationships = []
        
        logger.info(f"开始解析结果，分隔符: record='{self.record_delimiter}', tuple='{self.tuple_delimiter}'")
        logger.info(f"结果文本行数: {len(result_text.split(self.record_delimiter))}")
        
        for i, line in enumerate(result_text.split(self.record_delimiter)):
            line = line.strip()
            if not line or line == self.completion_delimiter:
                continue
                
            logger.info(f"处理第{i}行: {line[:100]}...")
            parts = line.split(self.tuple_delimiter)
            logger.info(f"分割后parts数量: {len(parts)}, 内容: {parts}")
            
            try:
                if parts[0] == "(entity":
                    # 仅输出四个属性：id, type, name, description；type 使用 STIX_ENTITY_TYPES 映射值
                    if len(parts) >= 4:
                        # parts 可能为 (entity, name, type, description, [properties])
                        # 验证和转换STIX类型
                        stix_type = self._validate_and_convert_stix_type(parts[2])

                        # 生成STIX标准ID
                        import uuid
                        stix_id = f"{stix_type}--{str(uuid.uuid4())}"

                        # 构建仅包含通用属性的实体
                        entity = {
                            "id": stix_id,
                            "type": stix_type,
                            "name": parts[1],
                            "description": parts[3] if len(parts) >= 4 else ""
                        }

                        entities.append(entity)
                        
                elif parts[0] == "(relationship":
                    # 格式: (relationship, source_entity, target_entity, relationship_type, relationship_description, relationship_properties)
                    if len(parts) >= 6:
                        # 生成STIX标准关系ID
                        import uuid
                        rel_id = f"relationship--{str(uuid.uuid4())}"
                        
                        rel = {
                            "id": rel_id,  # STIX标准关系ID
                            "type": "relationship",  # STIX关系类型
                            "source_ref": parts[1],  # 源实体引用
                            "target_ref": parts[2],  # 目标实体引用
                            "relationship_type": parts[3],  # 关系类型
                            "description": parts[4]  # 关系描述
                        }
                        
                        # 尝试解析属性JSON
                        try:
                            if parts[5].strip():
                                rel["properties"] = json.loads(parts[5])
                            else:
                                rel["properties"] = {}
                        except json.JSONDecodeError:
                            rel["properties"] = {"raw_text": parts[5]}
                            
                        relationships.append(rel)
            except Exception as e:
                logger.error(f"解析实体/关系时出错: {e}, 行: {line}")
        
        return entities, relationships
    
    def _validate_and_convert_stix_type(self, entity_type: str) -> str:
        """验证和转换实体类型为STIX标准格式
        
        Args:
            entity_type: 原始实体类型
            
        Returns:
            符合STIX标准的实体类型
        """
        if not entity_type or not isinstance(entity_type, str):
            return "other"
        
        # 清理输入
        entity_type = entity_type.strip().upper()
        
        # 直接匹配STIX_ENTITY_TYPES中的键
        if entity_type in STIX_ENTITY_TYPES:
            return STIX_ENTITY_TYPES[entity_type]
        
        # 尝试匹配STIX_ENTITY_TYPES中的值
        for key, value in STIX_ENTITY_TYPES.items():
            if entity_type == value.upper():
                return value
        
        # 模糊匹配常见变体
        type_mapping = {
            "MALWARE": "malware",
            "THREAT_ACTOR": "threat-actor", 
            "THREATACTOR": "threat-actor",
            "ATTACK_PATTERN": "attack-pattern",
            "ATTACKPATTERN": "attack-pattern",
            "INDICATOR": "indicator",
            "VULNERABILITY": "vulnerability",
            "CVE": "vulnerability",
            "FILE": "file",
            "PROCESS": "process",
            "NETWORK_TRAFFIC": "network-traffic",
            "NETWORKTRAFFIC": "network-traffic",
            "EMAIL_MESSAGE": "email-message",
            "EMAILMESSAGE": "email-message",
            "USER_ACCOUNT": "user-account",
            "USERACCOUNT": "user-account",
            "SOFTWARE": "software",
            "REPORT": "report",
            "CAMPAIGN": "campaign",
            "INTRUSION_SET": "intrusion-set",
            "INTRUSIONSET": "intrusion-set",
            "COURSE_OF_ACTION": "course-of-action",
            "COURSEOFACTION": "course-of-action",
            "COA": "course-of-action",
            "DIRECTORY": "directory",
            "REGISTRY_KEY": "registry-key",
            "REGISTRYKEY": "registry-key",
            "TTP": "ttp",
            "IP": "network-traffic",
            "IP_ADDRESS": "network-traffic",
            "IPADDRESS": "network-traffic",
            "URL": "network-traffic",
            "DOMAIN": "network-traffic",
            "HASH": "file",
            "MD5": "file",
            "SHA1": "file",
            "SHA256": "file"
        }
        
        # 尝试模糊匹配
        for key, value in type_mapping.items():
            if key in entity_type or entity_type in key:
                return value
        
        # 如果都不匹配，返回other
        logger.warning(f"未识别的实体类型: {entity_type}，将标记为other")
        return "other"
        
# 创建全局实例
entity_extractor = EntityExtractor()
