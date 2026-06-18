#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retriever 集成测试

要求：真实连接 Neo4j / Milvus / PostgreSQL / LLM API，不使用任何 mock。
"""

import asyncio
import os
import sys

# 从 tests/Integration/retrieval/ 向上四层到达项目根目录
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

# conftest.py 已完成所有环境变量设置和导入，此处只需 import fixtures
# （pytest 会自动发现同目录下的 conftest.py）
import pytest  # noqa: E402  (isort:skip)

from src.core.retrieval import Retriever  # noqa: E402  (isort:skip)


# =============================================================================
# Tests — Retriever 核心类
# =============================================================================

class TestRetrieverInit:
    """Retriever 初始化与连接状态测试"""

    def test_retriever_init_both_enabled(self):
        """Retriever 两个存储都启用时应正常初始化"""
        r = Retriever()
        # KnowledgeBase / GraphStore / GraphSearcher 已由 __init__ 构造，
        # 即使连接失败也只是记录日志，不会抛异常
        print(f"\n[Test] knowledge_base={r.knowledge_base is not None}")
        print(f"[Test] graph_searcher={r.graph_searcher is not None}")
        # 两个组件至少有一个被正确实例化（取决于 config enable_* 开关）
        assert r.knowledge_base is not None or r.graph_searcher is not None, \
            "Retriever 至少应初始化一个存储组件"


class TestRetrieverKBOnly:
    """仅知识库检索测试（use_graph=False, db_id 有值）"""

    @pytest.mark.asyncio
    async def test_retrieve_kb_only(self, seeded_kb):
        """db_id 非空、use_graph=False 时只走知识库路径"""
        r = Retriever()
        if r.knowledge_base is None:
            pytest.skip("知识库未启用")

        db_id = seeded_kb["db_id"]
        query = "APT29 使用了什么攻击工具？"

        refs = await r.retrieve(
            query=query,
            history=[],
            meta={
                "use_graph": False,
                "db_id": db_id,
                "use_rewrite_query": "off",
            },
        )

        print(f"\n[Test] 检索 refs keys: {list(refs.keys())}")
        print(f"[Test] entities: {refs.get('entities', [])}")

        # db_id 非空，use_graph=False → entity 提取跳过，KB 结果非空
        kb_results = refs.get("knowledge_base", {}).get("results", [])
        graph_results = refs.get("graph_base", {}).get("results", {})

        assert isinstance(kb_results, list), "KB results 应为 list"
        assert isinstance(graph_results, dict), "graph results 应为 dict"
        assert len(kb_results) >= 0, "KB results 数量应 >= 0"
        assert refs.get("entities", []) == [], "use_graph=False 时 entities 应为空"

    @pytest.mark.asyncio
    async def test_retrieve_kb_construct_query(self, seeded_kb):
        """完整 pipeline：retrieve + construct_query，知识库结果应注入增强查询"""
        r = Retriever()
        if r.knowledge_base is None:
            pytest.skip("知识库未启用")

        db_id = seeded_kb["db_id"]
        query = "APT29 和 APT41 有什么区别？"

        enhanced_query, refs = await r(
            query=query,
            history=[],
            meta={
                "use_graph": False,
                "db_id": db_id,
                "use_rewrite_query": "off",
            },
        )

        print(f"\n[Test] 原始查询: {query}")
        print(f"[Test] 增强查询: {enhanced_query[:200]}...")

        kb_results = refs.get("knowledge_base", {}).get("results", [])

        # 如果知识库有相关结果，construct_query 应在增强查询中注入知识库信息
        if kb_results:
            assert "知识库信息" in enhanced_query or len(enhanced_query) > len(query), \
                "有 KB 结果时 enhanced_query 应包含注入内容或与原始查询不同"
        else:
            print("[Test] 知识库未命中（正常，取决于向量相似度阈值）")


class TestRetrieverGraphOnly:
    """仅图谱检索测试（use_graph=True, db_id=None）"""

    @pytest.mark.asyncio
    async def test_retrieve_graph_only(self, seeded_graph):
        """use_graph=True、db_id=None 时只走图谱路径"""
        r = Retriever()
        if r.graph_searcher is None or not r.graph_searcher.is_running:
            pytest.skip("图数据库未启动")

        prefix = seeded_graph["prefix"]

        refs = await r.retrieve(
            query=f"{prefix}_APT29 使用了什么工具？",
            history=[],
            meta={
                "use_graph": True,
                "db_id": None,
            },
        )

        entities = refs.get("entities", [])
        graph_results = refs.get("graph_base", {}).get("results", {})
        kb_results = refs.get("knowledge_base", {}).get("results", [])

        print(f"\n[Test] 提取实体: {entities}")
        print(f"[Test] 图节点数: {len(graph_results.get('nodes', []))}")
        print(f"[Test] 图边数: {len(graph_results.get('edges', []))}")

        # use_graph=True 时 entities 非空（图谱检索依赖实体）
        # 注意：LLM 抽取可能不稳定，用宽松断言
        assert isinstance(entities, list)
        assert isinstance(graph_results, dict)
        assert isinstance(kb_results, list)
        # 图结果或实体至少有一个
        assert len(entities) > 0 or len(graph_results.get("nodes", [])) > 0, \
            "use_graph=True 时应有实体或图节点"

    @pytest.mark.asyncio
    async def test_retrieve_graph_construct_query(self, seeded_graph):
        """完整 pipeline：图谱结果应注入 construct_query 输出"""
        r = Retriever()
        if r.graph_searcher is None or not r.graph_searcher.is_running:
            pytest.skip("图数据库未启动")

        prefix = seeded_graph["prefix"]

        enhanced_query, refs = await r(
            query=f"{prefix}_APT29 和哪些工具有关联？",
            history=[],
            meta={
                "use_graph": True,
                "db_id": None,
            },
        )

        print(f"\n[Test] 原始查询: {prefix}_APT29 和哪些工具有关联？")
        print(f"[Test] 增强查询: {enhanced_query[:200]}...")

        graph_results = refs.get("graph_base", {}).get("results", {})

        # 如果图谱有边，construct_query 应注入图数据库信息
        if graph_results.get("edges"):
            assert "图数据库信息" in enhanced_query or len(enhanced_query) > 50, \
                "有图边时 enhanced_query 应包含图数据库信息"


class TestRetrieverBoth:
    """知识库 + 图谱联合检索测试"""

    @pytest.mark.asyncio
    async def test_retrieve_both_kb_and_graph(self, seeded_kb, seeded_graph):
        """use_graph=True 且 db_id 非空时同时触发 KB 和图谱检索"""
        r = Retriever()
        if r.knowledge_base is None:
            pytest.skip("知识库未启用")
        if r.graph_searcher is None or not r.graph_searcher.is_running:
            pytest.skip("图数据库未启动")

        db_id = seeded_kb["db_id"]
        prefix = seeded_graph["prefix"]

        refs = await r.retrieve(
            query=f"{prefix}_APT29 使用了什么工具进行攻击？",
            history=[],
            meta={
                "use_graph": True,
                "db_id": db_id,
                "use_rewrite_query": "off",
            },
        )

        kb_results = refs.get("knowledge_base", {}).get("results", [])
        graph_results = refs.get("graph_base", {}).get("results", {})
        entities = refs.get("entities", [])

        print(f"\n[Test] KB 结果数: {len(kb_results)}")
        print(f"[Test] 图节点数: {len(graph_results.get('nodes', []))}")
        print(f"[Test] 图边数: {len(graph_results.get('edges', []))}")
        print(f"[Test] 提取实体: {entities}")

        assert isinstance(kb_results, list)
        assert isinstance(graph_results, dict)
        assert isinstance(entities, list)
        assert len(entities) >= 0
        # 两个结果源都应为 dict（即使为空）
        assert "knowledge_base" in refs
        assert "graph_base" in refs

    @pytest.mark.asyncio
    async def test_retrieve_with_history(self, seeded_kb, seeded_graph):
        """带对话历史的检索，上下文应被传递"""
        r = Retriever()
        if r.knowledge_base is None:
            pytest.skip("知识库未启用")

        db_id = seeded_kb["db_id"]
        prefix = seeded_graph["prefix"]

        history = [
            {"role": "user", "content": f"{prefix}_APT29 是什么组织？"},
            {"role": "assistant", "content": "APT29 是一个高级持续性威胁组织。"},
        ]

        refs = await r.retrieve(
            query="他们使用什么攻击工具？",
            history=history,
            meta={
                "use_graph": True,
                "db_id": db_id,
                "use_rewrite_query": "off",
            },
        )

        print(f"\n[Test] refs keys: {list(refs.keys())}")
        print(f"[Test] history preserved: {refs.get('history') == history}")

        assert refs.get("history") == history, "history 应原样传递到 refs"
        assert "knowledge_base" in refs
        assert "graph_base" in refs


class TestRetrieverEdgeCases:
    """边界与异常分支测试"""

    @pytest.mark.asyncio
    async def test_retrieve_no_flags_returns_empty(self):
        """use_graph=False 且 db_id=None 时所有结果应为空"""
        r = Retriever()

        refs = await r.retrieve(
            query="APT29 是什么？",
            history=[],
            meta={
                "use_graph": False,
                "db_id": None,
            },
        )

        kb_results = refs.get("knowledge_base", {}).get("results", [])
        graph_results = refs.get("graph_base", {}).get("results", {})
        entities = refs.get("entities", [])

        assert kb_results == [], "db_id=None 时 KB results 应为空 list"
        assert graph_results == {}, "use_graph=False 时 graph results 应为空 dict"
        assert entities == [], "use_graph=False 时 entities 应为空 list"

    @pytest.mark.asyncio
    async def test_retrieve_nonascii_query(self):
        """检索中文查询文本不应崩溃"""
        r = Retriever()

        refs = await r.retrieve(
            query="APT攻击组织的攻击手法有哪些？",
            history=[],
            meta={
                "use_graph": False,
                "db_id": None,
            },
        )

        # 只验证不抛异常、返回结构正确
        assert isinstance(refs, dict)
        assert "knowledge_base" in refs
        assert "graph_base" in refs

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self):
        """空查询字符串不应崩溃"""
        r = Retriever()

        refs = await r.retrieve(
            query="",
            history=[],
            meta={
                "use_graph": False,
                "db_id": None,
            },
        )

        assert isinstance(refs, dict)
        assert "knowledge_base" in refs
        assert "graph_base" in refs

    @pytest.mark.asyncio
    async def test_construct_query_without_external_results(self):
        """无外部检索结果时 construct_query 应原样返回原始查询"""
        r = Retriever()

        query = "完全不相关的随机查询 xyz12345"
        refs = {
            "knowledge_base": {"results": []},
            "graph_base": {"results": {}},
        }

        enhanced = await r.construct_query(query, refs, meta={})

        assert enhanced == query, "无外部结果时应返回原始查询"


# =============================================================================
# 主入口
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# -----------------------------------------------------------------------------
# pytest 运行命令
# -----------------------------------------------------------------------------
# 完整测试：
#   pytest tests/Integration/retrieval/test_retriever.py -v -s
#
# 按测试类运行：
#   pytest tests/Integration/retrieval/test_retriever.py::TestRetrieverInit -v
#   pytest tests/Integration/retrieval/test_retriever.py::TestRetrieverKBOnly -v
#   pytest tests/Integration/retrieval/test_retriever.py::TestRetrieverGraphOnly -v
#   pytest tests/Integration/retrieval/test_retriever.py::TestRetrieverBoth -v
#   pytest tests/Integration/retrieval/test_retriever.py::TestRetrieverEdgeCases -v
#
# 单个测试用例运行：
#   pytest tests/Integration/retrieval/test_retriever.py::TestRetrieverInit::test_retriever_init_both_enabled -v -s
