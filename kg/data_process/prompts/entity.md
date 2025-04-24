这是一个网络安全威胁情报知识图谱实体关系提取的任务，请帮我从这个报告中提取所有实体和关系:{report_input}
涉及到的要求和相关知识如下:
实体、标签、关系相关描述及约束:
类型:
```python
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
```
关系:
```python

#分层图谱实体关系
#--------------------层内关系---------------------------------------------
#-------------------事件、情报层------------------------------------------

class RelationshipType(Enum):
    """
    定义图谱中实体间的关系类型
    """
    # 事件、情报层关系
    INVOLVE = "involve"  # Event → Person/Org （攻击事件涉及人员/组织）
    USE = "use"  # Event → Tool/Vul/IoC （攻击事件使用工具/漏洞/IoC）
    TARGET = "target"  # Event → Asset/Env （攻击事件针对资产/环境）
    
    # 知识层关系
    EXPLOIT = "exploit"  # Vul → Asset/Env （漏洞利用资产或环境缺陷）
    GENERATE = "generate"  # Tool → IoC/File （攻击工具生成IoC或文件）
    BELONG_TO = "belong_to"  # IoC → Asset （IoC属于某网络资产）
    AFFECT = "affect"  # File → Asset/Env （攻击文件影响资产或环境）

#-------------------知识层------------------------------------------------
class KGRelationshipType(Enum):
    """
      定义知识层图谱中实体间的关系类型
    """
    EMPLOY = "employ"  # Org → Attack （威胁组织使用攻击手段）
    MITIGATE = "mitigate"  # Defend → Attack （防御对策缓解攻击手段）
    TARGET_ATTACK = "target"  # Attack → Target （攻击手段针对特定目标）
    RELATE_TO = "relate_to"  # Attack → CAPEC （攻击手段关联CAPEC模式）
    BELONG_TO_TACTIC = "belong_to"  # Attack → Tactic （攻击技术属于某战术分类）


#-----------------层间关系-------------------------------------------------

class LayerRelationshipType(Enum):
    """
      定义不同层之间的关系类型
    """
    # 层间关系
    CLASSIFIED_AS = "classified_as"  # Event/Attack → TTP/CAPEC （事件/攻击被分类为TTP或CAPEC标签）
    ASSOCIATE_WITH = "associate_with"  # IoC/File → Attack （IoC/文件通过标签关联攻击手段）
    INDICATE = "indicate"  # Vul/Env → Attack （漏洞/环境通过标签指示潜在攻击）
    MAP_TO = "map_to"  # Defend → Vul/Asset （防御对策映射到漏洞/资产保护）
    ATTRIBUTE_TO = "attribute_to"  # Event → Org （事件通过标签归因于威胁组织）
```


输出格式:
```json
{
    "entitys": [
        {
            "entity_id": "entity_1", // 实体ID按顺序生成，不能重复
            "entity": "实体名称",
            "type": "实体类型", 
            "subtype": "实体子类型",
            "labels": ["实体标签值1", "实体标签值2", "实体标签值3"],
            "value": "实体值",
            "properties": {
                "属性名称": "属性值",
                "属性名称": "属性值"
            },
        },
        {
            "entity": "实体名称",
            "type": "实体类型", 
            "subtype": "实体子类型",
            "labels": ["实体标签值1", "实体标签值2", "实体标签值3"],
            "value": "实体值",
            "properties": {
                "属性名称": "属性值",
                "属性名称": "属性值"
            },
        }
    ],
    "relationships":[
        {
            "relationship": "关系名称",
            "source": "源实体entity_id的值",
            "target": "目标实体entity_id的值",
        },
    ]
}


```
提取示例:
