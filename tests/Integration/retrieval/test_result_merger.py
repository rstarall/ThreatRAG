#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ResultMerger 集成测试

要求：不使用任何 mock。
ResultMerger 是纯内存组件，通过 fixture 注入真实的 retrieval 结果来验证合并逻辑。
"""

import os
import sys

# 从 tests/Integration/retrieval/ 向上四层到达项目根目录
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

import pytest  # noqa: E402  (isort:skip)

from src.core.retrieval import ResultMerger  # noqa: E402  (isort:skip)


# =============================================================================
# Tests — ResultMerger
# =============================================================================

class TestResultMergerInit:
    """ResultMerger 初始化"""

    def test_init_no_exception(self):
        """初始化不应抛出异常"""
        rm = ResultMerger()
        assert rm is not None


class TestMergeKnowledgeResults:
    """merge_knowledge_results 测试"""

    def test_merge_empty_inputs(self):
        """空输入应返回空列表"""
        rm = ResultMerger()
        result = rm.merge_knowledge_results([], {})
        assert result == []
        assert isinstance(result, list)

    def test_merge_kb_only(self):
        """仅有知识库结果时"""
        rm = ResultMerger()
        kb_results = [
            {
                "id": "chunk_1",
                "distance": 0.85,
                "entity": {
                    "text": "APT29 使用 Cobalt Strike 进行攻击",
                    "metadata": {"filename": "apt29.txt"}
                }
            },
            {
                "id": "chunk_2",
                "distance": 0.72,
                "entity": {
                    "text": "APT41 攻击医疗行业",
                    "metadata": {"filename": "apt41.txt"}
                }
            },
        ]
        merged = rm.merge_knowledge_results(kb_results, {})
        assert len(merged) == 2
        # 所有结果来源应为 knowledge_base
        assert all(r["source"] == "knowledge_base" for r in merged)
        # 按分数降序排列
        scores = [r["score"] for r in merged]
        assert scores == sorted(scores, reverse=True)

    def test_merge_graph_only(self):
        """仅有图谱结果时"""
        rm = ResultMerger()
        graph_results = {
            "nodes": [
                {
                    "entity_name": "APT29",
                    "entity_type": "attacker",
                    "entity_id": "e1",
                    "entity_sub_type": "apt",
                    "labels": ["APT"],
                    "times": [],
                    "entity_variant_names": ["Cozy Bear"],
                    "properties": {},
                },
                {
                    "entity_name": "CobaltStrike",
                    "entity_type": "tool",
                    "entity_id": "e2",
                    "entity_sub_type": "beacon",
                    "labels": ["malware"],
                    "times": [],
                    "entity_variant_names": [],
                    "properties": {},
                },
            ],
            "edges": [
                {
                    "source": "APT29",
                    "target": "CobaltStrike",
                    "relationship_type": "use",
                }
            ]
        }
        merged = rm.merge_knowledge_results([], graph_results)
        assert len(merged) == 2
        assert all(r["source"] == "graph" for r in merged)

    def test_merge_both_sources(self):
        """KB 和图谱都有结果时"""
        rm = ResultMerger()
        kb_results = [
            {
                "id": "chunk_1",
                "distance": 0.90,
                "entity": {
                    "text": "APT29 是高级持续性威胁组织",
                    "metadata": {"filename": "apt29.txt"}
                }
            },
        ]
        graph_results = {
            "nodes": [
                {
                    "entity_name": "APT29",
                    "entity_type": "attacker",
                    "entity_id": "e1",
                    "entity_sub_type": "apt",
                    "labels": [],
                    "times": [],
                    "entity_variant_names": [],
                    "properties": {},
                },
            ],
            "edges": []
        }
        merged = rm.merge_knowledge_results(kb_results, graph_results)
        assert len(merged) == 2
        sources = [r["source"] for r in merged]
        assert "knowledge_base" in sources
        assert "graph" in sources

    def test_merge_custom_weights(self):
        """自定义权重配置"""
        rm = ResultMerger()
        kb_results = [
            {
                "id": "chunk_1",
                "distance": 1.0,
                "entity": {"text": "APT29", "metadata": {}}
            },
        ]
        graph_results = {
            "nodes": [
                {
                    "entity_name": "APT29",
                    "entity_type": "attacker",
                    "entity_id": "e1",
                    "entity_sub_type": "",
                    "labels": [],
                    "times": [],
                    "entity_variant_names": [],
                    "properties": {},
                },
            ],
            "edges": []
        }
        merged = rm.merge_knowledge_results(
            kb_results, graph_results,
            weights={"knowledge_base": 0.5, "graph": 0.5}
        )
        kb_item = next(r for r in merged if r["source"] == "knowledge_base")
        # KB score = distance * weight = 1.0 * 0.5 = 0.5
        assert kb_item["score"] == 0.5


class TestDeduplicateResults:
    """deduplicate_results 测试"""

    def test_dedup_empty(self):
        """空列表返回空列表"""
        rm = ResultMerger()
        result = rm.deduplicate_results([])
        assert result == []

    def test_dedup_no_duplicates(self):
        """无重复时应保留所有结果"""
        rm = ResultMerger()
        results = [
            {"content": "APT29 使用 Cobalt Strike", "score": 0.9},
            {"content": "APT41 攻击医疗行业", "score": 0.7},
            {"content": "SolarWinds 供应链攻击", "score": 0.6},
        ]
        deduped = rm.deduplicate_results(results)
        assert len(deduped) == 3

    def test_dedup_exact_duplicate(self):
        """完全相同内容应去重"""
        rm = ResultMerger()
        results = [
            {"content": "APT29 使用 Cobalt Strike", "score": 0.9},
            {"content": "APT29 使用 Cobalt Strike", "score": 0.7},
            {"content": "APT41 攻击医疗行业", "score": 0.6},
        ]
        deduped = rm.deduplicate_results(results, similarity_threshold=0.8)
        # 保留高分结果
        assert len(deduped) <= 2
        # 保留的应是 score=0.9 的那条
        top = max(deduped, key=lambda x: x["score"])
        assert top["score"] == 0.9

    def test_dedup_high_threshold(self):
        """高相似度阈值（0.95）应保留更多结果"""
        rm = ResultMerger()
        results = [
            {"content": "APT29 使用 Cobalt Strike 进行攻击", "score": 0.9},
            {"content": "APT29 使用 Cobalt Strike 进行网络渗透", "score": 0.8},
            {"content": "APT41 攻击医疗行业", "score": 0.6},
        ]
        deduped = rm.deduplicate_results(results, similarity_threshold=0.95)
        # 两个相似的描述去重后保留 1 个，加上第 3 个
        assert len(deduped) >= 2

    def test_dedup_low_threshold(self):
        """低相似度阈值（0.5）应触发更多去重"""
        rm = ResultMerger()
        results = [
            {"content": "APT29 使用 Cobalt Strike", "score": 0.9},
            {"content": "APT41 攻击医疗行业", "score": 0.8},
            {"content": "SolarWinds 供应链被攻击", "score": 0.7},
        ]
        deduped = rm.deduplicate_results(results, similarity_threshold=0.5)
        # 三个内容都不同，理论上都应保留
        assert len(deduped) == 3

    def test_dedup_preserves_order(self):
        """去重后结果顺序应按原始分数降序排列"""
        rm = ResultMerger()
        results = [
            {"content": "低分结果", "score": 0.3},
            {"content": "APT29 使用 Cobalt Strike 进行攻击", "score": 0.9},
            {"content": "APT29 使用 Cobalt Strike 进行横向移动", "score": 0.8},
        ]
        deduped = rm.deduplicate_results(results)
        scores = [r["score"] for r in deduped]
        assert scores == sorted(scores, reverse=True)


class TestRankResultsByRelevance:
    """rank_results_by_relevance 测试"""

    def test_rank_basic(self):
        """相关性排序应提升包含查询词的结果分数"""
        rm = ResultMerger()
        results = [
            {"content": "APT41 攻击游戏行业", "score": 0.6},   # 不含 APT29
            {"content": "APT29 使用 Cobalt Strike", "score": 0.6},  # 含 APT29
        ]
        ranked = rm.rank_results_by_relevance(results, "APT29")
        scores = {r["content"]: r["score"] for r in ranked}
        # 含 APT29 的分数应提升
        assert scores["APT29 使用 Cobalt Strike"] > 0.6
        # 不含 APT29 的分数保持不变
        assert scores["APT41 攻击游戏行业"] == 0.6

    def test_rank_no_overlap(self):
        """无词汇重叠时分数不变"""
        rm = ResultMerger()
        results = [
            {"content": "SolarWinds 供应链攻击事件", "score": 0.7},
        ]
        ranked = rm.rank_results_by_relevance(results, "APT29 完全不相关查询")
        assert ranked[0]["score"] == 0.7
        assert ranked[0].get("relevance_boost") == 0.0

    def test_rank_empty_query(self):
        """空查询不应崩溃"""
        rm = ResultMerger()
        results = [
            {"content": "APT29", "score": 0.5},
        ]
        ranked = rm.rank_results_by_relevance(results, "")
        assert len(ranked) == 1

    def test_rank_empty_results(self):
        """空结果列表应直接返回"""
        rm = ResultMerger()
        ranked = rm.rank_results_by_relevance([], "APT29")
        assert ranked == []

    def test_rank_relevance_boost_added(self):
        """每个结果应添加 relevance_boost 字段"""
        rm = ResultMerger()
        results = [
            {"content": "APT29 使用 Cobalt Strike", "score": 0.8},
        ]
        ranked = rm.rank_results_by_relevance(results, "APT29")
        assert "relevance_boost" in ranked[0]
        assert isinstance(ranked[0]["relevance_boost"], float)


class TestFormatResultsForDisplay:
    """format_results_for_display 测试"""

    def test_format_basic(self):
        """格式化结果应包含 rank、source、content、score、metadata"""
        rm = ResultMerger()
        results = [
            {
                "source": "knowledge_base",
                "content": "APT29 使用 Cobalt Strike 进行攻击" * 50,
                "score": 0.8765,
                "metadata": {"filename": "apt29.txt", "id": "chunk_1"},
            }
        ]
        formatted = rm.format_results_for_display(results, max_results=5)
        assert len(formatted) == 1
        item = formatted[0]
        assert item["rank"] == 1
        assert item["source"] == "knowledge_base"
        assert "score" in item
        assert item["score"] == 0.8765
        # 长内容应被截断到 500 字符
        assert len(item["content"]) <= 503  # 500 + "..."
        assert item["content"].endswith("...")

    def test_format_max_results(self):
        """max_results 限制应生效"""
        rm = ResultMerger()
        results = [
            {"source": "kb", "content": f"内容{i}", "score": 0.9 - i * 0.1, "metadata": {}}
            for i in range(20)
        ]
        formatted = rm.format_results_for_display(results, max_results=5)
        assert len(formatted) == 5

    def test_format_kb_fields(self):
        """KB 来源的结果应添加 filename 和 doc_id 字段"""
        rm = ResultMerger()
        results = [
            {
                "source": "knowledge_base",
                "content": "APT29",
                "score": 0.9,
                "metadata": {"filename": "apt29.txt", "id": "chunk_1"},
            }
        ]
        formatted = rm.format_results_for_display(results)
        item = formatted[0]
        assert "filename" in item
        assert "doc_id" in item
        assert item["filename"] == "apt29.txt"
        assert item["doc_id"] == "chunk_1"

    def test_format_graph_fields(self):
        """Graph 来源的结果应添加 entity_name、entity_type、labels 等字段"""
        rm = ResultMerger()
        results = [
            {
                "source": "graph",
                "content": "实体: APT29",
                "score": 0.5,
                "metadata": {
                    "entity_name": "APT29",
                    "entity_type": "attacker",
                    "entity_sub_type": "apt",
                    "labels": ["APT", "APT29"],
                    "times": ["2020", "2021"],
                    "entity_variant_names": ["Cozy Bear"],
                    "properties": {"country": "Russia"},
                },
            }
        ]
        formatted = rm.format_results_for_display(results)
        item = formatted[0]
        assert item["entity_name"] == "APT29"
        assert item["entity_type"] == "attacker"
        assert item["entity_sub_type"] == "apt"
        assert item["labels"] == ["APT", "APT29"]
        assert item["times"] == ["2020", "2021"]


class TestCreateResultSummary:
    """create_result_summary 测试"""

    def test_summary_empty(self):
        """空结果摘要应返回零值"""
        rm = ResultMerger()
        summary = rm.create_result_summary([])
        assert summary["total_results"] == 0
        assert summary["average_score"] == 0.0
        assert summary["top_score"] == 0.0
        assert summary["sources"] == {}

    def test_summary_basic(self):
        """正常结果摘要"""
        rm = ResultMerger()
        results = [
            {"source": "knowledge_base", "score": 0.9},
            {"source": "knowledge_base", "score": 0.7},
            {"source": "graph", "score": 0.5},
        ]
        summary = rm.create_result_summary(results)
        assert summary["total_results"] == 3
        assert summary["average_score"] == pytest.approx((0.9 + 0.7 + 0.5) / 3)
        assert summary["top_score"] == 0.9
        assert summary["sources"]["knowledge_base"] == 2
        assert summary["sources"]["graph"] == 1

    def test_summary_score_distribution(self):
        """分数分布统计应正确（high >=0.8, medium 0.5-0.8, low <0.5）"""
        rm = ResultMerger()
        results = [
            {"source": "kb", "score": 0.95},  # high
            {"source": "kb", "score": 0.85},  # high
            {"source": "kb", "score": 0.60},  # medium
            {"source": "graph", "score": 0.30},  # low
        ]
        summary = rm.create_result_summary(results)
        dist = summary["score_distribution"]
        assert dist["high"] == 2
        assert dist["medium"] == 1
        assert dist["low"] == 1


class TestFullPipeline:
    """ResultMerger 完整 pipeline 测试（模拟真实检索结果处理流程）"""

    def test_full_pipeline_with_real_structure(self):
        """模拟真实检索结果结构，执行完整处理流程"""
        rm = ResultMerger()

        # 模拟 KB 检索结果（从 Milvus 返回）
        kb_results = [
            {
                "id": "kb_chunk_1",
                "distance": 0.92,
                "entity": {
                    "text": "APT29（别名 Cozy Bear）是俄罗斯对外情报局下属的高级持续性威胁组织，主要使用鱼叉式钓鱼邮件进行初始访问",
                    "metadata": {"filename": "apt29_overview.txt"}
                }
            },
            {
                "id": "kb_chunk_2",
                "distance": 0.88,
                "entity": {
                    "text": "Cobalt Strike 是商业渗透测试框架，被 APT29 等组织广泛用于横向移动和 C&C 通信",
                    "metadata": {"filename": "cobalt_strike.txt"}
                }
            },
        ]

        # 模拟图谱检索结果（从 Neo4j 返回）
        graph_results = {
            "nodes": [
                {
                    "entity_name": "APT29",
                    "entity_type": "attacker",
                    "entity_id": "neo4j_node_1",
                    "entity_sub_type": "apt_group",
                    "labels": ["APT", "SVR"],
                    "times": ["2008"],
                    "entity_variant_names": ["Cozy Bear"],
                    "properties": {"country": "Russia"},
                },
                {
                    "entity_name": "CobaltStrike",
                    "entity_type": "tool",
                    "entity_id": "neo4j_node_2",
                    "entity_sub_type": "beacon",
                    "labels": ["malware"],
                    "times": [],
                    "entity_variant_names": ["CobaltStrike"],
                    "properties": {},
                },
            ],
            "edges": [
                {
                    "source": "APT29",
                    "target": "CobaltStrike",
                    "relationship_type": "use",
                    "relationship_id": "neo4j_edge_1",
                    "source_id": "neo4j_node_1",
                    "target_id": "neo4j_node_2",
                }
            ]
        }

        # Step 1: 合并两个来源
        merged = rm.merge_knowledge_results(kb_results, graph_results)
        print(f"\n[Test] 合并后结果数: {len(merged)}")
        assert len(merged) == 4  # 2 KB + 2 graph nodes
        sources = [r["source"] for r in merged]
        assert "knowledge_base" in sources
        assert "graph" in sources

        # Step 2: 去重（这个场景下应无重复）
        deduped = rm.deduplicate_results(merged, similarity_threshold=0.8)
        assert len(deduped) == 4

        # Step 3: 相关性重排（查询 APT29 相关信息）
        ranked = rm.rank_results_by_relevance(deduped, "APT29 使用了什么工具")
        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True), "结果应按分数降序"

        # Step 4: 格式化用于展示
        formatted = rm.format_results_for_display(ranked, max_results=10)
        assert len(formatted) == 4
        for item in formatted:
            assert "rank" in item
            assert "source" in item
            assert "score" in item
            assert "content" in item

        # Step 5: 生成摘要
        summary = rm.create_result_summary(formatted)
        print(f"[Test] 摘要: total={summary['total_results']}, "
              f"avg_score={summary['average_score']:.2f}, "
              f"distribution={summary['score_distribution']}")
        assert summary["total_results"] == 4
        assert summary["average_score"] > 0
        assert summary["top_score"] > 0


# =============================================================================
# 主入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# -----------------------------------------------------------------------------
# pytest 运行命令
# -----------------------------------------------------------------------------
# 完整测试：
#   pytest tests/Integration/retrieval/test_result_merger.py -v -s
#
# 按测试类运行：
#   pytest tests/Integration/retrieval/test_result_merger.py::TestResultMergerInit -v
#   pytest tests/Integration/retrieval/test_result_merger.py::TestMergeKnowledgeResults -v
#   pytest tests/Integration/retrieval/test_result_merger.py::TestDeduplicateResults -v
#   pytest tests/Integration/retrieval/test_result_merger.py::TestRankResultsByRelevance -v
#   pytest tests/Integration/retrieval/test_result_merger.py::TestFormatResultsForDisplay -v
#   pytest tests/Integration/retrieval/test_result_merger.py::TestCreateResultSummary -v
#   pytest tests/Integration/retrieval/test_result_merger.py::TestFullPipeline -v
#
# 单个测试用例运行：
#   pytest tests/Integration/retrieval/test_result_merger.py::TestMergeKnowledgeResults::test_merge_empty_inputs -v -s
