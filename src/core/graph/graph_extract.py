"""
网络安全情报文档实体关系抽取
基于 LLM 从情报文本中抽取实体和关系，构建威胁情报知识图谱。
"""

import os
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from ...config import config
from ...utils.logging_config import logger
from ...utils.llm_client import LLMClient, get_llm_client
from ...utils.xml_parser import XMLParser, parse_graph_xml, validate_entities, validate_relationships
from ...models.graph_model import (
    Entity, Relationship, KnowledgeGraph,
    EntityType, RelationshipType, TTPLabel,
)


@dataclass
class ExtractionTask:
    """抽取任务"""
    task_id: str
    text: str
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[KnowledgeGraph] = None
    error: Optional[str] = None
    created_at: float = 0.0
    completed_at: Optional[float] = None


@dataclass
class ExtractionResult:
    """抽取结果"""
    task_id: str
    success: bool
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_xml: Optional[str] = None
    processing_time_ms: Optional[float] = None


class GraphExtractor:
    """基于 LLM 的实体关系抽取器"""

    DEFAULT_PROMPT_FILE = "src/prompts/graph_extract_prompt_cn.md"

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_file: Optional[str] = None,
        max_retries: int = 3,
        temperature: float = 0.3,
        max_tokens: int = 8192,
    ):
        """初始化抽取器

        Args:
            llm_client: LLM 客户端实例
            prompt_file: 提示词模板文件路径
            max_retries: 最大重试次数
            temperature: 生成温度
            max_tokens: 最大生成 token 数
        """
        self.llm_client = llm_client or get_llm_client()
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.prompt_template = self._load_prompt_template(prompt_file)
        self.xml_parser = XMLParser()

    def _load_prompt_template(self, prompt_file: Optional[str]) -> str:
        """加载提示词模板

        Args:
            prompt_file: 提示词文件路径

        Returns:
            str: 提示词模板内容
        """
        if prompt_file is None:
            project_root = self._get_project_root()
            prompt_file = os.path.join(project_root, self.DEFAULT_PROMPT_FILE)

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                template = f.read()
            logger.info(f"Loaded prompt template from {prompt_file}")
            return template
        except FileNotFoundError:
            logger.warning(f"Prompt file not found: {prompt_file}, using default prompt")
            return self._get_default_prompt()
        except Exception as e:
            logger.error(f"Failed to load prompt template: {e}")
            return self._get_default_prompt()

    def _get_project_root(self) -> str:
        """获取项目根目录"""
        from pathlib import Path
        current_path = Path(__file__).resolve()
        for parent in current_path.parents:
            if (parent / "config.yaml").exists() or (parent / "requirements.txt").exists():
                return str(parent)
        return str(current_path.parent.parent.parent)

    def _get_default_prompt(self) -> str:
        """获取默认提示词（备用）"""
        return """你是一个专业的网络安全威胁情报分析助手，负责从网络安全报告中提取关键实体和它们之间的关系。

请从输入的报告中提取所有相关实体和关系，以XML格式输出。

## 实体类型
- attacker: 攻击者/组织
- victim: 受害者/组织
- event: 攻击事件
- asset: 网络资产（IP、域名等）
- vul: 漏洞（CVE、CWE等）
- ioc: 沦陷指标（IP、HASH、URL等）
- tool: 攻击工具/恶意软件
- file: 文件信息
- env: 环境信息

## 关系类型
- use: 攻击者使用工具/漏洞/IoC
- trigger: 受害者触发文件/环境/IoC
- involve: 攻击事件涉及人员/组织
- target: 攻击者针对受害者/资产/环境
- has: 受害者拥有资产或环境
- exploit: 漏洞利用资产或环境缺陷
- affect: 攻击文件影响资产或环境
- related_to: 工具与漏洞/IoC/文件相关联
- belong_to: 实体归属于组织或网络资产

## MITRE ATT&CK 标签
TA0001(初始访问), TA0002(执行), TA0003(持久化), TA0004(权限提升),
TA0005(防御规避), TA0006(凭据访问), TA0007(发现), TA0008(横向移动),
TA0009(收集), TA0010(数据渗出), TA0011(命令与控制), TA0040(影响)

请以以下XML格式输出：

<Entitys>
<Entity>
<EntityId>entity_1</EntityId>
<EntityName>实体名称</EntityName>
<EntityVariantNames>
<EntityVariantName>别名1</EntityVariantName>
</EntityVariantNames>
<EntityType>类型</EntityType>
<EntitySubType>子类型</EntitySubType>
<Labels>
<Label>TA0001</Label>
</Labels>
<Times>
<Time>1</Time>
</Times>
<Properties>
<Property name="属性名">属性值</Property>
</Properties>
</Entity>
</Entitys>

<Relationships>
<Relationship>
<RelationshipId>relationship_1</RelationshipId>
<RelationshipType>关系类型</RelationshipType>
<Source>源实体名称</Source>
<Target>目标实体名称</Target>
</Relationship>
</Relationships>
"""

    def _build_prompt(self, text: str) -> str:
        """构建提示词

        Args:
            text: 输入文本

        Returns:
            str: 格式化后的提示词
        """
        return self.prompt_template.replace("{input}", text)

    def extract(
        self,
        text: str,
        task_id: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        normalize: bool = True,
    ) -> ExtractionResult:
        """同步抽取实体关系

        Args:
            text: 输入文本
            task_id: 任务 ID（由调用方生成）
            source: 文本来源
            metadata: 额外元数据
            validate: 是否验证抽取结果
            normalize: 是否规范化结果

        Returns:
            ExtractionResult: 抽取结果
        """
        import time
        start_time = time.time()

        try:
            prompt = self._build_prompt(text)
            logger.info(f"[{task_id}] Calling LLM for entity extraction...")

            raw_xml = self.llm_client.chat(
                message=prompt,
                system_prompt="你是一个专业的网络安全威胁情报分析助手。",
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            logger.info(f"[{task_id}] Parsing XML response...")
            raw_entities, raw_relationships = self.xml_parser.parse(raw_xml)

            entities = [Entity.from_dict(e) for e in raw_entities]
            relationships = [Relationship.from_dict(r) for r in raw_relationships]

            errors = []

            if validate:
                valid_entities, entity_errors = validate_entities(raw_entities)
                errors.extend(entity_errors)

                valid_rels, rel_errors = validate_relationships(raw_relationships)
                errors.extend(rel_errors)

                entities = [Entity.from_dict(e) for e in valid_entities]
                relationships = [Relationship.from_dict(r) for r in valid_rels]

            if normalize:
                entities, relationships = self._normalize_results(entities, relationships)

            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"[{task_id}] Extraction completed: "
                f"{len(entities)} entities, {len(relationships)} relationships "
                f"in {processing_time:.2f}ms"
            )

            return ExtractionResult(
                task_id=task_id,
                success=True,
                entities=entities,
                relationships=relationships,
                errors=errors,
                raw_xml=raw_xml,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"[{task_id}] Extraction failed: {e}")
            return ExtractionResult(
                task_id=task_id,
                success=False,
                errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _normalize_results(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
    ) -> tuple[List[Entity], List[Relationship]]:
        """规范化抽取结果

        Args:
            entities: 实体列表
            relationships: 关系列表

        Returns:
            Tuple[List[Entity], List[Relationship]]: 规范化后的实体和关系
        """
        name_to_id: Dict[str, str] = {}
        for entity in entities:
            name_to_id[entity.entity_name] = entity.entity_id
            for variant in entity.entity_variant_names:
                name_to_id[variant] = entity.entity_id

        for rel in relationships:
            if rel.source in name_to_id:
                rel.source_id = name_to_id[rel.source]
            if rel.target in name_to_id:
                rel.target_id = name_to_id[rel.target]

        for entity in entities:
            valid_labels = []
            for label in entity.labels:
                if TTPLabel.is_valid(label):
                    valid_labels.append(label)
                else:
                    if label.startswith("TA") and len(label) == 5:
                        try:
                            int(label[2:])
                            valid_labels.append(label)
                        except ValueError:
                            pass
            entity.labels = valid_labels if valid_labels else ["TA0001"]

        for entity in entities:
            try:
                entity.entity_type = EntityType.normalize(entity.entity_type).value
            except ValueError:
                entity.entity_type = "asset"

        for rel in relationships:
            try:
                rel.relationship_type = RelationshipType(rel.relationship_type.lower().replace(" ", "_")).value
            except ValueError:
                rel.relationship_type = "related_to"

        return entities, relationships


_extractor: Optional[GraphExtractor] = None


def get_graph_extractor() -> GraphExtractor:
    """获取全局抽取器实例

    Returns:
        GraphExtractor: 抽取器实例
    """
    global _extractor
    if _extractor is None:
        _extractor = GraphExtractor()
    return _extractor


def extract_graph_from_text(
    text: str,
    task_id: str,
    source: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ExtractionResult:
    """便捷函数：从文本抽取图谱

    Args:
        text: 输入文本
        task_id: 任务 ID（由调用方生成）
        source: 文本来源
        metadata: 额外元数据

    Returns:
        ExtractionResult: 抽取结果
    """
    extractor = get_graph_extractor()
    return extractor.extract(text=text, task_id=task_id, source=source, metadata=metadata)


__all__ = [
    "GraphExtractor",
    "ExtractionTask",
    "ExtractionResult",
    "get_graph_extractor",
    "extract_graph_from_text",
]
