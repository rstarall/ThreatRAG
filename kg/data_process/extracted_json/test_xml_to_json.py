#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试XML到JSON转换器

这个脚本用于测试XML到JSON转换器是否能够正确提取Times属性。
"""

import os
import json
import logging
from pathlib import Path
from xml_to_json_converter import process_xml_file, parse_entity

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_parse_entity():
    """测试解析实体函数是否能够正确提取Times属性"""
    logger.info("测试解析实体函数是否能够正确提取Times属性")

    # 创建一个测试XML字符串
    test_xml = """
    <Entity>
        <EntityId>entity_1</EntityId>
        <EntityName>Test Entity</EntityName>
        <EntityType>test</EntityType>
        <EntitySubType>test</EntitySubType>
        <Labels>
            <Label>Test Label</Label>
        </Labels>
        <Times>
            <Time>1</Time>
            <Time>2</Time>
        </Times>
        <Properties>
            <Property name="test">test value</Property>
        </Properties>
    </Entity>
    """

    # 使用ElementTree解析XML字符串
    import xml.etree.ElementTree as ET
    entity_elem = ET.fromstring(test_xml)

    # 解析实体
    entity = parse_entity(entity_elem)

    # 验证Times属性是否被正确提取
    assert "Times" in entity, "Times属性未被提取"
    assert entity["Times"] == ["1", "2"], f"Times属性值不正确: {entity['Times']}"

    logger.info("解析实体函数测试通过")

def test_convert_xml_file():
    """测试转换XML文件是否能够正确提取Times属性"""
    logger.info("测试转换XML文件是否能够正确提取Times属性")

    # 测试文件路径
    test_file = Path("../extracted_entities/fixed_xml/2006/2006_WickedRose_andNCPH_38a41d6b.xml")

    # 如果文件不存在，尝试使用绝对路径
    if not test_file.exists():
        test_file = Path(__file__).parent.parent / "extracted_entities/fixed_xml/2006/2006_WickedRose_andNCPH_38a41d6b.xml"

    # 如果仍然不存在，尝试使用更多路径
    if not test_file.exists():
        test_file = Path("E:/CExperiment/ThreatRAG/kg/data_process/extracted_entities/fixed_xml/2006/2006_WickedRose_andNCPH_38a41d6b.xml")

    if not test_file.exists():
        logger.warning(f"测试文件 {test_file} 不存在，跳过此测试")
        return


    status, data = process_xml_file(str(test_file))

    print(f"status: {status}")

    # 验证Times属性是否被正确提取
    assert "Entities" in data, "Entities字段不存在"
    assert len(data["Entities"]) > 0, "Entities为空"

    # 检查第一个实体的Times属性
    entity = data["Entities"][0]
    assert "Times" in entity, f"第一个实体的Times属性未被提取: {entity}"
    assert entity["Times"] == ["1"], f"第一个实体的Times属性值不正确: {entity['Times']}"

    logger.info("转换XML文件测试通过")


def main():
    """主函数"""
    # 运行测试
    test_parse_entity()
    test_convert_xml_file()

    logger.info("所有测试通过")

if __name__ == "__main__":
    main()
