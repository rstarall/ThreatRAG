#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
关系约束修正工具

这个脚本用于修正JSON文件中的关系约束问题。
如果关系名称不符合预定义的约束（即关系两端的实体类型与关系名称不匹配），
则修改关系名称为符合约束的名称。
修正后的结果按年份保存到kg\data_process\extracted_json\result_fixed目录。
"""

import json
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kg/data_process/extracted_json/fix_relationship_constraints.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RelationshipFixer")

# 关系约束定义 - 使用集合而不是列表，提高查找效率
relationship_constraint = {
    "use": {
        "source_types": {"attacker"},
        "target_types": {"tool", "vul", "ioc"}
    },
    "trigger": {
        "source_types": {"victim"},
        "target_types": {"file", "env", "ioc"}
    },
    "involve": {
        "source_types": {"event"},
        "target_types": {"attacker", "victim"}
    },
    "target": {
        "source_types": {"attacker"},
        "target_types": {"victim", "asset", "env"}
    },
    "has": {
        "source_types": {"victim"},
        "target_types": {"asset", "env"}
    },
    "exploit": {
        "source_types": {"vul"},
        "target_types": {"asset", "env"}
    },
    "affect": {
        "source_types": {"file"},
        "target_types": {"asset", "env"}
    },
    "related_to": {
        "source_types": {"tool"},
        "target_types": {"vul", "ioc", "file"}
    },
    "belong_to": {
        "source_types": {"file", "ioc"},
        "target_types": {"asset", "env"}
    }
}

# 创建反向映射字典，用于快速查找给定源类型和目标类型的可能关系类型
# 格式: {(source_type, target_type): [relationship_type1, relationship_type2, ...]}
entity_pair_to_relationship = {}
for rel_type, constraint in relationship_constraint.items():
    for source_type in constraint["source_types"]:
        for target_type in constraint["target_types"]:
            # 如果实体对已存在，将关系类型添加到列表中
            if (source_type, target_type) in entity_pair_to_relationship:
                entity_pair_to_relationship[(source_type, target_type)].append(rel_type)
            # 否则，创建一个新的列表
            else:
                entity_pair_to_relationship[(source_type, target_type)] = [rel_type]

# 源目录和目标目录
SOURCE_DIR = Path("kg/data_process/extracted_json/results")
TARGET_DIR = Path("kg/data_process/extracted_json/result_fixed")


def ensure_dir_exists(dir_path):
    """确保目录存在，如果不存在则创建"""
    if not dir_path.exists():
        dir_path.mkdir(parents=True)
        logger.info(f"创建目录: {dir_path}")


def find_correct_relationship_type(source_type, target_type, current_rel_type=None):
    """
    根据源实体类型和目标实体类型找到正确的关系类型

    使用预先计算的反向映射字典，提高查找效率

    Args:
        source_type: 源实体类型
        target_type: 目标实体类型
        current_rel_type: 当前关系类型，如果提供，则尝试找到不同的关系类型

    Returns:
        str: 正确的关系类型，如果没有找到则返回None
    """
    # 转换为小写
    source_type = source_type.lower()
    target_type = target_type.lower()
    if current_rel_type:
        current_rel_type = current_rel_type.lower()

    # 从反向映射字典中查找可能的关系类型列表
    possible_rel_types = entity_pair_to_relationship.get((source_type, target_type), [])

    # 如果没有找到可能的关系类型，返回None
    if not possible_rel_types:
        return None

    # 如果当前关系类型不在可能的关系类型列表中，返回第一个可能的关系类型
    if current_rel_type not in possible_rel_types:
        return possible_rel_types[0]

    # 如果当前关系类型在可能的关系类型列表中，但不是唯一的，返回下一个可能的关系类型
    if len(possible_rel_types) > 1:
        # 找到当前关系类型在列表中的索引
        current_index = possible_rel_types.index(current_rel_type)
        # 返回下一个关系类型（如果当前是最后一个，则返回第一个）
        next_index = (current_index + 1) % len(possible_rel_types)
        return possible_rel_types[next_index]

    # 如果当前关系类型是唯一的可能关系类型，则返回它
    return current_rel_type


def fix_relationship_constraints(json_data):
    """
    修正关系约束

    如果关系名称不符合预定义的约束（即关系两端的实体类型与关系名称不匹配），
    则修改关系名称为符合约束的名称。

    优化版本：使用预处理的集合和映射，减少循环中的计算

    Args:
        json_data: 包含实体和关系的JSON数据

    Returns:
        tuple: (修正后的JSON数据, 修正的数量)
    """
    if "Entities" not in json_data or "Relationships" not in json_data:
        return json_data, 0

    entities = json_data["Entities"]
    relationships = json_data["Relationships"]

    # 创建实体ID和名称到实体的映射，同时预处理实体类型为小写
    entity_map = {}
    for entity in entities:
        entity_id = entity.get("EntityId")
        entity_name = entity.get("EntityName")
        # 预处理实体类型为小写
        if "EntityType" in entity:
            entity["EntityType"] = entity["EntityType"].lower()

        if entity_id:
            entity_map[entity_id] = entity
        if entity_name:
            entity_map[entity_name] = entity

    fixes_count = 0

    # 检查每个关系
    for relationship in relationships:
        rel_type_original = relationship.get("RelationshipType", "")
        rel_type = rel_type_original.lower()
        source_name = relationship.get("Source")
        target_name = relationship.get("Target")

        # 获取源实体和目标实体
        source_entity = entity_map.get(source_name)
        target_entity = entity_map.get(target_name)

        # 如果找不到实体，跳过
        if not source_entity or not target_entity:
            continue

        # 获取实体类型（已经预处理为小写）
        source_type = source_entity.get("EntityType", "")
        target_type = target_entity.get("EntityType", "")

        # 快速检查当前关系类型是否符合约束
        is_valid = False
        if rel_type in relationship_constraint:
            constraint = relationship_constraint[rel_type]
            if source_type in constraint["source_types"] and target_type in constraint["target_types"]:
                is_valid = True

        # 如果关系类型不符合约束，从映射中查找正确的关系类型
        if not is_valid:
            correct_rel_type = find_correct_relationship_type(source_type, target_type, rel_type)

            if correct_rel_type and correct_rel_type != rel_type:
                logger.info(f"修正关系: 从 '{rel_type_original}' 修改为 '{correct_rel_type}', 源实体 '{source_name}' (类型: {source_type}), 目标实体 '{target_name}' (类型: {target_type})")
                relationship["RelationshipType"] = correct_rel_type
                fixes_count += 1

    return json_data, fixes_count


def process_json_file(file_path):
    """
    处理单个JSON文件

    Args:
        file_path: JSON文件路径

    Returns:
        tuple: (是否成功, 修正的数量)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 修正关系约束
        fixed_data, fixes_count = fix_relationship_constraints(json_data)

        # 获取年份目录
        year = file_path.parent.name
        target_dir = TARGET_DIR / year
        ensure_dir_exists(target_dir)

        # 保存修正后的文件
        target_file = target_dir / file_path.name
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(fixed_data, f, ensure_ascii=False, indent=4)

        return True, fixes_count
    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
        return False, 0


def main():
    """主函数"""
    logger.info("开始修正关系名称约束")

    # 确保目标目录存在
    ensure_dir_exists(TARGET_DIR)

    # 统计
    total_files = 0
    processed_files = 0
    total_fixes = 0

    # 递归查找所有JSON文件
    for year_dir in SOURCE_DIR.iterdir():
        if not year_dir.is_dir():
            continue

        year = year_dir.name
        logger.info(f"处理年份: {year}")

        for json_file in year_dir.glob("*.json"):
            total_files += 1
            success, fixes = process_json_file(json_file)
            if success:
                processed_files += 1
                total_fixes += fixes

    logger.info(f"处理完成. 总文件数: {total_files}, 成功处理: {processed_files}, 关系名称修正数: {total_fixes}")


if __name__ == "__main__":
    main()
