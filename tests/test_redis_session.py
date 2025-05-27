import asyncio
import pytest
import sys
import os
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.cache.redis_session import RedisSessionManager

# 使用测试Redis URL
TEST_REDIS_URL = "redis://localhost:6379/1"  # 使用DB 1进行测试，避免影响生产数据

@pytest.fixture
async def redis_session():
    """创建Redis会话管理器实例"""
    session_manager = RedisSessionManager(redis_url=TEST_REDIS_URL, expire_time=60)
    yield session_manager
    # 清理测试数据
    redis = await session_manager._get_redis()
    await redis.flushdb()
    await session_manager.close()

@pytest.mark.asyncio
async def test_create_session(redis_session):
    """测试创建会话"""
    # 创建会话
    session_id = await redis_session.create_session(system_prompt="测试系统提示词")
    
    # 验证会话ID格式
    assert isinstance(session_id, str)
    assert len(session_id) > 0
    
    # 获取会话并验证
    session = await redis_session.get_session(session_id)
    assert session is not None
    assert "history" in session
    assert len(session["history"]) == 1
    assert session["history"][0]["role"] == "system"
    assert session["history"][0]["content"] == "测试系统提示词"

@pytest.mark.asyncio
async def test_add_message(redis_session):
    """测试添加消息"""
    # 创建会话
    session_id = await redis_session.create_session()
    
    # 添加用户消息
    await redis_session.add_message(session_id, "user", "你好")
    
    # 添加助手消息
    await redis_session.add_message(session_id, "assistant", "你好，有什么可以帮助你的？")
    
    # 获取会话历史
    history = await redis_session.get_history(session_id)
    
    # 验证历史记录
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "你好"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "你好，有什么可以帮助你的？"

@pytest.mark.asyncio
async def test_delete_session(redis_session):
    """测试删除会话"""
    # 创建会话
    session_id = await redis_session.create_session()
    
    # 验证会话存在
    session = await redis_session.get_session(session_id)
    assert session is not None
    
    # 删除会话
    result = await redis_session.delete_session(session_id)
    assert result is True
    
    # 验证会话已删除
    session = await redis_session.get_session(session_id)
    assert session is None

if __name__ == "__main__":
    asyncio.run(pytest.main(["-xvs", __file__]))