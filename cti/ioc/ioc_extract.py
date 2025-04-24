import json
from ioc_finder import find_iocs
from typing import Dict, Any

def extract_iocs(text: str) -> Dict[str, Any]:
    """提取文本中的IOC指标"""
    iocs = find_iocs(text)
    
    # 过滤空值和去重
    cleaned_iocs = {}
    for key, values in iocs.items():
        if values:
            # 去重并转换为列表
            cleaned_iocs[key] = list(set(values))
        
    return cleaned_iocs


# ------------------- 示例使用 -------------------
if __name__ == "__main__":
    # 示例文本（包含多种IOC）
    sample_text = """
    APT组织使用IP 192.168.1.100和域名evil.com进行攻击。
    恶意文件哈希：
    - MD5: d41d8cd98f00b204e9800998ecf8427e
    - SHA1: da39a3ee5e6b4b0d3255bfef95601890afd80709
    - SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    C2服务器URL: http://malicious.com/path?param=1
    漏洞利用CVE-2023-1234，联系邮箱：attacker@example.com
    假哈希（应被过滤）: e3d123a1b...
    """

    # 提取IOC
    iocs = extract_iocs(sample_text)
    

    # 打印结果
    print(json.dumps(iocs, indent=4))