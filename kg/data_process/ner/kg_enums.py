from enum import Enum

# 实体类型枚举
class EntityType(Enum):
    """
    实体类型枚举，定义知识图谱中的实体类型
    """
    ACTOR = "actor"               # 人员组织,攻击者、防御者、相关组织
    EVENT = "event"               # 攻击事件(报告),一般一个报告代表一个攻击事件
    ASSET = "asset"               # 网络资产,主机、IP、服务设施
    VULNERABILITY = "vul"         # 脆弱漏洞,CWE、CVE等
    IOC = "ioc"                   # 沦陷指标,IP、HASH、URL、payload、流量特征等
    TOOL = "tool"                 # 攻击工具,工具名称、执行命令，恶意软件名
    FILE = "file"                 # 文件信息,文件、代码等
    ENVIRONMENT = "env"           # 环境信息，操作系统信息，安全配置、软件信息等


# 实体子类型枚举
class ActorSubType(Enum):
    """
    人员组织子类型
    """
    PERSON = "person"             # 人员->名称
    ORGANIZATION = "org"          # 组织->名称


class EventSubType(Enum):
    """
    攻击事件子类型
    """
    ATTACK = "attack"             # 攻击事件->名称
    DEFENSE = "defend"            # 防御事件->名称
    LOCATION = "location"         # 攻击地点->名称


class AssetSubType(Enum):
    """
    网络资产子类型
    """
    IP = "ip"                     # ip地址 -> ip地址
    DOMAIN = "domain"             # 域名 -> 域名
    BUSINESS = "bussiness"        # 业务系统 -> 业务名


class VulnerabilitySubType(Enum):
    """
    脆弱漏洞子类型
    """
    CVE = "cve"                   # CVE漏洞 -> CVE编号
    CWE = "cwe"                   # CWE漏洞 -> CWE编号
    OTHERS = "others"             # 其他漏洞脆弱点 -> 名称


class IoCSubType(Enum):
    """
    沦陷指标子类型
    """
    IP = "ip"                     # ip地址 -> ip地址
    HASH = "hash"                 # HASH值 -> HASH值
    URL = "url"                   # URL地址 -> URL地址
    DOMAIN = "domain"             # 域名 -> 域名
    MALWARE = "malware"           # 恶意软件 -> 恶意软件名
    PAYLOAD = "payload"           # 恶意载荷 -> 载荷信息


class ToolSubType(Enum):
    """
    攻击工具子类型
    """
    TOOL = "tool"                 # 工具 -> 工具名


class FileSubType(Enum):
    """
    文件信息子类型
    """
    FILE = "file"                 # 文件 -> 文件名称
    CODE = "code"                 # 代码 -> 代码内容信息


class EnvironmentSubType(Enum):
    """
    环境信息子类型
    """
    OS = "os"                     # 操作系统 -> 操作系统信息
    NETWORK = "network"           # 网络环境 -> 网络环境信息
    SOFTWARE = "software"         # 软件环境 -> 软件环境信息


# 标签枚举 - 基于MITRE ATT&CK框架
class TTPLabel(Enum):
    """
    战术标签枚举，基于MITRE ATT&CK框架
    """
    RECONNAISSANCE = "TA0043"     # 侦察
    RESOURCE_DEVELOPMENT = "TA0042" # 资源开发
    INITIAL_ACCESS = "TA0001"     # 初始访问
    EXECUTION = "TA0002"          # 执行
    PERSISTENCE = "TA0003"        # 持久化
    PRIVILEGE_ESCALATION = "TA0004" # 权限提升
    DEFENSE_EVASION = "TA0005"    # 防御规避
    CREDENTIAL_ACCESS = "TA0006"  # 凭据访问
    DISCOVERY = "TA0007"          # 发现
    LATERAL_MOVEMENT = "TA0008"   # 横向移动
    COLLECTION = "TA0009"         # 收集
    COMMAND_AND_CONTROL = "TA0011" # 命令与控制
    EXFILTRATION = "TA0010"       # 数据渗出
    IMPACT = "TA0040"             # 影响


# 关系类型枚举
class RelationshipType(Enum):
    """
    关系类型枚举，定义实体间的关联方式
    """
    INVOLVE = "involve"           # Event → Actor （攻击事件涉及人员/组织）
    EVENT_USE = "event_use"       # Event → Tool/Vul/IoC （攻击事件中使用的工具/漏洞/IoC）
    ACTOR_USE = "actor_use"       # Actor → Tool/Vul/IoC （攻击人员/组织使用工具/漏洞/IoC）
    TARGET = "target"             # Event → Asset/Env （攻击事件针对资产/环境）
    EXPLOIT = "exploit"           # Vul → Asset/Env （漏洞利用资产或环境缺陷）
    GENERATE = "generate"         # Tool → IoC/File （攻击工具生成IoC或文件）
    BELONG_TO = "belong_to"       # IoC → Asset （IoC属于某网络资产）
    AFFECT = "affect"             # File → Asset/Env （攻击文件影响资产或环境）
