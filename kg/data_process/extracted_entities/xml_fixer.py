#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XML修复工具

这个脚本用于修复XML文件中的常见问题，包括：
1. 标签闭合问题（如 <tag> 没有对应的 </tag>）
2. 标签不对应问题（如 <tag1></tag2>）
3. 特殊字符和编码问题
4. 其他格式问题

使用方法：
1. 修复单个文件：python xml_fixer.py --file path/to/file.xml
2. 修复整个目录：python xml_fixer.py --dir path/to/directory
3. 修复并覆盖原文件：python xml_fixer.py --file path/to/file.xml --overwrite
4. 修复并保存到新目录：python xml_fixer.py --dir path/to/directory --output path/to/output
"""

import os
import re
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import html

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 定义常见的XML标签对应关系
TAG_PAIRS = {
    "EntityId": "EntityId",
    "EntityName": "EntityName",
    "EntityType": "EntityType",
    "EntitySubType": "EntitySubType",
    "EntityVariantNames": "EntityVariantNames",
    "EntityVariantName": "EntityVariantName",
    "Labels": "Labels",
    "Label": "Label",
    "Properties": "Properties",
    "Property": "Property",
    "Entitys": "Entitys",
    "Entity": "Entity",
    "RelationshipId": "RelationshipId",
    "RelationshipType": "RelationshipType",
    "Source": "Source",
    "Target": "Target",
    "Relationships": "Relationships",
    "Relationship": "Relationship",
    "Root": "Root"
}

def fix_tag_mismatch(content: str) -> str:
    """
    修复标签不匹配的问题

    Args:
        content: XML内容

    Returns:
        str: 修复后的XML内容
    """
    # 使用正则表达式查找所有的开始和结束标签
    open_tags = re.findall(r'<([a-zA-Z0-9_]+)(?:\s+[^>]*)?>', content)
    close_tags = re.findall(r'</([a-zA-Z0-9_]+)>', content)

    # 创建标签替换映射
    replacements = {}

    # 检查每个结束标签
    for i, close_tag in enumerate(close_tags):
        # 如果结束标签不在TAG_PAIRS中，尝试找到正确的标签
        if close_tag not in TAG_PAIRS.values():
            # 查找对应的开始标签
            if i < len(open_tags):
                open_tag = open_tags[i]
                if open_tag in TAG_PAIRS:
                    # 添加到替换映射
                    replacements[f'</{close_tag}>'] = f'</{TAG_PAIRS[open_tag]}>'
                    logger.debug(f"标签不匹配: </{close_tag}> -> </{TAG_PAIRS[open_tag]}>")
        # 如果结束标签在TAG_PAIRS中，但与对应的开始标签不匹配
        elif i < len(open_tags):
            open_tag = open_tags[i]
            if open_tag in TAG_PAIRS and TAG_PAIRS[open_tag] != close_tag:
                # 添加到替换映射
                replacements[f'</{close_tag}>'] = f'</{TAG_PAIRS[open_tag]}>'
                logger.debug(f"标签不匹配: </{close_tag}> -> </{TAG_PAIRS[open_tag]}>")

    # 应用替换
    for old, new in replacements.items():
        content = content.replace(old, new)

    return content

def fix_unclosed_tags(content: str) -> str:
    """
    修复未闭合的标签

    Args:
        content: XML内容

    Returns:
        str: 修复后的XML内容
    """
    # 使用正则表达式查找所有的开始标签
    open_tags = re.findall(r'<([a-zA-Z0-9_]+)(?:\s+[^>]*)?>', content)
    close_tags = re.findall(r'</([a-zA-Z0-9_]+)>', content)

    # 统计每个标签的开始和结束次数
    tag_counts = {}
    for tag in open_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1

    for tag in close_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) - 1

    # 找出未闭合的标签
    unclosed_tags = []
    for tag, count in tag_counts.items():
        if count > 0:
            unclosed_tags.extend([tag] * count)

    # 在内容末尾添加缺失的闭合标签
    for tag in reversed(unclosed_tags):
        content += f'</{tag}>'
        logger.debug(f"添加缺失的闭合标签: </{tag}>")

    return content

def fix_invalid_characters(content: str) -> str:
    """
    修复无效字符

    Args:
        content: XML内容

    Returns:
        str: 修复后的XML内容
    """
    # 使用html模块的escape函数转义特殊字符
    # 但我们需要保护XML标签不被转义

    # 先将所有的XML标签替换为特殊标记
    tag_pattern = r'<[^>]+>'
    tags = re.findall(tag_pattern, content)
    for i, tag in enumerate(tags):
        content = content.replace(tag, f"__TAG_{i}__")

    # 转义剩余的内容
    content = html.escape(content)

    # 恢复XML标签
    for i, tag in enumerate(tags):
        content = content.replace(f"__TAG_{i}__", tag)

    return content

def fix_property_attributes(content: str) -> str:
    """
    修复Property标签的属性

    Args:
        content: XML内容

    Returns:
        str: 修复后的XML内容
    """
    # 修复没有引号的属性值
    pattern = r'<Property\s+name=([^"\'>]+)([^>]*)>'
    content = re.sub(pattern, r'<Property name="\1"\2>', content)

    return content

def fix_xml_structure(content: str) -> str:
    """
    修复XML结构

    Args:
        content: XML内容

    Returns:
        str: 修复后的XML内容
    """
    # 检查是否已经有完整的XML结构
    has_entitys_open = "<Entitys>" in content
    has_entitys_close = "</Entitys>" in content
    has_relationships_open = "<Relationships>" in content
    has_relationships_close = "</Relationships>" in content
    has_entity = "<Entity>" in content
    has_relationship = "<Relationship>" in content

    # 如果没有Entitys标签但有Entity标签，添加Entitys标签
    if not has_entitys_open and has_entity:
        content = "<Entitys>\n" + content
        has_entitys_open = True

    # 如果有开始的Entitys标签但没有结束标签，添加结束标签
    if has_entitys_open and not has_entitys_close:
        # 如果有Relationships标签，在其前面添加Entitys结束标签
        if has_relationships_open:
            content = content.replace("<Relationships>", "</Entitys>\n<Relationships>")
        else:
            # 否则在末尾添加
            content += "\n</Entitys>"
        has_entitys_close = True

    # 如果没有Relationships标签但有Relationship标签，添加Relationships标签
    if not has_relationships_open and has_relationship:
        # 如果有Entitys结束标签，在其后添加Relationships开始标签
        if has_entitys_close:
            content = content.replace("</Entitys>", "</Entitys>\n<Relationships>")
        else:
            # 否则在末尾添加
            content += "\n<Relationships>"
        has_relationships_open = True

    # 如果有开始的Relationships标签但没有结束标签，添加结束标签
    if has_relationships_open and not has_relationships_close:
        content += "\n</Relationships>"

    # 确保Relationships标签在Entitys标签之后
    if has_entitys_open and has_relationships_open and has_entitys_close:
        # 检查Relationships是否在Entitys内部
        entitys_close_pos = content.find("</Entitys>")
        relationships_open_pos = content.find("<Relationships>")

        if relationships_open_pos < entitys_close_pos:
            # 如果Relationships在Entitys内部，需要移动它
            relationships_part = content[relationships_open_pos:content.find("</Relationships>") + len("</Relationships>")]
            # 从原位置删除
            content = content.replace(relationships_part, "")
            # 在Entitys后添加
            content = content.replace("</Entitys>", "</Entitys>\n" + relationships_part)

    return content

def fix_xml_content(content: str) -> str:
    """
    修复XML内容的主函数

    Args:
        content: 原始XML内容

    Returns:
        str: 修复后的XML内容
    """
    # 保存原始内容，以便在处理失败时恢复
    original_content = content

    # 检查是否包含关系部分
    has_relationships = "<Relationships>" in content and "</Relationships>" in content
    relationships_content = ""

    # 如果有关系部分，先提取出来
    if has_relationships:
        rel_start = content.find("<Relationships>")
        rel_end = content.find("</Relationships>") + len("</Relationships>")
        relationships_content = content[rel_start:rel_end]

        # 记录关系部分
        logger.debug(f"提取到关系部分: {relationships_content[:100]}...")

    # 应用各种修复
    content = fix_invalid_characters(content)
    content = fix_property_attributes(content)
    content = fix_tag_mismatch(content)
    content = fix_unclosed_tags(content)
    content = fix_xml_structure(content)

    # 使用BeautifulSoup进行最终清理，但要小心处理
    try:
        # 尝试使用BeautifulSoup解析
        soup = BeautifulSoup(content, 'xml')
        parsed_content = str(soup)

        # 检查清理后的内容是否保留了关系部分
        if has_relationships and "<Relationships>" not in parsed_content:
            logger.warning("BeautifulSoup清理后丢失了关系部分，将手动保留关系部分")

            # 如果丢失了关系部分，手动添加回去
            if "</Entitys>" in parsed_content:
                parsed_content = parsed_content.replace("</Entitys>", f"</Entitys>\n{relationships_content}")
            else:
                parsed_content += f"\n{relationships_content}"

            content = parsed_content
        else:
            content = parsed_content
    except Exception as e:
        logger.warning(f"BeautifulSoup清理失败: {str(e)}，将使用手动修复的内容")

        # 如果BeautifulSoup处理失败，使用手动修复的内容
        # 但要确保关系部分被保留
        if has_relationships and "<Relationships>" not in content:
            if "</Entitys>" in content:
                content = content.replace("</Entitys>", f"</Entitys>\n{relationships_content}")
            else:
                content += f"\n{relationships_content}"

    # 最终检查：如果修复后的内容丢失了实体或关系部分，恢复原始内容
    fixed_has_entities = "<Entity>" in content
    fixed_has_relationships = has_relationships and "<Relationship>" in content

    if (has_relationships and not fixed_has_relationships) or not fixed_has_entities:
        logger.warning("修复后的内容丢失了重要部分，将使用原始内容")
        return original_content

    return content

def validate_xml_content(content: str) -> Tuple[bool, bool, bool]:
    """
    验证XML内容是否包含实体和关系部分

    Args:
        content: XML内容

    Returns:
        Tuple[bool, bool, bool]: (是否有效, 是否包含实体, 是否包含关系)
    """
    has_entities = "<Entity>" in content
    has_relationships = "<Relationship>" in content

    # 简单检查XML是否有效
    try:
        # 尝试解析XML
        ET.fromstring(f"<Root>{content}</Root>")
        is_valid = True
    except Exception:
        is_valid = False

    return is_valid, has_entities, has_relationships

def fix_xml_file(file_path: str, output_path: Optional[str] = None, overwrite: bool = False) -> bool:
    """
    修复单个XML文件

    Args:
        file_path: XML文件路径
        output_path: 输出文件路径，如果为None则使用原文件路径加上.fixed后缀
        overwrite: 是否覆盖原文件

    Returns:
        bool: 是否成功修复
    """
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 验证原始内容
        orig_valid, orig_has_entities, orig_has_relationships = validate_xml_content(content)
        logger.debug(f"原始文件 {file_path} 验证结果: 有效={orig_valid}, 实体={orig_has_entities}, 关系={orig_has_relationships}")

        # 修复内容
        fixed_content = fix_xml_content(content)

        # 验证修复后的内容
        fixed_valid, fixed_has_entities, fixed_has_relationships = validate_xml_content(fixed_content)
        logger.debug(f"修复后文件验证结果: 有效={fixed_valid}, 实体={fixed_has_entities}, 关系={fixed_has_relationships}")

        # 检查是否丢失了实体或关系
        if orig_has_entities and not fixed_has_entities:
            logger.warning(f"警告: 修复后丢失了实体部分，将使用原始内容: {file_path}")
            fixed_content = content

        if orig_has_relationships and not fixed_has_relationships:
            logger.warning(f"警告: 修复后丢失了关系部分，将使用原始内容: {file_path}")
            fixed_content = content

        # 确定输出路径
        if output_path is None:
            if overwrite:
                output_path = file_path
            else:
                output_path = file_path + '.fixed'

        # 写入修复后的内容
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        logger.info(f"成功修复文件: {file_path} -> {output_path}")

        # 记录修复结果
        if orig_has_relationships and fixed_has_relationships:
            logger.info(f"成功保留关系部分: {file_path}")
        elif orig_has_relationships:
            logger.warning(f"警告: 可能未能保留关系部分: {file_path}")

        return True

    except Exception as e:
        logger.error(f"修复文件 {file_path} 失败: {str(e)}")
        return False

def fix_xml_directory(dir_path: str, output_dir: Optional[str] = None, overwrite: bool = False) -> Tuple[int, int, int, int]:
    """
    修复目录中的所有XML文件

    Args:
        dir_path: 目录路径
        output_dir: 输出目录路径，如果为None则使用原目录
        overwrite: 是否覆盖原文件

    Returns:
        Tuple[int, int, int, int]: (成功修复的文件数, 总文件数, 包含关系的文件数, 成功保留关系的文件数)
    """
    # 统计信息
    total_files = 0
    fixed_files = 0
    files_with_relationships = 0
    preserved_relationships = 0

    # 遍历目录
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.xml'):
                total_files += 1
                file_path = os.path.join(root, file)

                # 检查原始文件是否包含关系
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    _, _, has_relationships = validate_xml_content(content)
                    if has_relationships:
                        files_with_relationships += 1
                except Exception as e:
                    logger.error(f"读取文件失败: {file_path}, 错误: {str(e)}")
                    continue

                # 确定输出路径
                if output_dir is not None:
                    # 保持相对路径结构
                    rel_path = os.path.relpath(file_path, dir_path)
                    output_path = os.path.join(output_dir, rel_path)

                    # 确保输出目录存在
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                else:
                    output_path = None

                # 修复文件
                if fix_xml_file(file_path, output_path, overwrite):
                    fixed_files += 1

                    # 检查修复后的文件是否保留了关系
                    if has_relationships:
                        try:
                            actual_output_path = output_path if output_path else (file_path if overwrite else file_path + '.fixed')
                            with open(actual_output_path, 'r', encoding='utf-8') as f:
                                fixed_content = f.read()
                            _, _, fixed_has_relationships = validate_xml_content(fixed_content)
                            if fixed_has_relationships:
                                preserved_relationships += 1
                        except Exception as e:
                            logger.error(f"读取修复后文件失败: {actual_output_path}, 错误: {str(e)}")

    logger.info(f"目录修复完成: {dir_path}")
    logger.info(f"总文件数: {total_files}")
    logger.info(f"成功修复: {fixed_files}")
    logger.info(f"包含关系的文件数: {files_with_relationships}")
    logger.info(f"成功保留关系的文件数: {preserved_relationships}")

    if files_with_relationships > 0:
        preservation_rate = (preserved_relationships / files_with_relationships) * 100
        logger.info(f"关系保留率: {preservation_rate:.2f}%")

    return fixed_files, total_files, files_with_relationships, preserved_relationships

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='XML修复工具')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='要修复的XML文件路径')
    group.add_argument('--dir', help='要修复的XML文件目录')
    parser.add_argument('--output', help='输出路径')
    parser.add_argument('--overwrite', action='store_true', help='是否覆盖原文件')
    parser.add_argument('--verbose', action='store_true', help='显示详细日志')
    parser.add_argument('--check-only', action='store_true', help='仅检查文件，不进行修复')

    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # 修复文件或目录
    if args.file:
        # 如果只是检查
        if args.check_only:
            try:
                with open(args.file, 'r', encoding='utf-8') as f:
                    content = f.read()
                is_valid, has_entities, has_relationships = validate_xml_content(content)
                logger.info(f"文件检查结果: {args.file}")
                logger.info(f"有效XML: {is_valid}")
                logger.info(f"包含实体: {has_entities}")
                logger.info(f"包含关系: {has_relationships}")
            except Exception as e:
                logger.error(f"检查文件失败: {args.file}, 错误: {str(e)}")
        else:
            # 修复文件
            fix_xml_file(args.file, args.output, args.overwrite)
    elif args.dir:
        # 如果只是检查
        if args.check_only:
            total_files = 0
            valid_files = 0
            files_with_entities = 0
            files_with_relationships = 0

            # 遍历目录
            for root, _, files in os.walk(args.dir):
                for file in files:
                    if file.endswith('.xml'):
                        total_files += 1
                        file_path = os.path.join(root, file)

                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            is_valid, has_entities, has_relationships = validate_xml_content(content)
                            if is_valid:
                                valid_files += 1
                            if has_entities:
                                files_with_entities += 1
                            if has_relationships:
                                files_with_relationships += 1
                        except Exception as e:
                            logger.error(f"检查文件失败: {file_path}, 错误: {str(e)}")

            logger.info(f"目录检查完成: {args.dir}")
            logger.info(f"总文件数: {total_files}")
            logger.info(f"有效XML文件数: {valid_files}")
            logger.info(f"包含实体的文件数: {files_with_entities}")
            logger.info(f"包含关系的文件数: {files_with_relationships}")
        else:
            # 修复目录
            fixed_files, total_files, files_with_relationships, preserved_relationships = fix_xml_directory(args.dir, args.output, args.overwrite)

            # 打印总结
            logger.info("\n修复总结:")
            logger.info(f"总文件数: {total_files}")
            logger.info(f"成功修复: {fixed_files}")
            logger.info(f"包含关系的文件数: {files_with_relationships}")
            logger.info(f"成功保留关系的文件数: {preserved_relationships}")

            if files_with_relationships > 0:
                preservation_rate = (preserved_relationships / files_with_relationships) * 100
                logger.info(f"关系保留率: {preservation_rate:.2f}%")

                if preservation_rate < 100:
                    logger.warning("警告: 有些文件的关系部分可能未被保留！")
                    logger.warning("请检查日志以获取更多信息。")

if __name__ == "__main__":
    main()
