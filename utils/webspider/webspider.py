from utils.parser.baseParser import BaseParser
from typing import Union
from utils.request.request import GetRequest

get_request = GetRequest()
class WebSpider:
    def __init__(self):
        self.parser = WebParser()
    
    def get(self, url: str) -> dict:
        return get_request.get(url)
    
    async def getAsync(self, url: str) -> any:
        try:
            return await get_request.getAsync(url)
        except Exception as e:
            print(f"Error occurred: {e}")
            return None
    
    async def getAsyncAndParse(self, url: str) -> dict:

        content = await self.getAsync(url)
        if content is None:
            return []
        try:
            return self.parser.parse(content)
        except Exception as e:
            print(f"Error occurred: {e}")
            return []


class WebParser(BaseParser[dict]):
    def __init__(self):
        pass

    def parse(
            self, 
            input: Union[str, bytes],
            **kwargs
            ) -> dict:
        from bs4 import BeautifulSoup
        
        # 如果输入是bytes类型,先解码为字符串
        if isinstance(input, bytes):
            input = input.decode('utf-8')
            
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(input, 'html.parser')
        
        # 提取标题
        title = soup.title.string if soup.title else ''
        
        # 提取正文内容
        # 移除script和style标签
        for script in soup(['script', 'style']):
            script.decompose()
            
        # 获取所有文本内容
        content = ' '.join(soup.stripped_strings)
        
        # 返回解析结果
        return {
            'title': title,
            'content': content
        }
