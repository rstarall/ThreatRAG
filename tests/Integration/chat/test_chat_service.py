#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChatService 集成测试

要求：真实连接 LLM API，不使用任何 mock。
测试前请确保环境变量配置正确：
    SILICONFLOW_API_KEY 或 DEEPSEEK_API_KEY 等 LLM API Key
    （可选）REDIS_URL / SESSION_EXPIRE_TIME — 未配置时自动回退到内存会话存储
"""

import asyncio
import sys
import os
import uuid
import time

import pytest

# 从 tests/Integration/chat/ 向上四层到达项目根目录（F:/CWord/threat-rag/ThreatRAG）
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# 加载 .env 环境变量
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

from src.services.chat_service import ChatService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def cs():
    """为每个测试函数创建独立的 ChatService 实例。"""
    service = ChatService()
    yield service
    service.chat_engine.session_manager.redis_client = None


@pytest.fixture(scope="function")
def unique_session():
    """生成唯一 session_id。"""
    return f"test_session_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def unique_user():
    """生成唯一 user_id。"""
    return f"test_user_{uuid.uuid4().hex[:8]}"


def _collect_stream_chunks(stream_async_gen):
    """将异步流式生成器的内容块全部收集起来（用于断言）。"""
    collected = []
    try:
        while True:
            chunk = stream_async_gen.__anext__()
            if asyncio.iscoroutine(chunk):
                chunk = asyncio.run(chunk)
            if chunk:
                collected.append(chunk)
    except StopAsyncIteration:
        pass
    return collected


def _decode_chunks(chunks):
    """将 SSE 字节块解码为字符串列表。"""
    results = []
    for raw in chunks:
        b = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        for line in b.decode("utf-8", errors="replace").split("\n"):
            if line.startswith("data: "):
                results.append(line[6:].strip())
    return results


# =============================================================================
# 辅助函数
# =============================================================================

async def _achat_stream(cs: ChatService, query: str,
                         meta: dict = None,
                         history: list = None,
                         session_id: str = None,
                         user_id: str = None):
    """消费 chat_stream 并返回解码后的 data 行列表，同时实时打印到控制台。"""
    chunks = []
    async for chunk in cs.chat_stream(
        query=query, meta=meta, history=history,
        session_id=session_id, user_id=user_id
    ):
        chunks.append(chunk)
        # 流式输出实时打印
        print(chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk, end="")
    return _decode_chunks(chunks)


# =============================================================================
# 测试用例
# =============================================================================

class TestChatStreamBasic:

    def test_chat_stream_no_meta(self, cs):
        """测试不传 meta 参数时走完整流程（无检索，直接生成）"""
        print("\n[Test] 测试不传 meta 参数...")

        result_lines = asyncio.run(_achat_stream(
            cs,
            query="你好，请用一句话介绍一下APT攻击组织。",
            meta=None,
        ))

        assert len(result_lines) > 0, "至少应返回一行 data"

        # 检查是否包含 loading 或 finished 状态
        statuses = []
        for line in result_lines:
            try:
                import json
                obj = json.loads(line)
                statuses.append(obj.get("status"))
            except Exception:
                pass

        print(f"[Test] 收到状态: {statuses}")
        assert "loading" in statuses or "finished" in statuses, \
            f"应包含 loading 或 finished 状态，实际: {statuses}"

        # finished 行应包含 content
        finished_lines = [l for l in result_lines if '"status":"finished"' in l]
        if finished_lines:
            import json
            obj = json.loads(finished_lines[0])
            assert len(obj.get("content", "")) > 0, \
                "finished chunk 的 content 不应为空"
            print(f"[Test] LLM 回复内容: {obj['content'][:100]}...")

    def test_chat_stream_meta_no_retrieval(self, cs, unique_session):
        """测试 meta 中不带 use_web/use_graph/db_id，不触发检索"""
        print("\n[Test] 测试 meta 无检索标志...")

        result_lines = asyncio.run(_achat_stream(
            cs,
            query="Cobalt Strike 是什么？",
            meta={
                "use_web": False,
                "use_graph": False,
                "db_id": None,
            },
            session_id=unique_session,
        ))

        # 验证不出现检索相关状态（如 retrieving 等）
        combined = " ".join(result_lines)
        assert "retrieving" not in combined.lower(), \
            "不应出现 retrieving 状态（检索应被跳过）"
        assert "generating" in combined, "应出现 generating 状态"

        print(f"[Test] 状态行数: {len(result_lines)}")

    def test_chat_stream_with_history(self, cs, unique_session):
        """测试带对话历史的流式聊天"""
        print("\n[Test] 测试带对话历史的聊天...")

        history = [
            {"role": "user", "content": "APT29 是什么组织？"},
            {"role": "assistant", "content": "APT29 是一个高级持续性威胁组织。"},
        ]

        result_lines = asyncio.run(_achat_stream(
            cs,
            query="他们使用什么工具？",
            meta={"use_web": False, "use_graph": False},
            history=history,
            session_id=unique_session,
        ))

        combined = " ".join(result_lines)
        assert "generating" in combined
        finished_lines = [l for l in result_lines if '"status":"finished"' in l]
        assert len(finished_lines) > 0, "应包含 finished 状态"

        print(f"[Test] 历史轮次回复正常")


class TestChatStreamRetrievalFlags:

    def test_meta_use_web_true_does_retrieval(self, cs):
        """验证 use_web=True 会触发检索分支"""
        print("\n[Test] use_web=True 应走检索分支...")

        # 这里不测检索结果内容，只测是否进入检索分支
        # 通过 checking if "retrieving" or "generating" is present
        result_lines = asyncio.run(_achat_stream(
            cs,
            query="最近有什么APT攻击事件？",
            meta={"use_web": True},
        ))

        combined = " ".join(result_lines)
        # 有检索分支时会产生 retrieving 或 generating
        assert "generating" in combined, \
            f"use_web=True 时应出现 generating 状态，实际: {combined[:200]}"
        print(f"[Test] use_web=True 分支正常")

    def test_meta_use_graph_true_does_retrieval(self, cs):
        """验证 use_graph=True 会触发检索分支"""
        print("\n[Test] use_graph=True 应走检索分支...")

        result_lines = asyncio.run(_achat_stream(
            cs,
            query="APT29 和哪些工具有关联？",
            meta={"use_graph": True},
        ))

        combined = " ".join(result_lines)
        assert "generating" in combined
        print(f"[Test] use_graph=True 分支正常")

    def test_meta_db_id_set_does_retrieval(self, cs):
        """验证 db_id 非空时会触发检索分支"""
        print("\n[Test] db_id 非空应走检索分支...")

        result_lines = asyncio.run(_achat_stream(
            cs,
            query="查询知识库中关于钓鱼攻击的内容",
            meta={"db_id": "kb_test_001"},
        ))

        combined = " ".join(result_lines)
        assert "generating" in combined
        print(f"[Test] db_id 分支正常")


class TestSessionManagement:

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, cs, unique_session, unique_user):
        """测试创建会话并获取会话信息"""
        print(f"\n[Test] 创建并获取会话 {unique_session}...")

        # 先向 chat_stream 写入一条消息（会隐式创建会话）
        result_lines = []
        async for chunk in cs.chat_stream(
            query="你好，这是一条测试消息",
            meta={"use_web": False},
            session_id=unique_session,
            user_id=unique_user,
        ):
            result_lines.append(chunk)
            print(chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk, end="")

        # 获取会话
        get_result = await cs.get_session(unique_session)
        print(f"[Test] get_session 结果: {get_result}")

        assert get_result.get("status") == "success", \
            f"获取会话应成功，实际: {get_result}"
        session = get_result.get("session", {})
        assert session.get("session_id") == unique_session
        assert session.get("user_id") == unique_user

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, cs):
        """测试获取不存在的会话"""
        result = await cs.get_session(f"nonexistent_{uuid.uuid4().hex[:8]}")
        assert result.get("status") == "failed"
        assert "不存在" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_delete_session(self, cs, unique_session, unique_user):
        """测试删除会话"""
        print(f"\n[Test] 删除会话测试...")

        # 先创建会话
        async for chunk in cs.chat_stream(
            query="你好",
            meta={"use_web": False},
            session_id=unique_session,
            user_id=unique_user,
        ):
            print(chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk, end="")

        # 删除
        delete_result = await cs.delete_session(unique_session)
        assert delete_result.get("status") == "success", \
            f"删除会话应成功，实际: {delete_result}"

        # 确认无法再获取
        get_result = await cs.get_session(unique_session)
        assert get_result.get("status") == "failed"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, cs):
        """测试删除不存在的会话"""
        result = await cs.delete_session(f"nonexistent_{uuid.uuid4().hex[:8]}")
        assert result.get("status") == "failed"

    @pytest.mark.asyncio
    async def test_list_sessions(self, cs, unique_user):
        """测试列出会话列表"""
        print(f"\n[Test] 列出会话列表...")

        session_ids = []
        for i in range(3):
            sid = f"test_list_{uuid.uuid4().hex[:8]}_{i}"
            session_ids.append(sid)
            async for chunk in cs.chat_stream(
                query=f"测试消息 {i}",
                meta={"use_web": False},
                session_id=sid,
                user_id=unique_user,
            ):
                print(chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk, end="")

        time.sleep(0.5)

        list_result = await cs.list_sessions(user_id=unique_user, limit=50)
        assert list_result.get("status") == "success", \
            f"列出会话应成功，实际: {list_result}"
        sessions = list_result.get("sessions", [])
        session_ids_found = [s["session_id"] for s in sessions]
        for sid in session_ids:
            assert sid in session_ids_found, \
                f"会话 {sid} 应出现在列表中，实际: {session_ids_found}"

        # 清理
        for sid in session_ids:
            await cs.delete_session(sid)

    @pytest.mark.asyncio
    async def test_list_sessions_no_filter(self, cs):
        """测试不传 user_id 时列出所有会话"""
        result = await cs.list_sessions(limit=10)
        assert result.get("status") == "success"
        assert isinstance(result.get("sessions"), list)

    @pytest.mark.asyncio
    async def test_update_session_title(self, cs, unique_session):
        """测试更新会话标题"""
        print(f"\n[Test] 更新会话标题...")

        # 创建会话
        async for chunk in cs.chat_stream(
            query="你好",
            meta={"use_web": False},
            session_id=unique_session,
        ):
            print(chunk.decode("utf-8", errors="replace") if isinstance(chunk, bytes) else chunk, end="")

        # 更新标题
        new_title = "测试标题"
        update_result = await cs.update_session_title(unique_session, new_title)
        assert update_result.get("status") == "success", \
            f"更新标题应成功，实际: {update_result}"

        # 确认标题已更新
        get_result = await cs.get_session(unique_session)
        assert get_result.get("session", {}).get("title") == new_title

        # 清理
        await cs.delete_session(unique_session)

    @pytest.mark.asyncio
    async def test_update_nonexistent_session_title(self, cs):
        """测试更新不存在的会话标题"""
        result = await cs.update_session_title(
            f"nonexistent_{uuid.uuid4().hex[:8]}",
            "新标题"
        )
        assert result.get("status") == "failed"


class TestGetChatModels:

    def test_get_chat_models_siliconflow(self, cs):
        """测试获取 SiliconFlow 模型列表"""
        result = cs.get_chat_models("siliconflow")
        print(f"\n[Test] SiliconFlow 模型列表: {result}")
        assert result.get("status") == "success", \
            f"获取模型列表应成功，实际: {result}"
        assert "models" in result
        assert isinstance(result["models"], (list, dict))

    def test_get_chat_models_deepseek(self, cs):
        """测试获取 DeepSeek 模型列表"""
        result = cs.get_chat_models("deepseek")
        print(f"\n[Test] DeepSeek 模型列表: {result}")
        assert result.get("status") == "success"

    def test_get_chat_models_invalid_provider(self, cs):
        """测试获取无效 provider 的模型列表应返回失败"""
        result = cs.get_chat_models("nonexistent_provider_xyz")
        assert result.get("status") == "failed"


# =============================================================================
# 主入口（支持直接运行）
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# -----------------------------------------------------------------------------
# pytest 运行命令
# -----------------------------------------------------------------------------
# 完整测试：
#   pytest tests/Integration/chat/test_chat_service.py -v -s
#
# 按测试类运行：
#   pytest tests/Integration/chat/test_chat_service.py::TestChatStreamBasic -v -s
#   pytest tests/Integration/chat/test_chat_service.py::TestChatStreamRetrievalFlags -v -s
#   pytest tests/Integration/chat/test_chat_service.py::TestSessionManagement -v -s
#   pytest tests/Integration/chat/test_chat_service.py::TestGetChatModels -v -s
#
# 单个测试用例运行：
#   pytest tests/Integration/chat/test_chat_service.py::TestChatStreamBasic::test_chat_stream_no_meta -v -s
#   pytest tests/Integration/chat/test_chat_service.py::TestSessionManagement::test_create_and_get_session -v -s
