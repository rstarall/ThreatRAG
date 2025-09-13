import requests
import json

url = "http://localhost:8000/graph/extract-entities-from-file"
payload = 
response = requests.post(url, json=payload)
result = response.json()

# 打印结果
print(json.dumps(result, indent=2, ensure_ascii=False))