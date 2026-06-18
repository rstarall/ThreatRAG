#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QueryProcessor 集成测试

要求：不使用任何 mock。
QueryProcessor 是纯内存组件，不直接依赖外部服务（不连接 Neo4j / Milvus）。
"""

import os
import sys

# 从 tests/Integration/retrieval/ 向上四层到达项目根目录
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

import pytest  # noqa: E402  (isort:skip)

from src.core.retrieval import QueryProcessor  # noqa: E402  (isort:skip)


# =============================================================================
# Tests — QueryProcessor
# =============================================================================

class TestQueryProcessorInit:
    """QueryProcessor 初始化"""

    def test_init_no_exception(self):
        """初始化不应抛出异常"""
        qp = QueryProcessor()
        assert qp is not None


class TestExtractKeywords:
    """extract_keywords 测试"""

    def test_extract_keywords_chinese(self):
        """中文文本关键词提取"""
        qp = QueryProcessor()
        keywords = qp.extract_keywords("APT29 是一个高级持续性威胁组织，使用 Cobalt Strike 和 Mimikatz 进行攻击")
        print(f"\n[Test] 中文关键词: {keywords}")
        assert isinstance(keywords, list)
        # 停用词（的、了、在、是、和）不应出现
        for kw in keywords:
            assert kw not in {"的", "了", "在", "是", "和", "与", "或", "但"}, \
                f"停用词 '{kw}' 不应出现在关键词中"

    def test_extract_keywords_english(self):
        """英文文本关键词提取"""
        qp = QueryProcessor()
        keywords = qp.extract_keywords(
            "APT29 is an advanced persistent threat group that uses Cobalt Strike and Mimikatz"
        )
        print(f"\n[Test] 英文关键词: {keywords}")
        assert isinstance(keywords, list)
        assert len(keywords) <= 10, "关键词数量不超过 10 个"

    def test_extract_keywords_mixed(self):
        """中英混合文本"""
        qp = QueryProcessor()
        keywords = qp.extract_keywords(
            "APT29 组织使用 Cobalt Strike 攻击目标系统"
        )
        print(f"\n[Test] 混合关键词: {keywords}")
        assert isinstance(keywords, list)
        assert len(keywords) <= 10

    def test_extract_keywords_limit(self):
        """关键词数量上限为 10"""
        qp = QueryProcessor()
        long_text = " ".join([f"关键词{i}" for i in range(50)])
        keywords = qp.extract_keywords(long_text)
        assert len(keywords) <= 10

    def test_extract_keywords_empty(self):
        """空字符串返回空列表"""
        qp = QueryProcessor()
        keywords = qp.extract_keywords("")
        assert keywords == []


class TestCleanQuery:
    """clean_query 测试"""

    def test_clean_query_whitespace(self):
        """多余空格应被合并"""
        qp = QueryProcessor()
        cleaned = qp.clean_query("APT29    是一个   高级威胁组织")
        assert "    " not in cleaned
        assert "   " not in cleaned
        assert cleaned == "APT29 是一个 高级威胁组织"

    def test_clean_query_special_chars(self):
        """特殊字符应被移除，保留中文、英文、数字和基本标点"""
        qp = QueryProcessor()
        cleaned = qp.clean_query("APT29@#$%^&*()是一个高级威胁组织！")
        # @#$%^&*() 应被移除，中文、英文、数字、! 应保留
        assert "@" not in cleaned
        assert "#" not in cleaned
        assert "$" not in cleaned
        assert "%" not in cleaned
        assert "^" not in cleaned
        assert "&" not in cleaned
        assert "*" not in cleaned
        assert "(" not in cleaned
        assert ")" not in cleaned

    def test_clean_query_preserves_punctuation(self):
        """基本标点（.,!?;:) 应保留"""
        qp = QueryProcessor()
        cleaned = qp.clean_query("APT29,是一个?高级威胁组织!")
        assert "," in cleaned
        assert "?" in cleaned
        assert "!" in cleaned

    def test_clean_query_chinese_chars(self):
        """中文字符应保留"""
        qp = QueryProcessor()
        cleaned = qp.clean_query("APT29是一个高级威胁组织")
        assert "是" in cleaned
        assert "一个" in cleaned
        assert "高级" in cleaned

    def test_clean_query_strip(self):
        """首尾空格应被去除"""
        qp = QueryProcessor()
        cleaned = qp.clean_query("  APT29是什么  ")
        assert cleaned == cleaned.strip()
        assert not cleaned.startswith(" ")
        assert not cleaned.endswith(" ")


class TestExpandQuery:
    """expand_query 测试"""

    def test_expand_query_basic(self):
        """扩展词应追加到原始查询"""
        qp = QueryProcessor()
        expanded = qp.expand_query("APT29", ["CobaltStrike", "Mimikatz"])
        print(f"\n[Test] 扩展查询: {expanded}")
        assert "APT29" in expanded
        assert "CobaltStrike" in expanded
        assert "Mimikatz" in expanded

    def test_expand_query_limit(self):
        """扩展词最多 3 个"""
        qp = QueryProcessor()
        expanded = qp.expand_query(
            "APT29",
            ["词1", "词2", "词3", "词4", "词5"]
        )
        # 原始查询 + 最多3个扩展词
        tokens = expanded.split()
        added_tokens = [t for t in tokens if t not in {"APT29"}]
        assert len(added_tokens) <= 3

    def test_expand_query_empty(self):
        """无扩展词时返回原始查询"""
        qp = QueryProcessor()
        expanded = qp.expand_query("APT29", [])
        assert expanded == "APT29"

    def test_expand_query_empty_list(self):
        """空列表扩展词"""
        qp = QueryProcessor()
        expanded = qp.expand_query("APT29", [])
        assert expanded == "APT29"


class TestAnalyzeQueryIntent:
    """analyze_query_intent 测试"""

    def test_intent_factual(self):
        """含"什么是"应识别为 factual 类型"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("APT29 是什么组织？")
        print(f"\n[Test] factual intent: {intent}")
        assert intent["query_type"] == "factual"
        assert intent["entity_focus"] is True

    def test_intent_procedural(self):
        """含"如何"、"怎么"应识别为 procedural 类型"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("APT29 如何发起攻击？")
        print(f"\n[Test] procedural intent: {intent}")
        assert intent["query_type"] == "procedural"

    def test_intent_comparative(self):
        """含"比较"、"对比"应识别为 comparative 类型"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("比较 APT29 和 APT41 的攻击手法")
        print(f"\n[Test] comparative intent: {intent}")
        assert intent["query_type"] == "comparative"

    def test_intent_general(self):
        """无特征词默认为 general 类型"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("APT29 最近有什么活动？")
        print(f"\n[Test] general intent: {intent}")
        assert intent["query_type"] == "general"

    def test_intent_entity_focus(self):
        """含机构/人名类词汇应标记 entity_focus"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("APT29 攻击了哪些公司？")
        assert intent["entity_focus"] is True

    def test_intent_temporal_focus(self):
        """含时间词汇应标记 temporal_focus"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("APT29 在2023年发起了什么攻击？")
        print(f"\n[Test] temporal intent: {intent}")
        assert intent["temporal_focus"] is True

    def test_intent_requires_reasoning(self):
        """含原因/影响类词汇应标记 requires_reasoning"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("APT29 攻击的原因是什么？")
        print(f"\n[Test] reasoning intent: {intent}")
        assert intent["requires_reasoning"] is True

    def test_intent_all_fields_present(self):
        """返回结构应包含所有必要字段"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("APT29 是什么？")
        assert "query_type" in intent
        assert "entity_focus" in intent
        assert "temporal_focus" in intent
        assert "requires_reasoning" in intent

    def test_intent_english_keywords(self):
        """英文关键词也应被识别"""
        qp = QueryProcessor()
        intent = qp.analyze_query_intent("What is APT29?")
        assert intent["query_type"] == "factual"

        intent2 = qp.analyze_query_intent("How does APT29 attack?")
        assert intent2["query_type"] == "procedural"


class TestQueryProcessorPipeline:
    """QueryProcessor 完整 pipeline 测试"""

    def test_full_pipeline(self):
        """模拟真实使用场景：清洗 -> 关键词提取 -> 意图分析 -> 扩展"""
        qp = QueryProcessor()

        raw_query = "  APT29,APT41是什么组织?   它们   和    比较有什么区别?!  "

        cleaned = qp.clean_query(raw_query)
        print(f"\n[Test] 清洗后: {cleaned}")
        assert "  " not in cleaned  # 无多余空格

        keywords = qp.extract_keywords(cleaned)
        print(f"[Test] 关键词: {keywords}")
        assert isinstance(keywords, list)

        intent = qp.analyze_query_intent(cleaned)
        print(f"[Test] 意图: {intent}")
        assert "query_type" in intent

        # "比较"使 intent_type = comparative，这里演示扩展词追加
        if intent["query_type"] == "comparative":
            expanded = qp.expand_query(cleaned, ["APT29", "APT41", "Lazarus"])
            print(f"[Test] 扩展后: {expanded}")
            assert "APT29" in expanded
            assert "APT41" in expanded


# =============================================================================
# 主入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# -----------------------------------------------------------------------------
# pytest 运行命令
# -----------------------------------------------------------------------------
# 完整测试：
#   pytest tests/Integration/retrieval/test_query_processor.py -v -s
#
# 按测试类运行：
#   pytest tests/Integration/retrieval/test_query_processor.py::TestQueryProcessorInit -v
#   pytest tests/Integration/retrieval/test_query_processor.py::TestExtractKeywords -v
#   pytest tests/Integration/retrieval/test_query_processor.py::TestCleanQuery -v
#   pytest tests/Integration/retrieval/test_query_processor.py::TestExpandQuery -v
#   pytest tests/Integration/retrieval/test_query_processor.py::TestAnalyzeQueryIntent -v
#   pytest tests/Integration/retrieval/test_query_processor.py::TestQueryProcessorPipeline -v
#
# 单个测试用例运行：
#   pytest tests/Integration/retrieval/test_query_processor.py::TestExtractKeywords::test_extract_keywords_chinese -v -s
