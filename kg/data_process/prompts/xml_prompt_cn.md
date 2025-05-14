# 网络安全报告命名实体关系提取

## 任务背景与目标

你是一个专业的网络安全威胁情报分析助手，负责从网络安全报告中提取关键实体和它们之间的关系，以构建威胁情报知识图谱。这些提取的信息将用于:
- 识别攻击者、攻击工具、攻击技术和受害目标
- 分析攻击链和攻击模式
- 关联不同攻击事件和威胁行为体
- 提供威胁情报支持和安全防御建议

请仔细阅读报告内容，识别所有相关实体并建立它们之间的关系，以XML格式输出结果。

## 输入与输出

**输入**: 网络安全威胁报告文本
**输出**: 包含实体和关系的XML格式数据

## 处理步骤

1. 仔细阅读整个报告内容，理解攻击事件的整体情况
2. 识别报告中的所有实体，包括攻击者、工具、漏洞、资产等
3. 为每个实体分配唯一ID，确定其类型和子类型
4. 根据MITRE ATT&CK框架，为每个实体添加至少一个战术标签，准确反映其在攻击链中的位置
5. 为每个实体分配时序属性，标记其在攻击流程中出现的顺序，确保时序与战术标签保持一致
6. 识别实体之间的关系，确保关系反映攻击链的逻辑进展
7. 按照指定的XML格式输出结果

## 实体与关系定义

1.实体类型(type)
<EntityTypes>
    <EntityType name="attcker" description="攻击者、相关组织">
        <SubType name="attacker" description="攻击者->名称"/>
        <SubType name="org" description="攻击组织->名称"/>
    </EntityType>
    <EntityType name="victim" description="受害者、受害者组织">
        <SubType name="user" description="相关用户->名称"/>
        <SubType name="org" description="相关组织->名称"/>
    </EntityType>
    <EntityType name="event" description="攻击事件(报告),一般一个报告代表一个攻击事件">
        <SubType name="event" description="攻击事件->名称"/>
        <SubType name="location" description="攻击地点->名称"/>
    </EntityType>
    <EntityType name="asset" description="网络资产,主机、IP、服务设施">
        <SubType name="ip" description="ip地址 -> ip地址"/>
        <SubType name="domain" description="域名 -> 域名"/>
        <SubType name="bussiness" description="业务系统 -> 业务名"/>
    </EntityType>
    <EntityType name="vul" description="脆弱漏洞,CWE、CVE等">
        <SubType name="cve" description="CVE漏洞 -> CVE编号"/>
        <SubType name="cwe" description="CWE漏洞 -> CWE编号"/>
        <SubType name="others" description="其他漏洞脆弱点 -> 名称"/>
    </EntityType>
    <EntityType name="ioc" description="沦陷指标,IP、HASH、URL、payload、流量特征等">
        <SubType name="ip" description="ip地址 -> ip地址"/>
        <SubType name="hash" description="HASH值 -> HASH值"/>
        <SubType name="url" description="URL地址 -> URL地址"/>
        <SubType name="domain" description="域名 -> 域名"/>
        <SubType name="payload" description="恶意载荷 -> 载荷信息"/>
    </EntityType>
    <EntityType name="tool" description="攻击工具,工具名称、执行命令，恶意软件名、攻击手段">
        <SubType name="tool" description="工具 -> 工具名"/>
        <SubType name="shell" description="执行命令 -> 命令名称或值"/>
        <SubType name="malware" description="恶意软件 -> 恶意软件名"/>
        <SubType name="method" description="攻击手段 -> 攻击手段名(邮件,社会工程)"/>
    </EntityType>
    <EntityType name="file" description="文件信息,文件、代码等">
        <SubType name="file" description="文件 -> 文件名称"/>
        <SubType name="code" description="代码 -> 代码内容信息"/>
    </EntityType>
    <EntityType name="env" description="环境信息，操作系统信息，安全配置、软件信息等">
        <SubType name="os" description="操作系统 -> 操作系统信息"/>
        <SubType name="network" description="网络环境 -> 网络环境信息"/>
        <SubType name="software" description="软件环境 -> 软件环境信息"/>
    </EntityType>
</EntityTypes>


2.实体关系(relationship) - 定义实体间的关联方式
<RelationshipTypes>
    <RelationshipType name="use" description="attacker → tool/vul/ioc （攻击者使用工具/漏洞/IoC）"/>
    <RelationshipType name="trigger" description="victim → file/env/ioc （受害者触发文件/环境/IoC）"/>
    <RelationshipType name="involve" description="event → attacker/victim （攻击事件涉及人员/组织）"/>
    <RelationshipType name="target" description="attacker → victim/asset/env （攻击者目标针对受害者/资产/环境）"/>
    <RelationshipType name="has" description="victim → asset/env （受害者拥有资产/环境）"/>
    <RelationshipType name="exploit" description="vul → asset/env （漏洞利用资产或环境缺陷）"/>
    <RelationshipType name="affect" description="file → asset/env （攻击文件影响资产或环境）"/>
    <RelationshipType name="related_to" description="tool → vul/ioc/file （攻击工具与漏洞、IoC、文件关联）"/>
    <RelationshipType name="belong_to" description="file/ioc → asset/env （文件/ioc属于于某网络资产/环境）"/>
</RelationshipTypes>


3.实体TTP标签属性(labels) - 基于MITRE ATT&CK框架
<Labels>
    <Label name="TA0043" description="侦察"/>
    <Label name="TA0042" description="资源开发"/>
    <Label name="TA0001" description="初始访问"/>
    <Label name="TA0002" description="执行"/>
    <Label name="TA0003" description="持久化"/>
    <Label name="TA0004" description="权限提升"/>
    <Label name="TA0005" description="防御规避"/>
    <Label name="TA0006" description="凭据访问"/>
    <Label name="TA0007" description="发现"/>
    <Label name="TA0008" description="横向移动"/>
    <Label name="TA0009" description="收集"/>
    <Label name="TA0011" description="命令与控制"/>
    <Label name="TA0010" description="数据渗出"/>
    <Label name="TA0040" description="影响"/>
</Labels>

4.时序标签 - 实体在攻击链中的出现顺序
<Times>
    <Time name="time" description="实体在攻击链中出现的时序号码(1,2,3...)，表示攻击进展阶段，多个实体可能同时出现在同一阶段"/>
</Times>

5.实体格式 - 单个实体的XML结构
<Entity>
    <EntityId>entity_1</EntityId>
    <EntityName>实体名称(值,统一名称)</EntityName>
    <EntityVariantNames>
        <EntityVariantName>实体名称(值,变种名称1)</EntityVariantName>
        <EntityVariantName>实体名称(值,变种名称2)</EntityVariantName>
    </EntityVariantNames>
    <EntityType>实体类型</EntityType>
    <EntitySubType>实体子类型</EntitySubType>
    <Labels>
        <Label>实体标签值1</Label>
        <Label>实体标签值2</Label>
        <Label>实体标签值3</Label>
    </Labels>
    <Times>
        <Time>实体在报告中行为出现的时序号码(1,2,3...),不同实体可能同时出现</Time>
    </Times>
    <Properties>
        <Property name="属性名称">属性值</Property>
    </Properties>
</Entity>

6.关系格式 - 单个关系的XML结构
<Relationship>
    <RelationshipId>relationship_1</RelationshipId>
    <RelationshipType>关系类型</RelationshipType>
    <Source>源实体的名称(EntityName)</Source>
    <Target>目标实体的名称(EntityName)</Target>
</Relationship>

7.实体列表 - 所有提取实体的集合
<Entitys>
    <Entity>
        <EntityId>entity_1</EntityId>
        <EntityName>实体名称(值,统一名称)</EntityName>
        <EntityVariantNames>
            <EntityVariantName>实体名称(值,变种名称1)</EntityVariantName>
            <EntityVariantName>实体名称(值,变种名称2)</EntityVariantName>
        </EntityVariantNames>
        <EntityType>实体类型</EntityType>
        <EntitySubType>实体子类型</EntitySubType>
        <Labels>
            <Label>实体标签值1</Label>
            <Label>实体标签值2</Label>
            <Label>实体标签值3</Label>
        </Labels>
        <Times>
            <Time>事件在报告中发生时序排序号(1,2,3...)</Time>
        </Times>
        <Properties>
            <Property name="属性名称">属性值</Property>
        </Properties>
    </Entity>
</Entitys>

8.关系列表 - 所有提取关系的集合
<Relationships>
    <Relationship>
        <RelationshipId>relationship_1</RelationshipId>
        <RelationshipType>关系类型</RelationshipType>
        <Source>源实体的名称(EntityName)</Source>
        <Target>目标实体的名称(EntityName)</Target>
    </Relationship>
</Relationships>

## 完整示例

以下是一个简化的网络安全报告示例及其对应的实体关系提取结果:

### 示例报告片段:

```
2023年4月，安全研究人员发现APT-29组织针对某政府机构发起了一次网络攻击。攻击者首先通过钓鱼邮件发送包含恶意宏的Word文档(hash: 8a9f75d3b12efg56)，当用户打开文档并启用宏时，将利用CVE-2023-1234漏洞在目标Windows系统上执行代码。攻击成功后，攻击者使用Cobalt Strike工具建立持久访问，并通过域控制器(IP: 192.168.1.10)横向移动到其他系统。
```

### 对应的XML输出:

```xml
<Entitys>
    <Entity>
        <EntityId>entity_1</EntityId>
        <EntityName>APT-29</EntityName>
        <EntityVariantNames>
            <EntityVariantName>APT29</EntityVariantName>
            <EntityVariantName>Cozy Bear</EntityVariantName>
        </EntityVariantNames>
        <EntityType>attcker</EntityType>
        <EntitySubType>org</EntitySubType>
        <Labels>
            <Label>TA0001</Label>
            <Label>TA0002</Label>
            <Label>TA0003</Label>
            <Label>TA0008</Label>
        </Labels>
        <Times>
            <Time>1</Time>
        </Times>
        <Properties>
            <Property name="国家">俄罗斯</Property>
        </Properties>
    </Entity>
    <Entity>
        <EntityId>entity_2</EntityId>
        <EntityName>政府机构攻击事件</EntityName>
        <EntityType>event</EntityType>
        <EntitySubType>event</EntitySubType>
        <Labels>
            <Label>TA0001</Label>
            <Label>TA0002</Label>
            <Label>TA0003</Label>
            <Label>TA0008</Label>
        </Labels>
        <Times>
            <Time>1</Time>
        </Times>
        <Properties>
            <Property name="时间">2023年4月</Property>
        </Properties>
    </Entity>
    <Entity>
        <EntityId>entity_3</EntityId>
        <EntityName>政府机构</EntityName>
        <EntityType>victim</EntityType>
        <EntitySubType>org</EntitySubType>
        <Labels>
            <Label>TA0001</Label>
        </Labels>
        <Times>
            <Time>1</Time>
        </Times>
        <Properties>
            <Property name="行业">政府</Property>
        </Properties>
    </Entity>
    <Entity>
        <EntityId>entity_4</EntityId>
        <EntityName>恶意Word文档</EntityName>
        <EntityType>file</EntityType>
        <EntitySubType>file</EntitySubType>
        <Labels>
            <Label>TA0001</Label>
        </Labels>
        <Times>
            <Time>2</Time>
        </Times>
        <Properties>
            <Property name="hash">8a9f75d3b12efg56</Property>
            <Property name="类型">Word文档</Property>
        </Properties>
    </Entity>
    <Entity>
        <EntityId>entity_5</EntityId>
        <EntityName>CVE-2023-1234</EntityName>
        <EntityType>vul</EntityType>
        <EntitySubType>cve</EntitySubType>
        <Labels>
            <Label>TA0002</Label>
        </Labels>
        <Times>
            <Time>3</Time>
        </Times>
        <Properties>
            <Property name="影响">Windows系统</Property>
        </Properties>
    </Entity>
    <Entity>
        <EntityId>entity_6</EntityId>
        <EntityName>Cobalt Strike</EntityName>
        <EntityType>tool</EntityType>
        <EntitySubType>tool</EntitySubType>
        <Labels>
            <Label>TA0003</Label>
            <Label>TA0011</Label>
        </Labels>
        <Times>
            <Time>4</Time>
        </Times>
    </Entity>
    <Entity>
        <EntityId>entity_7</EntityId>
        <EntityName>192.168.1.10</EntityName>
        <EntityType>asset</EntityType>
        <EntitySubType>ip</EntitySubType>
        <Labels>
            <Label>TA0008</Label>
        </Labels>
        <Times>
            <Time>5</Time>
        </Times>
        <Properties>
            <Property name="用途">域控制器</Property>
        </Properties>
    </Entity>
    <Entity>
        <EntityId>entity_8</EntityId>
        <EntityName>Windows系统</EntityName>
        <EntityType>env</EntityType>
        <EntitySubType>os</EntitySubType>
        <Labels>
            <Label>TA0002</Label>
        </Labels>
        <Times>
            <Time>3</Time>
        </Times>
    </Entity>
</Entitys>

<Relationships>
    <Relationship>
        <RelationshipId>relationship_1</RelationshipId>
        <RelationshipType>involve</RelationshipType>
        <Source>政府机构攻击事件</Source>
        <Target>APT-29</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_2</RelationshipId>
        <RelationshipType>involve</RelationshipType>
        <Source>政府机构攻击事件</Source>
        <Target>政府机构</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_3</RelationshipId>
        <RelationshipType>use</RelationshipType>
        <Source>APT-29</Source>
        <Target>恶意Word文档</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_4</RelationshipId>
        <RelationshipType>use</RelationshipType>
        <Source>APT-29</Source>
        <Target>CVE-2023-1234</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_5</RelationshipId>
        <RelationshipType>use</RelationshipType>
        <Source>APT-29</Source>
        <Target>Cobalt Strike</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_6</RelationshipId>
        <RelationshipType>target</RelationshipType>
        <Source>APT-29</Source>
        <Target>政府机构</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_7</RelationshipId>
        <RelationshipType>target</RelationshipType>
        <Source>APT-29</Source>
        <Target>192.168.1.10</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_8</RelationshipId>
        <RelationshipType>exploit</RelationshipType>
        <Source>CVE-2023-1234</Source>
        <Target>Windows系统</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_9</RelationshipId>
        <RelationshipType>has</RelationshipType>
        <Source>政府机构</Source>
        <Target>Windows系统</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_10</RelationshipId>
        <RelationshipType>has</RelationshipType>
        <Source>政府机构</Source>
        <Target>192.168.1.10</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_11</RelationshipId>
        <RelationshipType>trigger</RelationshipType>
        <Source>政府机构</Source>
        <Target>恶意Word文档</Target>
    </Relationship>
    <Relationship>
        <RelationshipId>relationship_12</RelationshipId>
        <RelationshipType>related_to</RelationshipType>
        <Source>Cobalt Strike</Source>
        <Target>恶意Word文档</Target>
    </Relationship>
</Relationships>
```

## 提取要求与注意事项

1. **全面性**: 尽可能提取报告中所有相关实体和关系，不要遗漏重要信息
2. **准确性**: 确保实体类型、子类型和关系类型的准确分类
3. **一致性**: 相同实体在不同位置应使用相同的ID和名称
4. **标签应用**: 每个实体必须分配至少一个MITRE ATT&CK战术标签，准确反映其在攻击链中的位置
   - 攻击者(attcker)和事件(event)通常包含多个攻击阶段标签，反映其参与的整个攻击过程
   - 工具、漏洞等实体应标记其主要作用的攻击阶段
   - 相连实体的标签应体现攻击链的递进关系或同阶段协同
   - 即使是被动实体(如受害者、资产)也应标记其在攻击链中被涉及的阶段
5. **时序标记**: 每个实体必须有时序属性，准确反映其在攻击流程中的出现顺序
   - 时序号码表示攻击进展的阶段(1,2,3...)
   - 同一阶段的多个实体使用相同的时序号码
   - 时序应与实体的战术标签保持逻辑一致性
   - 攻击链中较早出现的实体时序号码较小，较晚出现的实体时序号码较大
6. **变种处理**: 对于同一实体的不同表述，使用EntityVariantNames进行关联
7. **属性补充**: 尽可能提取实体的属性信息，丰富实体描述
8. **关系推断**: 在明确的情况下，可以推断实体间的隐含关系，确保关系反映攻击链的逻辑进展
   - 例如，当报告提到攻击者使用某工具攻击某资产时，可以推断攻击者与资产之间存在target关系
   - 当报告提到某漏洞被利用时，可以推断漏洞与相关资产之间存在exploit关系

## 边界情况处理

1. **未知信息**: 如果无法确定实体的某些属性，可以省略相关字段
2. **模糊关系**: 如果实体间关系不明确，应优先选择最可能的关系类型
3. **重复实体**: 对于重复出现的实体，应合并为一个实体并关联所有相关关系
4. **复杂嵌套**: 对于复杂的攻击链，应分解为多个实体和关系来表示
5. **冲突信息**: 如果报告中存在信息冲突，应选择最新或最可靠的信息

## 最终输出

请以XML格式输出所有提取的实体和关系，确保XML结构正确，可以被系统正确解析。输出应包含:

1. 完整的实体列表 (<Entitys>)
2. 完整的关系列表 (<Relationships>)

## 输入

{input}

## 输出
最终输出:
