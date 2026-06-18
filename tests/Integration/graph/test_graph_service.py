#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphService 集成测试

要求：真实连接 Neo4j 数据库和 LLM API，不使用任何 mock。
测试前请确保环境变量配置正确：
    NEO4J_URL, NEO4J_USERNAME, NEO4J_PASSWORD
    SILICONFLOW_API_KEY 或 DEEPSEEK_API_KEY 等 LLM API Key
"""

import asyncio
import sys
import os
import time
import uuid

import pytest

# 从 tests/Integration/graph/ 向上四层到达项目根目录（F:/CWord/threat-rag/ThreatRAG）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# 加载 .env 环境变量（config.py 本身未调用 load_dotenv）
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

from src.services.graph_service import GraphService
from src.core.graph.graph_store import GraphStore
from src.models.graph_model import KnowledgeGraph, Entity, Relationship


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def gs():
    """为每个测试函数创建独立的 GraphService 实例。

    仅实例化核心组件（GraphExtractor），不初始化 GraphStore（Neo4j 连接），
    适用于只需要 LLM 抽取、不需要数据库保存/查询的场景。
    """
    service = GraphService()
    # 用一个空壳替换 graph_store，避免 GraphStore.__init__ 尝试连接 Neo4j
    service.graph_store = None
    yield service
    service.shutdown()


@pytest.fixture(scope="function")
def store():
    """为每个测试函数创建独立的 GraphStore 实例。"""
    store_instance = GraphStore()
    yield store_instance
    store_instance.close()


@pytest.fixture(scope="function")
def unique_prefix():
    """生成唯一前缀，用于隔离测试数据。"""
    return f"test_{uuid.uuid4().hex[:8]}"


# =============================================================================
# 辅助函数
# =============================================================================

def cleanup_test_data(store: GraphStore, prefix: str):
    """清理以指定前缀开头的测试节点和关系。"""
    try:
        store.client.write(
            """
            MATCH (n:Entity)
            WHERE n.entityName STARTS WITH $prefix
            DETACH DELETE n
            """,
            {"prefix": prefix}
        )
    except Exception:
        pass


# =============================================================================
# 测试用例
# =============================================================================

class TestGraphServiceBasic:

    def test_get_graph_info(self, gs):
        """测试获取图数据库基本信息"""
        result = gs.get_graph_info()
        assert result.get("status") == "success", f"获取图信息失败: {result}"
        assert "node_count" in result or "relationship_count" in result or "nodes" in result or "relationships" in result

    def test_get_graph_node_nonexistent(self, gs, unique_prefix):
        """测试查询不存在的节点应返回空结果"""
        result = gs.get_graph_node(f"NonExistentNode_{unique_prefix}_{time.time()}")
        assert result.get("status") == "success"
        assert result.get("nodes", result.get("edges", [])) == []

    def test_get_graph_nodes(self, gs):
        """测试获取图节点列表"""
        result = gs.get_graph_nodes(num=10)
        assert result.get("status") == "success"
        assert "nodes" in result
        assert "edges" in result
        assert "stats" in result


class TestTriplesOperations:

    def test_add_triples_success(self, gs, store, unique_prefix):
        """测试添加三元组并验证可以查询到"""
        prefix = unique_prefix
        triples = [
            {
                "subject": f"{prefix}_AttackerA",
                "predicate": "use",
                "object": f"{prefix}_ToolB",
                "subject_type": "attacker",
                "object_type": "tool",
            },
            {
                "subject": f"{prefix}_ToolB",
                "predicate": "target",
                "object": f"{prefix}_VictimC",
                "subject_type": "tool",
                "object_type": "victim",
            },
        ]

        add_result = gs.add_triples(triples, user_id="test_user")
        assert add_result.get("status") == "success", f"添加三元组失败: {add_result}"
        assert add_result.get("count") == 2

        time.sleep(0.5)

        node_result = gs.get_graph_node(f"{prefix}_AttackerA")
        assert node_result.get("status") == "success"
        assert len(node_result.get("nodes", [])) >= 1

        found = False
        for node in node_result.get("nodes", []):
            if node["name"] == f"{prefix}_AttackerA":
                found = True
                assert node["label"] == "attacker"
                break
        assert found, f"未找到测试节点 {prefix}_AttackerA"

        cleanup_test_data(store, prefix)

    def test_add_triples_empty_list(self, gs):
        """测试添加空三元组列表"""
        result = gs.add_triples([])
        assert result.get("status") == "success"
        assert result.get("count") == 0


class TestExtraction:

    def test_extract_entities_with_llm(self, gs, unique_prefix):
        """测试基于 LLM 的实体关系抽取"""
        test_text = (
            f"{unique_prefix}：APT29 组织使用 Cobalt Strike 对某金融公司发起攻击。"
            "攻击者通过钓鱼邮件获取了受害者域控权限，并部署了 Mimikatz 窃取凭据。"
            "恶意样本的 MD5 为 deadbeef1234567890abcdef，关联的 C&C 服务器 IP 为 1.2.3.4。"
        )

        print(f"\n[Test] 输入文本:\n{test_text}\n")

        result = gs.extract_entities(text=test_text, source="test")

        assert result.get("status") == "success", f"抽取失败: {result}"
        assert result.get("entity_count", 0) >= 1, "应至少抽取到 1 个实体"
        assert "task_id" in result

        # 输出 LLM 抽取结果
        entities = result.get("entities", [])
        relationships = result.get("relationships", [])
        # raw_xml = result.get("raw_xml")
        # print(f"[Test] ===== LLM 原始 XML =====")
        # print(raw_xml if raw_xml else "[Test] raw_xml 为空")
        # print(f"[Test] =======================\n")
        print(f"[Test] ===== LLM 抽取结果 =====")
        print(f"[Test] 实体数量: {len(entities)}")
        for e in entities:
            print(f"  - [{e.get('entity_type')}] {e.get('entity_name')}  (sub_type={e.get('entity_sub_type')}, labels={e.get('labels')})")
        print(f"[Test] 关系数量: {len(relationships)}")
        for r in relationships:
            print(f"  - [{r.get('source')} {r.get('relationship_type')} {r.get('target')}]")
        print(f"[Test] 处理耗时: {result.get('processing_time_ms', 0):.0f} ms")
        print(f"[Test] ==========================\n")

    @pytest.mark.skip(reason="需要 Neo4j 数据库连接，单独运行跳过")
    def test_extract_and_save(self, gs, store, unique_prefix):
        """测试抽取实体并保存到图数据库"""
        prefix = unique_prefix
        test_text = (
            f"{prefix}_TestCase：Lazarus Group 利用零日漏洞攻击某加密货币交易所。"
            "攻击者使用了定制化的后门程序，关联的比特币地址为 1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2。"
        )

        result = asyncio.run(gs.extract_and_save(text=test_text, source="integration_test"))

        assert result.get("status") == "success", f"extract_and_save 失败: {result}"
        assert result.get("saved") is True, "应标记为已保存"
        assert result.get("entity_count", 0) >= 1, "应至少抽取到 1 个实体"
        assert "saved_stats" in result

        time.sleep(1.0)

        cleanup_test_data(store, prefix)

    def test_extract_entities_async(self, gs, unique_prefix):
        """测试异步实体关系抽取"""
        prefix = unique_prefix
        test_text = (
            f"{prefix}_Async：DarkSide 勒索软件组织对 Colonial Pipeline 发起攻击，"
            "导致美国东海岸燃油管道被迫关闭。"
        )

        print(f"\n[Test] 提交异步抽取任务，文本长度: {len(test_text)}")
        task_id = gs.extract_entities_async(
            text=test_text,
            source="test_async",
            save_to_graph=False,
        )
        print(f"[Test] task_id = {task_id!r}")
        print(f"[Test] task_id 格式符合 task_ 前缀: {task_id.startswith('task_')}")

        print(f"[Test] 异步任务已提交，无需等待结果")
        assert task_id.startswith("task_"), "task_id 应以 task_ 开头"


class TestGraphStore:

    def test_store_save_and_query(self, store, unique_prefix):
        """测试 GraphStore 的直接保存和查询功能"""
        prefix = unique_prefix

        entities = [
            Entity(
                entity_id=f"{prefix}_store_e1",
                entity_name=f"{prefix}_PhishingEmail",
                entity_type="event",
                entity_sub_type="initial_access",
                labels=["T1566"],
                times=[],
            ),
            Entity(
                entity_id=f"{prefix}_store_e2",
                entity_name=f"{prefix}_TargetHost",
                entity_type="asset",
                entity_sub_type="endpoint",
                labels=[],
                times=[],
            ),
        ]

        relationships = [
            Relationship(
                relationship_id=f"{prefix}_store_r1",
                relationship_type="target",
                source=f"{prefix}_PhishingEmail",
                target=f"{prefix}_TargetHost",
            )
        ]

        kg = KnowledgeGraph(entities=entities, relationships=relationships)
        stats = store.save_knowledge_graph(kg)

        assert stats.get("nodes_created", 0) >= 2 or stats.get("relationships_created", 0) >= 1

        time.sleep(0.5)

        cleanup_test_data(store, prefix)

    def test_graph_store_is_running(self, store):
        """测试 GraphStore 状态检查"""
        assert store.is_running() is True


# =============================================================================
# 主入口（支持直接运行）
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""
pytest tests/Integration/graph/test_graph_service.py::TestExtraction -v -s

"""