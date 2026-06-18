# 批量推理实体提取

本目录包含用于通过SiliconCloud批量推理API从安全报告中提取命名实体和关系的脚本。

## 文件说明

- `prepare_batch_inference.py`: 准备批量推理任务的输入文件
- `submit_batch_job.py`: 提交批量推理任务到SiliconCloud
- `process_batch_results.py`: 处理批量推理任务的结果

## 使用流程

### 1. 准备批量推理任务的输入文件

```bash
python prepare_batch_inference.py --input_dir kg/data_spider/aptnote_text/pypdf --output_file kg/data_process/batch_inference/batch_entity_extraction.jsonl --prompt_template kg/data_process/prompts/xml_prompt_cn.md --model deepseek-ai/DeepSeek-V3
```

参数说明:
- `--input_dir`: 输入目录，包含按年份组织的报告文件
- `--output_file`: 输出JSONL文件路径
- `--prompt_template`: 提示词模板路径
- `--model`: 使用的模型名称

### 2. 提交批量推理任务到SiliconCloud

```bash
python submit_batch_job.py --input_file kg/data_process/batch_inference/batch_entity_extraction.jsonl --model deepseek-ai/DeepSeek-V3 --completion_window 24h --api_key YOUR_API_KEY
```

参数说明:
- `--input_file`: 输入JSONL文件路径
- `--model`: 使用的模型名称
- `--completion_window`: 完成窗口时间
- `--api_key`: SiliconCloud API密钥，默认从环境变量API_KEY读取
- `--api_base`: SiliconCloud API基础URL，默认为https://api.siliconflow.cn/v1

### 3. 处理批量推理任务的结果

```bash
python process_batch_results.py --batch_id batch_abc123 --output_dir kg/data_process/extracted_entities --api_key YOUR_API_KEY
```

参数说明:
- `--batch_id`: 批量推理任务ID
- `--output_dir`: 输出目录，用于保存提取的实体和关系
- `--api_key`: SiliconCloud API密钥，默认从环境变量API_KEY读取
- `--api_base`: SiliconCloud API基础URL，默认为https://api.siliconflow.cn/v1

## 环境变量配置

可以在`.env`文件中配置以下环境变量:

```
API_KEY=your_siliconcloud_api_key
```

## 支持的模型

目前SiliconCloud批量推理API支持以下模型:

- deepseek-ai/DeepSeek-V3
- deepseek-ai/DeepSeek-R1
- Qwen/QwQ-32B

## 批量推理价格

SiliconCloud平台模型推理价格表（单位：￥/百万Tokens）:

| 模型名称 | 批量推理 - 输入 | 批量推理 - 输出 |
|---------|--------------|--------------|
| DeepSeek-R1 | ¥2 | ¥8 |
| DeepSeek-V3 | ¥1 | ¥4 |
| Qwen/QwQ-32B | ¥0.5 | ¥2 |

## 示例

### 1. 准备批量推理任务的输入文件

```bash
python prepare_batch_inference.py
```

输出:
```
处理年份: 2022
已处理 10 个文件...
已处理 20 个文件...
年份 2022 处理完成: 25 个文件
处理年份: 2023
已处理 30 个文件...
年份 2023 处理完成: 15 个文件

批量推理文件生成完成:
- 输出文件: kg/data_process/batch_inference/batch_entity_extraction.jsonl
- 文件大小: 2.5 MB
- 总文件数: 40
- 处理文件数: 40
- 跳过文件数: 0
- 处理时间: 1.25 秒
统计信息已保存至: kg/data_process/batch_inference/batch_entity_extraction_stats.json
```

### 2. 提交批量推理任务到SiliconCloud

```bash
python submit_batch_job.py
```

输出:
```
正在上传文件: kg/data_process/batch_inference/batch_entity_extraction.jsonl...
文件上传成功，文件ID: file-abc123
正在创建批量推理任务...
批量推理任务创建成功，任务ID: batch_abc123
批量推理任务状态: in_queue
请求总数: 40
已完成请求数: 0
失败请求数: 0
批量推理任务信息已保存至: kg/data_process/batch_inference/batch_job_batch_abc123.json

批量推理任务已提交，请稍后检查状态
批量推理任务ID: batch_abc123
批量推理任务信息已保存至: kg/data_process/batch_inference/batch_job_batch_abc123.json
```

### 3. 处理批量推理任务的结果

```bash
python process_batch_results.py --batch_id batch_abc123
```

输出:
```
批量推理任务状态: completed
请求总数: 40
已完成请求数: 40
失败请求数: 0
输出文件ID: file-def456
错误文件ID: file-ghi789
正在下载文件ID: file-def456...
文件下载成功，已保存至: kg/data_process/batch_inference/batch_results_batch_abc123.jsonl
共有 40 个结果需要处理
已处理 10/40 个结果...
已处理 20/40 个结果...
已处理 30/40 个结果...
已处理 40/40 个结果...

批量推理结果处理完成:
- 总结果数: 40
- 处理成功数: 40
- 处理失败数: 0
- 处理时间: 2.5 秒
统计信息已保存至: kg/data_process/batch_inference/batch_results_batch_abc123_stats.json
正在下载文件ID: file-ghi789...
文件下载成功，已保存至: kg/data_process/batch_inference/batch_errors_batch_abc123.jsonl
错误文件已下载至: kg/data_process/batch_inference/batch_errors_batch_abc123.jsonl
```
