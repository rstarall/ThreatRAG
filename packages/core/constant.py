# ==============================================================================
# 修订后的实体类型 (参考 STIX 2.1 核心对象)
# ==============================================================================
STIX_ENTITY_TYPES = {
    # 威胁主体 (Threat Actors & Campaigns)
    "THREAT_ACTOR": "threat-actor",          # 威胁行动者 (替代 ATTACK_ORGANIZATION)
    "INTRUSION_SET": "intrusion-set",        # 入侵集合
    "CAMPAIGN": "campaign",                  # 战役 (新增)

    # 威胁手段 (TTPs & Malware)
    "ATTACK_PATTERN": "attack-pattern",      # 攻击模式 (TTPs，非常重要)
    "MALWARE": "malware",                    # 恶意软件
    "TOOL": "tool",                          # 工具 (被用于攻击的合法或非法软件)
    "PAYLOAD": "payload",                    # 有效载荷

    # 漏洞与指标 (Vulnerabilities & Indicators)
    "VULNERABILITY": "vulnerability",        # 漏洞 (CVE 是其一个实例)
    "INDICATOR": "indicator",                # 指标 (如 "IP 1.2.3.4 是 C2 服务器")

    # 应对与信息 (Response & Information)
    "COURSE_OF_ACTION": "course-of-action",  # 应对措施 (新增)
    "IDENTITY": "identity",                  # 身份信息
    "LOCATION": "location",                  # 地理位置 (新增)
    "REPORT": "report",                      # 情报报告 (新增，用于关联一组情报)

    # 可观察对象 (Cyber Observables - SCOs)
    "ARTIFACT": "artifact",                  # 文件、payload 等二进制对象
    "FILE": "file",                          # 文件
    "DIRECTORY": "directory",                # 目录
    "FILE_HASH": "file-hash",                # 文件哈希 (新增，用于统一管理 MD5, SHA等)
    "IP_ADDRESS": "ipv4-addr",               # IP 地址 (STIX标准为 ipv4-addr/ipv6-addr)
    "DOMAIN": "domain-name",                 # 域名
    "URL": "url",                            # URL
    "EMAIL_ADDRESS": "email-addr",           # 邮箱地址
    "USER_ACCOUNT": "user-account",          # 用户账户
    "PROCESS": "process",                    # 进程
    "NETWORK_TRAFFIC": "network-traffic",    # 网络流量
    "SOFTWARE": "software",                  # 软件 (包括操作系统、中间件等)
}

# ==============================================================================
# 修订后的关系类型 (参考 STIX 2.1 核心关系)
# ==============================================================================
REVISED_STIX_RELATIONSHIPS = {
    # 核心通用关系
    "RELATED_TO": "related-to",              # 两个对象之间存在某种模糊的联系
    
    # 归因与从属关系
    "ATTRIBUTED_TO": "attributed-to",        # (入侵集合) 归因于 (威胁行动者)
    "PART_OF": "part-of",                    # A 是 B 的一部分 (新增)
    "DERIVED_FROM": "derived-from",          # (指标) 来源于 (观察数据)
    
    # 行为与能力关系
    "USES": "uses",                          # (威胁行动者) 使用 (恶意软件/工具/攻击模式)
    "TARGETS": "targets",                    # (入侵集合) 瞄准 (身份/地理位置)
    "EXPLOITS": "exploits",                  # (恶意软件) 利用 (漏洞)
    "DELIVERS": "delivers",                  # (恶意软件) 投递 (另一个恶意软件)
    
    # 指示与定位关系
    "INDICATES": "indicates",                # (指标) 指示 (恶意软件/入侵集合)
    "LOCATED_AT": "located-at",              # (身份) 位于 (地理位置)
    
    # 网络与主机关系
    "COMMUNICATES_WITH": "communicates-with",# (恶意软件) 与 (IP地址) 通信
    "CONNECTS_TO": "connects-to",            # (IP地址) 连接到 (IP地址)
    "RESOLVES_TO": "resolves-to",            # (域名) 解析到 (IP地址)
    "HOSTS": "hosts",                        # (服务器) 托管 (恶意软件)
    
    # 包含关系
    "CONTAINS": "contains",                  # (报告/对象) 包含 (可观察对象)
    "HAS_WEAKNESS": "has-weakness",          # (软件) 有 (弱点)
    "HAS_PAYLOAD": "has-payload",            # (软件) 有 (有效载荷)

}

# STIX2.0 实体属性关键字（通用属性）
STIX_COMMON_PROPERTIES = {
    "ID": "id",  # 唯一标识符（如attack-pattern--xxxx）
    "TYPE": "type",  # 实体类型（对应STIX_ENTITY_TYPES）
    "NAME": "name",  # 实体名称
    "DESCRIPTION": "description",  # 实体描述

}

# 实体提取相关常量
ENTITY_EXTRACTION = {
    "MIN_CONFIDENCE": 0.7,  # 实体提取最小置信度阈值
    "MAX_ENTITIES_PER_DOC": 100,  # 单文档最大提取实体数
    "STIX_ENTITY_PATTERNS": {
        # 可添加STIX实体的正则匹配模式（辅助NLP提取）
        "VULNERABILITY": r"CVE-\d{4}-\d{4,7}",  # CVE漏洞编号模式
        "FILE": r"[a-zA-Z0-9_]+\.(exe|dll|docx|pdf)",  # 常见文件名模式
    }
}