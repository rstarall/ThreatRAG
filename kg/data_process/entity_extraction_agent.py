import os
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

from langchain.agents import AgentType, initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain.callbacks.base import BaseCallbackHandler
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate

# 加载环境变量
load_dotenv()

class EntityExtractionAgent:
    """
    实体提取代理类，用于从安全报告中提取命名实体和关系
    """

    def __init__(
        self,
        model_name: str = None,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        verbose: bool = False,
        use_ollama: bool = False,
        prompt_template_path: str = "kg/data_process/prompts/xml_prompt_cn.md"
    ):
        """初始化实体提取代理

        Args:
            model_name: 模型名称，如果为None则从环境变量BASE_MODEL读取
            api_base: API基础URL，如果为None则从环境变量API_BASE读取
            api_key: API密钥，如果为None则从环境变量API_KEY读取
            temperature: 温度参数
            max_tokens: 最大token数
            verbose: 是否显示详细日志
            use_ollama: 是否使用ollama
            prompt_template_path: 提示词模板路径
        """
        # 从环境变量读取配置
        self.model_name = model_name or os.getenv("BASE_MODEL", "gpt-3.5-turbo-16k")
        self.api_base = api_base or os.getenv("API_BASE")
        self.api_key = api_key or os.getenv("API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.verbose = verbose
        self.use_ollama = use_ollama

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template(prompt_template_path)

    def _load_prompt_template(self, template_path: str) -> str:
        """加载提示词模板

        Args:
            template_path: 模板文件路径

        Returns:
            str: 提示词模板
        """
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        return template

    def _create_llm(self):
        """创建LLM实例

        Returns:
            LLM: LLM实例
        """
        if self.use_ollama:
            return ChatOllama(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        else:
            return ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                openai_api_base=self.api_base,
                openai_api_key=self.api_key
            )

    def extract_entities(self, report_text: str) -> str:
        """从报告文本中提取实体和关系

        Args:
            report_text: 报告文本

        Returns:
            str: 提取的实体和关系的XML格式
        """
        try:
            # 创建LLM实例
            llm = self._create_llm()

            # 创建提示词
            prompt = self.prompt_template.replace("{input}", report_text)

            # 调用LLM
            response = llm.invoke(prompt)

            # 提取XML内容
            xml_content = self._extract_xml_from_response(response.content)

            return xml_content
        except Exception as e:
            error_msg = f"提取实体时出错: {str(e)}"
            print(error_msg)
            # 返回一个包含错误信息的XML
            return f"""<Entitys>
                    <Entity>
                        <EntityId>error</EntityId>
                        <EntityName>Error</EntityName>
                        <EntityType>error</EntityType>
                        <EntitySubType>error</EntitySubType>
                        <Properties>
                            <Property name="error_message">{error_msg}</Property>
                        </Properties>
                    </Entity>
                </Entitys>
                <Relationships>
                </Relationships>"""

    def _extract_xml_from_response(self, response: str) -> str:
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

    def process_report_file(self, file_path: str, output_dir: str) -> Tuple[str, float, bool]:
        """处理单个报告文件

        Args:
            file_path: 报告文件路径
            output_dir: 输出目录

        Returns:
            Tuple[str, float, bool]: 输出文件路径, 处理时间(秒), 是否成功
        """
        start_time = time.time()
        success = True
        output_file_path = ""

        try:
            # 读取报告文件
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                report_text = f.read()

            # 提取文件名和年份
            file_name = os.path.basename(file_path)
            year_match = re.search(r'\((\d{2}-\d{2}-\d{4})\)', file_name)

            if year_match:
                date_str = year_match.group(1)
                try:
                    date_obj = datetime.strptime(date_str, '%m-%d-%Y')
                    year = str(date_obj.year)
                except ValueError:
                    # 如果日期格式不匹配，尝试从文件路径获取年份
                    year = os.path.basename(os.path.dirname(file_path))
            else:
                # 如果文件名中没有年份，从文件路径获取
                year = os.path.basename(os.path.dirname(file_path))

            # 创建输出目录
            output_year_dir = os.path.join(output_dir, year)
            os.makedirs(output_year_dir, exist_ok=True)

            # 提取实体和关系
            xml_content = self.extract_entities(report_text)

            # 保存结果
            output_file_path = os.path.join(output_year_dir, f"{os.path.splitext(file_name)[0]}.xml")
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            elapsed_time = time.time() - start_time
            print(f"已处理: {file_path} -> {output_file_path} (耗时: {elapsed_time:.2f}秒)")

        except Exception as e:
            elapsed_time = time.time() - start_time
            success = False
            print(f"处理文件失败: {file_path}, 错误: {str(e)} (耗时: {elapsed_time:.2f}秒)")

        return output_file_path, elapsed_time, success

    def process_reports_directory(self, input_dir: str, output_dir: str) -> Dict[str, Any]:
        """处理目录中的所有报告文件

        Args:
            input_dir: 输入目录
            output_dir: 输出目录

        Returns:
            Dict[str, Any]: 处理统计信息，包含成功数、失败数、总时间等
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 统计信息
        stats = {
            "total_files": 0,
            "success_count": 0,
            "failed_count": 0,
            "total_time": 0.0,
            "failed_files": []
        }

        start_total_time = time.time()

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
                            _, elapsed_time, success = self.process_report_file(file_path, output_dir)
                            stats["total_time"] += elapsed_time

                            if success:
                                stats["success_count"] += 1
                            else:
                                stats["failed_count"] += 1
                                stats["failed_files"].append(file_path)
                        except Exception as e:
                            stats["failed_count"] += 1
                            stats["failed_files"].append(file_path)
                            print(f"处理文件时发生未预期错误: {file_path}, 错误: {str(e)}")

                print(f"年份 {year_dir} 处理完成: {year_file_count} 个文件")

        stats["total_time"] = time.time() - start_total_time
        return stats


if __name__ == "__main__":
    # 创建实体提取代理
    agent = EntityExtractionAgent(
        # 配置将从环境变量中读取
        verbose=True
    )

    # 处理报告目录
    input_dir = "kg/data_spider/aptnote_text/pypdf"
    output_dir = "kg/data_process/extracted_entities"

    agent.process_reports_directory(input_dir, output_dir)
