#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
e2e/chat/utils.py
SSE 流式响应解析辅助函数
"""

import json
import re
from typing import Generator, List, Dict, Any, Optional


def parse_sse_stream(raw_bytes: bytes) -> Generator[str, None, None]:
    """将 SSE 字节流逐一产出 data: <content> 行内容（不含前缀）。

    用于 chat_post 返回的 StreamingResponse。
    每个 data: 行会被 yield 一次；空行和注释行会被跳过。
    """
    text = raw_bytes.decode("utf-8", errors="replace")
    for line in text.split("\n"):
        line = line.rstrip("\r")
        if not line:
            continue
        if line.startswith("data: "):
            yield line[6:]
        elif line.startswith("data:"):
            yield line[5:].lstrip()


def decode_stream_events(raw_bytes: bytes) -> List[Dict[str, Any]]:
    """将 SSE 字节流解析为 JSON 对象列表。"""
    results = []
    for payload in parse_sse_stream(raw_bytes):
        payload = payload.strip()
        if not payload:
            continue
        try:
            results.append(json.loads(payload))
        except json.JSONDecodeError:
            results.append({"raw": payload})
    return results


def extract_finished_content(events: List[Dict[str, Any]]) -> Optional[str]:
    """从事件列表中提取 status=finished 的 content。"""
    for ev in events:
        if ev.get("status") == "finished":
            return ev.get("content", "")
    return None


def extract_all_content(events: List[Dict[str, Any]]) -> str:
    """从事件列表中收集所有增量 content 并拼接。"""
    parts = []
    for ev in events:
        c = ev.get("content", "")
        if c:
            parts.append(c)
    return "".join(parts)


def extract_statuses(events: List[Dict[str, Any]]) -> List[str]:
    """返回所有出现过的 status 值列表（去重）。"""
    seen = set()
    result = []
    for ev in events:
        s = ev.get("status")
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result


def extract_error_message(events: List[Dict[str, Any]]) -> Optional[str]:
    """从事件列表中提取第一个 error 消息。"""
    for ev in events:
        if ev.get("type") == "error":
            return ev.get("error", "")
    return None