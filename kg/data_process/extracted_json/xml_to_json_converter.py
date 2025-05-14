#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
改进版XML到JSON转换器

这个脚本使用ElementTree直接解析XML实体关系文件，将其转换为JSON格式。
相比原版，这个版本更简洁、更鲁棒，直接使用ET解析XML文件。

处理规则：
1. 如果文件缺少实体(Entities)，则不保存
2. 如果文件缺少关系(Relationships)但有实体，则保存到单独的目录
3. 如果文件同时包含实体和关系，则保存到正常目录
"""

import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from enum import Enum

# 定义处理结果状态
class ProcessStatus(Enum):
    SUCCESS = 0           # 成功处理，包含实体和关系
    MISSING_ENTITIES = 1  # 缺少实体，不保存
    MISSING_RELATIONS = 2 # 缺少关系但有实体，保存到单独目录
    ERROR = 3             # 处理出错

# 源目录和目标目录
BASE_DIR = Path(__file__).parent.parent.parent.resolve()  # 项目根目录
SOURCE_DIR = BASE_DIR / "data_process" / "extracted_entities" / "fixed_xml"  # 使用修复的XML文件
DEST_DIR = Path(__file__).parent / "results"
MISSING_REL_DIR = Path(__file__).parent / "results_missing_relations"  # 缺少关系的文件保存目录

# 打印路径信息以便调试
print(f"BASE_DIR: {BASE_DIR}")
print(f"SOURCE_DIR: {SOURCE_DIR}")
print(f"DEST_DIR: {DEST_DIR}")
print(f"MISSING_REL_DIR: {MISSING_REL_DIR}")

def ensure_dir_exists(directory):
    """确保指定目录存在，如果不存在则创建"""
    os.makedirs(directory, exist_ok=True)

def parse_entity(entity_elem, report_year=None, report_name=None):
    """
    解析单个实体元素

    Args:
        entity_elem: 实体XML元素
        report_year: 报告年份，用于event类型实体的observe_time属性
        report_name: 报告名称，用于event类型实体的report_name属性

    Returns:
        dict: 实体的字典表示
    """
    entity = {}

    # 处理简单元素
    for child in entity_elem:
        if child.tag == "EntityId":
            entity["EntityId"] = child.text
        elif child.tag == "EntityName":
            entity["EntityName"] = child.text
        elif child.tag == "EntityType":
            entity["EntityType"] = child.text
        elif child.tag == "EntitySubType":
            entity["EntitySubType"] = child.text
        elif child.tag == "EntityVariantNames":
            entity["EntityVariantNames"] = [name.text for name in child.findall("EntityVariantName")]
        elif child.tag == "Labels":
            entity["Labels"] = [label.text for label in child.findall("Label")]
        elif child.tag == "Times":
            entity["Times"] = [time.text for time in child.findall("Time")]
        elif child.tag == "Properties":
            properties = {}
            for prop in child.findall("Property"):
                if "name" in prop.attrib:
                    properties[prop.attrib["name"]] = prop.text or ""
            entity["Properties"] = properties

    # 如果没有找到EntityVariantNames，但有直接的EntityVariantName子元素
    if "EntityVariantNames" not in entity and entity_elem.findall("EntityVariantName"):
        entity["EntityVariantNames"] = [name.text for name in entity_elem.findall("EntityVariantName")]

    # 如果没有找到Labels，但有直接的Label子元素
    if "Labels" not in entity and entity_elem.findall("Label"):
        entity["Labels"] = [label.text for label in entity_elem.findall("Label")]

    # 如果没有找到Times，但有直接的Time子元素
    if "Times" not in entity and entity_elem.findall("Time"):
        entity["Times"] = [time.text for time in entity_elem.findall("Time")]

    # 如果没有找到Properties，但有直接的Property子元素
    if "Properties" not in entity and entity_elem.findall("Property"):
        properties = {}
        for prop in entity_elem.findall("Property"):
            if "name" in prop.attrib:
                properties[prop.attrib["name"]] = prop.text or ""
        if properties:
            entity["Properties"] = properties

    # 如果实体类型是event，添加observe_time和report_name属性
    if entity.get("EntityType") == "event":
        if "Properties" not in entity:
            entity["Properties"] = {}
        if report_year:
            entity["Properties"]["observe_time"] = report_year
        if report_name:
            entity["Properties"]["report_name"] = report_name

    return entity

def parse_relationship(rel_elem):
    """
    解析单个关系元素

    Args:
        rel_elem: 关系XML元素

    Returns:
        dict: 关系的字典表示
    """
    relationship = {}

    # 处理简单元素
    for child in rel_elem:
        if child.tag in ["RelationshipId", "RelationshipType", "Source", "Target"]:
            relationship[child.tag] = child.text

    return relationship

def process_xml_file(xml_file_path):
    """
    处理单个XML文件并转换为JSON

    Args:
        xml_file_path: XML文件路径

    Returns:
        tuple: (ProcessStatus, data) - 处理状态和转换后的数据
    """
    try:
        # 初始化数据字典
        data = {
            "Entities": [],
            "Relationships": []
        }

        # 从文件路径中提取报告年份和报告名称
        # 路径格式应该是 .../fixed_xml/YYYY/filename.xml
        path_parts = Path(xml_file_path).parts
        report_year = None
        for part in path_parts:
            # 尝试将路径部分解析为年份（4位数字）
            if part.isdigit() and len(part) == 4:
                report_year = part
                break

        # 提取报告名称（文件名，不包含扩展名）
        report_name = Path(xml_file_path).stem

        # 读取XML文件内容
        with open(xml_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试直接解析XML文件
        try:
            # 解析XML文件,xml必须有xml头
            tree = ET.parse(xml_file_path)
            root = tree.getroot()

            # 如果根元素不是Root，我们需要找到Entitys和Relationships节点
            if root.tag != "Root":
                # 查找Entitys节点
                entitys_elem = root if root.tag == "Entitys" else root.find("Entitys")
                if entitys_elem is not None:
                    for entity_elem in entitys_elem.findall("Entity"):
                        entity = parse_entity(entity_elem, report_year, report_name)
                        data["Entities"].append(entity)

                # 查找Relationships节点
                relationships_elem = root if root.tag == "Relationships" else root.find("Relationships")
                if relationships_elem is not None:
                    for rel_elem in relationships_elem.findall("Relationship"):
                        relationship = parse_relationship(rel_elem)
                        data["Relationships"].append(relationship)
            else:
                # 如果根元素是Root，直接查找Entity和Relationship元素
                for entity_elem in root.findall(".//Entity"):
                    entity = parse_entity(entity_elem, report_year, report_name)
                    data["Entities"].append(entity)

                for rel_elem in root.findall(".//Relationship"):
                    relationship = parse_relationship(rel_elem)
                    data["Relationships"].append(relationship)

        except ET.ParseError:
            # 如果直接解析失败，尝试分别解析Entitys和Relationships部分
            print(f"警告: 解析 {xml_file_path} 失败，尝试修复XML...")

            # 提取Entitys部分
            entitys_start = content.find("<Entitys>")
            entitys_end = content.find("</Entitys>")

            if entitys_start >= 0 and entitys_end > entitys_start:
                entitys_content = content[entitys_start:entitys_end + len("</Entitys>")]
                try:
                    # 包装在根元素中
                    entitys_content = f"<?xml version='1.0' encoding='UTF-8'?>{entitys_content}"
                    entitys_root = ET.fromstring(entitys_content)

                    # 处理所有Entity元素
                    for entity_elem in entitys_root.findall("Entity"):
                        entity = parse_entity(entity_elem, report_year, report_name)
                        data["Entities"].append(entity)
                except ET.ParseError as e:
                    print(f"警告: 无法解析Entitys部分: {str(e)}")

            # 提取Relationships部分
            relationships_start = content.find("<Relationships>")
            relationships_end = content.find("</Relationships>")

            if relationships_start >= 0 and relationships_end > relationships_start:
                relationships_content = content[relationships_start:relationships_end + len("</Relationships>")]
                try:
                    # 包装在根元素中
                    relationships_content = f"<?xml version='1.0' encoding='UTF-8'?>{relationships_content}"
                    relationships_root = ET.fromstring(relationships_content)

                    # 处理所有Relationship元素
                    for rel_elem in relationships_root.findall("Relationship"):
                        relationship = parse_relationship(rel_elem)
                        data["Relationships"].append(relationship)
                except ET.ParseError as e:
                    print(f"警告: 无法解析Relationships部分: {str(e)}")

            # 如果上述方法都失败，尝试包装整个内容
            if not data["Entities"] and not data["Relationships"]:
                try:
                    # 尝试添加根元素包装
                    modified_content = f"<?xml version='1.0' encoding='UTF-8'?><Root>{content}</Root>"
                    root = ET.fromstring(modified_content)

                    # 查找Entity元素
                    for entity_elem in root.findall(".//Entity"):
                        entity = parse_entity(entity_elem, report_year, report_name)
                        data["Entities"].append(entity)

                    # 查找Relationship元素
                    for rel_elem in root.findall(".//Relationship"):
                        relationship = parse_relationship(rel_elem)
                        data["Relationships"].append(relationship)
                except Exception as e:
                    print(f"警告: 包装整个内容失败: {str(e)}")

        # 检查是否包含Entities
        has_entities = len(data["Entities"]) > 0
        has_relationships = len(data["Relationships"]) > 0

        # 如果缺少Entities字段，则不保存文件并返回错误
        if not has_entities:
            error_msg = f"错误: {xml_file_path} 解析结果不完整。 缺少Entities字段。"
            print(error_msg)
            return ProcessStatus.MISSING_ENTITIES, data

        # 如果缺少Relationships字段，返回特殊状态
        if not has_relationships:
            print(f"警告: {xml_file_path} 缺少Relationships字段，将保存到单独目录。")
            return ProcessStatus.MISSING_RELATIONS, data

        # 如果既有实体又有关系，返回成功状态
        return ProcessStatus.SUCCESS, data

    except Exception as e:
        print(f"错误: 处理 {xml_file_path} 失败: {str(e)}")
        return ProcessStatus.ERROR, None

def save_json_file(data, json_file_path):
    """
    将数据保存为JSON文件

    Args:
        data: 要保存的数据
        json_file_path: JSON文件保存路径

    Returns:
        bool: 是否成功保存
    """
    try:
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"错误: 保存JSON文件 {json_file_path} 失败: {str(e)}")
        return False

def main():
    """主函数，处理所有XML文件，包括子目录中的文件"""
    print(f"开始从 {SOURCE_DIR} 转换到 {DEST_DIR} 和 {MISSING_REL_DIR}")

    # 检查源目录是否存在
    if not SOURCE_DIR.exists():
        print(f"错误: 源目录 {SOURCE_DIR} 不存在。")
        return

    # 确保目标目录存在
    ensure_dir_exists(DEST_DIR)
    ensure_dir_exists(MISSING_REL_DIR)

    # 统计数据
    total_files = 0
    success_files = 0  # 成功转换且包含实体和关系
    missing_rel_files = 0  # 缺少关系但有实体
    missing_entity_files = 0  # 缺少实体
    error_files = 0  # 处理出错

    # 检查源目录结构
    print(f"检查源目录结构:")
    for item in SOURCE_DIR.iterdir():
        if item.is_dir():
            print(f"  - 目录: {item.name}")
            for subitem in item.iterdir():
                if subitem.is_file() and subitem.suffix.lower() == '.xml':
                    print(f"    - XML文件: {subitem.name}")
        elif item.is_file() and item.suffix.lower() == '.xml':
            print(f"  - XML文件: {item.name}")

    # 递归查找所有XML文件，包括子目录中的文件
    xml_files = list(SOURCE_DIR.glob("**/*.xml"))
    total_files = len(xml_files)

    if total_files == 0:
        print(f"警告: 在 {SOURCE_DIR} 及其子目录中没有找到XML文件。")
    else:
        print(f"在 {SOURCE_DIR} 及其子目录中找到 {total_files} 个XML文件。")

    # 处理每个XML文件
    for xml_file in xml_files:
        # 获取相对路径，用于保持目录结构
        rel_path = xml_file.relative_to(SOURCE_DIR)
        parent_dir = rel_path.parent

        # 处理XML文件
        status, data = process_xml_file(xml_file)

        # 根据处理状态进行不同的操作
        if status == ProcessStatus.SUCCESS:
            # 成功处理，包含实体和关系
            # 确保目标目录中存在相应的子目录
            output_dir = DEST_DIR / parent_dir
            ensure_dir_exists(output_dir)

            json_file = output_dir / f"{xml_file.stem}.json"
            if save_json_file(data, json_file):
                success_files += 1
                print(f"已转换 {xml_file} 到 {json_file}")
            else:
                error_files += 1

        elif status == ProcessStatus.MISSING_RELATIONS:
            # 缺少关系但有实体，保存到单独目录
            # 确保目标目录中存在相应的子目录
            output_dir = MISSING_REL_DIR / parent_dir
            ensure_dir_exists(output_dir)

            json_file = output_dir / f"{xml_file.stem}.json"
            if save_json_file(data, json_file):
                missing_rel_files += 1
                print(f"已转换缺少关系的文件 {xml_file} 到 {json_file}")
            else:
                error_files += 1

        elif status == ProcessStatus.MISSING_ENTITIES:
            # 缺少实体，不保存
            missing_entity_files += 1
            print(f"跳过缺少实体的文件 {xml_file}")

        else:  # ProcessStatus.ERROR
            # 处理出错
            error_files += 1
            print(f"处理文件 {xml_file} 时出错")

    # 打印摘要
    print("\n转换摘要:")
    print(f"总共处理文件: {total_files}")
    print(f"完整成功转换: {success_files} (保存到 {DEST_DIR})")
    print(f"缺少关系文件: {missing_rel_files} (保存到 {MISSING_REL_DIR})")
    print(f"缺少实体文件: {missing_entity_files} (未保存)")
    print(f"处理出错文件: {error_files}")
    print(f"转换完成。")

if __name__ == "__main__":
    main()
