#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
处理批量推理任务的结果

该脚本下载批量推理任务的结果文件，并将提取的实体和关系保存为XML文件。
"""

import os
import json
import re
import argparse
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def download_from_url(url: str, output_file: str) -> str:
    """从URL下载文件

    Args:
        url: 文件URL
        output_file: 输出文件路径

    Returns:
        str: 输出文件路径
    """
    print(f"正在从URL下载文件: {url}...")

    try:
        # 发送GET请求
        response = requests.get(url, stream=True)
        response.raise_for_status()  # 如果请求失败，抛出异常

        # 保存文件
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"文件下载成功，已保存至: {output_file}")
        return output_file
    except Exception as e:
        print(f"从URL下载文件失败: {str(e)}")
        raise

def download_batch_results(client, file_id_or_url: str, output_file: str) -> str:
    """下载批量推理结果文件

    Args:
        client: OpenAI客户端，如果是URL下载则可以为None
        file_id_or_url: 文件ID或URL
        output_file: 输出文件路径

    Returns:
        str: 输出文件路径
    """
    # 判断是URL还是文件ID
    if file_id_or_url.startswith('http'):
        return download_from_url(file_id_or_url, output_file)

    print(f"正在下载文件ID: {file_id_or_url}...")

    try:
        # 获取文件内容
        response = client.files.content(file_id_or_url)
        content = response.read()

        # 保存文件
        with open(output_file, 'wb') as f:
            f.write(content)

        print(f"文件下载成功，已保存至: {output_file}")
        return output_file
    except Exception as e:
        print(f"文件下载失败: {str(e)}")
        raise

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

def check_batch_status(client, batch_id: str) -> Dict[str, Any]:
    """检查批量推理任务状态

    Args:
        client: OpenAI客户端
        batch_id: 批量推理任务ID

    Returns:
        Dict[str, Any]: 批量推理任务的状态
    """
    try:
        batch = client.batches.retrieve(batch_id)
        print(f"批量推理任务状态: {batch.status}")
        print(f"请求总数: {batch.request_counts.total}")
        print(f"已完成请求数: {batch.request_counts.completed}")
        print(f"失败请求数: {batch.request_counts.failed}")

        if batch.status == "completed":
            print(f"输出文件ID: {batch.output_file_id}")
            print(f"错误文件ID: {batch.error_file_id}")

        return batch
    except Exception as e:
        print(f"检查批量推理任务状态失败: {str(e)}")
        raise

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='处理批量推理任务的结果')

    # 批量任务相关参数
    parser.add_argument('--batch_id', type=str, default=None,
                        help='批量推理任务ID')

    # 直接URL下载相关参数
    parser.add_argument('--output_file_url', type=str, default=None,
                        help='输出文件的直接下载URL')

    parser.add_argument('--error_file_url', type=str, default=None,
                        help='错误文件的直接下载URL')

    # 通用参数
    parser.add_argument('--output_dir', type=str, default='kg/data_process/extracted_entities',
                        help='输出目录，用于保存提取的实体和关系')

    parser.add_argument('--api_key', type=str, default=None,
                        help='SiliconCloud API密钥，默认从环境变量API_KEY读取')

    parser.add_argument('--api_base', type=str, default='https://api.siliconflow.cn/v1',
                        help='SiliconCloud API基础URL')

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # 确保结果目录存在
    os.makedirs("kg/data_process/batch_inference/results", exist_ok=True)

    # 处理直接URL下载模式
    if args.output_file_url or args.error_file_url:
        try:
            # 下载输出文件
            if args.output_file_url:
                # 生成一个唯一的文件名
                timestamp = int(time.time())
                results_file = os.path.join(
                    "kg/data_process/batch_inference/results",
                    f"batch_results_{timestamp}.jsonl"
                )

                # 下载文件
                download_from_url(args.output_file_url, results_file)

                # 处理结果
                stats = process_batch_results(results_file, args.output_dir)

                # 保存处理统计信息
                stats_file = os.path.join(
                    "kg/data_process/batch_inference",
                    f"batch_results_{timestamp}_stats.json"
                )

                with open(stats_file, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)

                print(f"统计信息已保存至: {stats_file}")

            # 下载错误文件
            if args.error_file_url:
                timestamp = int(time.time())
                error_file = os.path.join(
                    "kg/data_process/batch_inference",
                    f"batch_errors_{timestamp}.jsonl"
                )

                download_from_url(args.error_file_url, error_file)
                print(f"错误文件已下载至: {error_file}")

        except Exception as e:
            print(f"处理直接URL下载时发生错误: {str(e)}")
            exit(1)

    # 处理批量任务ID模式
    elif args.batch_id:
        # 获取API密钥
        api_key = args.api_key or os.getenv("API_KEY")
        if not api_key:
            print("未提供API密钥，请通过--api_key参数或设置API_KEY环境变量提供")
            exit(1)

        try:
            # 导入OpenAI库
            from openai import OpenAI

            # 创建OpenAI客户端
            client = OpenAI(
                api_key=api_key,
                base_url=args.api_base
            )

            # 检查批量推理任务状态
            batch_status = check_batch_status(client, args.batch_id)

            # 如果任务已完成，下载并处理结果
            if batch_status.status == "completed":
                if batch_status.output_file_id:
                    # 下载输出文件
                    results_file = os.path.join(
                        "kg/data_process/batch_inference/results",
                        f"batch_results_{args.batch_id}.jsonl"
                    )

                    download_batch_results(client, batch_status.output_file_id, results_file)

                    # 处理结果
                    stats = process_batch_results(results_file, args.output_dir)

                    # 保存处理统计信息
                    stats_file = os.path.join(
                        "kg/data_process/batch_inference",
                        f"batch_results_{args.batch_id}_stats.json"
                    )

                    with open(stats_file, 'w', encoding='utf-8') as f:
                        json.dump(stats, f, ensure_ascii=False, indent=2)

                    print(f"统计信息已保存至: {stats_file}")

                # 如果有错误文件，也下载
                if batch_status.error_file_id:
                    error_file = os.path.join(
                        "kg/data_process/batch_inference",
                        f"batch_errors_{args.batch_id}.jsonl"
                    )

                    download_batch_results(client, batch_status.error_file_id, error_file)
                    print(f"错误文件已下载至: {error_file}")
            else:
                print(f"批量推理任务尚未完成，当前状态: {batch_status.status}")
                print("请等待任务完成后再运行此脚本")

        except ImportError:
            print("未安装OpenAI库，请使用pip install openai安装")
            exit(1)
        except Exception as e:
            print(f"处理批量推理任务结果时发生错误: {str(e)}")
            exit(1)

    else:
        print("错误: 必须提供批量任务ID (--batch_id) 或直接下载URL (--output_file_url)")
        print("示例:")
        print("1. 使用批量任务ID: python process_batch_results.py --batch_id batch_ugnxfqfqzz")
        print("2. 使用直接下载URL: python process_batch_results.py --output_file_url https://example.com/output.jsonl")
