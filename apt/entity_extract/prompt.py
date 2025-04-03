entity_extract_prompt = """
Instruction: Please identify the following types of entities and then extract the relationships between these extracted entities: malware(e.g.
'Stuxnet'), threat type(e.g., 'ransomware'),...
If there are no entities and relationships pertaining to the specified types, please state 'No related entities and relations. Make sure to followthe output format shown in the following example.

example:
Input: A hitherto umknown attack group has been observed targetimg a materals research oreanization i Asia. The eroup, which Symanteccalls Clasiopa. is characterized by a distinct toolset, which includes one piece of custom malware (Backdoor.Atharvan). At present, there isno firm evidence on where Clasiopa is based or whom it acts on behalf.
Output: Named Entities: (Clasiopa, atacker), (custom malware, malware), (Backdoor.Atharvan, malware)\\nRelationships: (Clasiopa, usecustom malware),(custom malware, name,Backdoor.Atharvan)

Input:{text}
Output:
"""