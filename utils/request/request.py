import asyncio
from abc import ABC, abstractmethod
import requests


class BaseRequest:
    def __init__(self):
        pass


class GetRequest(BaseRequest):
    def __init__(self):
        super().__init__()

    def get(self, url: str) -> any:
        response = requests.get(url)
        return response.content

    
    async def getAsync(self, url: str) -> any:
        return await asyncio.to_thread(self.get, url)

class PostRequest(BaseRequest):
    def __init__(self):
        super().__init__()

    def post(self, url: str, data: dict) -> any:
        pass

    async def postAsync(self, url: str, data: dict) -> any:
        pass
