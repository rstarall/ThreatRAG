"""
XML 解析工具
用于解析 LLM 返回的 XML 格式实体关系数据。
支持容错解析，自动提取 Entitys 和 Relationships 标签内容。
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from src.models.graph_model import EntityType

from .logging_config import logger


class XMLParseError(Exception):
    """XML 解析错误"""
    pass


class XMLParser:
    """XML 解析器，专注于解析实体关系 XML"""
    
    # 实体标签映射（支持中英文和变体）
    ENTITY_TAGS = ["Entity", "entity", "实体", "ENTITY"]
    
    # 关系标签映射
    RELATIONSHIP_TAGS = ["Relationship", "relationship", "关系", "RELATIONSHIP"]
    
    # 列表标签
    ENTITY_LIST_TAGS = ["Entitys", "Entities", "entitys", "entities", "实体列表", "ENTITIES"]
    RELATIONSHIP_LIST_TAGS = ["Relationships", "relationships", "关系列表", "RELATIONSHIPS"]
    
    def __init__(self, strict: bool = False):
        """初始化 XML 解析器
        
        Args:
            strict: 是否启用严格模式（严格模式下解析失败会抛出异常）
        """
        self.strict = strict
    
    def parse(self, xml_string: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """解析 XML 字符串，提取实体和关系列表
        
        Args:
            xml_string: XML 格式字符串
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (实体列表, 关系列表)
        """
        # 预处理：清理 XML 字符串
        cleaned_xml = self._preprocess_xml(xml_string)
        
        if not cleaned_xml:
            if self.strict:
                raise XMLParseError("Empty XML content after preprocessing")
            return [], []
        
        # 尝试标准 XML 解析
        try:
            return self._parse_standard_xml(cleaned_xml)
        except Exception as e:
            logger.debug(f"Standard XML parsing failed, trying regex extraction: {e}")
        
        # 降级到正则表达式提取
        if self.strict:
            raise XMLParseError(f"Failed to parse XML: {e}")
        
        try:
            return self._parse_regex_extraction(cleaned_xml)
        except Exception as e:
            logger.error(f"Regex extraction also failed: {e}")
            return [], []
    
    def _preprocess_xml(self, xml_string: str) -> str:
        """预处理 XML 字符串
        
        Args:
            xml_string: 原始 XML 字符串
            
        Returns:
            str: 预处理后的 XML 字符串
        """
        if not xml_string:
            return ""
        
        # 移除 markdown 代码块标记
        xml_string = re.sub(r'^```xml\s*', '', xml_string, flags=re.MULTILINE)
        xml_string = re.sub(r'^```\s*$', '', xml_string, flags=re.MULTILINE)
        
        # 移除开头的 "最终输出:" 等文字
        xml_string = re.sub(r'^(?:最终输出|输出结果|Result|结果)[:：]?\s*', '', xml_string, flags=re.MULTILINE)
        
        # 移除 BOM 标记
        xml_string = xml_string.lstrip('\ufeff')
        
        # 规范化空白字符
        xml_string = re.sub(r'[\r\n\t]+', ' ', xml_string)
        
        # 移除多余的空格
        xml_string = re.sub(r'\s+', ' ', xml_string)
        
        return xml_string.strip()
    
    def _parse_standard_xml(self, xml_string: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """使用标准 XML 解析器解析
        
        Args:
            xml_string: 预处理后的 XML 字符串
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (实体列表, 关系列表)
        """
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as e:
            # 尝试修复常见的 XML 错误
            fixed_xml = self._fix_common_xml_errors(xml_string)
            try:
                root = ET.fromstring(fixed_xml)
            except ET.ParseError:
                raise XMLParseError(f"Failed to parse XML after fixes: {e}")
        
        entities = []
        relationships = []
        
        # 查找实体列表
        for tag in self.ENTITY_LIST_TAGS:
            entity_root = root.find(f".//{tag}")
            if entity_root is not None:
                entities = self._parse_entity_list(entity_root)
                break
        
        # 如果没有找到列表标签，尝试在根节点下直接查找实体
        if not entities:
            entities = self._parse_entity_list(root)
        
        # 查找关系列表
        for tag in self.RELATIONSHIP_LIST_TAGS:
            rel_root = root.find(f".//{tag}")
            if rel_root is not None:
                relationships = self._parse_relationship_list(rel_root)
                break
        
        # 如果没有找到列表标签，尝试在根节点下直接查找关系
        if not relationships:
            relationships = self._parse_relationship_list(root)
        
        return entities, relationships
    
    def _fix_common_xml_errors(self, xml_string: str) -> str:
        """修复常见的 XML 错误
        
        Args:
            xml_string: 可能有问题的 XML 字符串
            
        Returns:
            str: 修复后的 XML 字符串
        """
        # 修复未闭合的标签
        # 匹配 <Entity>...</Entity> 但可能没有正确闭合的情况
        fixed = xml_string
        
        # 移除 XML 声明前的内容
        fixed = re.sub(r'^[^<]*', '', fixed)
        
        # 尝试找到实体列表和关系列表的边界
        # 这是一个简化实现
        if '<Entitys>' in fixed and '</Entitys>' not in fixed:
            # 找到最后一个完整的 <Entity>...</Entity> 块
            pass
        
        if '<Relationships>' in fixed and '</Relationships>' not in fixed:
            # 找到最后一个完整的关系块
            pass
        
        return fixed
    
    def _parse_entity_list(self, root) -> List[Dict[str, Any]]:
        """解析实体列表
        
        Args:
            root: XML 元素
            
        Returns:
            List[Dict]: 实体字典列表
        """
        entities = []
        
        for tag in self.ENTITY_TAGS:
            for entity_elem in root.iter(tag):
                entity = self._parse_entity(entity_elem)
                if entity:
                    entities.append(entity)
        
        return entities
    
    def _parse_entity(self, entity_elem) -> Optional[Dict[str, Any]]:
        """解析单个实体
        
        Args:
            entity_elem: 实体 XML 元素
            
        Returns:
            Dict: 实体字典
        """
        def get_text(elem, tag: str, default: str = "") -> str:
            """获取子元素的文本"""
            child = elem.find(tag)
            return child.text.strip() if child is not None and child.text else default
        
        def get_all_text(elem, tag: str) -> List[str]:
            """获取所有同名子元素的文本列表"""
            texts = []
            for child in elem.findall(f"./{tag}"):
                if child.text and child.text.strip():
                    texts.append(child.text.strip())
            return texts
        
        def get_properties(elem) -> Dict[str, str]:
            """获取属性字典"""
            props = {}
            props_elem = elem.find("Properties")
            if props_elem is not None:
                for prop in props_elem.findall("Property"):
                    name = prop.get("name", "")
                    value = prop.text.strip() if prop.text else ""
                    if name:
                        props[name] = value
            return props
        
        entity = {
            "entity_id": get_text(entity_elem, "EntityId"),
            "entity_name": get_text(entity_elem, "EntityName"),
            "entity_variant_names": get_all_text(entity_elem, "EntityVariantName"),
            "entity_type": get_text(entity_elem, "EntityType"),
            "entity_sub_type": get_text(entity_elem, "EntitySubType"),
            "labels": get_all_text(entity_elem, "Label"),
            "times": get_all_text(entity_elem, "Time"),
            "properties": get_properties(entity_elem),
        }
        
        # 如果有关键字段，返回实体
        if entity["entity_name"] or entity["entity_id"]:
            return entity
        
        return None
    
    def _parse_relationship_list(self, root) -> List[Dict[str, Any]]:
        """解析关系列表
        
        Args:
            root: XML 元素
            
        Returns:
            List[Dict]: 关系字典列表
        """
        relationships = []
        
        for tag in self.RELATIONSHIP_TAGS:
            for rel_elem in root.iter(tag):
                relationship = self._parse_relationship(rel_elem)
                if relationship:
                    relationships.append(relationship)
        
        return relationships
    
    def _parse_relationship(self, rel_elem) -> Optional[Dict[str, Any]]:
        """解析单个关系
        
        Args:
            rel_elem: 关系 XML 元素
            
        Returns:
            Dict: 关系字典
        """
        def get_text(elem, tag: str, default: str = "") -> str:
            """获取子元素的文本"""
            child = elem.find(tag)
            return child.text.strip() if child is not None and child.text else default
        
        relationship = {
            "relationship_id": get_text(rel_elem, "RelationshipId"),
            "relationship_type": get_text(rel_elem, "RelationshipType").lower(),
            "source": get_text(rel_elem, "Source"),
            "target": get_text(rel_elem, "Target"),
        }
        
        # 如果有关键字段，返回关系
        if relationship["source"] and relationship["target"]:
            return relationship
        
        return None
    
    def _parse_regex_extraction(self, xml_string: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """使用正则表达式提取实体和关系（降级方案）
        
        Args:
            xml_string: XML 字符串
            
        Returns:
            Tuple[List[Dict], List[Dict]]: (实体列表, 关系列表)
        """
        entities = []
        relationships = []
        
        # 提取实体
        entity_patterns = [
            r'<Entity[^>]*>.*?</Entity>',
            r'<entity[^>]*>.*?</entity>',
        ]
        
        for pattern in entity_patterns:
            for match in re.finditer(pattern, xml_string, re.DOTALL):
                entity_xml = match.group()
                entity = self._extract_entity_by_regex(entity_xml)
                if entity:
                    entities.append(entity)
        
        # 提取关系
        rel_patterns = [
            r'<Relationship[^>]*>.*?</Relationship>',
            r'<relationship[^>]*>.*?</relationship>',
        ]
        
        for pattern in rel_patterns:
            for match in re.finditer(pattern, xml_string, re.DOTALL):
                rel_xml = match.group()
                rel = self._extract_relationship_by_regex(rel_xml)
                if rel:
                    relationships.append(rel)
        
        return entities, relationships
    
    def _extract_entity_by_regex(self, entity_xml: str) -> Optional[Dict[str, Any]]:
        """使用正则表达式提取实体属性
        
        Args:
            entity_xml: 实体 XML 字符串
            
        Returns:
            Dict: 实体字典
        """
        def extract_tag(tag: str) -> str:
            """提取标签内容"""
            pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
            match = re.search(pattern, entity_xml, re.DOTALL)
            return match.group(1).strip() if match else ""
        
        def extract_list_tag(tag: str) -> List[str]:
            """提取列表标签的所有内容"""
            texts = []
            # 使用更精确的模式，只匹配不包含 < 的内容，避免嵌套标签问题
            pattern = rf'<{tag}[^>]*>([^<]*)</{tag}>'
            matches = re.findall(pattern, entity_xml)
            for m in matches:
                if m.strip():
                    texts.append(m.strip())
            return texts
        
        def extract_properties() -> Dict[str, str]:
            """提取属性字典"""
            props = {}
            prop_pattern = r'<Property\s+name="([^"]+)"[^>]*>([^<]*)</Property>'
            for match in re.finditer(prop_pattern, entity_xml):
                name, value = match.groups()
                props[name] = value.strip()
            return props
        
        entity = {
            "entity_id": extract_tag("EntityId"),
            "entity_name": extract_tag("EntityName"),
            "entity_variant_names": extract_list_tag("EntityVariantName"),
            "entity_type": extract_tag("EntityType"),
            "entity_sub_type": extract_tag("EntitySubType"),
            "labels": extract_list_tag("Label"),
            "times": extract_list_tag("Time"),
            "properties": extract_properties(),
        }
        
        if entity["entity_name"] or entity["entity_id"]:
            return entity
        
        return None
    
    def _extract_relationship_by_regex(self, rel_xml: str) -> Optional[Dict[str, Any]]:
        """使用正则表达式提取关系属性
        
        Args:
            rel_xml: 关系 XML 字符串
            
        Returns:
            Dict: 关系字典
        """
        def extract_tag(tag: str) -> str:
            """提取标签内容"""
            pattern = rf'<{tag}[^>]*>(.*?)</{tag}>'
            match = re.search(pattern, rel_xml, re.DOTALL)
            return match.group(1).strip() if match else ""
        
        relationship = {
            "relationship_id": extract_tag("RelationshipId"),
            "relationship_type": extract_tag("RelationshipType"),
            "source": extract_tag("Source"),
            "target": extract_tag("Target"),
        }
        
        if relationship["source"] and relationship["target"]:
            return relationship
        
        return None


def parse_graph_xml(xml_string: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """便捷函数：解析图谱 XML
    
    Args:
        xml_string: XML 格式字符串
        
    Returns:
        Tuple[List[Dict], List[Dict]]: (实体列表, 关系列表)
    """
    parser = XMLParser()
    return parser.parse(xml_string)


def validate_entities(entities: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """验证实体列表的完整性
    
    Args:
        entities: 实体列表
        
    Returns:
        Tuple[List[Dict], List[str]]: (有效实体列表, 错误消息列表)
    """
    valid_entities = []
    errors = []
    
    for i, entity in enumerate(entities):
        entity_errors = []
        
        # 检查必需字段
        if not entity.get("entity_name"):
            entity_errors.append(f"实体 {i+1} 缺少 entity_name")
        
        if not entity.get("entity_type"):
            entity_errors.append(f"实体 {i+1} 缺少 entity_type")
        
        if not entity.get("labels"):
            entity_errors.append(f"实体 {i+1} 缺少 labels（MITRE ATT&CK 标签）")
        
        # 验证类型值
        valid_types = [e.value for e in EntityType]
        entity_type = entity.get("entity_type", "").lower()
        if entity_type and entity_type not in valid_types:
            entity_errors.append(f"实体 {i+1} 的 entity_type '{entity_type}' 不在允许的范围内")
        
        # 验证标签值
        valid_labels = [
            "TA0043", "TA0042", "TA0001", "TA0002", "TA0003", "TA0004",
            "TA0005", "TA0006", "TA0007", "TA0008", "TA0009", "TA0010", "TA0011", "TA0040"
        ]
        labels = entity.get("labels", [])
        for label in labels:
            if label not in valid_labels:
                entity_errors.append(f"实体 {i+1} 的 label '{label}' 不是有效的 MITRE ATT&CK 标签")
        
        if entity_errors:
            errors.extend(entity_errors)
            logger.warning(f"实体验证失败: {'; '.join(entity_errors)}")
        else:
            valid_entities.append(entity)
    
    return valid_entities, errors


def validate_relationships(relationships: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """验证关系列表的完整性
    
    Args:
        relationships: 关系列表
        
    Returns:
        Tuple[List[Dict], List[str]]: (有效关系列表, 错误消息列表)
    """
    valid_relationships = []
    errors = []
    
    valid_types = ["use", "trigger", "involve", "target", "has", "exploit", "affect", "related_to", "belong_to"]
    
    for i, rel in enumerate(relationships):
        rel_errors = []
        
        # 检查必需字段
        if not rel.get("source"):
            rel_errors.append(f"关系 {i+1} 缺少 source")
        
        if not rel.get("target"):
            rel_errors.append(f"关系 {i+1} 缺少 target")
        
        # 验证关系类型
        rel_type = rel.get("relationship_type", "").lower()
        if rel_type and rel_type not in valid_types:
            rel_errors.append(f"关系 {i+1} 的 relationship_type '{rel_type}' 不在允许的范围内")
        
        if rel_errors:
            errors.extend(rel_errors)
            logger.warning(f"关系验证失败: {'; '.join(rel_errors)}")
        else:
            valid_relationships.append(rel)
    
    return valid_relationships, errors


__all__ = [
    "XMLParser",
    "XMLParseError",
    "parse_graph_xml",
    "validate_entities",
    "validate_relationships",
]
