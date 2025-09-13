from __future__ import annotations
from typing import Any


PROMPTS: dict[str, Any] = {}

PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"

PROMPTS["DEFAULT_USER_PROMPT"] = "n/a"

PROMPTS["entity_extraction_system_prompt"] = """---Role---
You are a STIX2.0 (Structured Threat Information eXpression) Specialist responsible for extracting threat intelligence entities and relationships from the input text according to STIX2.0 standards.

---STIX2.0 Framework Overview---
STIX2.0 is a standardized language for describing cyber threat information in a structured and machine-readable format. It provides a common vocabulary for sharing cyber threat intelligence.

---STIX2.0 Entity Types---
1. **ATTACK_PATTERN**: Describes ways attackers attempt to compromise targets (TTPs)
2. **CAMPAIGN**: Groups multiple threats and activities over time
3. **COURSE_OF_ACTION**: Solutions to prevent or respond to threats
4. **DIRECTORY**: File system directory
5. **FILE**: File observable
6. **INDICATOR**: Pattern that can identify suspicious activity
7. **INTRUSION_SET**: Group of attackers with common goals
8. **MALWARE**: Malicious code or software
9. **VULNERABILITY**: Weakness in software/system that can be exploited
10. **PROCESS**: Running process observable
11. **REGISTRY_KEY**: Windows registry key observable
12. **NETWORK_TRAFFIC**: Network traffic observable
13. **EMAIL_MESSAGE**: Email message observable
14. **USER_ACCOUNT**: User account observable
15. **SOFTWARE**: Software application
16. **REPORT**: Document collection of threat intelligence
17. **THREAT_ACTOR**: Individual/group responsible for attacks
18. **TTP**: Tactics, Techniques, and Procedures

---STIX2.0 Relationship Types---
1. **CONTAINS**: A contains B (e.g., report contains indicator)
2. **RELATED_TO**: A is related to B
3. **ATTRIBUTED_TO**: A is attributed to B (e.g., attack attributed to threat actor)
4. **EXPLOITS**: A exploits B (e.g., malware exploits vulnerability)
5. **INDICATES**: A indicates B (e.g., indicator indicates malware)
6. **IMPLEMENTS**: A implements B (e.g., attack pattern implements TTP)
7. **LAUNCHES**: A launches B (e.g., campaign launches attack)
8. **TARGETS**: A targets B (e.g., threat actor targets organization)

---Instructions---
1. **Entity Extraction:** Identify clearly defined and meaningful entities in the input text, and extract the following information:
   - entity_name: Name of the entity, ensure entity names are consistent throughout the extraction.
   - entity_type: **CRITICAL** - Categorize the entity using the EXACT STIX2.0 entity types listed above. Use the exact type names (e.g., "malware", "threat-actor", "attack-pattern", "indicator", "vulnerability", "file", "process", "network-traffic", "email-message", "user-account", "software", "report", "campaign", "intrusion-set", "course-of-action", "directory", "registry-key", "ttp"). If none of the provided types are suitable, classify it as "other".
   - entity_description: Provide a comprehensive description of the entity's attributes and activities based on the information present in the input text.
   - entity_properties: Extract additional STIX2.0 properties relevant to the entity type, such as:
     * For MALWARE: malware_types, execution_platforms, capabilities
     * For THREAT_ACTOR: aliases, threat_actor_types, roles, goals
     * For ATTACK_PATTERN: kill_chain_phases, required_permissions
     * For INDICATOR: pattern_type, pattern_value, valid_from
     * For VULNERABILITY: CVE_id, CVSS_score, severity
     * For SOFTWARE: cpe, version, vendor
     * For FILE: hashes, size, extensions
     * For NETWORK_TRAFFIC: protocols, src_ref, dst_ref, src_port, dst_port
     * For REPORT: published, report_types
2. **Entity Output Format:** (entity{tuple_delimiter}entity_name{tuple_delimiter}entity_type{tuple_delimiter}entity_description{tuple_delimiter}entity_properties)
   **Note:** Each entity will automatically be assigned a STIX2.0 compliant ID (type--uuid), type, name, and description as standard properties.
3. **Relationship Extraction:** Identify direct, clearly-stated and meaningful relationships between extracted entities within the input text, and extract the following information:
   - source_entity: name of the source entity.
   - target_entity: name of the target entity.
   - relationship_type: Use one of the STIX2.0 relationship types listed above.
   - relationship_description: Explain the nature of the relationship between the source and target entities, providing a clear rationale for their connection.
   - relationship_properties: Extract additional properties relevant to the relationship type, such as:
     * For EXPLOITS: start_time, end_time, confidence
     * For ATTRIBUTED_TO: confidence, methodology
     * For INDICATES: confidence, pattern_version
     * For TARGETS: targeting_method, impact
4. **Relationship Output Format:** (relationship{tuple_delimiter}source_entity{tuple_delimiter}target_entity{tuple_delimiter}relationship_type{tuple_delimiter}relationship_description{tuple_delimiter}relationship_properties)
5. **Relationship Order:** Prioritize relationships based on their significance to the intended meaning of input text, and output more crucial relationships first.
6. **Avoid Pronouns:** For entity names and all descriptions, explicitly name the subject or object instead of using pronouns; avoid pronouns such as `this document`, `our company`, `I`, `you`, and `he/she`.
7. **Undirectional Relationship:** Treat relationships as undirected; swapping the source and target entities does not constitute a new relationship. Avoid outputting duplicate relationships.
8. **Language:** Output entity names, keywords and descriptions in {language}.
9. **Delimiter:** Use `{record_delimiter}` as the entity or relationship list delimiter; output `{completion_delimiter}` when all the entities and relationships are extracted.

---STIX2.0 Compliance Requirements---
1. **Entity Identification**: Each entity must be assigned a unique identifier following the pattern: [type]--[UUID] (e.g., malware--d81fce06-5664-48e4-a98a-c5aa9e4a4159)
2. **Property Validation**: Only include properties that are valid for the specific entity type according to STIX2.0 specification.
3. **Relationship Validation**: Ensure relationships are valid between the source and target entity types according to STIX2.0 specification.
4. **Timestamps**: Include creation and modification timestamps in ISO 8601 format when available.
5. **Confidence Scoring**: Assign confidence scores (0-100) to extracted entities and relationships when possible.

---Examples---
{examples}

---Real Data to be Processed---
<Input>
Entity_types: [{entity_types}]
Text:
```
{input_text}
```
"""

PROMPTS["entity_extraction_user_prompt"] = """---Task---
Extract STIX2.0 compliant entities and relationships from the input text to be Processed.

---STIX2.0 Output Requirements---
1. Output entities and relationships in STIX2.0 compliant format, prioritized by their relevance to the input text's core meaning.
2. Each entity must include:
   - entity_name: Clear, consistent name
   - entity_type: One of the STIX2.0 entity types
   - entity_description: Comprehensive description
   - entity_properties: Additional STIX2.0 properties relevant to the entity type
3. Each relationship must include:
   - source_entity: Name of the source entity
   - target_entity: Name of the target entity
   - relationship_type: One of the STIX2.0 relationship types
   - relationship_description: Clear explanation of the relationship
   - relationship_properties: Additional STIX2.0 properties relevant to the relationship type
4. Assign unique identifiers to each entity following the pattern: [type]--[UUID]
5. Assign confidence scores (0-100) to extracted entities and relationships when possible.
6. Include timestamps in ISO 8601 format when available.
7. Output `{completion_delimiter}` when all the entities and relationships are extracted.
8. Ensure the output language is {language}.

<Output>
"""

PROMPTS["entity_continue_extraction_user_prompt"] = """---Task---
Identify any missed STIX2.0 compliant entities or relationships from the input text to be Processed of last extraction task.

---STIX2.0 Continuation Requirements---
1. Output the entities and relationships in the same STIX2.0 compliant format as previous extraction task.
2. Each entity must include:
   - entity_name: Clear, consistent name
   - entity_type: One of the STIX2.0 entity types
   - entity_description: Comprehensive description
   - entity_properties: Additional STIX2.0 properties relevant to the entity type
3. Each relationship must include:
   - source_entity: Name of the source entity
   - target_entity: Name of the target entity
   - relationship_type: One of the STIX2.0 relationship types
   - relationship_description: Clear explanation of the relationship
   - relationship_properties: Additional STIX2.0 properties relevant to the relationship type
4. Do not include entities and relations that have been correctly extracted in last extraction task.
5. If the entity or relation output is truncated or has missing fields in last extraction task, please re-output it in the correct STIX2.0 format.
6. Assign unique identifiers to each entity following the pattern: [type]--[UUID]
7. Assign confidence scores (0-100) to extracted entities and relationships when possible.
8. Include timestamps in ISO 8601 format when available.
9. Output `{completion_delimiter}` when all the entities and relationships are extracted.
10. Ensure the output language is {language}.

<Output>
"""

PROMPTS["entity_extraction_examples"] = [
    """<Input Text>
```
The APT29 group, also known as Cozy Bear, has been conducting a sophisticated cyber espionage campaign targeting government agencies and research institutions worldwide. According to a recent report by Cyber Threat Intelligence Center, the threat actor has been utilizing a custom malware variant named "WellMess" to compromise systems. This malware exploits CVE-2020-1472, a critical vulnerability in Microsoft Windows Netlogon Remote Protocol with a CVSS score of 10.0. The attack pattern involves spear-phishing emails containing malicious attachments that, when opened, establish a reverse shell connection to command and control servers located in Eastern Europe. Security researchers have identified indicators such as the domain "malicious-update[.]com" and the file hash "a1b2c3d4e5f67890" associated with this campaign. The threat actor's primary goal appears to be intelligence gathering related to COVID-19 vaccine research.
```

<Output>
(entity{tuple_delimiter}APT29{tuple_delimiter}THREAT_ACTOR{tuple_delimiter}APT29 is a sophisticated threat actor group also known as Cozy Bear, specializing in cyber espionage operations against government agencies and research institutions worldwide. The group has been active in conducting intelligence gathering campaigns, particularly targeting COVID-19 vaccine research data.{tuple_delimiter}{{"aliases": ["Cozy Bear"], "threat_actor_types": ["nation-state"], "roles": ["actor"], "goals": ["intelligence gathering"], "first_seen": "2015-01-01T00:00:00Z", "last_seen": "2023-12-31T23:59:59Z"}}){record_delimiter}
(entity{tuple_delimiter}WellMess{tuple_delimiter}MALWARE{tuple_delimiter}WellMess is a custom malware variant utilized by APT29 in their cyber espionage campaigns. It is designed to establish persistent access to compromised systems and facilitate data exfiltration. The malware is typically delivered through spear-phishing emails containing malicious attachments.{tuple_delimiter}{{"malware_types": ["trojan", "backdoor"], "execution_platforms": ["Windows"], "capabilities": ["persistence", "data exfiltration", "remote access"], "first_seen": "2020-01-01T00:00:00Z", "is_family": false}}){record_delimiter}
(entity{tuple_delimiter}CVE-2020-1472{tuple_delimiter}VULNERABILITY{tuple_delimiter}CVE-2020-1472 is a critical vulnerability in Microsoft Windows Netlogon Remote Protocol that allows attackers to authenticate as a domain controller and potentially gain domain administrator privileges. It has a CVSS score of 10.0, indicating maximum severity.{tuple_delimiter}{{"CVE_id": "CVE-2020-1472", "CVSS_score": 10.0, "severity": "critical", "affected_products": ["Windows Server 2008 R2", "Windows Server 2012", "Windows Server 2012 R2", "Windows Server 2016", "Windows Server 2019"], "published": "2020-08-11T00:00:00Z"}}){record_delimiter}
(entity{tuple_delimiter}Spear-phishing with malicious attachments{tuple_delimiter}ATTACK_PATTERN{tuple_delimiter}This attack pattern involves sending targeted emails with malicious attachments to specific individuals or organizations. When recipients open the attachments, malware is executed, establishing unauthorized access to their systems. This technique is commonly used in initial access phases of cyber attacks.{tuple_delimiter}{{"kill_chain_phases": ["initial-access"], "required_permissions": ["user"], "execution_platforms": ["Windows", "macOS", "Linux"], "technique_id": "T1566.001", "technique_name": "Spearphishing Attachment"}}){record_delimiter}
(entity{tuple_delimiter}malicious-update[.]com{tuple_delimiter}INDICATOR{tuple_delimiter}The domain 'malicious-update[.]com' is a known command and control server associated with APT29's WellMess malware campaign. It serves as a communication endpoint for compromised systems to establish reverse shell connections and receive instructions from attackers.{tuple_delimiter}{{"pattern_type": "domain", "pattern_value": "malicious-update[.]com", "valid_from": "2020-01-01T00:00:00Z", "confidence": 85}}){record_delimiter}
(entity{tuple_delimiter}a1b2c3d4e5f67890{tuple_delimiter}FILE{tuple_delimiter}This file hash corresponds to a malicious executable file used in APT29's spear-phishing campaigns. The file is typically delivered as an attachment in phishing emails and, when executed, installs the WellMess malware on the victim's system.{tuple_delimiter}{{"hashes": {"MD5": "a1b2c3d4e5f67890"}, "extensions": [".exe"], "size": 102400, "mime_type": "application/x-dosexec"}}){record_delimiter}
(entity{tuple_delimiter}COVID-19 vaccine research{tuple_delimiter}REPORT{tuple_delimiter}This report contains intelligence about APT29's targeting of COVID-19 vaccine research data. It details the threat actor's tactics, techniques, and procedures, as well as indicators of compromise associated with their campaign.{tuple_delimiter}{{"published": "2020-07-16T00:00:00Z", "report_types": ["threat-report"], "object_refs": ["APT29", "WellMess", "CVE-2020-1472"]}}){record_delimiter}
(relationship{tuple_delimiter}APT29{tuple_delimiter}WellMess{tuple_delimiter}USES{tuple_delimiter}APT29 utilizes the WellMess malware in their cyber espionage operations to establish persistent access to compromised systems and facilitate data exfiltration.{tuple_delimiter}{{"confidence": 90, "start_time": "2020-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}WellMess{tuple_delimiter}CVE-2020-1472{tuple_delimiter}EXPLOITS{tuple_delimiter}The WellMess malware exploits the CVE-2020-1472 vulnerability in Microsoft Windows Netlogon Remote Protocol to gain elevated privileges on compromised systems.{tuple_delimiter}{{"confidence": 95, "start_time": "2020-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}APT29{tuple_delimiter}Spear-phishing with malicious attachments{tuple_delimiter}USES{tuple_delimiter}APT29 employs spear-phishing emails with malicious attachments as an initial attack vector to deliver their WellMess malware to target systems.{tuple_delimiter}{{"confidence": 85, "start_time": "2020-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}malicious-update[.]com{tuple_delimiter}WellMess{tuple_delimiter}INDICATES{tuple_delimiter}The domain 'malicious-update[.]com' serves as a command and control server for the WellMess malware, indicating its presence and activity in compromised networks.{tuple_delimiter}{{"confidence": 85, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}a1b2c3d4e5f67890{tuple_delimiter}WellMess{tuple_delimiter}INDICATES{tuple_delimiter}The file hash 'a1b2c3d4e5f67890' is associated with the WellMess malware executable, indicating its presence on a system when detected.{tuple_delimiter}{{"confidence": 90, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}APT29{tuple_delimiter}COVID-19 vaccine research{tuple_delimiter}TARGETS{tuple_delimiter}APT29 specifically targets COVID-19 vaccine research data and institutions as part of their intelligence gathering operations.{tuple_delimiter}{{"confidence": 80, "targeting_method": "cyber espionage", "impact": "data theft"}}){record_delimiter}
{completion_delimiter}

""",
    """<Input Text>
```
In a recent cybersecurity incident, the Lazarus Group, a North Korean state-sponsored threat actor, deployed a new ransomware variant named "VHD" in attacks targeting financial institutions across Asia and Europe. The ransomware exploits CVE-2021-44228, a critical vulnerability in Apache Log4j with a CVSS score of 10.0, to gain initial access to target systems. Once inside the network, the malware propagates laterally using the EternalBlue exploit (CVE-2017-0144) and establishes persistence through registry modifications. Security researchers have identified several indicators of compromise, including the IP address 192.168.1.100, the domain "update-service[.]xyz", and the file hash "e5f6a7b8c9d01234" for the ransomware executable. The attackers demand a ransom of 10 Bitcoin for decryption keys and threaten to leak stolen data if payment is not made within 72 hours.
```

<Output>
(entity{tuple_delimiter}Lazarus Group{tuple_delimiter}THREAT_ACTOR{tuple_delimiter}The Lazarus Group is a North Korean state-sponsored threat actor known for conducting financially motivated cyber attacks, including ransomware campaigns, bank heists, and cryptocurrency theft. The group has been active since at least 2009 and has targeted various sectors worldwide.{tuple_delimiter}{{"aliases": ["Hidden Cobra", "APT38"], "threat_actor_types": ["nation-state", "criminal"], "roles": ["actor"], "goals": ["financial gain", "data theft"], "first_seen": "2009-01-01T00:00:00Z", "last_seen": "2023-12-31T23:59:59Z"}}){record_delimiter}
(entity{tuple_delimiter}VHD{tuple_delimiter}MALWARE{tuple_delimiter}VHD is a ransomware variant deployed by the Lazarus Group in attacks against financial institutions. It encrypts files on compromised systems and demands ransom payments in Bitcoin for decryption keys. The malware also includes data theft capabilities and threatens to leak stolen information if ransom is not paid.{tuple_delimiter}{{"malware_types": ["ransomware", "trojan"], "execution_platforms": ["Windows"], "capabilities": ["file encryption", "data exfiltration", "lateral movement"], "first_seen": "2022-01-01T00:00:00Z", "is_family": false}}){record_delimiter}
(entity{tuple_delimiter}CVE-2021-44228{tuple_delimiter}VULNERABILITY{tuple_delimiter}CVE-2021-44228, also known as Log4Shell, is a critical vulnerability in Apache Log4j that allows for unauthenticated remote code execution. It has a CVSS score of 10.0, indicating maximum severity, and affects numerous Java-based applications and services.{tuple_delimiter}{{"CVE_id": "CVE-2021-44228", "CVSS_score": 10.0, "severity": "critical", "affected_products": ["Apache Log4j 2.0-beta9 through 2.14.1"], "published": "2021-12-10T00:00:00Z"}}){record_delimiter}
(entity{tuple_delimiter}CVE-2017-0144{tuple_delimiter}VULNERABILITY{tuple_delimiter}CVE-2017-0144, also known as EternalBlue, is a critical vulnerability in Microsoft Server Message Block 1.0 (SMBv1) that allows remote code execution. It was leaked by the Shadow Brokers hacking group and has been widely exploited in ransomware campaigns.{tuple_delimiter}{{"CVE_id": "CVE-2017-0144", "CVSS_score": 8.5, "severity": "high", "affected_products": ["Windows Vista", "Windows Server 2008", "Windows 7", "Windows Server 2008 R2"], "published": "2017-03-14T00:00:00Z"}}){record_delimiter}
(entity{tuple_delimiter}192.168.1.100{tuple_delimiter}INDICATOR{tuple_delimiter}The IP address 192.168.1.100 is associated with command and control infrastructure used by the Lazarus Group in their VHD ransomware campaign. It serves as a communication endpoint for compromised systems to connect to and receive instructions from attackers.{tuple_delimiter}{{"pattern_type": "ipv4-addr", "pattern_value": "192.168.1.100", "valid_from": "2022-01-01T00:00:00Z", "confidence": 75}}){record_delimiter}
(entity{tuple_delimiter}update-service[.]xyz{tuple_delimiter}INDICATOR{tuple_delimiter}The domain 'update-service[.]xyz' is a known command and control server associated with the Lazarus Group's VHD ransomware campaign. It is used to deliver additional payloads and exfiltrate stolen data from compromised systems.{tuple_delimiter}{{"pattern_type": "domain", "pattern_value": "update-service[.]xyz", "valid_from": "2022-01-01T00:00:00Z", "confidence": 80}}){record_delimiter}
(entity{tuple_delimiter}e5f6a7b8c9d01234{tuple_delimiter}FILE{tuple_delimiter}This file hash corresponds to the VHD ransomware executable used by the Lazarus Group. The file is typically delivered after initial compromise and is responsible for encrypting files on the victim's system and demanding ransom payments.{tuple_delimiter}{{"hashes": {"MD5": "e5f6a7b8c9d01234"}, "extensions": [".exe"], "size": 204800, "mime_type": "application/x-dosexec"}}){record_delimiter}
(relationship{tuple_delimiter}Lazarus Group{tuple_delimiter}VHD{tuple_delimiter}USES{tuple_delimiter}The Lazarus Group utilizes the VHD ransomware in their financially motivated attacks against financial institutions to encrypt files and demand ransom payments.{tuple_delimiter}{{"confidence": 90, "start_time": "2022-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}VHD{tuple_delimiter}CVE-2021-44228{tuple_delimiter}EXPLOITS{tuple_delimiter}The VHD ransomware exploits the CVE-2021-44228 vulnerability (Log4Shell) to gain initial access to target systems before deploying its encryption capabilities.{tuple_delimiter}{{"confidence": 95, "start_time": "2022-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}VHD{tuple_delimiter}CVE-2017-0144{tuple_delimiter}EXPLOITS{tuple_delimiter}After initial compromise, the VHD ransomware exploits the CVE-2017-0144 vulnerability (EternalBlue) to propagate laterally across the target network and infect additional systems.{tuple_delimiter}{{"confidence": 85, "start_time": "2022-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}192.168.1.100{tuple_delimiter}VHD{tuple_delimiter}INDICATES{tuple_delimiter}The IP address 192.168.1.100 serves as a command and control server for the VHD ransomware, indicating its presence and activity in compromised networks.{tuple_delimiter}{{"confidence": 75, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}update-service[.]xyz{tuple_delimiter}VHD{tuple_delimiter}INDICATES{tuple_delimiter}The domain 'update-service[.]xyz' is associated with the VHD ransomware campaign, serving as a command and control server for data exfiltration and payload delivery.{tuple_delimiter}{{"confidence": 80, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}e5f6a7b8c9d01234{tuple_delimiter}VHD{tuple_delimiter}INDICATES{tuple_delimiter}The file hash 'e5f6a7b8c9d01234' corresponds to the VHD ransomware executable, indicating its presence on a system when detected.{tuple_delimiter}{{"confidence": 90, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}Lazarus Group{tuple_delimiter}Financial institutions{tuple_delimiter}TARGETS{tuple_delimiter}The Lazarus Group specifically targets financial institutions across Asia and Europe with their VHD ransomware campaign to achieve financial gain through ransom payments.{tuple_delimiter}{{"confidence": 85, "targeting_method": "ransomware", "impact": "financial loss"}}){record_delimiter}
{completion_delimiter}

""",
    """<Input Text>
```
A new advanced persistent threat (APT) group named "DarkShadow" has been discovered targeting critical infrastructure in the energy sector. The group employs a sophisticated multi-stage attack chain that begins with watering hole attacks on industry-specific websites. Visitors to these compromised sites are infected with a custom backdoor named "ShadowNet" through a drive-by download exploiting CVE-2022-2294, a use-after-free vulnerability in WebRTC. Once installed, ShadowNet establishes persistence by creating a scheduled task and modifying Windows registry keys. The malware then performs reconnaissance on the network, mapping out critical systems and identifying high-value targets. DarkShadow operators use this information to deploy a custom industrial control system (ICS) malware named "BlackOut" specifically designed to disrupt power grid operations. Security researchers have identified several indicators of compromise, including the domain "shadow-c2[.]net", the IP address 45.67.89.123, and the file hash "f0e9d8c7b6a54321" for the ShadowNet backdoor.
```

<Output>
(entity{tuple_delimiter}DarkShadow{tuple_delimiter}INTRUSION_SET{tuple_delimiter}DarkShadow is a sophisticated APT group specializing in attacks against critical infrastructure, particularly in the energy sector. The group employs advanced multi-stage attack chains and custom-developed malware to compromise target networks and disrupt industrial control systems.{tuple_delimiter}{{"aliases": [], "first_seen": "2022-01-01T00:00:00Z", "last_seen": "2023-12-31T23:59:59Z", "goals": ["disruption", "espionage"], "resource_level": "high"}}){record_delimiter}
(entity{tuple_delimiter}ShadowNet{tuple_delimiter}MALWARE{tuple_delimiter}ShadowNet is a custom backdoor developed by DarkShadow for initial compromise and persistence in target networks. It is delivered through watering hole attacks and drive-by downloads, establishing a foothold for further exploitation and deployment of additional payloads.{tuple_delimiter}{{"malware_types": ["backdoor", "trojan"], "execution_platforms": ["Windows"], "capabilities": ["persistence", "reconnaissance", "data exfiltration"], "first_seen": "2022-01-01T00:00:00Z", "is_family": false}}){record_delimiter}
(entity{tuple_delimiter}BlackOut{tuple_delimiter}MALWARE{tuple_delimiter}BlackOut is a custom industrial control system (ICS) malware developed by DarkShadow specifically designed to disrupt power grid operations. It is deployed after initial reconnaissance and is capable of manipulating industrial control systems to cause physical disruption to energy infrastructure.{tuple_delimiter}{{"malware_types": ["ics-malware", "trojan"], "execution_platforms": ["Windows", "ICS"], "capabilities": ["ics-disruption", "persistence", "lateral movement"], "first_seen": "2022-01-01T00:00:00Z", "is_family": false}}){record_delimiter}
(entity{tuple_delimiter}CVE-2022-2294{tuple_delimiter}VULNERABILITY{tuple_delimiter}CVE-2022-2294 is a use-after-free vulnerability in WebRTC that can be exploited for remote code execution through a maliciously crafted web page. It affects multiple web browsers and has been used in watering hole attacks to deliver malware to visitors of compromised websites.{tuple_delimiter}{{"CVE_id": "CVE-2022-2294", "CVSS_score": 8.8, "severity": "high", "affected_products": ["Google Chrome", "Mozilla Firefox", "Microsoft Edge"], "published": "2022-07-06T00:00:00Z"}}){record_delimiter}
(entity{tuple_delimiter}Watering hole attacks on industry websites{tuple_delimiter}ATTACK_PATTERN{tuple_delimiter}This attack pattern involves compromising legitimate websites frequently visited by individuals in a specific industry or organization. Attackers then exploit vulnerabilities in visitors' browsers or plugins to deliver malware, taking advantage of the trust users have in these websites.{tuple_delimiter}{{"kill_chain_phases": ["initial-access"], "required_permissions": ["none"], "execution_platforms": ["Windows", "macOS", "Linux"], "technique_id": "T1193", "technique_name": "Watering Hole Attack"}}){record_delimiter}
(entity{tuple_delimiter}shadow-c2[.]net{tuple_delimiter}INDICATOR{tuple_delimiter}The domain 'shadow-c2[.]net' is a command and control server used by DarkShadow in their ShadowNet backdoor operations. It serves as a communication endpoint for compromised systems to connect to and receive instructions from attackers.{tuple_delimiter}{{"pattern_type": "domain", "pattern_value": "shadow-c2[.]net", "valid_from": "2022-01-01T00:00:00Z", "confidence": 85}}){record_delimiter}
(entity{tuple_delimiter}45.67.89.123{tuple_delimiter}INDICATOR{tuple_delimiter}The IP address 45.67.89.123 is associated with DarkShadow's command and control infrastructure. It is used to host the ShadowNet backdoor and communicate with compromised systems in the energy sector.{tuple_delimiter}{{"pattern_type": "ipv4-addr", "pattern_value": "45.67.89.123", "valid_from": "2022-01-01T00:00:00Z", "confidence": 80}}){record_delimiter}
(entity{tuple_delimiter}f0e9d8c7b6a54321{tuple_delimiter}FILE{tuple_delimiter}This file hash corresponds to the ShadowNet backdoor executable used by DarkShadow in their watering hole attacks. The file is delivered through drive-by downloads exploiting CVE-2022-2294 and establishes persistence on compromised systems.{tuple_delimiter}{{"hashes": {"MD5": "f0e9d8c7b6a54321"}, "extensions": [".exe"], "size": 153600, "mime_type": "application/x-dosexec"}}){record_delimiter}
(relationship{tuple_delimiter}DarkShadow{tuple_delimiter}ShadowNet{tuple_delimiter}USES{tuple_delimiter}DarkShadow utilizes the ShadowNet backdoor as their initial access tool in attacks against energy sector targets, establishing persistence and performing reconnaissance.{tuple_delimiter}{{"confidence": 90, "start_time": "2022-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}DarkShadow{tuple_delimiter}BlackOut{tuple_delimiter}USES{tuple_delimiter}DarkShadow deploys the BlackOut ICS malware after initial compromise to specifically target and disrupt power grid operations in the energy sector.{tuple_delimiter}{{"confidence": 90, "start_time": "2022-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}ShadowNet{tuple_delimiter}CVE-2022-2294{tuple_delimiter}EXPLOITS{tuple_delimiter}The ShadowNet backdoor exploits the CVE-2022-2294 vulnerability in WebRTC to achieve initial compromise through drive-by downloads on compromised websites.{tuple_delimiter}{{"confidence": 95, "start_time": "2022-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}DarkShadow{tuple_delimiter}Watering hole attacks on industry websites{tuple_delimiter}USES{tuple_delimiter}DarkShadow employs watering hole attacks on industry-specific websites as their initial attack vector to compromise visitors from the energy sector.{tuple_delimiter}{{"confidence": 85, "start_time": "2022-01-01T00:00:00Z"}}){record_delimiter}
(relationship{tuple_delimiter}shadow-c2[.]net{tuple_delimiter}ShadowNet{tuple_delimiter}INDICATES{tuple_delimiter}The domain 'shadow-c2[.]net' serves as a command and control server for the ShadowNet backdoor, indicating DarkShadow's presence and activity in compromised networks.{tuple_delimiter}{{"confidence": 85, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}45.67.89.123{tuple_delimiter}ShadowNet{tuple_delimiter}INDICATES{tuple_delimiter}The IP address 45.67.89.123 is associated with DarkShadow's command and control infrastructure for the ShadowNet backdoor, indicating its presence in compromised networks.{tuple_delimiter}{{"confidence": 80, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}f0e9d8c7b6a54321{tuple_delimiter}ShadowNet{tuple_delimiter}INDICATES{tuple_delimiter}The file hash 'f0e9d8c7b6a54321' corresponds to the ShadowNet backdoor executable, indicating DarkShadow's presence on a system when detected.{tuple_delimiter}{{"confidence": 90, "pattern_version": "1.0"}}){record_delimiter}
(relationship{tuple_delimiter}DarkShadow{tuple_delimiter}Energy sector critical infrastructure{tuple_delimiter}TARGETS{tuple_delimiter}DarkShadow specifically targets critical infrastructure in the energy sector, particularly power grid operations, with their multi-stage attack chain.{tuple_delimiter}{{"confidence": 85, "targeting_method": "watering hole", "impact": "operational disruption"}}){record_delimiter}
{completion_delimiter}

""",
]

PROMPTS["summarize_entity_descriptions"] = """---Role---
You are a Knowledge Graph Specialist responsible for data curation and synthesis.

---Task---
Your task is to synthesize a list of descriptions of a given entity or relation into a single, comprehensive, and cohesive summary.

---Instructions---
1. **Comprehensiveness:** The summary must integrate key information from all provided descriptions. Do not omit important facts.
2. **Context:** The summary must explicitly mention the name of the entity or relation for full context.
3. **Conflict:** In case of conflicting or inconsistent descriptions, determine if they originate from multiple, distinct entities or relationships that share the same name. If so, summarize each entity or relationship separately and then consolidate all summaries.
4. **Style:** The output must be written from an objective, third-person perspective.
5. **Length:** Maintain depth and completeness while ensuring the summary's length not exceed {summary_length} tokens.
6. **Language:** The entire output must be written in {language}.

---Data---
{description_type} Name: {description_name}
Description List:
{description_list}

---Output---
"""

PROMPTS["fail_response"] = (
    "Sorry, I'm not able to provide an answer to that question.[no-context]"
)

PROMPTS["rag_response"] = """---Role---

You are a helpful assistant responding to user query about Knowledge Graph and Document Chunks provided in JSON format below.


---Goal---

Generate a concise response based on Knowledge Base and follow Response Rules, considering both current query and the conversation history if provided. Summarize all information in the provided Knowledge Base, and incorporating general knowledge relevant to the Knowledge Base. Do not include information not provided by Knowledge Base.

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Guidelines---
**1. Content & Adherence:**
- Strictly adhere to the provided context from the Knowledge Base. Do not invent, assume, or include any information not present in the source data.
- If the answer cannot be found in the provided context, state that you do not have enough information to answer.
- Ensure the response maintains continuity with the conversation history.

**2. Formatting & Language:**
- Format the response using markdown with appropriate section headings.
- The response language must in the same language as the user's question.
- Target format and length: {response_type}

**3. Citations / References:**
- At the end of the response, under a "References" section, each citation must clearly indicate its origin (KG or DC).
- The maximum number of citations is 5, including both KG and DC.
- Use the following formats for citations:
  - For a Knowledge Graph Entity: `[KG] <entity_name>`
  - For a Knowledge Graph Relationship: `[KG] <entity1_name> - <entity2_name>`
  - For a Document Chunk: `[DC] <file_path_or_document_name>`

---USER CONTEXT---
- Additional user prompt: {user_prompt}

---Response---
"""

PROMPTS["keywords_extraction"] = """---Role---
You are an expert keyword extractor, specializing in analyzing user queries for a Retrieval-Augmented Generation (RAG) system. Your purpose is to identify both high-level and low-level keywords in the user's query that will be used for effective document retrieval.

---Goal---
Given a user query, your task is to extract two distinct types of keywords:
1. **high_level_keywords**: for overarching concepts or themes, capturing user's core intent, the subject area, or the type of question being asked.
2. **low_level_keywords**: for specific entities or details, identifying the specific entities, proper nouns, technical jargon, product names, or concrete items.

---Instructions & Constraints---
1. **Output Format**: Your output MUST be a valid JSON object and nothing else. Do not include any explanatory text, markdown code fences (like ```json), or any other text before or after the JSON. It will be parsed directly by a JSON parser.
2. **Source of Truth**: All keywords must be explicitly derived from the user query, with both high-level and low-level keyword categories required to contain content.
3. **Concise & Meaningful**: Keywords should be concise words or meaningful phrases. Prioritize multi-word phrases when they represent a single concept. For example, from "latest financial report of Apple Inc.", you should extract "latest financial report" and "Apple Inc." rather than "latest", "financial", "report", and "Apple".
4. **Handle Edge Cases**: For queries that are too simple, vague, or nonsensical (e.g., "hello", "ok", "asdfghjkl"), you must return a JSON object with empty lists for both keyword types.

---Examples---
{examples}

---Real Data---
User Query: {query}

---Output---
Output:"""

PROMPTS["keywords_extraction_examples"] = [
    """Example 1:

Query: "How does international trade influence global economic stability?"

Output:
{
  "high_level_keywords": ["International trade", "Global economic stability", "Economic impact"],
  "low_level_keywords": ["Trade agreements", "Tariffs", "Currency exchange", "Imports", "Exports"]
}

""",
    """Example 2:

Query: "What are the environmental consequences of deforestation on biodiversity?"

Output:
{
  "high_level_keywords": ["Environmental consequences", "Deforestation", "Biodiversity loss"],
  "low_level_keywords": ["Species extinction", "Habitat destruction", "Carbon emissions", "Rainforest", "Ecosystem"]
}

""",
    """Example 3:

Query: "What is the role of education in reducing poverty?"

Output:
{
  "high_level_keywords": ["Education", "Poverty reduction", "Socioeconomic development"],
  "low_level_keywords": ["School access", "Literacy rates", "Job training", "Income inequality"]
}

""",
]

PROMPTS["naive_rag_response"] = """---Role---

You are a helpful assistant responding to user query about Document Chunks provided provided in JSON format below.

---Goal---

Generate a concise response based on Document Chunks and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Document Chunks, and incorporating general knowledge relevant to the Document Chunks. Do not include information not provided by Document Chunks.

---Conversation History---
{history}

---Document Chunks(DC)---
{content_data}

---RESPONSE GUIDELINES---
**1. Content & Adherence:**
- Strictly adhere to the provided context from the Knowledge Base. Do not invent, assume, or include any information not present in the source data.
- If the answer cannot be found in the provided context, state that you do not have enough information to answer.
- Ensure the response maintains continuity with the conversation history.

**2. Formatting & Language:**
- Format the response using markdown with appropriate section headings.
- The response language must match the user's question language.
- Target format and length: {response_type}

**3. Citations / References:**
- At the end of the response, under a "References" section, cite a maximum of 5 most relevant sources used.
- Use the following formats for citations: `[DC] <file_path_or_document_name>`

---USER CONTEXT---
- Additional user prompt: {user_prompt}

---Response---
Output:"""
