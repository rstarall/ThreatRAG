import asyncio
import pytest
import sys
import os
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.utils.coroutine_pool import CoroutinePool

@pytest.fixture
def coroutine_pool():
    """创建协程池实例"""
    return CoroutinePool(max_workers=5)

async def dummy_task(duration, return_value=None, raise_error=False):
    """测试用的虚拟任务"""
    await asyncio.sleep(duration)
    if raise_error:
        raise ValueError("测试错误")
    return return_value or duration

@pytest.mark.asyncio
async def test_submit_task(coroutine_pool):
    """测试提交任务"""
    # 提交任务
    result = await coroutine_pool.submit(dummy_task(0.1, "测试结果"))
    
    # 验证结果
    assert result == "测试结果"

@pytest.mark.asyncio
async def test_concurrent_tasks(coroutine_pool):
    """测试并发任务"""
    # 提交多个任务
    start_time = time.time()
    tasks = [
        coroutine_pool.submit(dummy_task(0.5, i))
        for i in range(10)
    ]
    
    # 等待所有任务完成
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # 验证结果
    assert results == list(range(10))
    
    # 验证并发执行（总时间应该小于串行执行的时间）
    # 5个工作协程，每个任务0.5秒，应该需要约1秒完成
    assert end_time - start_time < 2.0  # 添加一些余量

@pytest.mark.asyncio
async def test_cancel_task(coroutine_pool):
    """测试取消任务"""
    # 提交长时间运行的任务
    async def long_task():
        try:
            await asyncio.sleep(10)
            return "完成"
        except asyncio.CancelledError:
            return "已取消"
    
    task_id = "test_task"
    task = asyncio.create_task(coroutine_pool.submit(long_task(), task_id=task_id))
    
    # 等待一小段时间确保任务已开始
    await asyncio.sleep(0.1)
    
    # 取消任务
    result = await coroutine_pool.cancel_task(task_id)
    assert result is True
    
    # 验证任务已从池中移除
    assert task_id not in coroutine_pool.tasks

@pytest.mark.asyncio
async def test_error_handling(coroutine_pool):
    """测试错误处理"""
    # 提交会引发错误的任务
    with pytest.raises(ValueError, match="测试错误"):
        await coroutine_pool.submit(dummy_task(0.1, raise_error=True))
    
    # 验证任务已从池中移除
    assert len(coroutine_pool.tasks) == 0

if __name__ == "__main__":
    asyncio.run(pytest.main(["-xvs", __file__]))