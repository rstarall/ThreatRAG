import asyncio
from typing import Callable, Dict, Any, Coroutine, TypeVar, Optional, List
import functools
import time

T = TypeVar('T')

class CoroutinePool:
    """协程池管理器，用于限制并发协程数量"""
    
    def __init__(self, max_workers: int = 10):
        """初始化协程池
        
        Args:
            max_workers: 最大工作协程数
        """
        self.semaphore = asyncio.Semaphore(max_workers)
        self.tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_lock = asyncio.Lock()
        
    async def submit(self, coro: Coroutine[Any, Any, T], task_id: Optional[str] = None) -> T:
        """提交协程到池中执行
        
        Args:
            coro: 要执行的协程
            task_id: 任务ID，如果为None则自动生成
            
        Returns:
            协程执行结果
        """
        async with self.semaphore:
            if task_id is None:
                task_id = f"task_{id(coro)}_{time.time()}"
                
            task = asyncio.create_task(coro)
            self.tasks[task_id] = task
            
            try:
                result = await task
                return result
            finally:
                # 任务完成后清理
                async with self._cleanup_lock:
                    if task_id in self.tasks:
                        del self.tasks[task_id]
    
    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务ID列表"""
        return list(self.tasks.keys())
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            async with self._cleanup_lock:
                if task_id in self.tasks:
                    del self.tasks[task_id]
            return True
        return False
    
    async def wait_all(self):
        """等待所有任务完成"""
        if not self.tasks:
            return
            
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)