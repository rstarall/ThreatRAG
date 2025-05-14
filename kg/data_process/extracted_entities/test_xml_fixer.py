#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XML修复工具测试脚本

这个脚本用于测试XML修复工具的功能，特别是标签闭合问题的修复。
"""

import os
import sys
import logging
from pathlib import Path

# 导入XML修复工具
from xml_fixer import fix_xml_content

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def test_fix_tag_mismatch():
    """测试修复标签不匹配的功能"""
    logger.info("测试修复标签不匹配的功能")

    # 测试用例1：简单的标签不匹配
    test_xml1 = """<Entity>
    <EntityId>entity_1</EntityId>
    <EntityName>Test Entity</EntityName>
    <EntityType>test</EntityType>
</Entity>
<Relationship>
    <RelationshipId>relationship_1</RelationshipType>
    <RelationshipType>test</RelationshipType>
    <Source>Test Entity</Source>
    <Target>Another Entity</Target>
</Relationship>"""

    fixed_xml1 = fix_xml_content(test_xml1)  # 使用完整的修复函数
    logger.info(f"测试用例1修复结果：\n{fixed_xml1}")
    assert "<RelationshipId>relationship_1</RelationshipId>" in fixed_xml1, "标签不匹配修复失败"

    # 测试用例2：嵌套的标签不匹配
    test_xml2 = """<Entitys>
    <Entity>
        <EntityId>entity_1</EntityId>
        <EntityName>Test Entity</EntityName>
        <EntityType>test</EntityType>
    </Entity>
</Entitys>
<Relationships>
    <Relationship>
        <RelationshipId>relationship_1</RelationshipType>
        <RelationshipType>test</RelationshipType>
        <Source>Test Entity</Source>
        <Target>Another Entity</Target>
    </Relationship>
</Relationships>"""

    fixed_xml2 = fix_xml_content(test_xml2)  # 使用完整的修复函数
    logger.info(f"测试用例2修复结果：\n{fixed_xml2}")
    assert "<RelationshipId>relationship_1</RelationshipId>" in fixed_xml2, "嵌套标签不匹配修复失败"

    # 测试用例3：实际的标签不匹配问题
    test_xml3 = """<Relationship>
        <RelationshipId>relationship_6</RelationshipType>
        <RelationshipType>target</RelationshipType>
        <Source>Peng Yong</Source>
        <Target>Google</Target>
    </Relationship>"""

    fixed_xml3 = fix_xml_content(test_xml3)  # 使用完整的修复函数
    logger.info(f"测试用例3修复结果：\n{fixed_xml3}")
    assert "<RelationshipId>relationship_6</RelationshipId>" in fixed_xml3, "实际标签不匹配修复失败"

    logger.info("标签不匹配修复测试通过")

def test_fix_unclosed_tags():
    """测试修复未闭合标签的功能"""
    logger.info("测试修复未闭合标签的功能")

    # 测试用例1：简单的未闭合标签
    test_xml1 = """<Entity>
    <EntityId>entity_1</EntityId>
    <EntityName>Test Entity</EntityName>
    <EntityType>test</EntityType>
</Entity>
<Relationship>
    <RelationshipId>relationship_1</RelationshipId>
    <RelationshipType>test</RelationshipType>
    <Source>Test Entity</Source>
    <Target>Another Entity"""

    fixed_xml1 = fix_xml_content(test_xml1)  # 使用完整的修复函数
    logger.info(f"测试用例1修复结果：\n{fixed_xml1}")
    assert "</Target>" in fixed_xml1, "未闭合标签修复失败"
    assert "</Relationship>" in fixed_xml1, "未闭合标签修复失败"

    # 测试用例2：嵌套的未闭合标签
    test_xml2 = """<Entitys>
    <Entity>
        <EntityId>entity_1</EntityId>
        <EntityName>Test Entity</EntityName>
        <EntityType>test</EntityType>
    </Entity>
</Entitys>
<Relationships>
    <Relationship>
        <RelationshipId>relationship_1</RelationshipId>
        <RelationshipType>test</RelationshipType>
        <Source>Test Entity</Source>
        <Target>Another Entity"""

    fixed_xml2 = fix_xml_content(test_xml2)  # 使用完整的修复函数
    logger.info(f"测试用例2修复结果：\n{fixed_xml2}")
    assert "</Target>" in fixed_xml2, "嵌套未闭合标签修复失败"
    assert "</Relationship>" in fixed_xml2, "嵌套未闭合标签修复失败"
    assert "</Relationships>" in fixed_xml2, "嵌套未闭合标签修复失败"

    logger.info("未闭合标签修复测试通过")

def test_fix_xml_content():
    """测试完整的XML内容修复功能"""
    logger.info("测试完整的XML内容修复功能")

    # 测试用例：包含多种问题的XML
    test_xml = """<?xml version="1.0" encoding="utf-8"?>
<Entitys>
<Entity>
<EntityId>entity_1</EntityId>
<EntityName>Test Entity</EntityName>
<EntityType>test</EntityType>
<EntitySubType>test</EntitySubType>
<Labels>
<Label>Test Label</Label>
</Labels>
</Entity>
</Entitys>
<Relationships>
    <Relationship>
        <RelationshipId>relationship_1</RelationshipType>
        <RelationshipType>test</RelationshipType>
        <Source>Test Entity</Source>
        <Target>Another Entity"""

    fixed_xml = fix_xml_content(test_xml)
    logger.info(f"完整修复结果：\n{fixed_xml}")

    # 验证修复结果
    assert "<RelationshipId>relationship_1</RelationshipId>" in fixed_xml, "标签不匹配修复失败"
    assert "</Target>" in fixed_xml, "未闭合标签修复失败"
    assert "</Relationship>" in fixed_xml, "未闭合标签修复失败"
    assert "</Relationships>" in fixed_xml, "未闭合标签修复失败"

    logger.info("完整XML内容修复测试通过")

def test_real_file():
    """测试修复真实的XML文件"""
    logger.info("测试修复真实的XML文件")

    # 测试文件路径
    test_file = Path("fixed_xml/2010/2010_Aurora_HBGARY_DRAFT_06a0673a.xml")
    # 如果文件不存在，尝试使用绝对路径
    if not test_file.exists():
        test_file = Path(__file__).parent / "fixed_xml/2010/2010_Aurora_HBGARY_DRAFT_06a0673a.xml"

    if not test_file.exists():
        logger.warning(f"测试文件 {test_file} 不存在，跳过此测试")
        return

    # 读取文件内容
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复内容
    fixed_content = fix_xml_content(content)

    # 保存修复后的内容到临时文件
    temp_file = test_file.with_suffix('.fixed.xml')
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(fixed_content)

    logger.info(f"修复后的文件已保存到 {temp_file}")

def main():
    """主函数"""
    # 运行测试
    test_fix_tag_mismatch()
    test_fix_unclosed_tags()
    test_fix_xml_content()
    test_real_file()

    logger.info("所有测试通过")

if __name__ == "__main__":
    main()
