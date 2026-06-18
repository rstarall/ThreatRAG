# Neo4j图谱数据保存工具

这个工具用于将JSON格式的实体关系图谱数据保存到Neo4j数据库中。

## 功能特点

- 保存实体及其所有属性
- 保存实体之间的关系
- 为实体和关系生成唯一的u4id标识符
- 支持处理单个文件或整个目录
- 自动处理实体和关系的依赖关系
- 错误处理和日志记录

## 环境要求

- Python 3.6+
- neo4j-driver
- python-dotenv

## 配置

在项目根目录创建`.env`文件，包含以下配置：

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
DATA_DIR=kg/data_process/extracted_json/results
```

## 使用方法

### 处理所有数据

```bash
python save_to_neo4j.py
```

### 测试单个文件

```bash
python test_save_to_neo4j.py
```

### 测试处理目录

```bash
python test_save_to_neo4j.py directory
```

## 数据格式

输入JSON文件格式示例：

```json
{
    "Entities": [
        {
            "EntityId": "entity_1",
            "EntityName": "Russian Business Network",
            "EntityVariantNames": {
                "EntityVariantNames": [
                    "RBN"
                ]
            },
            "EntityType": "actor",
            "EntitySubType": "org",
            "Labels": {
                "Labels": [
                    "TA0001",
                    "TA0011"
                ]
            },
            "Properties": {
                "Properties": {
                    "Location": "St. Petersburg, Russia"
                }
            }
        },
        ...
    ],
    "Relationships": [
        {
            "RelationshipId": "relationship_1",
            "RelationshipType": "involve",
            "Source": "Russian Cyberwar on Georgia",
            "Target": "Russian Business Network"
        },
        ...
    ]
}
```

## 实体属性处理

脚本会处理以下实体属性：

- EntityId: 实体ID
- EntityName: 实体名称
- EntityType: 实体类型
- EntitySubType: 实体子类型
- EntityVariantNames: 实体别名
- Labels: 实体标签
- Properties: 实体属性

所有嵌套的属性都会被扁平化处理，例如：

```json
"Properties": {
    "Properties": {
        "Location": "St. Petersburg, Russia"
    }
}
```

会被转换为：

```json
"Location": "St. Petersburg, Russia"
```

## 唯一标识符

脚本会为每个实体和关系生成唯一的u4id标识符，使用UUID格式。

## 处理流程

1. 读取JSON文件
2. 创建实体和关系的映射
3. 先创建所有基本实体（只包含名称和类型）
4. 处理实体的详细属性
5. 确保所有关系中的实体都存在
6. 处理关系
7. 记录处理结果

## 错误处理

脚本包含全面的错误处理机制：

- 处理实体和关系时的异常捕获
- 详细的错误日志记录
- 即使部分实体或关系处理失败，也会继续处理其他数据

## 注意事项

- 确保Neo4j数据库已启动并可访问
- 确保环境变量中包含正确的Neo4j连接信息
- 对于大量数据，处理可能需要较长时间
