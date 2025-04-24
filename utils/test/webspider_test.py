import sys
import os
import pytest


from utils.webspider.webspider import WebSpider

def test_webspider_get():
    spider = WebSpider()
    # 使用一个稳定的测试网站
    result = spider.get("https://example.com")
    
    # 验证返回结果
    assert result is not None
    assert isinstance(result, (str, bytes))
    assert len(result) > 0

@pytest.mark.asyncio
async def test_webspider_get_async():
    spider = WebSpider()
    result = await spider.getAsync("https://example.com")
    
    # 验证异步获取结果
    assert result is not None
    assert isinstance(result, (str, bytes))
    assert len(result) > 0

@pytest.mark.asyncio
async def test_webspider_get_async_and_parse():
    spider = WebSpider()
    result = await spider.getAsyncAndParse("https://example.com")
    
    # 验证解析结果格式
    assert isinstance(result, dict)
    assert 'title' in result
    assert 'content' in result
    
    # 验证字段类型和内容
    assert isinstance(result['title'], str)
    assert isinstance(result['content'], str)
    assert len(result['content']) > 0

def test_web_parser():
    from utils.webspider.webspider import WebParser
    parser = WebParser()
    
    # 测试HTML字符串
    test_html = """
    <html>
        <head><title>Test Title</title></head>
        <body>
            <p>Test Content</p>
            <script>console.log('test')</script>
            <style>.test{color:red}</style>
        </body>
    </html>
    """
    
    result = parser.parse(test_html)
    
    # 验证解析结果
    assert isinstance(result, dict)
    assert 'title' in result
    assert 'content' in result
    assert result['title'] == 'Test Title'
    assert 'Test Content' in result['content']
    # 验证script和style内容被移除
    assert 'console.log' not in result['content']
    assert 'color:red' not in result['content']

    # 测试bytes输入
    bytes_html = test_html.encode('utf-8')
    bytes_result = parser.parse(bytes_html)
    assert bytes_result == result

if __name__ == "__main__":
    pytest.main([__file__])
