#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
提交批量推理任务到SiliconCloud

该脚本上传JSONL文件到SiliconCloud，并创建批量推理任务。
"""

import os
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def upload_batch_file(client, file_path: str) -> Dict[str, Any]:
    """上传批量推理输入文件

    Args:
        client: OpenAI客户端
        file_path: JSONL文件路径

    Returns:
        Dict[str, Any]: 上传文件的响应
    """
    print(f"正在上传文件: {file_path}...")

    try:
        # 确保文件存在且可读
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 检查文件大小
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        print(f"文件大小: {file_size:.2f} MB")

        # 打开并上传文件
        with open(file_path, 'rb') as file:
            response = client.files.create(
                file=file,
                purpose="batch"
            )

        # 尝试从响应中获取文件ID
        file_id = None

        # 1. 直接从response对象获取id
        if hasattr(response, 'id') and response.id:
            file_id = response.id

        # 2. 从SiliconCloud特定的响应格式中获取
        elif hasattr(response, 'model_extra') and isinstance(response.model_extra, dict):
            if 'data' in response.model_extra and isinstance(response.model_extra['data'], dict):
                if 'id' in response.model_extra['data']:
                    file_id = response.model_extra['data']['id']

        if not file_id:
            raise ValueError("上传成功但未能从响应中提取文件ID")

        print(f"文件上传成功，文件ID: {file_id}")

        # 返回一个简单的字典，包含文件ID
        return {"id": file_id}
    except Exception as e:
        print(f"文件上传失败: {str(e)}")
        raise

def create_batch_job(client, input_file_id: str, model: str, completion_window: str = "24h") -> Dict[str, Any]:
    """创建批量推理任务

    Args:
        client: OpenAI客户端
        input_file_id: 输入文件ID
        model: 模型名称
        completion_window: 完成窗口时间

    Returns:
        Dict[str, Any]: 批量推理任务的响应
    """
    print(f"正在创建批量推理任务...")

    try:
        # 根据SiliconCloud文档创建批量推理任务
        response = client.batches.create(
            input_file_id=input_file_id,
            endpoint="/v1/chat/completions",
            completion_window=completion_window,
            metadata={
                "description": "Entity extraction from security reports"
            },
            extra_body={"replace": {"model": model}}
        )

        # 尝试从响应中获取批量任务ID
        batch_id = None

        # 1. 直接从response对象获取id
        if hasattr(response, 'id') and response.id:
            batch_id = response.id

        # 2. 从SiliconCloud特定的响应格式中获取
        elif hasattr(response, 'model_extra') and isinstance(response.model_extra, dict):
            if 'data' in response.model_extra and isinstance(response.model_extra['data'], dict):
                if 'id' in response.model_extra['data']:
                    batch_id = response.model_extra['data']['id']

        if not batch_id:
            raise ValueError("创建批量推理任务成功但未能从响应中提取任务ID")

        print(f"批量推理任务创建成功，任务ID: {batch_id}")

        # 返回一个简单的字典，包含批量任务ID
        return {"id": batch_id}
    except Exception as e:
        print(f"创建批量推理任务失败: {str(e)}")
        raise

def check_batch_status(client, batch_id: str) -> Dict[str, Any]:
    """检查批量推理任务状态

    Args:
        client: OpenAI客户端
        batch_id: 批量推理任务ID

    Returns:
        Dict[str, Any]: 批量推理任务的状态
    """
    try:
        # 根据SiliconCloud文档检查批量推理任务状态
        response = client.batches.retrieve(batch_id)

        # 创建一个标准的响应对象
        batch_status = {
            "id": batch_id,
            "status": "unknown",
            "request_counts": {
                "total": 0,
                "completed": 0,
                "failed": 0
            },
            "created_at": 0,
            "expires_at": 0,
            "output_file_id": "",
            "error_file_id": ""
        }

        # 1. 尝试直接从response对象获取状态信息
        if hasattr(response, 'status'):
            batch_status["status"] = response.status

            if hasattr(response, 'request_counts') and response.request_counts:
                if hasattr(response.request_counts, 'total'):
                    batch_status["request_counts"]["total"] = response.request_counts.total
                if hasattr(response.request_counts, 'completed'):
                    batch_status["request_counts"]["completed"] = response.request_counts.completed
                if hasattr(response.request_counts, 'failed'):
                    batch_status["request_counts"]["failed"] = response.request_counts.failed

            if hasattr(response, 'created_at'):
                batch_status["created_at"] = response.created_at
            if hasattr(response, 'expires_at'):
                batch_status["expires_at"] = response.expires_at
            if hasattr(response, 'output_file_id'):
                batch_status["output_file_id"] = response.output_file_id
            if hasattr(response, 'error_file_id'):
                batch_status["error_file_id"] = response.error_file_id

        # 2. 从SiliconCloud特定的响应格式中获取
        elif hasattr(response, 'model_extra') and isinstance(response.model_extra, dict):
            if 'data' in response.model_extra and isinstance(response.model_extra['data'], dict):
                data = response.model_extra['data']

                if 'status' in data:
                    batch_status["status"] = data['status']

                if 'request_counts' in data and isinstance(data['request_counts'], dict):
                    counts = data['request_counts']
                    if 'total' in counts:
                        batch_status["request_counts"]["total"] = counts['total']
                    if 'completed' in counts:
                        batch_status["request_counts"]["completed"] = counts['completed']
                    if 'failed' in counts:
                        batch_status["request_counts"]["failed"] = counts['failed']

                if 'created_at' in data:
                    batch_status["created_at"] = data['created_at']
                if 'expires_at' in data:
                    batch_status["expires_at"] = data['expires_at']
                if 'output_file_id' in data:
                    batch_status["output_file_id"] = data['output_file_id']
                if 'error_file_id' in data:
                    batch_status["error_file_id"] = data['error_file_id']

        # 打印状态信息
        print(f"批量推理任务状态: {batch_status['status']}")
        print(f"请求总数: {batch_status['request_counts']['total']}")
        print(f"已完成请求数: {batch_status['request_counts']['completed']}")
        print(f"失败请求数: {batch_status['request_counts']['failed']}")

        if batch_status['status'] == "completed":
            print(f"输出文件ID: {batch_status['output_file_id']}")
            print(f"错误文件ID: {batch_status['error_file_id']}")

        # 创建一个包含必要信息的对象返回
        class BatchStatusResponse:
            def __init__(self, data):
                self.id = data["id"]
                self.status = data["status"]
                self.created_at = data["created_at"]
                self.expires_at = data["expires_at"]
                self.output_file_id = data["output_file_id"]
                self.error_file_id = data["error_file_id"]

                # 创建请求计数对象
                class RequestCounts:
                    def __init__(self, counts):
                        self.total = counts["total"]
                        self.completed = counts["completed"]
                        self.failed = counts["failed"]

                self.request_counts = RequestCounts(data["request_counts"])

        return BatchStatusResponse(batch_status)
    except Exception as e:
        print(f"检查批量推理任务状态失败: {str(e)}")
        raise

def save_batch_info(batch_info: Dict[str, Any], output_file: str):
    """保存批量推理任务信息

    Args:
        batch_info: 批量推理任务信息
        output_file: 输出文件路径
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(batch_info, f, ensure_ascii=False, indent=2)

    print(f"批量推理任务信息已保存至: {output_file}")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='提交批量推理任务到SiliconCloud')

    parser.add_argument('--input_file', type=str, default='kg/data_process/batch_inference/batch_entity_extraction.jsonl',
                        help='输入JSONL文件路径')

    parser.add_argument('--model', type=str, default='deepseek-ai/DeepSeek-V3',
                        help='使用的模型名称')

    parser.add_argument('--completion_window', type=str, default='24h',
                        help='完成窗口时间')

    parser.add_argument('--api_key', type=str, default=None,
                        help='SiliconCloud API密钥，默认从环境变量API_KEY读取')

    parser.add_argument('--api_base', type=str, default='https://api.siliconflow.cn/v1',
                        help='SiliconCloud API基础URL')

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"输入文件不存在: {args.input_file}")
        exit(1)

    # 检查输入文件格式
    with open(args.input_file, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
        try:
            json_obj = json.loads(first_line)
            if not all(key in json_obj for key in ['custom_id', 'method', 'url', 'body']):
                print(f"输入文件格式不正确，缺少必要字段。第一行内容: {first_line}")
                print("每行必须包含custom_id, method, url, body字段")
                exit(1)
        except json.JSONDecodeError:
            print(f"输入文件不是有效的JSONL格式。第一行内容: {first_line}")
            exit(1)

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

        print(f"使用API基础URL: {args.api_base}")
        print(f"使用模型: {args.model}")

        # 上传批量推理输入文件
        batch_input_file = upload_batch_file(client, args.input_file)

        if not batch_input_file or "id" not in batch_input_file:
            print("上传文件成功但未获取到有效的文件ID，无法继续")
            exit(1)

        print(f"文件上传成功，准备创建批量推理任务...")

        # 创建批量推理任务
        batch_job = create_batch_job(
            client=client,
            input_file_id=batch_input_file["id"],
            model=args.model,
            completion_window=args.completion_window
        )

        if not batch_job or "id" not in batch_job:
            print("创建批量推理任务成功但未获取到有效的任务ID，无法继续")
            exit(1)

        # 检查批量推理任务状态
        batch_status = check_batch_status(client, batch_job["id"])

        # 保存批量推理任务信息
        batch_info = {
            "batch_id": batch_job["id"],
            "input_file_id": batch_input_file["id"],
            "model": args.model,
            "completion_window": args.completion_window,
            "status": batch_status.status,
            "created_at": batch_status.created_at,
            "expires_at": batch_status.expires_at,
            "request_counts": {
                "total": batch_status.request_counts.total,
                "completed": batch_status.request_counts.completed,
                "failed": batch_status.request_counts.failed
            }
        }

        batch_info_file = os.path.join(
            os.path.dirname(args.input_file),
            f"batch_job_{batch_job['id']}.json"
        )

        save_batch_info(batch_info, batch_info_file)

        print("\n批量推理任务已提交，请稍后检查状态")
        print(f"批量推理任务ID: {batch_job['id']}")
        print(f"批量推理任务信息已保存至: {batch_info_file}")

    except ImportError:
        print("未安装OpenAI库，请使用pip install openai安装")
        exit(1)
    except Exception as e:
        print(f"提交批量推理任务时发生错误: {str(e)}")
        # 打印更详细的错误信息
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        exit(1)
