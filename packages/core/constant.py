# # STIX2.0 实体类型（核心对象）
# STIX_ENTITY_TYPES = {
#     # 攻击模式
#     "ATTACK_PATTERN": "attack-pattern",
#     # 战役
#     "CAMPAIGN": "campaign",
#     # 课程-of-action
#     "COA": "course-of-action",
#     # 目录
#     "DIRECTORY": "directory",
#     # 指示器
#     "INDICATOR": "indicator",
#     # 入侵集合
#     "INTRUSION_SET": "intrusion-set",
#     # 恶意软件
#     "MALWARE": "malware",
#     # 漏洞
#     "VULNERABILITY": "vulnerability",
#     # observables（可观察对象）
#     "PROCESS": "process",
#     "NETWORK_TRAFFIC": "network-traffic",
#     "EMAIL_MESSAGE": "email-message",
#     "USER_ACCOUNT": "user-account",
#     "SOFTWARE": "software",
#     # IOC指标
#     "IP_ADDRESS": "ip-address",      # IP地址（如192.168.1.1、203.0.113.5）
#     "DOMAIN_NAME": "domain",      # 域名（如malicious.com、example[.]top）
#     "FILE_HASH": "file",        # 文件哈希（MD5/SHA1/SHA256，如a1b2c3d4...）
#     "URL_PATH": "url",         # URL路径（如http://malicious.com/backdoor.php）
#     "REGISTRY_KEY": "registry-key",     # 注册表项（如HKEY_CURRENT_USER\Software\Malware）
#     "EMAIL_ADDRESS": "email-address",    # 邮箱地址（如phish@malicious.com）
#     "CERTIFICATE_HASH": "certificate-hash", # 证书哈希（如SSL证书指纹）
#     "NETWORK_PORT": "network-port",     # 网络端口（如异常开放的3389、4444端口）
#     "MUTEX": "mutex",            # 互斥体（恶意软件创建的唯一标识，如Global\MalwareMutex）
#     "PROCESS_NAME": "process",      # 进程名（如malware.exe、svchost.exe[异常路径]）


# }

# # STIX2.0 关系类型（核心关系）
# STIX_RELATIONSHIP_TYPES = {
#     # 包含关系
#     "CONTAINS": "contains",  # A contains B（如报告包含指示器）
#     # 关联关系
#     "RELATED_TO": "related-to",  # A 与 B 相关
#     # 归因关系
#     "ATTRIBUTED_TO": "attributed-to",  # A 归因于 B（如攻击归因于威胁演员）
#     # 利用关系
#     "EXPLOITS": "exploits",  # A 利用 B（如恶意软件利用漏洞）
#     # 指示关系
#     "INDICATES": "indicates",  # A 指示 B（如指示器指示恶意软件）
#     # 实现关系
#     "IMPLEMENTS": "implements",  # A 实现 B（如攻击模式实现TTP）
#     # 发起关系
#     "LAUNCHES": "launches",  # A 发起 B（如战役发起攻击）
#     # 目标关系
#     "TARGETS": "targets", 
#     # 交互关系
#     "INTERACTS_WITH": "interacts-with", # A 与 B 交互（如IP与域名交互）
#     # 使用关系
#     "USES": "uses", # A 使用 B（如恶意软件使用漏洞）
# }

# 威胁情报领域实体类型与关系类型常量定义（适配日志、流量、漏洞利用链，对齐STIX 2.1）
# 核心优化：补充漏洞利用链路、修复关系逻辑、统一STIX属性映射

# ------------------------------
# 1. 核心实体类型（对齐STIX 2.1类型名，补充漏洞利用专属实体）
# ------------------------------
THREAT_INTEL_ENTITY_TYPES = {
    # 威胁源头类（STIX 2.1 Threat Actor/Malware扩展）
    "THREAT_ORGANIZATION": "threat-organization",  # 威胁组织（如Conti、Lapsus$）
    "THREAT_ACTOR": "threat-actor",                # 威胁个体（如黑帽黑客、内部威胁人员）
    "APT_GROUP": "apt-group",                      # APT组织（如APT29、APT34，STIX Threat Actor子类）
    "MALWARE": "malware",                          # 恶意软件（如Emotet、WannaCry，STIX标准实体）
    "RANSOMWARE_FAMILY": "malware-family--ransomware",  # 勒索软件家族（STIX Malware子类）
    
    # 攻击手段类（新增漏洞利用链实体，对齐STIX Attack Pattern）
    "IOC_INDICATOR": "indicator",                  # 通用IOC（如IP/域名/哈希，STIX标准实体）
    "VULNERABILITY": "vulnerability",              # 漏洞（如CVE-2021-44228，STIX标准实体）
    "ATTACK_TTP": "attack-pattern",                # 攻击战术/技术（映射MITRE ATT&CK，STIX标准实体）
    "EXPLOIT_TOOL": "tool--exploit",               # 漏洞利用工具（如Metasploit、PoC脚本，STIX Tool子类）
    "EXPLOIT_TECHNIQUE": "attack-pattern--exploit",# 漏洞利用技术（如RCE、SQL注入，ATT&CK技术子类）
    "ATTACK_PAYLOAD": "malware--payload",          # 攻击载荷（如反弹Shell、矿工程序，STIX Malware子类）
    "COMMAND_CONTROL": "infrastructure--c2",       # C2服务器（STIX Infrastructure子类）
    "NETWORK_PORT": "network-location--port",      # 网络端口（如445/3389，STIX Network Location子类）
    
    # 攻击目标类（STIX Target扩展）
    "TARGET_ORGANIZATION": "identity--target-org",  # 目标组织（如金融机构，STIX Identity子类）
    "TARGET_SYSTEM": "software--target-os",         # 目标系统（如Windows 10，STIX Software子类）
    "TARGET_SERVICE": "software--target-service",   # 目标服务（如Apache 2.4，STIX Software子类）
    "TARGET_DEVICE": "device--target",              # 目标设备（如服务器、交换机，STIX Device实体）
    "TARGET_USER": "identity--target-user",         # 目标用户（如管理员账号，STIX Identity子类）
    
    # 攻击结果类（STIX Incident扩展）
    "ATTACK_EVENT": "incident--attack",            # 攻击事件（如2024勒索攻击，STIX Incident子类）
    "DATA_BREACH": "incident--data-breach",        # 数据泄露（如用户信息泄露，STIX Incident子类）
    "DAMAGE_ASSESSMENT": "report--damage",         # 损失评估（如经济损失，STIX Report子类）
    
    # 日志专属实体（STIX Logs扩展，适配多源日志）
    "LOG_ENTRY": "log--entry",                     # 日志条目（单条日志，如防火墙阻断记录）
    "LOG_SOURCE": "log--source",                   # 日志来源（如防火墙、EDR，STIX Logs子类）
    "LOG_ANOMALY": "log--anomaly",                 # 日志异常（如登录失败、异常进程）
    "LOG_FIELD": "log--field",                     # 日志字段（如src_ip、event_id，STIX Logs属性映射）
    
    # 流量专属实体（STIX Network Traffic扩展）
    "NETWORK_FLOW": "network-traffic--flow",       # 网络流（如TCP/UDP流，STIX Network Traffic子类）
    "FLOW_ANOMALY": "network-traffic--anomaly",    # 流量异常（如C2心跳包、端口扫描）
    "PACKET_FEATURE": "network-traffic--packet",   # 数据包特征（如畸形TCP头、异常Payload）
    "TRAFFIC_SESSION": "network-traffic--session"  # 流量会话（如C2完整通信，STIX Network Traffic子类）
}

# ------------------------------
# 2. 细分实体子类型（补充漏洞/流量子类型，强化场景适配）
# ------------------------------
# 2.1 IOC子类型（补充漏洞/日志/流量IOC，对齐STIX Indicator类型）
IOC_SUB_TYPES = {
    # 通用IOC（STIX Indicator标准类型）
    "IP_ADDRESS": "indicator--ip",                 # IP地址（如192.168.1.1）
    "DOMAIN_NAME": "indicator--domain",            # 域名（如malicious.com）
    "FILE_HASH": "indicator--file-hash",           # 文件哈希（MD5/SHA256）
    "URL_PATH": "indicator--url",                  # URL路径（如http://malicious.com/backdoor）
    "REGISTRY_KEY": "indicator--registry",         # 注册表项（如HKEY_CURRENT_USER\Malware）
    "EMAIL_ADDRESS": "indicator--email",           # 邮箱地址（如phish@malicious.com）
    # 漏洞/日志/流量专属IOC
    "EVENT_ID": "indicator--log-eventid",          # 日志事件ID（如Windows 4688<进程创建>）
    "PROCESS_ID": "indicator--process-id",         # 进程ID（如PID=1234<恶意进程>）
    "PORT_NUMBER": "indicator--port",              # 端口号（如4444<C2>、22<SSH扫描>）
    "PROTOCOL_TYPE": "indicator--protocol",        # 协议类型（如UDP隧道、ICMP隐蔽通信）
    "SESSION_ID": "indicator--session",            # 会话ID（如Web会话、流量会话标识）
    "CVE_ID": "indicator--cve",                    # CVE漏洞ID（如CVE-2021-44228，STIX Vulnerability映射）
}

# 2.2 日志子类型（按设备/场景分类，适配日志采集）
LOG_SOURCE_SUB_TYPES = {
    "FIREWALL_LOG": "log-source--firewall",        # 防火墙日志（华为、Palo Alto）
    "IDS_IPS_LOG": "log-source--ids-ips",          # IDS/IPS日志（Snort、Suricata）
    "SYSTEM_LOG": "log-source--os",                # 系统日志（Windows Event Log、Linux /var/log）
    "APPLICATION_LOG": "log-source--app",          # 应用日志（Nginx、MySQL）
    "ENDPOINT_LOG": "log-source--edr",             # 终端日志（EDR、杀毒软件）
    "CLOUD_LOG": "log-source--cloud",              # 云日志（AWS CloudTrail、阿里云ActionTrail）
    "NETWORK_LOG": "log-source--network-device",   # 网络设备日志（交换机、路由器）
}

# 2.3 流量子类型（按协议/场景分类，适配流量解析）
TRAFFIC_SUB_TYPES = {
    "TCP_FLOW": "network-flow--tcp",               # TCP流量（C2通信、Web访问）
    "UDP_FLOW": "network-flow--udp",               # UDP流量（DNS隧道、UDP后门）
    "ICMP_FLOW": "network-flow--icmp",             # ICMP流量（ICMP隧道、ping扫描）
    "HTTP_FLOW": "network-flow--http",             # HTTP流量（WebShell、恶意API）
    "HTTPS_FLOW": "network-flow--https",           # HTTPS流量（加密C2、恶意SSL）
    "DNS_FLOW": "network-flow--dns",               # DNS流量（DGA、DNS隐蔽信道）
    "SMB_FLOW": "network-flow--smb",               # SMB流量（SMB漏洞利用、文件共享）
}

# 2.4 漏洞子类型（按利用方式分类，对齐CVE分类标准 OWASP ）
VULNERABILITY_SUB_TYPES = {
    "RCE": "vuln--rce",                            # 远程代码执行（如Log4j、ProxyShell）
    "PRIVILEGE_ESCALATION": "vuln--priv-esc",      # 权限提升（如Windows内核漏洞、Linux提权）
    "SQL_INJECTION": "vuln--sql-inj",              # SQL注入（盲注、报错注入）
    "LFI_RFI": "vuln--lfi-rfi",                    # 本地/远程文件包含
    "XSS": "vuln--xss",                            # 跨站脚本（存储型、反射型）
    "DENIAL_OF_SERVICE": "vuln--dos",              # 拒绝服务（DDoS、资源耗尽）
    "CSRF": "vuln--csrf",                          # 跨站请求伪造
    "SSRF": "vuln--ssrf",                          # 请求伪造
    "XXE": "vuln--xxe",                            # 外部实体注入
    "SEARILIZATION": "vuln--serialization",        # 序列化漏洞
    "DESERIALIZATION": "vuln--deserialization",    # 反序列化漏洞
    "BRUTE_FORCE_ATTACK": "vuln--brute-force",      # 暴力破解
    "GET_SHELL": "vuln--get-shell",                # 获取Shell
    "BACKDOOR": "vuln--backdoor",                  # 后门
    "WEAK_PASSWORD": "vuln--weak-password",        # 弱密码 
}

# ------------------------------
# 3. 核心关系类型（修复逻辑漏洞、补充漏洞利用链关系，对齐STIX 2.1 Relationship）
# ------------------------------
THREAT_INTEL_RELATION_TYPES = [
    # 【威胁组织-攻击手段】核心链路（STIX Relationship: Uses/Develops）
    ("USES", "THREAT_ORGANIZATION", "MALWARE", "威胁组织使用某恶意软件", "relationship--uses"),
    ("DEVELOPS", "THREAT_ORGANIZATION", "EXPLOIT_TOOL", "威胁组织开发某利用工具", "relationship--develops"),
    ("EMPLOYS", "THREAT_ORGANIZATION", "ATTACK_TTP", "威胁组织采用某攻击技术", "relationship--employs"),
    ("CONTROLS", "THREAT_ORGANIZATION", "COMMAND_CONTROL", "威胁组织控制某C2服务器", "relationship--controls"),
    ("TARGETS", "THREAT_ORGANIZATION", "TARGET_ORGANIZATION", "威胁组织针对某组织发起攻击", "relationship--targets"),
    
    # 【漏洞利用链】关键关系（新增，覆盖工具-漏洞-端口链路）
    ("TARGETS_VULN", "EXPLOIT_TOOL", "VULNERABILITY", "利用工具针对某漏洞设计", "relationship--targets-vuln"),
    ("IMPLEMENTS_TECH", "EXPLOIT_TOOL", "EXPLOIT_TECHNIQUE", "利用工具实现某利用技术（如RCE）", "relationship--implements-tech"),
    ("CARRIES_PAYLOAD", "EXPLOIT_TOOL", "ATTACK_PAYLOAD", "利用工具携带某攻击载荷", "relationship--carries-payload"),
    ("REQUIRES_PORT", "VULNERABILITY", "NETWORK_PORT", "漏洞利用需通过某端口（如443/445）", "relationship--requires-port"),
    ("AFFECTS_SYSTEM", "VULNERABILITY", "TARGET_SYSTEM", "漏洞影响某目标系统（如Windows Server）", "relationship--affects-system"),
    ("COMPROMISES", "EXPLOIT_TECHNIQUE", "TARGET_DEVICE", "利用技术攻陷某目标设备", "relationship--compromises"),
    
    # 【恶意软件-关联实体】关系（补充IOC/载荷关联）
    ("CONTAINS_IOC", "MALWARE", "IOC_INDICATOR", "恶意软件包含某IOC（如哈希/注册表）", "relationship--contains-ioc"),
    ("USES_VULN", "MALWARE", "VULNERABILITY", "恶意软件利用某漏洞传播/执行", "relationship--uses-vuln"),
    ("CONNECTS_C2", "MALWARE", "COMMAND_CONTROL", "恶意软件连接某C2服务器", "relationship--connects-c2"),
    
    # 【日志-威胁链路】关联（强化日志与攻击事件的映射）
    ("GENERATES_LOG", "LOG_SOURCE", "LOG_ENTRY", "日志来源产生某日志条目（如防火墙日志）", "relationship--generates-log"),
    ("HAS_FIELD", "LOG_ENTRY", "LOG_FIELD", "日志条目包含某关键字段（如src_ip/event_id）", "relationship--has-field"),
    ("RECORDS_IOC", "LOG_ENTRY", "IOC_INDICATOR", "日志记录某威胁IOC（如恶意IP/PID）", "relationship--records-ioc"),
    ("SHOWS_ANOMALY", "LOG_ENTRY", "LOG_ANOMALY", "日志反映某异常（如登录失败/异常进程）", "relationship--shows-anomaly"),
    ("TRIGGERED_BY_TTP", "LOG_ANOMALY", "ATTACK_TTP", "日志异常由某攻击技术触发（如T1059）", "relationship--triggered-by-ttp"),
    ("LINKS_EVENT", "LOG_ENTRY", "ATTACK_EVENT", "日志条目关联某攻击事件（如勒索攻击）", "relationship--links-event"),
    
    # 【流量-威胁链路】关联（强化流量与C2/恶意软件的映射）
    ("COMPOSES_SESSION", "NETWORK_FLOW", "TRAFFIC_SESSION", "网络流构成某流量会话（如C2会话）", "relationship--composes-session"),
    ("HAS_PACKET_FEAT", "NETWORK_FLOW", "PACKET_FEATURE", "网络流包含某数据包特征（如畸形TCP头）", "relationship--has-packet-feat"),
    ("SHOWS_FLOW_ANOMALY", "TRAFFIC_SESSION", "FLOW_ANOMALY", "流量会话呈现某异常（如心跳包）", "relationship--shows-flow-anomaly"),
    ("CONNECTS_C2_SESSION", "TRAFFIC_SESSION", "COMMAND_CONTROL", "流量会话连接某C2服务器", "relationship--connects-c2-session"),
    ("CARRIES_MALWARE", "NETWORK_FLOW", "MALWARE", "网络流传输某恶意软件（如HTTP下载）", "relationship--carries-malware"),
    ("LINKS_LOG", "TRAFFIC_SESSION", "LOG_ENTRY", "流量会话关联某日志条目（如防火墙允许日志）", "relationship--links-log")
]

# ------------------------------
# 4. STIX 2.1 实体属性关键字（统一属性映射，适配STIX数据格式）
# ------------------------------
STIX_COMMON_PROPERTIES = {
    "ID": "id",                          # 唯一标识符（STIX标准格式：实体类型--UUID，如malware--xxxx）
    "TYPE": "type",                      # 实体类型（对应THREAT_INTEL_ENTITY_TYPES的值）
    "NAME": "name",                      # 实体名称（如"CVE-2021-44228"、"APT29"）
    "DESCRIPTION": "description",        # 实体描述（如漏洞详情、攻击事件背景）
    "CONFIDENCE": "confidence",          # 置信度（0-100，如"IOC可信度90"）
    "SOURCE": "source",                  # 情报来源（如"CISA"、"MITRE"）
    "PUBLISH_TIMESTAMP": "published",    # 情报发布时间（如漏洞公告、IOC发布时间，ISO 8601格式）
    "EXPIRY_TIMESTAMP": "expires",       # 情报过期时间（如IOC失效时间、临时威胁预警有效期，必填于时效性强的实体）
    "LAST_UPDATED_TIMESTAMP": "modified" # 情报最后更新时间（如漏洞补丁发布后更新情报、IOC状态变更时间）
}


# 4.1 各实体专属STIX属性（补充核心业务属性）
STIX_ENTITY_PROPERTIES = {
    # 漏洞专属属性
    "VULNERABILITY": {
        "CVE_ID": "cve_id",              # CVE编号（如"CVE-2021-44228"）
        "CVSS_SCORE": "cvss_base_score", # CVSS评分（如9.8）
        "PUBLISH_DATE": "published_date" # 发布日期（ISO 8601）
    },
    # 日志专属属性
    "LOG_ENTRY": {
        "LOG_TIMESTAMP": "log_timestamp",# 日志时间戳（如"2024-05-20T14:30:00Z"）
        "LOG_LEVEL": "log_level",        # 日志级别（如"INFO"、"WARN"、"ERROR"）
        "DEVICE_ID": "device_id"         # 日志来源设备ID（如防火墙设备编号）
    },
    # 流量专属属性
    "NETWORK_FLOW": {
        "SRC_IP": "src_ip",              # 源IP地址
        "DST_IP": "dst_ip",              # 目的IP地址
        "SRC_PORT": "src_port",          # 源端口
        "DST_PORT": "dst_port",          # 目的端口
        "PROTOCOL": "protocol",          # 协议类型（如"TCP"、"UDP"）
        "FLOW_DURATION": "duration"      # 流持续时间（秒）
    }
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

# ------------------------------
# 4. 漏洞利用链示例（实体-关系组合）
# 场景：APT组织利用ProxyShell漏洞攻击Exchange服务器
# ------------------------------
EXPLOIT_CHAIN_EXAMPLE = {
    "entities": [
        {"id": "org1", "type": "THREAT_ORGANIZATION", "name": "APT34"},
        {"id": "tool1", "type": "EXPLOIT_TOOL", "subtype": "POC_SCRIPT", "name": "ProxyShell Exploit Python脚本"},
        {"id": "vuln1", "type": "VULNERABILITY", "subtype": "RCE", "name": "CVE-2021-34527（ProxyShell）"},
        {"id": "port1", "type": "NETWORK_PORT", "subtype": "WEB_PORT", "name": "443/TCP"},
        {"id": "service1", "type": "TARGET_SERVICE", "name": "Exchange EWS服务"},
        {"id": "system1", "type": "TARGET_SYSTEM", "name": "Exchange Server 2019"},
        {"id": "step1", "type": "EXPLOIT_CHAIN_STEP", "name": "步骤1：漏洞扫描"},
        {"id": "step2", "type": "EXPLOIT_CHAIN_STEP", "name": "步骤2：远程代码执行"},
        {"id": "tech1", "type": "EXPLOIT_TECHNIQUE", "name": "远程代码执行（RCE）"},
        {"id": "ttp1", "type": "ATTACK_TTP", "name": "T1190（利用已知漏洞）"}
    ],
    "relations": [
        ("DEVELOPS", "org1", "tool1", "APT34开发ProxyShell攻击脚本"),
        ("TARGETS_VULNERABILITY", "tool1", "vuln1", "脚本针对CVE-2021-34527设计"),
        ("REQUIRES_PORT", "vuln1", "port1", "ProxyShell漏洞利用需通过443端口"),
        ("AFFECTS_SERVICE", "vuln1", "service1", "漏洞影响Exchange EWS服务"),
        ("STEP_USES_TOOL", "step1", "tool1", "步骤1使用扫描工具探测漏洞"),
        ("STEP_EXPLOITS_VULN", "step2", "vuln1", "步骤2利用CVE-2021-34527执行代码"),
        ("NEXT_STEP", "step1", "step2", "步骤1之后执行步骤2"),
        ("CHAIN_MAPS_TO_TTP", "step2", "ttp1", "步骤2对应T1190战术"),
        ("COMPROMISES_SYSTEM", "tech1", "system1", "RCE技术攻陷Exchange服务器")
    ]
}