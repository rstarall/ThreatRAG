#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Retriever 集成测试 — 共享 fixtures

要求：真实连接 Neo4j / Milvus / PostgreSQL / LLM API，不使用任何 mock。

连接地址说明：
    Docker Desktop 中服务名为容器名（neo4j / milvus-standalone / postgres），
    但从宿主机 localhost 访问时必须使用 bolt://localhost:7687 / localhost:19530 / localhost:5432。
    本 fixture 在加载配置前显式设置对应的环境变量，确保测试始终连到 localhost。
"""

import os
import sys
import time
import uuid
import asyncio

import pytest

# 从 tests/Integration/retrieval/ 向上四层到达项目根目录
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

# ============================================================================
# 强制覆盖环境变量（必须在 dotenv.load_dotenv 之前，且要在 Config 单例化之前）
# ============================================================================

os.environ["NEO4J_URL"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "12345678"
os.environ["NEO4J_DATABASE"] = "neo4j"

os.environ["MILVUS_HOST"] = "localhost"
os.environ["MILVUS_PORT"] = "19530"
os.environ["MILVUS_USER"] = ""
os.environ["MILVUS_PASSWORD"] = ""

os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_DB"] = "knowledge_db"
os.environ["POSTGRES_USER"] = "postgres"
os.environ["POSTGRES_PASSWORD"] = "12345678"

# 加载 .env（dotenv 不会覆盖已存在的环境变量）
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"), override=False)

# 清理并重新加载 config 单例（清除 lru_cache，确保环境变量生效）
from src.config import config as _config_module
_config_module._config_instance = None  # type: ignore
_config_module._config = None           # type: ignore

# ============================================================================
# 导入必须在环境变量设置之后
# ============================================================================

from src.services.knowledge_service import KnowledgeService
from src.services.graph_service import GraphService
from src.core.retrieval import Retriever, QueryProcessor, ResultMerger
from src.core.graph.graph_store import GraphStore
from src.models.graph_model import KnowledgeGraph, Entity, Relationship


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def unique_prefix():
    """生成唯一前缀，用于隔离测试数据。"""
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def kb_service():
    """创建独立的 KnowledgeService 实例。"""
    service = KnowledgeService()
    yield service


@pytest.fixture(scope="function")
def graph_service():
    """创建独立的 GraphService 实例。"""
    service = GraphService()
    yield service
    service.shutdown()


@pytest.fixture(scope="function")
def graph_store():
    """创建独立的 GraphStore 实例。"""
    store = GraphStore()
    yield store
    store.close()


@pytest.fixture(scope="function")
def seeded_kb(kb_service, unique_prefix):
    """创建知识库数据库并写入测试文档，测试结束后删除。"""
    prefix = unique_prefix

    # 创建知识库（会在 Milvus 建集合 + PostgreSQL 建记录）
    db_info = kb_service.create_database(
        database_name=f"{prefix}_APT_KB",
        description="APT攻击知识库集成测试",
    )
    assert db_info.get("status") == "success", f"创建知识库失败: {db_info}"
    db_id = db_info["db_id"]
    print(f"\n[Fixture] 创建知识库 db_id={db_id}")

    # 写入测试文档（会在 Milvus 插入向量 + PostgreSQL 建 chunk 记录）
    test_documents = [
        {
            "id": f"{prefix}_chunk_1",
            "text": (
                "APT29（别名 Cozy Bear）是俄罗斯对外情报局（SVR）下属的高级持续性威胁组织。"
                "该组织最早于2008年被发现，2016年美国大选期间因攻击民主党全国委员会（DNC）而闻名。"
                "APT29 主要使用鱼叉式钓鱼邮件、Cobalt Strike、恶意宏文档等攻击手段。"
            ),
            "metadata": {"filename": "apt29_overview.txt", "source": "integration_test"},
        },
        {
            "id": f"{prefix}_chunk_2",
            "text": (
                "Cobalt Strike 是一款商业渗透测试框架，由美国公司 Fortra（前身 Rapid7）开发。"
                "该工具被 APT 组织广泛滥用，常用于横向移动、权限维持和 C&C 通信。"
                "Cobalt Strike 的 beacon 支持 DNS、HTTPS、TCP 等多种协议。"
            ),
            "metadata": {"filename": "cobalt_strike.txt", "source": "integration_test"},
        },
        {
            "id": f"{prefix}_chunk_3",
            "text": (
                "Mimikatz 是法国安全研究员 Benjamin Delpy 开发的凭据提取工具，主要用于 Windows 凭据提取。"
                "APT 组织常利用 Mimikatz 从内存中提取明文密码、NTLM Hash 和 Kerberos 票据。"
                "它支持 Pass-the-Hash、Pass-the-Ticket 等横向移动技术。"
            ),
            "metadata": {"filename": "mimikatz.txt", "source": "integration_test"},
        },
        {
            "id": f"{prefix}_chunk_4",
            "text": (
                "APT41 是位于中国境内的高级持续性威胁组织，同时开展国家支持的网络间谍活动和以经济利益为目的的网络犯罪。"
                "该组织自2012年起活跃，攻击目标涵盖医疗、游戏、科技、电信等多个行业。"
                "APT41 使用了包括供应链攻击、水坑攻击在内的多种高级攻击手法。"
            ),
            "metadata": {"filename": "apt41_overview.txt", "source": "integration_test"},
        },
        {
            "id": f"{prefix}_chunk_5",
            "text": (
                "SolarWinds 供应链攻击（Sunburst）是由 UNC2452（疑似俄罗斯组织）发起的APT攻击事件。"
                "攻击者篡改了 SolarWinds Orion 软件更新服务器，向约18000家客户推送了恶意更新。"
                "包括美国财政部、商务部、DHS、CISA 等政府机构和企业受到影响。"
            ),
            "metadata": {"filename": "solarwinds_sunburst.txt", "source": "integration_test"},
        },
    ]

    add_result = kb_service.add_documents(db_id, test_documents)
    assert add_result.get("status") == "success", f"添加文档失败: {add_result}"
    print(f"[Fixture] 写入 {len(test_documents)} 个文档块到 {db_id}")

    # Milvus 索引需要短暂等待
    time.sleep(1.0)

    yield {
        "prefix": prefix,
        "db_id": db_id,
        "service": kb_service,
    }

    # Teardown: 删除知识库（Milvus 集合 + PostgreSQL 记录）
    try:
        kb_service.delete_database(db_id)
        print(f"[Fixture] 清理知识库 db_id={db_id}")
    except Exception as e:
        print(f"[Fixture] 清理知识库失败（可忽略）: {e}")


@pytest.fixture(scope="function")
def seeded_graph(graph_service, graph_store, unique_prefix):
    """向图数据库写入测试实体和关系，测试结束后删除。"""
    prefix = unique_prefix

    # 直接使用 GraphStore.save_knowledge_graph 写入数据
    # （GraphService.add_triples 不存在）
    entities = [
        Entity(
            entity_id=f"{prefix}_APT29",
            entity_name=f"{prefix}_APT29",
            entity_type="attacker",
            entity_sub_type="apt_group",
            labels=["APT", "APT29"],
            times=["2008", "2016", "2020"],
            entity_variant_names=["Cozy Bear", "The Dukes"],
            properties={"country": "Russia", "sponsor": "SVR"},
        ),
        Entity(
            entity_id=f"{prefix}_SVR",
            entity_name=f"{prefix}_SVR",
            entity_type="attacker",
            entity_sub_type="org",
            labels=["org"],
            times=[],
            entity_variant_names=["Russian SVR"],
            properties={"country": "Russia"},
        ),
        Entity(
            entity_id=f"{prefix}_CobaltStrike",
            entity_name=f"{prefix}_CobaltStrike",
            entity_type="tool",
            entity_sub_type="beacon",
            labels=["malware", "C2"],
            times=["2012"],
            entity_variant_names=["Cobalt Strike", "CS"],
            properties={"vendor": "Fortra", "license": "commercial"},
        ),
        Entity(
            entity_id=f"{prefix}_Mimikatz",
            entity_name=f"{prefix}_Mimikatz",
            entity_type="tool",
            entity_sub_type="credential_theft",
            labels=["tool"],
            times=["2014"],
            entity_variant_names=["Mimikatz"],
            properties={"author": "Benjamin Delpy", "language": "C"},
        ),
        Entity(
            entity_id=f"{prefix}_DNC",
            entity_name=f"{prefix}_DNC",
            entity_type="victim",
            entity_sub_type="organization",
            labels=["victim"],
            times=["2016"],
            entity_variant_names=["Democratic National Committee"],
            properties={"country": "USA", "sector": "government"},
        ),
        Entity(
            entity_id=f"{prefix}_APT41",
            entity_name=f"{prefix}_APT41",
            entity_type="attacker",
            entity_sub_type="apt_group",
            labels=["APT", "APT41"],
            times=["2012", "2020"],
            entity_variant_names=["Winnti Group", "BARIUM"],
            properties={"country": "China"},
        ),
        Entity(
            entity_id=f"{prefix}_SolarWinds",
            entity_name=f"{prefix}_SolarWinds",
            entity_type="event",
            entity_sub_type="event",
            labels=["supply_chain"],
            times=["2020"],
            entity_variant_names=["SolarWinds Corp"],
            properties={"product": "Orion", "country": "USA"},
        ),
        Entity(
            entity_id=f"{prefix}_Sunburst",
            entity_name=f"{prefix}_Sunburst",
            entity_type="tool",
            entity_sub_type="malware",
            labels=["malware", "APT"],
            times=["2020"],
            entity_variant_names=["SUNBURST", "Solorigate"],
            properties={"target": "SolarWinds Orion update servers"},
        ),
    ]

    relationships = [
        Relationship(
            relationship_id=f"{prefix}_r1",
            relationship_type="belong_to",
            source=f"{prefix}_APT29",
            target=f"{prefix}_SVR",
            source_id=f"{prefix}_APT29",
            target_id=f"{prefix}_SVR",
        ),
        Relationship(
            relationship_id=f"{prefix}_r2",
            relationship_type="use",
            source=f"{prefix}_APT29",
            target=f"{prefix}_CobaltStrike",
            source_id=f"{prefix}_APT29",
            target_id=f"{prefix}_CobaltStrike",
        ),
        Relationship(
            relationship_id=f"{prefix}_r3",
            relationship_type="use",
            source=f"{prefix}_APT29",
            target=f"{prefix}_Mimikatz",
            source_id=f"{prefix}_APT29",
            target_id=f"{prefix}_Mimikatz",
        ),
        Relationship(
            relationship_id=f"{prefix}_r4",
            relationship_type="target",
            source=f"{prefix}_CobaltStrike",
            target=f"{prefix}_DNC",
            source_id=f"{prefix}_CobaltStrike",
            target_id=f"{prefix}_DNC",
        ),
        Relationship(
            relationship_id=f"{prefix}_r5",
            relationship_type="target",
            source=f"{prefix}_APT41",
            target=f"{prefix}_SolarWinds",
            source_id=f"{prefix}_APT41",
            target_id=f"{prefix}_SolarWinds",
        ),
        Relationship(
            relationship_id=f"{prefix}_r6",
            relationship_type="related_to",
            source=f"{prefix}_SolarWinds",
            target=f"{prefix}_Sunburst",
            source_id=f"{prefix}_SolarWinds",
            target_id=f"{prefix}_Sunburst",
        ),
    ]

    kg = KnowledgeGraph(entities=entities, relationships=relationships)
    stats = graph_store.save_knowledge_graph(kg)
    print(f"\n[Fixture] 写入 {len(entities)} 个实体、{len(relationships)} 个关系到 Neo4j，stats={stats}")

    # Neo4j 写入后需要短暂等待
    time.sleep(1.0)

    yield {
        "prefix": prefix,
        "service": graph_service,
        "store": graph_store,
    }

    # Teardown: 删除以 prefix 开头的所有节点
    _cleanup_graph(graph_store, prefix)


# ============================================================================
# 辅助函数
# ============================================================================

def _cleanup_graph(store: GraphStore, prefix: str):
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
        print(f"[Fixture] 清理 Neo4j 前缀={prefix}")
    except Exception as e:
        print(f"[Fixture] 清理 Neo4j 失败（可忽略）: {e}")


# -----------------------------------------------------------------------------
# pytest 运行命令（示例：运行使用了这些 fixtures 的测试文件）
# -----------------------------------------------------------------------------
# 完整测试：
#   pytest tests/Integration/retrieval/test_retriever.py -v -s
#   pytest tests/Integration/retrieval/test_query_processor.py -v -s
#   pytest tests/Integration/retrieval/test_result_merger.py -v -s
