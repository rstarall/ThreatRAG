import pytest
from utils.parser.pdfParser import PDFParser

def test_pdfparser():
    pdfparser = PDFParser()
    result = pdfparser.parse("./utils/test/CosmicDuke.pdf")
    # 验证解析结果不为空
    assert result is not None
    # 验证解析结果是字符串类型
    assert isinstance(result, str)
    # 验证解析结果包含实际内容
    assert len(result.strip()) > 0

@pytest.mark.asyncio
async def test_pdfparser_async():
    pdfparser = PDFParser()
    result = await pdfparser.getAndParseAsync("https://blog-assets.f-secure.com/wp-content/uploads/2019/10/15163405/CosmicDuke.pdf")
    # 验证异步解析结果不为空
    assert result is not None
    # 验证异步解析结果是字符串类型
    assert isinstance(result, str)
    # 验证异步解析结果包含实际内容
    assert len(result.strip()) > 0

if __name__ == "__main__":
    pytest.main([__file__])

