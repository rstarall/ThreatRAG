#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
准备批量推理任务的输入文件

该脚本读取安全报告文件，结合提示词模板，生成SiliconCloud批量推理所需的JSONL格式文件。
每一行包含一个完整的API请求，用于从安全报告中提取命名实体和关系。
"""

import os
import json
import re
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid
import time
from datetime import datetime

def load_prompt_template(template_path: str) -> str:
    """加载提示词模板

    Args:
        template_path: 模板文件路径

    Returns:
        str: 提示词模板
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    return template

def read_report_file(file_path: str) -> str:
    """读取报告文件内容

    Args:
        file_path: 报告文件路径

    Returns:
        str: 报告文本内容
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        print(f"读取文件 {file_path} 时出错: {str(e)}")
        return ""

def create_batch_request(custom_id: str, report_text: str, prompt_template: str, model: str = "deepseek-ai/DeepSeek-V3") -> Dict[str, Any]:
    """创建批量请求对象

    Args:
        custom_id: 唯一请求ID
        report_text: 报告文本
        prompt_template: 提示词模板
        model: 使用的模型名称

    Returns:
        Dict[str, Any]: 批量请求对象
    """
    # 替换提示词模板中的{input}占位符
    prompt = prompt_template.replace("{input}", report_text)

    # 创建请求对象 - 确保格式符合SiliconCloud批量推理API要求
    request = {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的网络安全威胁情报分析助手，负责从网络安全报告中提取关键实体和它们之间的关系，以构建威胁情报知识图谱。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 4096
        }
    }

    # 验证请求对象格式
    if not all(key in request for key in ['custom_id', 'method', 'url', 'body']):
        raise ValueError(f"请求对象格式不正确，缺少必要字段: {request}")

    if not all(key in request['body'] for key in ['model', 'messages']):
        raise ValueError(f"请求体格式不正确，缺少必要字段: {request['body']}")

    return request

def process_reports_directory(input_dir: str, output_file: str, prompt_template_path: str, model: str) -> Dict[str, Any]:
    """处理目录中的所有报告文件，生成批量推理JSONL文件

    Args:
        input_dir: 输入目录
        output_file: 输出JSONL文件路径
        prompt_template_path: 提示词模板路径
        model: 使用的模型名称

    Returns:
        Dict[str, Any]: 处理统计信息
    """
    # 加载提示词模板
    prompt_template = load_prompt_template(prompt_template_path)

    # 统计信息
    stats = {
        "total_files": 0,
        "processed_files": 0,
        "skipped_files": 0,
        "total_size_mb": 0,
        "start_time": time.time(),
        "end_time": None,
        "elapsed_time": None
    }

    # 打开输出文件
    with open(output_file, 'w', encoding='utf-8') as f_out:
        # 遍历输入目录中的所有年份文件夹
        for year_dir in os.listdir(input_dir):
            year_path = os.path.join(input_dir, year_dir)

            # 检查是否是目录且名称是年份
            if os.path.isdir(year_path) and year_dir.isdigit():
                print(f"处理年份: {year_dir}")
                year_file_count = 0

                # 遍历年份目录中的所有文本文件
                for file_name in os.listdir(year_path):
                    if file_name.endswith('.txt'):
                        file_path = os.path.join(year_path, file_name)
                        stats["total_files"] += 1
                        year_file_count += 1

                        try:
                            # 读取报告文件
                            report_text = read_report_file(file_path)

                            if not report_text:
                                print(f"跳过空文件: {file_path}")
                                stats["skipped_files"] += 1
                                continue

                            # 创建唯一ID
                            custom_id = f"{year_dir}_{os.path.splitext(file_name)[0]}_{uuid.uuid4().hex[:8]}"

                            # 创建批量请求对象
                            request = create_batch_request(custom_id, report_text, prompt_template, model)

                            # 写入JSONL文件
                            f_out.write(json.dumps(request, ensure_ascii=False) + '\n')

                            stats["processed_files"] += 1

                            # 每处理10个文件打印一次进度
                            if stats["processed_files"] % 10 == 0:
                                print(f"已处理 {stats['processed_files']} 个文件...")

                        except Exception as e:
                            print(f"处理文件时发生错误: {file_path}, 错误: {str(e)}")
                            stats["skipped_files"] += 1

                print(f"年份 {year_dir} 处理完成: {year_file_count} 个文件")

    # 计算JSONL文件大小
    output_file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
    stats["total_size_mb"] = round(output_file_size, 2)

    # 计算处理时间
    stats["end_time"] = time.time()
    stats["elapsed_time"] = round(stats["end_time"] - stats["start_time"], 2)

    print(f"\n批量推理文件生成完成:")
    print(f"- 输出文件: {output_file}")
    print(f"- 文件大小: {stats['total_size_mb']} MB")
    print(f"- 总文件数: {stats['total_files']}")
    print(f"- 处理文件数: {stats['processed_files']}")
    print(f"- 跳过文件数: {stats['skipped_files']}")
    print(f"- 处理时间: {stats['elapsed_time']} 秒")

    return stats

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='准备批量推理任务的输入文件')

    parser.add_argument('--input_dir', type=str, default='kg/data_spider/aptnote_text/pypdf',
                        help='输入目录，包含按年份组织的报告文件')

    parser.add_argument('--output_file', type=str, default='kg/data_process/batch_inference/batch_entity_extraction.jsonl',
                        help='输出JSONL文件路径')

    parser.add_argument('--prompt_template', type=str, default='kg/data_process/prompts/xml_prompt_en.md',
                        help='提示词模板路径')

    parser.add_argument('--model', type=str, default='deepseek-ai/DeepSeek-V3',
                        help='使用的模型名称')

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

    # 检查提示词模板是否存在
    if not os.path.exists(args.prompt_template):
        print(f"提示词模板文件不存在: {args.prompt_template}")
        exit(1)

    # 检查输入目录是否存在
    if not os.path.exists(args.input_dir):
        print(f"输入目录不存在: {args.input_dir}")
        exit(1)

    try:
        # 处理报告目录
        stats = process_reports_directory(
            input_dir=args.input_dir,
            output_file=args.output_file,
            prompt_template_path=args.prompt_template,
            model=args.model
        )

        # 验证生成的JSONL文件
        print("\n验证生成的JSONL文件...")
        valid_lines = 0
        invalid_lines = 0

        with open(args.output_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                try:
                    json_obj = json.loads(line)
                    if all(key in json_obj for key in ['custom_id', 'method', 'url', 'body']):
                        valid_lines += 1
                    else:
                        invalid_lines += 1
                        print(f"第 {i+1} 行格式不正确，缺少必要字段")
                except json.JSONDecodeError:
                    invalid_lines += 1
                    print(f"第 {i+1} 行不是有效的JSON格式")

        print(f"验证结果: 有效行数 {valid_lines}, 无效行数 {invalid_lines}")

        if invalid_lines > 0:
            print("警告: JSONL文件包含无效行，可能导致批量推理任务失败")

        # 保存处理统计信息
        stats["valid_lines"] = valid_lines
        stats["invalid_lines"] = invalid_lines
        stats_file = os.path.splitext(args.output_file)[0] + '_stats.json'
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        print(f"统计信息已保存至: {stats_file}")

        # 显示使用说明
        print("\n下一步:")
        print(f"运行以下命令提交批量推理任务:")
        print(f"python submit_batch_job.py --input_file {args.output_file} --model {args.model}")

    except Exception as e:
        print(f"处理报告目录时发生错误: {str(e)}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        exit(1)
