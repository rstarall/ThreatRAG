# STIX2.0 实体类型（核心对象）
STIX_ENTITY_TYPES = {
    # 攻击模式
    "ATTACK_PATTERN": "attack-pattern",
    # 战役
    "CAMPAIGN": "campaign",
    # 课程-of-action
    "COA": "course-of-action",
    # 目录
    "DIRECTORY": "directory",
    # 文件
    "FILE": "file",
    # 指示器
    "INDICATOR": "indicator",
    # 入侵集合
    "INTRUSION_SET": "intrusion-set",
    # 恶意软件
    "MALWARE": "malware",
    # 漏洞
    "VULNERABILITY": "vulnerability",
    # observables（可观察对象）
    "PROCESS": "process",
    "REGISTRY_KEY": "registry-key",
    "NETWORK_TRAFFIC": "network-traffic",
    "EMAIL_MESSAGE": "email-message",
    "USER_ACCOUNT": "user-account",
    "SOFTWARE": "software",
    # 威胁演员
    "THREAT_ACTOR": "threat-actor",
    "IP": "ip",
    "IP_ADDRESS": "ip-address",
    "URL": "url",
    "DOMAIN": "domain",

}

# STIX2.0 关系类型（核心关系）
STIX_RELATIONSHIP_TYPES = {
    # 包含关系
    "CONTAINS": "contains",  # A contains B（如报告包含指示器）
    # 关联关系
    "RELATED_TO": "related-to",  # A 与 B 相关
    # 归因关系
    "ATTRIBUTED_TO": "attributed-to",  # A 归因于 B（如攻击归因于威胁演员）
    # 利用关系
    "EXPLOITS": "exploits",  # A 利用 B（如恶意软件利用漏洞）
    # 指示关系
    "INDICATES": "indicates",  # A 指示 B（如指示器指示恶意软件）
    # 实现关系
    "IMPLEMENTS": "implements",  # A 实现 B（如攻击模式实现TTP）
    # 发起关系
    "LAUNCHES": "launches",  # A 发起 B（如战役发起攻击）
    # 目标关系
    "TARGETS": "targets", 
    "INTERACTS_WITH": "interacts-with", # A 与 B 交互（如IP与域名交互）
    
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