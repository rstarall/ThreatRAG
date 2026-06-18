"""
威胁情报知识图谱数据模型

基于 docs/knowledge_graph_schema.md 定义的实体关系 Schema。
包含：枚举、实体、关系、子图、搜索参数。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class EntityType(str, Enum):
    """实体大类枚举。attacker/victim 的 typo 在 normalize() 中做兼容转换。"""

    ATTACKER = "attacker"
    VICTIM = "victim"
    EVENT = "event"
    ASSET = "asset"
    VUL = "vul"
    IOC = "ioc"
    TOOL = "tool"
    FILE = "file"
    ENV = "env"

    @classmethod
    def display_name(cls) -> Dict["EntityType", str]:
        return {
            cls.ATTACKER: "攻击者/组织",
            cls.VICTIM: "受害者/组织",
            cls.EVENT: "攻击事件",
            cls.ASSET: "网络资产",
            cls.VUL: "漏洞/脆弱点",
            cls.IOC: "沦陷指标",
            cls.TOOL: "攻击工具/恶意软件",
            cls.FILE: "文件信息",
            cls.ENV: "环境信息",
        }

    @classmethod
    def normalize(cls, value: str) -> "EntityType":
        mapping = {
            "attacker": cls.ATTACKER,
            "victim": cls.VICTIM
        }
        if value in mapping:
            return mapping[value]
        return cls(value)


class RelationshipType(str, Enum):
    """关系类型枚举，Source → Target。"""

    USE = "use"              # attacker/org → tool/vul/ioc（攻击者使用工具/漏洞/IoC）
    TRIGGER = "trigger"      # victim → file/env/ioc（受害者触发文件/环境/IoC）
    INVOLVE = "involve"     # event → attacker/victim（攻击事件涉及人员/组织）
    TARGET = "target"        # attacker/org → victim/asset/env（攻击者针对受害者/资产/环境）
    HAS = "has"              # victim → asset/env（受害者拥有资产或环境）
    EXPLOIT = "exploit"      # vul → asset/env（漏洞利用资产或环境缺陷）
    AFFECT = "affect"        # file → asset/env（攻击文件影响资产或环境）
    RELATED_TO = "related_to"  # tool ↔ vul/ioc/file（工具与漏洞/IoC/文件相关联）
    BELONG_TO = "belong_to"  # file/ioc/asset → asset/env; attacker → org（实体归属于组织或网络资产）

    @property
    def description(self) -> str:
        return {
            self.USE: "攻击者/组织使用工具/漏洞/IoC",
            self.TRIGGER: "受害者触发文件/环境/IoC",
            self.INVOLVE: "攻击事件涉及人员/组织",
            self.TARGET: "攻击者针对受害者/资产/环境",
            self.HAS: "受害者拥有资产或环境",
            self.EXPLOIT: "漏洞利用资产或环境缺陷",
            self.AFFECT: "攻击文件影响资产或环境",
            self.RELATED_TO: "工具与漏洞/IoC/文件相关联",
            self.BELONG_TO: "实体归属于组织或网络资产",
        }[self]


# ---------------------------------------------------------------------------
# 子类型枚举
# ---------------------------------------------------------------------------

class AttackerSubType(str, Enum):
    """attacker 实体的细分子类。

    - attacker: 单个攻击者（如 Wicked Rose、KuNgBiM、Rodag）
    - org: 攻击组织/黑客团队（如 NCPH、Evil Security Team）
    """
    ATTACKER = "attacker"
    ORG = "org"


class VictimSubType(str, Enum):
    """victim 实体的细分子类。

    - user: 相关用户
    - org: 受害者组织（如 US DoD Entity、Japanese Organization）
    """
    USER = "user"
    ORG = "org"


class EventSubType(str, Enum):
    """event 实体的细分子类。

    - event: 攻击事件名称
    - location: 攻击发生地点
    """
    EVENT = "event"
    LOCATION = "location"


class AssetSubType(str, Enum):
    """asset 实体的细分子类。

    - ip: IP 地址
    - domain: 域名（如 www.ncph.net、www.mghacker.com）
    - bussiness: 业务系统名称
    """
    IP = "ip"
    DOMAIN = "domain"
    BUSSINESS = "bussiness"


class VulSubType(str, Enum):
    """vul 实体的细分子类。

    - cve: CVE 编号漏洞（如 CVE-2023-1234）
    - cwe: CWE 分类弱点
    - others: 其他漏洞泛指（如 Microsoft Word Malformed OLE Structure Code Execution）
    """
    CVE = "cve"
    CWE = "cwe"
    OTHERS = "others"


class IocSubType(str, Enum):
    """ioc 实体的细分子类（沦陷指标）。

    - ip: IP 地址
    - hash: 文件 Hash 值
    - url: URL 地址
    - domain: 域名
    - payload: 恶意载荷信息
    """
    IP = "ip"
    HASH = "hash"
    URL = "url"
    DOMAIN = "domain"
    PAYLOAD = "payload"


class ToolSubType(str, Enum):
    """tool 实体的细分子类。

    - tool: 攻击工具
    - shell: 执行命令
    - malware: 恶意软件名称（如 GinWui、RipGof、PcShare Trojan）
    - method: 攻击手段（如社工、邮件）
    """
    TOOL = "tool"
    SHELL = "shell"
    MALWARE = "malware"
    METHOD = "method"


class FileSubType(str, Enum):
    """file 实体的细分子类。

    - file: 文件名称（如 Planning document 5-16-2006.doc）
    - code: 代码内容片段
    """
    FILE = "file"
    CODE = "code"


class EnvSubType(str, Enum):
    """env 实体的细分子类。

    - os: 操作系统（如 Windows系统）
    - network: 网络环境
    - software: 软件环境（如 Microsoft Word）
    """
    OS = "os"
    NETWORK = "network"
    SOFTWARE = "software"


class TTPLabel(str, Enum):
    """MITRE ATT&CK 战术标签枚举，对应 Schema §4。"""

    RECONNAISSANCE = "TA0043"           # 侦察（Reconnaissance）：收集目标相关信息
    RESOURCE_DEVELOPMENT = "TA0042"     # 资源开发（Resource Development）：建立攻击资源
    INITIAL_ACCESS = "TA0001"           # 初始访问（Initial Access）：突破边界进入目标网络
    EXECUTION = "TA0002"                # 执行（Execution）：在目标环境运行攻击代码
    PERSISTENCE = "TA0003"              # 持久化（Persistence）：保持长期访问
    PRIVILEGE_ESCALATION = "TA0004"     # 权限提升（Privilege Escalation）：获取更高权限
    DEFENSE_EVASION = "TA0005"          # 防御规避（Defense Evasion）：绕过安全检测
    CREDENTIAL_ACCESS = "TA0006"        # 凭据访问（Credential Access）：窃取账户凭据
    DISCOVERY = "TA0007"                # 发现（Discovery）：了解目标环境
    LATERAL_MOVEMENT = "TA0008"         # 横向移动（Lateral Movement）：在网络中移动
    COLLECTION = "TA0009"               # 收集（Collection）：收集目标数据
    COMMAND_AND_CONTROL = "TA0011"       # 命令与控制（Command and Control）：远程控制受感染主机
    EXFILTRATION = "TA0010"             # 数据渗出（Exfiltration）：窃取目标数据
    IMPACT = "TA0040"                   # 影响（Impact）：造成业务影响或破坏

    @classmethod
    def is_valid(cls, label: str) -> bool:
        try:
            cls(label)
            return True
        except ValueError:
            return False


# ---------------------------------------------------------------------------
# 核心数据模型
# ---------------------------------------------------------------------------

@dataclass
class Entity:
    """知识图谱实体，对应 Schema §2 的所有字段。

    字段说明：
    - entity_id: 唯一标识，格式 "entity_N"（N 从 1 递增）
    - entity_name: 规范唯一名称，用于全局引用
    - entity_type: 实体大类（attacker/victim/event/asset/vul/ioc/tool/file/env）
    - entity_sub_type: 细分子类（如 attacker/org/ip/domain/cve 等）
    - labels: MITRE ATT&CK 战术标签数组，至少 1 个
    - times: 时序阶段标签数组，表示实体在攻击链中出现的时间阶段
    - entity_variant_names: 别名/变种名数组
    - properties: 额外键值属性，key/value 均为 string
    - neo4j_id: Neo4j 内部节点 ID
    - embedding: 实体向量嵌入（可选）
    """

    entity_id: str                          # 唯一标识，格式 "entity_N"
    entity_name: str                         # 规范唯一名称
    entity_type: str                         # 实体大类（attacker/victim/event/asset/vul/ioc/tool/file/env）
    entity_sub_type: str                     # 细分子类
    labels: List[str]                        # MITRE ATT&CK 战术标签数组，至少 1 个
    times: List[str]                         # 时序阶段标签数组，如 ["1"]、["2", "3"]
    entity_variant_names: List[str] = field(default_factory=list)  # 别名/变种名数组
    properties: Dict[str, str] = field(default_factory=dict)        # 额外键值属性，key/value 均为 string
    neo4j_id: Optional[int] = None            # Neo4j 内部节点 ID
    embedding: Optional[List[float]] = None   # 实体向量嵌入（可选）

    def __post_init__(self):
        self.entity_type = EntityType.normalize(self.entity_type).value

    @property
    def display_type(self) -> str:
        return EntityType.display_name().get(
            EntityType.normalize(self.entity_type), self.entity_type
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "entity_variant_names": self.entity_variant_names,
            "entity_type": self.entity_type,
            "entity_sub_type": self.entity_sub_type,
            "labels": self.labels,
            "times": self.times,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        return cls(
            entity_id=data.get("entity_id", ""),
            entity_name=data.get("entity_name", ""),
            entity_variant_names=data.get("entity_variant_names") or [],
            entity_type=data.get("entity_type", ""),
            entity_sub_type=data.get("entity_sub_type", ""),
            labels=data.get("labels") or [],
            times=data.get("times") or [],
            properties=data.get("properties") or {},
            neo4j_id=data.get("neo4j_id"),
            embedding=data.get("embedding"),
        )


@dataclass
class Relationship:
    """知识图谱关系（有向边），对应 Schema §3 的所有字段。

    字段说明：
    - relationship_id: 唯一标识，格式 "relationship_N"
    - relationship_type: 关系类型（use/trigger/involve/target/has/exploit/affect/related_to/belong_to）
    - source: 源实体名称（对应 Entity.entity_name）
    - target: 目标实体名称（对应 Entity.entity_name）
    - source_id: 规范化后的源 entity_id（入库后填充）
    - target_id: 规范化后的目标 entity_id（入库后填充）
    - neo4j_rel_id: Neo4j 内部关系 ID
    """

    relationship_id: str      # 唯一标识，格式 "relationship_N"
    relationship_type: str     # use/trigger/involve/target/has/exploit/affect/related_to/belong_to
    source: str                # 源实体名称（对应 Entity.entity_name）
    target: str                # 目标实体名称（对应 Entity.entity_name）
    source_id: Optional[str] = None    # 规范化后的源 entity_id（入库后填充）
    target_id: Optional[str] = None    # 规范化后的目标 entity_id（入库后填充）
    neo4j_rel_id: Optional[int] = None  # Neo4j 内部关系 ID

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "relationship_id": self.relationship_id,
            "relationship_type": self.relationship_type,
            "source": self.source,
            "target": self.target,
        }
        if self.source_id:
            d["source_id"] = self.source_id
        if self.target_id:
            d["target_id"] = self.target_id
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        return cls(
            relationship_id=data.get("relationship_id", ""),
            relationship_type=data.get("relationship_type", ""),
            source=data.get("source", ""),
            target=data.get("target", ""),
            source_id=data.get("source_id"),
            target_id=data.get("target_id"),
            neo4j_rel_id=data.get("neo4j_rel_id"),
        )


# ---------------------------------------------------------------------------
# 知识图谱 & 子图容器
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeGraph:
    """顶层知识图谱容器，包含全部实体与关系。"""

    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)

    @property
    def entity_map(self) -> Dict[str, Entity]:
        return {e.entity_name: e for e in self.entities}

    @property
    def entity_id_map(self) -> Dict[str, Entity]:
        return {e.entity_id: e for e in self.entities}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        entities = [Entity.from_dict(e) for e in data.get("entities", [])]
        relationships = [Relationship.from_dict(r) for r in data.get("relationships", [])]
        return cls(entities=entities, relationships=relationships)


@dataclass
class SubGraph:
    """子图数据存储结构——存储子图内的所有实体和关系，不包含 BFS 路径等衍生数据。"""

    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    start_entity_name: Optional[str] = None
    max_depth: int = 1
    query_time_ms: Optional[float] = None

    @property
    def entity_map(self) -> Dict[str, Entity]:
        return {e.entity_name: e for e in self.entities}

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "metadata": {
                "start_entity_name": self.start_entity_name,
                "max_depth": self.max_depth,
                "entity_count": self.entity_count,
                "relationship_count": self.relationship_count,
                "query_time_ms": self.query_time_ms,
            },
        }

    def to_knowledge_graph(self) -> KnowledgeGraph:
        return KnowledgeGraph(entities=self.entities, relationships=self.relationships)


# ---------------------------------------------------------------------------
# 搜索参数
# ---------------------------------------------------------------------------

@dataclass
class SubGraphSearchParams:
    """子图搜索参数。"""

    start_entity_name: str
    max_depth: int = 2
    direction: str = "both"  # outgoing / incoming / both
    entity_types: Optional[List[str]] = None
    labels: Optional[List[str]] = None
    relationship_types: Optional[List[str]] = None
    limit_per_depth: Optional[int] = None

    def validate(self) -> bool:
        if self.max_depth < 1:
            self.max_depth = 1
        if self.max_depth > 10:
            self.max_depth = 10
        if self.direction not in ("outgoing", "incoming", "both"):
            self.direction = "both"
        return True


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def normalize_entity_type(value: str) -> str:
    """将 Schema 中的 typo 规范化为标准值。"""
    return EntityType.normalize(value).value


def build_subgraph_from_search(
    start_entity: Entity,
    bfs_results: List[Dict[str, Any]],
    entity_map: Dict[str, Entity],
    max_depth: int = 2,
    query_time_ms: Optional[float] = None,
) -> SubGraph:
    """从 Neo4j BFS 原始结果构建 SubGraph。"""
    entity_names: set = {start_entity.entity_name}
    rels: List[Relationship] = []

    for record in bfs_results:
        src_name: str = record["start"]
        tgt_name: str = record["end"]
        rel_type: str = record.get("rel_type", "related_to")

        src_entity = entity_map.get(src_name)
        tgt_entity = entity_map.get(tgt_name)
        if src_entity is None or tgt_entity is None:
            continue

        entity_names.add(src_name)
        entity_names.add(tgt_name)

        rels.append(Relationship(
            relationship_id=f"rel_{uuid.uuid4().hex[:8]}",
            relationship_type=rel_type,
            source=src_name,
            target=tgt_name,
            source_id=src_entity.entity_id,
            target_id=tgt_entity.entity_id,
        ))

    entities = [entity_map[name] for name in entity_names if name in entity_map]
    return SubGraph(
        entities=entities,
        relationships=rels,
        start_entity_name=start_entity.entity_name,
        max_depth=max_depth,
        query_time_ms=query_time_ms,
    )


__all__ = [
    # 实体大类
    "EntityType",
    # 实体细分子类
    "AttackerSubType",
    "VictimSubType",
    "EventSubType",
    "AssetSubType",
    "VulSubType",
    "IocSubType",
    "ToolSubType",
    "FileSubType",
    "EnvSubType",
    # 关系类型
    "RelationshipType",
    # ATT&CK 标签
    "TTPLabel",
    # 核心数据模型
    "Entity",
    "Relationship",
    "KnowledgeGraph",
    "SubGraph",
    # 搜索参数
    "SubGraphSearchParams",
    # 工具函数
    "normalize_entity_type",
    "build_subgraph_from_search",
]
