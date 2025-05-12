from enum import Enum


#实体标签
class EntityLabel(Enum):
    Tactic = "Tactic"
    Technique = "Technique"
    Procedure = "Procedure" #攻击程序
    Others = "Others"
    #从文件获取到 TTP信息
    #从文件获取到CAPEC信息

Tactics = {
    "TA0043": "Reconnaissance",           # 侦察
    "TA0042": "Resource Development",     # 资源开发
    "TA0001": "Initial Access",           # 初始访问
    "TA0002": "Execution",                # 执行
    "TA0003": "Persistence",              # 持久化
    "TA0004": "Privilege Escalation",     # 权限提升
    "TA0005": "Defense Evasion",          # 防御规避
    "TA0006": "Credential Access",        # 凭据访问
    "TA0007": "Discovery",                # 发现
    "TA0008": "Lateral Movement",         # 横向移动
    "TA0009": "Collection",               # 收集
    "TA0011": "Command and Control",      # 命令与控制
    "TA0010": "Exfiltration",             # 数据渗出
    "TA0040": "Impact"                    # 影响
}

Techniques = {
    "T1003": "System Owner/User Discovery",
    "T1006": "System Information Discovery", 
}
