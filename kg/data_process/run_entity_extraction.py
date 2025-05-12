import os
import sys
import time
import argparse
import traceback
from dotenv import load_dotenv
from entity_extraction_agent import EntityExtractionAgent

# 加载环境变量
load_dotenv()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='从安全报告中提取命名实体和关系')

    parser.add_argument('--input_dir', type=str, default='kg/data_spider/aptnote_text/pypdf',
                        help='输入目录，包含按年份组织的报告文件')

    parser.add_argument('--output_dir', type=str, default='kg/data_process/extracted_entities',
                        help='输出目录，用于保存提取的实体和关系')

    parser.add_argument('--model', type=str, default=None,
                        help='使用的LLM模型名称，默认从环境变量BASE_MODEL读取')

    parser.add_argument('--api_base', type=str, default=None,
                        help='OpenAI API基础URL，默认从环境变量API_BASE读取')

    parser.add_argument('--api_key', type=str, default=None,
                        help='OpenAI API密钥，默认从环境变量API_KEY读取')

    parser.add_argument('--temperature', type=float, default=0.2,
                        help='LLM温度参数')

    parser.add_argument('--max_tokens', type=int, default=4096,
                        help='LLM最大token数')

    parser.add_argument('--use_ollama', action='store_true',
                        help='是否使用Ollama而不是OpenAI')

    parser.add_argument('--prompt_template', type=str, default='kg/data_process/prompts/xml_prompt_cn.md',
                        help='提示词模板路径')

    parser.add_argument('--verbose', action='store_true',
                        help='是否显示详细日志')

    parser.add_argument('--single_file', type=str, default=None,
                        help='处理单个文件而不是整个目录')

    parser.add_argument('--year', type=str, default=None,
                        help='仅处理指定年份的报告')

    return parser.parse_args()

def print_stats(stats):
    """打印处理统计信息"""
    print("\n" + "="*50)
    print("处理统计信息:")
    print(f"总文件数: {stats['total_files']}")
    print(f"成功处理: {stats['success_count']}")
    print(f"处理失败: {stats['failed_count']}")
    print(f"总处理时间: {stats['total_time']:.2f}秒")

    if stats['total_files'] > 0:
        avg_time = stats['total_time'] / stats['total_files'] if stats['total_files'] > 0 else 0
        print(f"平均每个文件处理时间: {avg_time:.2f}秒")
        success_rate = (stats['success_count'] / stats['total_files']) * 100 if stats['total_files'] > 0 else 0
        print(f"成功率: {success_rate:.2f}%")

    if stats['failed_files']:
        print("\n失败的文件:")
        for file_path in stats['failed_files']:
            print(f"  - {file_path}")
    print("="*50)

def main():
    """主函数"""
    start_time = time.time()

    try:
        args = parse_args()

        print(f"开始处理，时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 创建实体提取代理
        agent = EntityExtractionAgent(
            model_name=args.model,
            api_base=args.api_base,
            api_key=args.api_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            verbose=args.verbose,
            use_ollama=args.use_ollama,
            prompt_template_path=args.prompt_template
        )

        # 创建输出目录
        os.makedirs(args.output_dir, exist_ok=True)

        # 统计信息
        stats = {
            "total_files": 0,
            "success_count": 0,
            "failed_count": 0,
            "total_time": 0.0,
            "failed_files": []
        }

        # 处理单个文件或整个目录
        if args.single_file:
            if os.path.exists(args.single_file):
                stats["total_files"] = 1
                output_file, elapsed_time, success = agent.process_report_file(args.single_file, args.output_dir)
                stats["total_time"] = elapsed_time

                if success:
                    stats["success_count"] = 1
                    print(f"\n处理完成: {args.single_file} -> {output_file}")
                else:
                    stats["failed_count"] = 1
                    stats["failed_files"].append(args.single_file)
            else:
                print(f"文件不存在: {args.single_file}")
        else:
            if args.year:
                # 仅处理指定年份的报告
                year_dir = os.path.join(args.input_dir, args.year)
                if os.path.exists(year_dir) and os.path.isdir(year_dir):
                    print(f"处理年份: {args.year}")
                    year_stats = {
                        "total_files": 0,
                        "success_count": 0,
                        "failed_count": 0,
                        "total_time": 0.0,
                        "failed_files": []
                    }

                    year_start_time = time.time()

                    for file_name in os.listdir(year_dir):
                        if file_name.endswith('.txt'):
                            file_path = os.path.join(year_dir, file_name)
                            year_stats["total_files"] += 1

                            try:
                                _, elapsed_time, success = agent.process_report_file(file_path, args.output_dir)
                                year_stats["total_time"] += elapsed_time

                                if success:
                                    year_stats["success_count"] += 1
                                else:
                                    year_stats["failed_count"] += 1
                                    year_stats["failed_files"].append(file_path)
                            except Exception as e:
                                year_stats["failed_count"] += 1
                                year_stats["failed_files"].append(file_path)
                                print(f"处理文件时发生未预期错误: {file_path}, 错误: {str(e)}")

                    # 更新总统计信息
                    stats["total_files"] += year_stats["total_files"]
                    stats["success_count"] += year_stats["success_count"]
                    stats["failed_count"] += year_stats["failed_count"]
                    stats["total_time"] += year_stats["total_time"]
                    stats["failed_files"].extend(year_stats["failed_files"])

                    year_total_time = time.time() - year_start_time
                    print(f"\n年份 {args.year} 处理完成: 总共 {year_stats['total_files']} 个文件, 成功 {year_stats['success_count']}, 失败 {year_stats['failed_count']}, 总耗时 {year_total_time:.2f}秒")
                else:
                    print(f"年份目录不存在: {year_dir}")
            else:
                # 处理所有年份的报告
                stats = agent.process_reports_directory(args.input_dir, args.output_dir)

        # 打印统计信息
        print_stats(stats)

        total_time = time.time() - start_time
        print(f"\n全部处理完成，总耗时: {total_time:.2f}秒")
        print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    except KeyboardInterrupt:
        print("\n用户中断处理")
        total_time = time.time() - start_time
        print(f"中断时总耗时: {total_time:.2f}秒")
    except Exception as e:
        print(f"\n处理过程中发生错误: {str(e)}")
        traceback.print_exc()
        total_time = time.time() - start_time
        print(f"错误发生时总耗时: {total_time:.2f}秒")
        sys.exit(1)

if __name__ == "__main__":
    main()
