from enum import Enum

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

