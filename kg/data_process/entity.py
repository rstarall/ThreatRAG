from enum import Enum
import os

#分层知识图谱数据结构
#-------------------事件、情报层-------------------------------------
class EntityType(Enum):
    PERSON = "person"              # 人员组织
    EVENT = "event"               # 攻击事件
    ASSET = "asset"               # 网络资产
    VULNERABILITY = "vul"         # 脆弱漏洞
    IOC = "ioc"                   # 沦陷指标
    TOOL = "tool"                 # 攻击工具
    FILE = "file"                 # 文件信息
    ENVIRONMENT = "env"           # 环境信息


class PersonSubType(Enum):
    PERSON = "person"  #人员->名称
    ORGANIZATION = "org"  #组织->名称

class EventSubType(Enum):
    #每个报告可以有一个或多个攻击事件
    ATTACK = "attack"  #攻击事件->名称
    DEFENSE = "defend" #防御事件->名称
    LOCATION = "location" #攻击地点->名称

class AssetSubType(Enum):
    #代表攻击目标的资产
    IP = "ip" #ip地址 -> ip地址
    DOMAIN = "domain" #域名 -> 域名
    Bussniess = "business" #业务系统 -> 业务名

class VulnerabilitySubType(Enum):
    CVE = "cve" #CVE漏洞 -> CVE编号
    CWE = "cwe" #CWE漏洞 -> CWE编号
    Others = "others" #其他漏洞脆弱点 -> 名称

class IOCType(Enum):
    IP = "ip" #ip地址 -> ip地址
    HASH = "hash" #HASH值 -> HASH值
    URL = "url" #URL地址 -> URL地址
    DOMAIN = "domain" #域名 -> 域名
    MALWARE = "malware" #恶意软件 -> 恶意软件名
    PAYLOAD = "payload" #恶意载荷 -> 载荷信息

class ToolSubType(Enum):
    TOOL = "tool" #工具 -> 工具名

class FileSubType(Enum):
    FILE = "file" #文件 -> 文件名称
    CODE = "code" #代码 -> 代码内容信息

class EnvironmentSubType(Enum):
    OS = "os" #操作系统 -> 操作系统信息
    NETWORK = "network" #网络环境 -> 网络环境信息
    SOFTWARE = "software" #软件环境 -> 软件环境信息



#-------------------知识层-----------------------------------------
class KGEntityType(Enum):
    ATTACK = "attack"             # 攻击手段
    DEFENSE = "defend"            # 防御对策
    ORGANIZATION = "org"          # 威胁组织
    TARGET = "target"             # 攻击目标

class KGAttackSubType(Enum):
    Tactics = "tactics"           # 攻击战术
    Techniques = "techniques"     # 攻击技术
    SubTechniques = "subtechniques" # 子攻击技术
    Procedure = "procedure"     # 攻击程序
