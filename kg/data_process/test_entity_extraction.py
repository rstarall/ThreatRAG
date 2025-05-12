import os
import time
from dotenv import load_dotenv
from entity_extraction_agent import EntityExtractionAgent

# 加载环境变量
load_dotenv()

def test_single_file():
    """测试处理单个文件"""
    # 创建实体提取代理
    agent = EntityExtractionAgent(
        # 配置将从环境变量中读取
        verbose=True
    )

    # 测试文件路径
    test_file = "kg/data_spider/aptnote_text/pypdf/2022/Ahnlab-APT-disguised-NorthKorean-defector-resume-VBS-script(03-29-2022).txt"
    output_dir = "kg/data_process/extracted_entities"

    # 处理测试文件
    start_time = time.time()
    output_file_path, elapsed_time, success = agent.process_report_file(test_file, output_dir)
    total_time = time.time() - start_time

    print(f"测试完成，输出文件: {output_file_path}")
    print(f"处理耗时: {elapsed_time:.2f}秒")
    print(f"总耗时: {total_time:.2f}秒")
    print(f"处理状态: {'成功' if success else '失败'}")

    # 显示输出文件内容
    if output_file_path and os.path.exists(output_file_path):
        with open(output_file_path, 'r', encoding='utf-8') as f:
            print("\n输出内容:")
            print(f.read())
    else:
        print("\n无法读取输出文件，可能处理失败")

if __name__ == "__main__":
    test_single_file()
