#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试处理批量推理结果
"""

import os
import json
import re
import time
from pathlib import Path
from typing import Dict, Any

def extract_xml_from_response(response: str) -> str:
    """从LLM响应中提取XML内容

    Args:
        response: LLM响应

    Returns:
        str: 提取的XML内容
    """
    # 尝试提取<Entitys>和<Relationships>部分
    entitys_pattern = r'<Entitys>.*?</Entitys>'
    relationships_pattern = r'<Relationships>.*?</Relationships>'

    entitys_match = re.search(entitys_pattern, response, re.DOTALL)
    relationships_match = re.search(relationships_pattern, response, re.DOTALL)

    xml_content = ""

    if entitys_match:
        xml_content += entitys_match.group(0) + "\n"

    if relationships_match:
        xml_content += relationships_match.group(0)

    # 如果没有找到匹配，返回完整响应
    if not xml_content:
        # 尝试提取```xml和```之间的内容
        xml_block_pattern = r'```xml\s*(.*?)\s*```'
        xml_block_match = re.search(xml_block_pattern, response, re.DOTALL)

        if xml_block_match:
            return xml_block_match.group(1)
        else:
            return response

    return xml_content

def process_batch_results(results_file: str, output_dir: str) -> Dict[str, Any]:
    """处理批量推理结果文件

    Args:
        results_file: 结果文件路径
        output_dir: 输出目录

    Returns:
        Dict[str, Any]: 处理统计信息
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 统计信息
    stats = {
        "total_results": 0,
        "processed_results": 0,
        "failed_results": 0,
        "start_time": time.time(),
        "end_time": None,
        "elapsed_time": None
    }

    try:
        # 读取结果文件
        with open(results_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        stats["total_results"] = len(lines)
        print(f"共有 {stats['total_results']} 个结果需要处理")

        # 处理每个结果
        for i, line in enumerate(lines):
            try:
                # 解析JSON
                result = json.loads(line)

                # 获取custom_id
                custom_id = result.get("custom_id", f"unknown_{i}")

                # 获取响应内容
                response = result.get("response", {})
                
                # 处理SiliconCloud API的特殊响应结构
                # 检查是否有body字段，这是SiliconCloud API的特殊结构
                if "body" in response:
                    body = response.get("body", {})
                    choices = body.get("choices", [])
                else:
                    # 兼容旧的直接结构
                    choices = response.get("choices", [])

                if not choices:
                    print(f"结果 {custom_id} 没有choices字段")
                    stats["failed_results"] += 1
                    continue

                # 获取消息内容
                message = choices[0].get("message", {})
                content = message.get("content", "")

                if not content:
                    print(f"结果 {custom_id} 没有content字段")
                    stats["failed_results"] += 1
                    continue

                # 提取XML内容
                xml_content = extract_xml_from_response(content)

                # 解析custom_id获取年份和文件名
                parts = custom_id.split('_')
                if len(parts) >= 2:
                    year = parts[0]

                    # 创建年份目录
                    year_dir = os.path.join(output_dir, year)
                    os.makedirs(year_dir, exist_ok=True)

                    # 构建输出文件路径
                    output_file = os.path.join(year_dir, f"{custom_id}.xml")
                else:
                    # 如果无法解析custom_id，使用默认输出文件路径
                    output_file = os.path.join(output_dir, f"{custom_id}.xml")

                # 保存XML内容
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(xml_content)

                stats["processed_results"] += 1

                # 每处理10个结果打印一次进度
                if (i + 1) % 10 == 0:
                    print(f"已处理 {i + 1}/{stats['total_results']} 个结果...")

            except Exception as e:
                print(f"处理结果 {i} 时发生错误: {str(e)}")
                stats["failed_results"] += 1

        # 计算处理时间
        stats["end_time"] = time.time()
        stats["elapsed_time"] = round(stats["end_time"] - stats["start_time"], 2)

        print(f"\n批量推理结果处理完成:")
        print(f"- 总结果数: {stats['total_results']}")
        print(f"- 处理成功数: {stats['processed_results']}")
        print(f"- 处理失败数: {stats['failed_results']}")
        print(f"- 处理时间: {stats['elapsed_time']} 秒")

        return stats

    except Exception as e:
        print(f"处理批量推理结果时发生错误: {str(e)}")
        stats["end_time"] = time.time()
        stats["elapsed_time"] = round(stats["end_time"] - stats["start_time"], 2)
        return stats

if __name__ == "__main__":
    #指定结果文件和输出目录
    results_file = "kg/data_process/batch_inference/results/batch_results_batch_igmtythevy.jsonl"
    output_dir = "kg/data_process/extracted_entities"
    
    #处理结果
    stats = process_batch_results(results_file, output_dir)
    
    #保存处理统计信息
    stats_file = "kg/data_process/batch_inference/test_stats.json"
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"统计信息已保存至: {stats_file}")
