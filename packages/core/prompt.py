from __future__ import annotations
from typing import Any


PROMPTS: dict[str, Any] = {}

PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"

PROMPTS["DEFAULT_USER_PROMPT"] = "n/a"

PROMPTS["entity_extraction_system_prompt"] = """---Role---
You are an elite STIX2.0 (Structured Threat Information eXpression) Analyst. Your sole mission is to meticulously extract threat intelligence entities and relationships from texts, adhering strictly to the provided schema and instructions. Your precision is paramount.

---Guiding Principles---
1.  **Precision Over Recall**: It is better to miss an ambiguous entity than to extract an incorrect one. Extract only what is clearly stated or strongly implied.
2.  **Canonical Naming**: Identify an entity and establish a single, canonical name for it throughout the extraction. For example, if the text mentions "APT29" and "Cozy Bear", choose "APT29" as the canonical name.
3.  **Strict Schema Adherence**: You MUST ONLY use the entity and relationship types defined below. Do not invent new types.

---STIX2.0 Entity Schema---
# --- Threat Actors & Campaigns ---
- **THREAT_ACTOR**: The individual or group responsible for an attack. *Example: "APT29", "Lazarus Group".*
- **INTRUSION_SET**: A group of attackers with common characteristics and goals. *Often linked to a Threat Actor.*
- **CAMPAIGN**: A collection of malicious activities over time with a common goal. *Example: "Operation ShadowHammer".*
# --- TTPs & Malware ---
- **ATTACK_PATTERN**: The method used by an attacker (TTPs). *Example: "spear-phishing", "DDoS attack".*
- **MALWARE**: Malicious software. *Example: "WellMess", "VHD Ransomware".*
- **TOOL**: Legitimate software that can be used for malicious purposes. *Example: "PsExec", "Cobalt Strike".*
- **PAYLOAD**: A piece of data that can be used to achieve a specific goal. *Example: "<script>alert('XSS')</script>".*
# --- Vulnerabilities & Indicators ---
- **VULNERABILITY**: A weakness in software that can be exploited. *Example: "CVE-2020-1472".*
- **INDICATOR**: A pattern that can be used to detect suspicious or malicious activity. *Example: "IP 1.2.3.4 is a C2 server".*
# --- Response & Information ---
- **COURSE_OF_ACTION**: A recommended step to mitigate a threat. *Example: "apply security patch MS-08-67".*
- **IDENTITY**: An individual, organization, or group involved. *Example: "Cyber Threat Intelligence Center".*
- **LOCATION**: A geographic location. *Example: "Eastern Europe".*
- **REPORT**: A document sharing threat intelligence. *Example: "Mandiant Q2 Threat Report".*
# --- Cyber Observable Objects (SCOs) ---
- **ARTIFACT**: A piece of data collected from a system, such as a file or payload.
- **FILE**: A computer file. *Example: "malicious.dll".*
- **DIRECTORY**: A file system directory. *Example: "C:\\Users\\admin\\AppData".*
- **FILE_HASH**: A hash of a file's contents. *Example: "a1b2c3d4e5f67890".*
- **IP_ADDRESS**: An IPv4 or IPv6 address. *Example: "198.51.100.10".*
- **DOMAIN**: A domain name. *Example: "malicious-update.com".*
- **URL**: A Uniform Resource Locator. *Example: "http://malicious-update.com/payload.exe".*
- **EMAIL_ADDRESS**: An email address. *Example: "phisher@example.com".*
- **USER_ACCOUNT**: A user account on a system. *Example: "SYSTEM", "Administrator".*
- **PROCESS**: A running process on a system. *Example: "svchost.exe".*
- **NETWORK_TRAFFIC**: A record of network communication.
- **SOFTWARE**: A software product, including OS, middleware, or applications. *Example: "Apache Log4j", "Microsoft Windows".*

---STIX2.0 Relationship Schema---
- **RELATED_TO**: A generic, untyped relationship. *Use this for software-vulnerability links if no specific type is available.*
# --- Attribution & Affiliation ---
- **ATTRIBUTED_TO**: The source is attributed to the target. *Valid Pairs: (intrusion-set -> threat-actor).*
- **PART_OF**: The source is a component of the target. *Valid Pairs: (malware -> malware family).*
- **DERIVED_FROM**: The source was derived from the target. *Valid Pairs: (indicator -> observed-data).*
# --- Behavior & Capability ---
- **USES**: The source uses the target. *Valid Pairs: (threat-actor -> tool), (malware -> attack-pattern).*
- **TARGETS**: The source is targeting the target. *Valid Pairs: (campaign -> identity), (intrusion-set -> location).*
- **EXPLOITS**: The source leverages a weakness in the target. *Valid Pairs: (malware -> vulnerability), (attack-pattern -> vulnerability).*
- **DELIVERS**: The source sends the target to a destination. *Valid Pairs: (attack-pattern -> malware).*
# --- Indication & Location ---
- **INDICATES**: The source indicates the presence of the target. *Valid Pairs: (indicator -> malware), (indicator -> intrusion-set).*
- **LOCATED_AT**: The source is located at the target. *Valid Pairs: (threat-actor -> location).*
# --- Network & Host ---
- **COMMUNICATES_WITH**: The source and target communicate. *Valid Pairs: (malware -> domain).*
- **CONNECTS_TO**: The source connects to the target. *Valid Pairs: (ip-address -> ip-address).*
- **RESOLVES_TO**: The source domain name resolves to the target IP address. *Valid Pairs: (domain -> ip-address).*
- **HOSTS**: The source hosts the target. *Valid Pairs: (ip-address -> malware).*
# --- Containment ---
- **CONTAINS**: The source contains the target. *Valid Pairs: (report -> indicator), (file -> artifact).*
- **HAS_WEAKNESS**: The source has a weakness in the target. *Valid Pairs: (software -> vulnerability).*
- **HAS_PAYLOAD**: The source has a payload in the target. *Valid Pairs: (software -> payload).*

---Attack Chain and Causal Reasoning---
Beyond extracting simple pairs, your primary goal is to reconstruct the logical attack chain. A common and critical chain to identify follows this pattern:

1.  **The Foundation**: A `SOFTWARE` entity.
2.  **The Weakness**: The software `HAS` a `VULNERABILITY`. (Use the `HAS_WEAKNESS` relationship and explain it in the description, or a more specific one if available).
3.  **The Method**: The `VULNERABILITY` is targeted by an `ATTACK_PATTERN` or `MALWARE` via an `EXPLOITS` relationship.
4.  **The Actor**: The `ATTACK_PATTERN` or `MALWARE` is wielded by a `THREAT_ACTOR` or `INTRUSION_SET` via a `USES` relationship.

**Your task is to actively look for this causal sequence.** When you identify entities that fit this pattern, prioritize extracting the relationships that connect them. Pay close attention to causal language such as "allows for," "leads to," "by means of," "which enables," "as a result of," and "in order to."


---Chain-of-Thought Process---
Before generating the output, follow these steps internally:
1.  **First Pass - Entity Identification**: Read the entire text and identify all potential entities. For each, note its name and preliminary type from the schema.
2.  **Second Pass - Entity Canonicalization**: Review the list of entities. Merge duplicates and assign a single, consistent canonical name for each unique entity.
3.  **Third Pass - Causal Chain & Relationship Identification**: Re-read the text. First, look for the causal attack chains as described above. Then, identify other clear, direct relationships between the canonical entities.
4.  **Fourth Pass - Description Generation**: For each canonical entity and relationship, gather all descriptive details from the text.
5.  **Final Pass - Formatting**: Format the extracted data precisely according to the output format rules.

---Output Format and Rules---
1.  **Entity Extraction:** Identify entities and extract the following:
    - `entity_name`: The canonical name of the entity.
    - `entity_type`: **CRITICAL** - The EXACT type from the Entity Schema.
    - `entity_description`: A comprehensive summary of the entity's role and actions from the text.
    - `entity_properties`: **CRITICAL** - This field must be an empty JSON object: `{}`.
2.  **Entity Output Format:** `(entity{tuple_delimiter}entity_name{tuple_delimiter}entity_type{tuple_delimiter}entity_description{tuple_delimiter}entity_properties)`
3.  **Relationship Extraction:** Identify direct relationships between extracted entities.
    - `source_entity`: Canonical name of the source entity.
    - `target_entity`: Canonical name of the target entity.
    - `relationship_type`: The EXACT type from the Relationship Schema.
    - `relationship_description`: A clear explanation of the relationship, citing evidence from the text.
    - `relationship_properties`: **CRITICAL** - This field must be an empty JSON object: `{}`.
4.  **Relationship Output Format:** `(relationship{tuple_delimiter}source_entity{tuple_delimiter}target_entity{tuple_delimiter}relationship_type{tuple_delimiter}relationship_description{tuple_delimiter}relationship_properties)`
5.  **CRITICAL RULE: No Pronouns.** In all names and descriptions, use explicit names.
6.  **CRITICAL RULE: Language.** All output must be in `{language}`.
7.  **CRITICAL RULE: Delimiters.** Use `{record_delimiter}` to separate each record. Output `{completion_delimiter}` at the very end.

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
   - entity_type: One of the STIX2.0 entity types exactly as defined in the schema
   - entity_description: Comprehensive description
   - entity_properties: Empty JSON object {}
3. Each relationship must include:
   - source_entity: Name of the source entity
   - target_entity: Name of the target entity
   - relationship_type: One of the STIX2.0 relationship types exactly as defined in the schema
   - relationship_description: Clear explanation of the relationship
   - relationship_properties: Empty JSON object {}
4. Output `{completion_delimiter}` when all the entities and relationships are extracted.
5. Ensure the output language is {language}.

<Output>
"""

PROMPTS["entity_continue_extraction_user_prompt"] = """---Task---
Identify any missed STIX2.0 compliant entities or relationships from the input text to be Processed of last extraction task.

---STIX2.0 Continuation Requirements---
1. Output the entities and relationships in the same STIX2.0 compliant format as previous extraction task.
2. Each entity must include:
   - entity_name: Clear, consistent name
   - entity_type: One of the STIX2.0 entity types exactly as defined in the schema
   - entity_description: Comprehensive description
   - entity_properties: Empty JSON object {}
3. Each relationship must include:
   - source_entity: Name of the source entity
   - target_entity: Name of the target entity
   - relationship_type: One of the STIX2.0 relationship types exactly as defined in the schema
   - relationship_description: Clear explanation of the relationship
   - relationship_properties: Empty JSON object {}
4. Do not include entities and relations that have been correctly extracted in last extraction task.
5. If the entity or relation output is truncated or has missing fields in last extraction task, please re-output it in the correct STIX2.0 format.
6. Output `{completion_delimiter}` when all the entities and relationships are extracted.
7. Ensure the output language is {language}.

<Output>
"""

PROMPTS["entity_extraction_examples"] = [
    """<Input Text>
The APT29 group, also known as Cozy Bear, has been conducting a sophisticated cyber espionage campaign targeting government agencies and research institutions worldwide. According to a recent report by Cyber Threat Intelligence Center, the threat actor has been utilizing a custom malware variant named "WellMess" to compromise systems. This malware exploits CVE-2020-1472, a critical vulnerability in Microsoft Windows Netlogon Remote Protocol. The attack pattern involves spear-phishing emails containing malicious attachments. Security researchers have identified indicators such as the domain "malicious-update[.]com" and the IP address 203.0.113.25, and the file hash "a1b2c3d4e5f67890" associated with this campaign. The report indicates the campaign targeted multiple government agencies in North America.```

<o>
(entity{tuple_delimiter}APT29{tuple_delimiter}THREAT_ACTOR{tuple_delimiter}APT29 is a sophisticated threat actor group also known as Cozy Bear, specializing in cyber espionage operations against government agencies and research institutions worldwide.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}WellMess{tuple_delimiter}MALWARE{tuple_delimiter}WellMess is a custom malware variant utilized by APT29 for persistent access and data exfiltration in targeted espionage operations.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}CVE-2020-1472{tuple_delimiter}VULNERABILITY{tuple_delimiter}CVE-2020-1472 is a critical vulnerability in Microsoft Windows Netlogon Remote Protocol allowing privilege escalation to domain admin.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Spear-phishing with malicious attachments{tuple_delimiter}ATTACK_PATTERN{tuple_delimiter}A targeted email technique using malicious attachments to execute malware and gain initial access.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}malicious-update[.]com{tuple_delimiter}DOMAIN{tuple_delimiter}A known command and control domain associated with WellMess operations.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}203.0.113.25{tuple_delimiter}IP_ADDRESS{tuple_delimiter}An IP address used as part of command and control infrastructure in the campaign.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}a1b2c3d4e5f67890{tuple_delimiter}FILE_HASH{tuple_delimiter}A file hash associated with the WellMess payload distributed via spear-phishing.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Cyber Threat Intelligence Center Report{tuple_delimiter}REPORT{tuple_delimiter}A report documenting APT29’s campaign, TTPs, indicators, and victims.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}North American government agencies{tuple_delimiter}IDENTITY{tuple_delimiter}Government agencies targeted by APT29’s campaign in North America.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}APT29{tuple_delimiter}WellMess{tuple_delimiter}USES{tuple_delimiter}APT29 uses WellMess to establish persistence and exfiltrate data from compromised systems.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}WellMess{tuple_delimiter}CVE-2020-1472{tuple_delimiter}EXPLOITS{tuple_delimiter}WellMess exploits CVE-2020-1472 to escalate privileges in Windows environments.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}malicious-update[.]com{tuple_delimiter}WellMess{tuple_delimiter}INDICATES{tuple_delimiter}The domain indicates presence of WellMess C2 communications.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}203.0.113.25{tuple_delimiter}WellMess{tuple_delimiter}INDICATES{tuple_delimiter}The IP address indicates command and control activity related to WellMess.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}APT29{tuple_delimiter}Spear-phishing with malicious attachments{tuple_delimiter}USES{tuple_delimiter}APT29 employs spear-phishing with malicious attachments as initial access.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}APT29{tuple_delimiter}North American government agencies{tuple_delimiter}TARGETS{tuple_delimiter}APT29 targets government agencies to conduct espionage.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}APT29{tuple_delimiter}Cyber Threat Intelligence Center Report{tuple_delimiter}RELATED_TO{tuple_delimiter}The report documents APT29’s campaign and indicators.{tuple_delimiter}{{}){record_delimiter}
{completion_delimiter}
""",
"""<Input Text>
An APT group named "DarkShadow" targets critical energy infrastructure. Visitors to compromised industry websites are infected with a custom backdoor "ShadowNet" via a drive-by download exploiting CVE-2022-2294 (WebRTC). ShadowNet persists via scheduled tasks and registry modifications, performs reconnaissance, and coordinates with an ICS-disruption malware "BlackOut". C2 communication is observed with domain "shadow-c2[.]net" and IP 45.67.89.123; the domain resolves to 45.67.89.123. A hosting server 203.0.113.50 is identified as hosting "BlackOut" payloads. Affected substations are located in Eastern Europe.```

<o>
(entity{tuple_delimiter}DarkShadow{tuple_delimiter}INTRUSION_SET{tuple_delimiter}An APT group focusing on critical energy infrastructure operations.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}ShadowNet{tuple_delimiter}MALWARE{tuple_delimiter}A custom backdoor used for initial access, persistence, and reconnaissance.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}BlackOut{tuple_delimiter}MALWARE{tuple_delimiter}An ICS-disruption malware designed to impact power grid operations.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}CVE-2022-2294{tuple_delimiter}VULNERABILITY{tuple_delimiter}A use-after-free vulnerability in WebRTC enabling remote code execution.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Drive-by download on industry websites{tuple_delimiter}ATTACK_PATTERN{tuple_delimiter}Compromised trusted sites trigger automatic malware delivery upon visit.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}shadow-c2[.]net{tuple_delimiter}DOMAIN{tuple_delimiter}A C2 domain used by ShadowNet.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}45.67.89.123{tuple_delimiter}IP_ADDRESS{tuple_delimiter}An IP involved in C2 communications linked to ShadowNet.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}203.0.113.50{tuple_delimiter}IP_ADDRESS{tuple_delimiter}A hosting server used to deliver BlackOut payloads.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Eastern Europe{tuple_delimiter}LOCATION{tuple_delimiter}Geographic region where affected substations are located.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Regional power substations{tuple_delimiter}IDENTITY{tuple_delimiter}Targeted energy infrastructure assets within Eastern Europe.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}DarkShadow{tuple_delimiter}ShadowNet{tuple_delimiter}USES{tuple_delimiter}DarkShadow uses ShadowNet for initial access and control.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}DarkShadow{tuple_delimiter}BlackOut{tuple_delimiter}USES{tuple_delimiter}DarkShadow deploys BlackOut to disrupt ICS operations.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}ShadowNet{tuple_delimiter}CVE-2022-2294{tuple_delimiter}EXPLOITS{tuple_delimiter}ShadowNet exploits the vulnerability for initial compromise.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}shadow-c2[.]net{tuple_delimiter}45.67.89.123{tuple_delimiter}RESOLVES_TO{tuple_delimiter}The domain resolves to the IP used in C2.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}ShadowNet{tuple_delimiter}shadow-c2[.]net{tuple_delimiter}COMMUNICATES_WITH{tuple_delimiter}ShadowNet communicates with the C2 domain.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}ShadowNet{tuple_delimiter}45.67.89.123{tuple_delimiter}COMMUNICATES_WITH{tuple_delimiter}ShadowNet communicates with the C2 IP.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}203.0.113.50{tuple_delimiter}BlackOut{tuple_delimiter}HOSTS{tuple_delimiter}The server hosts BlackOut payloads.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}DarkShadow{tuple_delimiter}Regional power substations{tuple_delimiter}TARGETS{tuple_delimiter}DarkShadow targets substations to disrupt power operations.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}Regional power substations{tuple_delimiter}Eastern Europe{tuple_delimiter}LOCATED_AT{tuple_delimiter}The targeted infrastructure is located in Eastern Europe.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}shadow-c2[.]net{tuple_delimiter}ShadowNet{tuple_delimiter}INDICATES{tuple_delimiter}The domain indicates activity of ShadowNet.{tuple_delimiter}{{}){record_delimiter}
{completion_delimiter}
""",
"""<Input Text>
A group "CodeStealers" compromised popular open-source JavaScript libraries by inserting a malicious updater module. The updater module downloads a payload "DevInjector" which drops files into "C:\\ProgramData\\Updater" and spawns "updater.exe". It creates a hidden user "svc_update", schedules a process via WMI, and tunnels exfiltration over HTTPS to "dev-updates[.]info" and 23.45.67.89. The operation abuses "Node.js Package Manager" (software) with a configuration weakness tracked as CVE-2023-1234. The payload later delivers "DevThief" malware for code theft. Emails from "alerts@dev-updates[.]info" were used for phishing.```

<o>
(entity{tuple_delimiter}CodeStealers{tuple_delimiter}THREAT_ACTOR{tuple_delimiter}A threat group specializing in software supply chain attacks against developers.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Node.js Package Manager{tuple_delimiter}SOFTWARE{tuple_delimiter}A software package manager targeted during the compromise.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}CVE-2023-1234{tuple_delimiter}VULNERABILITY{tuple_delimiter}A configuration weakness enabling code execution during package install/update.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Updater module{tuple_delimiter}TOOL{tuple_delimiter}A trojanized update component inserted into open-source libraries.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}DevInjector{tuple_delimiter}PAYLOAD{tuple_delimiter}A payload downloaded by the updater that stages further malware.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}DevThief{tuple_delimiter}MALWARE{tuple_delimiter}A malware used to steal source code and credentials.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}C:\\Users\\Public\\Documents{tuple_delimiter}DIRECTORY{tuple_delimiter}A directory scanned by the payload for sensitive files.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}C:\\ProgramData\\Updater\\updater.exe{tuple_delimiter}FILE{tuple_delimiter}An executable dropped by the payload for persistence.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}https://dev-updates.info/api{tuple_delimiter}URL{tuple_delimiter}A URL endpoint used for encrypted exfiltration.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}alerts@dev-updates.info{tuple_delimiter}EMAIL_ADDRESS{tuple_delimiter}A sender address used during phishing stages.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}svc_update{tuple_delimiter}USER_ACCOUNT{tuple_delimiter}A hidden local user created for persistence and privilege separation.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}WMI Provider Host{tuple_delimiter}PROCESS{tuple_delimiter}A process abused to schedule malicious tasks.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}HTTPS exfiltration{tuple_delimiter}NETWORK_TRAFFIC{tuple_delimiter}Encrypted outbound traffic carrying staged data.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}dev-updates[.]info{tuple_delimiter}DOMAIN{tuple_delimiter}A C2/control domain for staging and exfiltration.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}23.45.67.89{tuple_delimiter}IP_ADDRESS{tuple_delimiter}A C2 IP endpoint used by the operation.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Technology firms{tuple_delimiter}IDENTITY{tuple_delimiter}Target organizations impacted by the supply chain attack.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}CodeStealers{tuple_delimiter}Updater module{tuple_delimiter}USES{tuple_delimiter}CodeStealers uses the trojanized updater to distribute payloads.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}Node.js Package Manager{tuple_delimiter}CVE-2023-1234{tuple_delimiter}HAS_WEAKNESS{tuple_delimiter}The software exhibits a configuration weakness exploited during updates.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}Updater module{tuple_delimiter}DevInjector{tuple_delimiter}DELIVERS{tuple_delimiter}The updater delivers the DevInjector payload.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}DevInjector{tuple_delimiter}DevThief{tuple_delimiter}DELIVERS{tuple_delimiter}The payload further delivers DevThief malware.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}DevInjector{tuple_delimiter}C:\\ProgramData\\Updater\\updater.exe{tuple_delimiter}CONTAINS{tuple_delimiter}The payload drops and contains a persistent executable.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}DevInjector{tuple_delimiter}C:\\Users\\Public\\Documents{tuple_delimiter}CONTAINS{tuple_delimiter}The payload collects files from the directory for staging.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}HTTPS exfiltration{tuple_delimiter}dev-updates[.]info{tuple_delimiter}COMMUNICATES_WITH{tuple_delimiter}Exfiltration traffic communicates with the domain.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}HTTPS exfiltration{tuple_delimiter}23.45.67.89{tuple_delimiter}COMMUNICATES_WITH{tuple_delimiter}Exfiltration traffic communicates with the IP.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}Updater module{tuple_delimiter}Open-source library{tuple_delimiter}PART_OF{tuple_delimiter}The trojanized updater is part of a library bundle.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}IOC list{tuple_delimiter}DevThief{tuple_delimiter}DERIVED_FROM{tuple_delimiter}Indicators were derived from observed DevThief activity.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}CodeStealers{tuple_delimiter}Technology firms{tuple_delimiter}TARGETS{tuple_delimiter}The campaign targets technology firms.{tuple_delimiter}{{}){record_delimiter}
{completion_delimiter}
""",
"""<Input Text>
"Operation Silent Ledger" is a multi-month campaign targeting financial ERP systems. The threat actor "LedgerCrack" uses a credential-stuffing attack pattern and a custom dropper to deploy memory-only modules. The targeted software "AcmeERP" has a weakness tracked as CVE-2024-4242 allowing insecure default admin passwords. A recommended course of action "Disable default accounts and rotate secrets" mitigates initial access. A technical report "Silent Ledger Technical Analysis" includes collected memory artifacts.```

<o>
(entity{tuple_delimiter}Operation Silent Ledger{tuple_delimiter}CAMPAIGN{tuple_delimiter}A sustained campaign focusing on compromising financial ERP systems.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}LedgerCrack{tuple_delimiter}THREAT_ACTOR{tuple_delimiter}A financially motivated actor targeting ERP platforms.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Credential stuffing against ERP{tuple_delimiter}ATTACK_PATTERN{tuple_delimiter}Reuse of compromised credentials to gain unauthorized access to ERP accounts.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}AcmeERP{tuple_delimiter}SOFTWARE{tuple_delimiter}An ERP platform affected by weak default account configurations.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}CVE-2024-4242{tuple_delimiter}VULNERABILITY{tuple_delimiter}A weakness in AcmeERP enabling initial access through default credentials.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Disable default accounts and rotate secrets{tuple_delimiter}COURSE_OF_ACTION{tuple_delimiter}A mitigation to prevent initial access via default credentials.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Silent Ledger Technical Analysis{tuple_delimiter}REPORT{tuple_delimiter}A report documenting campaign details, techniques, and collected evidence.{tuple_delimiter}{{}){record_delimiter}
(entity{tuple_delimiter}Volatile memory dump fragment{tuple_delimiter}ARTIFACT{tuple_delimiter}A collected artifact containing code fragments of the memory-only module.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}Operation Silent Ledger{tuple_delimiter}LedgerCrack{tuple_delimiter}ATTRIBUTED_TO{tuple_delimiter}The campaign is attributed to the threat actor LedgerCrack.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}LedgerCrack{tuple_delimiter}Credential stuffing against ERP{tuple_delimiter}USES{tuple_delimiter}The actor uses credential stuffing to access ERP accounts.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}AcmeERP{tuple_delimiter}CVE-2024-4242{tuple_delimiter}HAS_WEAKNESS{tuple_delimiter}The software has a default-credential weakness tracked as CVE-2024-4242.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}Credential stuffing against ERP{tuple_delimiter}CVE-2024-4242{tuple_delimiter}EXPLOITS{tuple_delimiter}The attack pattern exploits the weakness to gain access.{tuple_delimiter}{{}){record_delimiter}
(relationship{tuple_delimiter}Silent Ledger Technical Analysis{tuple_delimiter}Volatile memory dump fragment{tuple_delimiter}CONTAINS{tuple_delimiter}The report contains a collected memory artifact.{tuple_delimiter}{{}){record_delimiter}
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

Query: "What indicators of compromise are associated with the latest Emotet campaign in 2024?"

Output:
{
  "high_level_keywords": [
    "Indicators of compromise",
    "Emotet campaign 2024",
    "Malware infection",
    "Email phishing"
  ],
  "low_level_keywords": [
    "C2 servers",
    "Malicious domains",
    "IP addresses",
    "File hashes",
    "Attachment macros",
    "TTPs"
  ]
}

""",
    """Example 2:

Query: "How is CVE-2021-44228 (Log4Shell) exploited by ransomware groups for initial access?"

Output:
{
  "high_level_keywords": [
    "Vulnerability exploitation",
    "Ransomware operations",
    "Initial access",
    "Post-exploitation"
  ],
  "low_level_keywords": [
    "CVE-2021-44228",
    "Log4Shell",
    "Lateral movement",
    "Privilege escalation",
    "C2 beacons",
    "Data exfiltration"
  ]
}

""",
    """Example 3:

Query: "Map APT29 spear-phishing TTPs to ATT&CK techniques and related infrastructure."

Output:
{
  "high_level_keywords": [
    "ATT&CK mapping",
    "Spear-phishing",
    "Social engineering",
    "Threat actor profiling"
  ],
  "low_level_keywords": [
    "APT29",
    "T1566.001",
    "Malicious attachments",
    "C2 domain",
    "IP address",
    "Email infrastructure"
  ]
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
