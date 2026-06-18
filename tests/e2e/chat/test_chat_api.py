#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e2e/chat/test_chat_api.py
直接通过 HTTP 访问本地的 8080 端口服务，对 /chat 路由进行端到端测试。

运行前提：
    1. 启动服务器：python main.py（默认监听 localhost:8080）
    2. 配置 .env 中的 LLM API Key（SILICONFLOW_API_KEY / DEEPSEEK_API_KEY）
       及必要的服务（Redis、Milvus、Neo4j，可选）
    3. 安装依赖：pip install requests pytest pytest-asyncio httpx

运行示例：
    pytest tests/e2e/chat/test_chat_api.py -v -s
    pytest tests/e2e/chat/test_chat_api.py::TestChatGet -v
    pytest tests/e2e/chat/test_chat_api.py::TestChatPost -v
    pytest tests/e2e/chat/test_chat_api.py::TestSessionManagement -v
"""

import json
import time
import uuid
import requests

import pytest

from .utils import (
    parse_sse_stream,
    decode_stream_events,
    extract_finished_content,
    extract_all_content,
    extract_statuses,
    extract_error_message,
)

BASE_URL = "http://localhost:8000"


# ============================================================================
# 辅助函数
# ============================================================================

def _wait_for_server(url: str, timeout: int = 10) -> bool:
    """等待服务器就绪（polling /health）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{url}/health", timeout=3)
            if r.status_code == 200:
                return True
        except requests.ConnectionError:
            pass
        time.sleep(0.5)
    return False


def _chat_post(
    base_url: str,
    query: str,
    meta=None,
    history=None,
    session_id=None,
    user_id=None,
    timeout: int = 120,
):
    """对 /chat POST 端点发请求，返回 SSE 原始字节内容。"""
    payload = {"query": query}
    if meta is not None:
        payload["meta"] = meta
    if history is not None:
        payload["history"] = history
    if session_id is not None:
        payload["session_id"] = session_id
    if user_id is not None:
        payload["user_id"] = user_id

    with requests.post(
        f"{base_url}/chat/",
        json=payload,
        stream=True,
        timeout=timeout,
        headers={"Accept": "text/event-stream"},
    ) as resp:
        resp.raise_for_status()
        raw = b"".join(resp.iter_content(chunk_size=8192))
    return raw


# ============================================================================
# 测试类
# ============================================================================

class TestServerAvailability:
    """确保测试执行前服务器可用。"""

    def test_server_is_up(self):
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200, f"服务器未就绪: {r.status_code}"
        data = r.json()
        assert data.get("status") in ("ok", "warning"), f"Health 不正常: {data}"

    def test_chat_router_exists(self):
        r = requests.get(f"{BASE_URL}/chat/", timeout=5)
        assert r.status_code == 200
        assert "message" in r.json()


class TestChatGet:
    """GET /chat/"""

    def test_chat_get_returns_200(self):
        r = requests.get(f"{BASE_URL}/chat/", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "message" in data


class TestChatPost:
    """POST /chat/ — 核心流式聊天端点"""

    def test_chat_post_basic(self):
        """最基础的聊天请求，验证 SSE 流正常返回且包含 finished 状态。"""
        raw = _chat_post(
            BASE_URL,
            query="请用一句话介绍一下APT攻击组织。",
            timeout=120,
        )
        print(f"\n[E2E] 原始响应 (bytes, len={len(raw)}):\n{raw}\n")

        events = decode_stream_events(raw)
        print(f"[E2E] 解码后的事件列表 (共 {len(events)} 个):")
        for i, ev in enumerate(events):
            print(f"  [{i}] {ev}")

        assert len(events) > 0, f"SSE 流不应为空。原始响应: {raw[:500]}"

        statuses = extract_statuses(events)
        assert "finished" in statuses, f"应包含 finished 状态，实际: {statuses}。事件列表: {events}"

        content = extract_finished_content(events)
        assert content and len(content) > 0, f"finished chunk 的 content 不应为空，事件列表: {events}"
        print(f"\n[E2E] 回复内容: {content[:150]}...")

    def test_chat_post_no_retrieval(self):
        """meta 中不设置检索标志，应直接生成，不出现 retrieving。"""
        raw = _chat_post(
            BASE_URL,
            query="Cobalt Strike 是什么？",
            meta={"use_web": False, "use_graph": False, "db_id": None},
            timeout=60,
        )
        print(f"\n[E2E] 原始响应 (bytes, len={len(raw)}):\n{raw}\n")

        events = decode_stream_events(raw)
        print(f"[E2E] 解码后的事件列表 (共 {len(events)} 个):")
        for i, ev in enumerate(events):
            print(f"  [{i}] {ev}")

        combined_text = " ".join(
            json.dumps(ev, ensure_ascii=False) for ev in events
        )
        assert "retrieving" not in combined_text.lower(), \
            f"不传检索标志时不应出现 retrieving。事件列表: {events}"
        assert "generating" in combined_text, \
            f"应出现 generating 状态。事件列表: {events}"

    def test_chat_post_with_history(self):
        """传入对话历史，上下文应被正确理解。"""
        raw = _chat_post(
            BASE_URL,
            query="他们使用什么工具？",
            meta={"use_web": False, "use_graph": False},
            history=[
                {"role": "user", "content": "APT29 是什么组织？"},
                {"role": "assistant", "content": "APT29 是一个高级持续性威胁组织。"},
            ],
            session_id=f"e2e_history_{uuid.uuid4().hex[:8]}",
            timeout=60,
        )
        events = decode_stream_events(raw)
        statuses = extract_statuses(events)
        assert "finished" in statuses, f"应包含 finished 状态: {statuses}"
        content = extract_finished_content(events)
        assert content and len(content) > 0

    def test_chat_post_with_session_id(self):
        """session_id 应被接受并在响应中得到体现。"""
        sid = f"e2e_sid_{uuid.uuid4().hex[:8]}"
        raw = _chat_post(
            BASE_URL,
            query="你好，这是一条测试消息",
            meta={"use_web": False},
            session_id=sid,
            timeout=60,
        )
        events = decode_stream_events(raw)
        statuses = extract_statuses(events)
        assert "finished" in statuses, f"SSE 流应正常结束: {statuses}"

    def test_chat_post_with_user_id(self):
        """user_id 应被接受。"""
        raw = _chat_post(
            BASE_URL,
            query="你好",
            meta={"use_web": False},
            user_id=f"e2e_user_{uuid.uuid4().hex[:8]}",
            timeout=60,
        )
        events = decode_stream_events(raw)
        statuses = extract_statuses(events)
        assert "finished" in statuses

    def test_chat_post_with_meta_use_web_true(self):
        """use_web=True 时应触发检索分支。"""
        raw = _chat_post(
            BASE_URL,
            query="最近有什么APT攻击事件？",
            meta={"use_web": True},
            timeout=120,
        )
        events = decode_stream_events(raw)
        combined = " ".join(json.dumps(ev, ensure_ascii=False) for ev in events)
        assert "generating" in combined, \
            f"use_web=True 应出现 generating，实际前200字: {combined[:200]}"

    def test_chat_post_with_meta_use_graph_true(self):
        """use_graph=True 时应触发检索分支。"""
        raw = _chat_post(
            BASE_URL,
            query="APT29 和哪些工具有关联？",
            meta={"use_graph": True},
            timeout=120,
        )
        events = decode_stream_events(raw)
        combined = " ".join(json.dumps(ev, ensure_ascii=False) for ev in events)
        assert "generating" in combined

    def test_chat_post_with_meta_db_id_set(self):
        """db_id 非空时应走知识库检索分支。"""
        raw = _chat_post(
            BASE_URL,
            query="查询知识库中关于钓鱼攻击的内容",
            meta={"db_id": "kb_test_001"},
            timeout=120,
        )
        events = decode_stream_events(raw)
        combined = " ".join(json.dumps(ev, ensure_ascii=False) for ev in events)
        assert "generating" in combined


class TestSessionManagement:
    """会话管理端点：GET /chat/sessions、GET /chat/session/{id}、DELETE /chat/session/{id}、PUT /chat/session/{id}/title"""

    @pytest.fixture
    def session_id(self):
        return f"e2e_sm_{uuid.uuid4().hex[:8]}"

    @pytest.fixture
    def user_id(self):
        return f"e2e_sm_user_{uuid.uuid4().hex[:8]}"

    def test_create_session_via_chat(self, session_id, user_id):
        """先通过 chat 创建会话，再通过 API 验证会话存在。"""
        _chat_post(
            BASE_URL,
            query="你好，这是一条测试消息",
            meta={"use_web": False},
            session_id=session_id,
            user_id=user_id,
            timeout=60,
        )
        time.sleep(0.3)

        r = requests.get(f"{BASE_URL}/chat/session/{session_id}", timeout=5)
        assert r.status_code == 200, f"获取会话应返回 200: {r.text}"
        data = r.json()
        assert data.get("status") == "success"
        assert data["session"]["session_id"] == session_id
        assert data["session"]["user_id"] == user_id

        # 清理
        requests.delete(f"{BASE_URL}/chat/session/{session_id}", timeout=5)

    def test_get_nonexistent_session(self):
        sid = f"nonexistent_{uuid.uuid4().hex[:8]}"
        r = requests.get(f"{BASE_URL}/chat/session/{sid}", timeout=5)
        assert r.status_code == 404, f"不存在的会话应返回 404，实际: {r.status_code}"
        data = r.json()
        assert data.get("status") == 404

    def test_delete_session(self, session_id, user_id):
        """创建 → 删除 → 再获取应返回 404。"""
        _chat_post(
            BASE_URL,
            query="你好",
            meta={"use_web": False},
            session_id=session_id,
            user_id=user_id,
            timeout=60,
        )
        time.sleep(0.3)

        r = requests.delete(f"{BASE_URL}/chat/session/{session_id}", timeout=5)
        assert r.status_code == 200, f"删除会话应返回 200: {r.text}"
        assert r.json().get("status") == "success"

        r2 = requests.get(f"{BASE_URL}/chat/session/{session_id}", timeout=5)
        assert r2.status_code == 404, "删除后获取应返回 404"

    def test_delete_nonexistent_session(self):
        sid = f"nonexistent_{uuid.uuid4().hex[:8]}"
        r = requests.delete(f"{BASE_URL}/chat/session/{sid}", timeout=5)
        assert r.status_code == 404

    def test_list_sessions(self, user_id):
        """创建 2 个会话 → 列出 → 验证两者都在列表中 → 清理。"""
        sids = []
        for i in range(2):
            sid = f"e2e_list_{uuid.uuid4().hex[:8]}_{i}"
            sids.append(sid)
            _chat_post(
                BASE_URL,
                query=f"测试消息 {i}",
                meta={"use_web": False},
                session_id=sid,
                user_id=user_id,
                timeout=60,
            )

        time.sleep(0.5)

        r = requests.get(
            f"{BASE_URL}/chat/sessions",
            params={"user_id": user_id, "limit": 50},
            timeout=5,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "success"
        found_ids = {s["session_id"] for s in data.get("sessions", [])}
        for sid in sids:
            assert sid in found_ids, f"会话 {sid} 应出现在列表中"

        # 清理
        for sid in sids:
            requests.delete(f"{BASE_URL}/chat/session/{sid}", timeout=5)

    def test_list_sessions_no_filter(self):
        """不传 user_id 也能列出所有会话。"""
        r = requests.get(f"{BASE_URL}/chat/sessions", params={"limit": 10}, timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "success"
        assert isinstance(data.get("sessions"), list)

    def test_update_session_title(self, session_id):
        """更新会话标题并验证。"""
        _chat_post(
            BASE_URL,
            query="你好",
            meta={"use_web": False},
            session_id=session_id,
            timeout=60,
        )
        time.sleep(0.3)

        new_title = "E2E测试标题"
        r = requests.put(
            f"{BASE_URL}/chat/session/{session_id}/title",
            json={"title": new_title},
            timeout=5,
        )
        assert r.status_code == 200, f"更新标题应返回 200: {r.text}"
        assert r.json().get("status") == "success"

        r2 = requests.get(f"{BASE_URL}/chat/session/{session_id}", timeout=5)
        assert r2.json()["session"]["title"] == new_title

        # 清理
        requests.delete(f"{BASE_URL}/chat/session/{session_id}", timeout=5)

    def test_update_nonexistent_session_title(self):
        sid = f"nonexistent_{uuid.uuid4().hex[:8]}"
        r = requests.put(
            f"{BASE_URL}/chat/session/{sid}/title",
            json={"title": "新标题"},
            timeout=5,
        )
        assert r.status_code == 404


class TestGetChatModels:
    """GET /chat/models/{model_provider}"""

    def test_get_models_siliconflow(self):
        r = requests.get(f"{BASE_URL}/chat/models/siliconflow", timeout=15)
        assert r.status_code == 200, f"应返回 200: {r.text}"
        data = r.json()
        assert data.get("status") == "success", f"获取模型列表应成功: {data}"
        assert "models" in data

    def test_get_models_deepseek(self):
        r = requests.get(f"{BASE_URL}/chat/models/deepseek", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "success"

    def test_get_models_invalid_provider(self):
        r = requests.get(
            f"{BASE_URL}/chat/models/nonexistent_provider_xyz", timeout=10
        )
        assert r.status_code == 500, f"无效 provider 应返回 500: {r.status_code}"
        data = r.json()
        assert data.get("detail") is not None


# ============================================================================
# 主入口
# ============================================================================

# -----------------------------------------------------------------------------
# pytest 运行命令
# -----------------------------------------------------------------------------
# 完整测试：
#   pytest tests/e2e/chat/test_chat_api.py -v -s
#
# 按测试类运行：
#   pytest tests/e2e/chat/test_chat_api.py::TestServerAvailability -v
#   pytest tests/e2e/chat/test_chat_api.py::TestChatGet -v
#   pytest tests/e2e/chat/test_chat_api.py::TestChatPost -v
#   pytest tests/e2e/chat/test_chat_api.py::TestSessionManagement -v
#   pytest tests/e2e/chat/test_chat_api.py::TestGetChatModels -v
#
# 单个测试用例运行：
#   pytest tests/e2e/chat/test_chat_api.py::TestChatPost::test_chat_post_basic -v -s
#
# 注意：运行前需确保服务器已启动（python main.py，默认 localhost:8000）
