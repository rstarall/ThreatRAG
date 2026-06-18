# Neo4j数据库清除工具

这个工具用于清除Neo4j数据库中的所有数据（节点、关系、属性标签、索引和约束）。

## 功能特点

- 清除Neo4j数据库中的所有节点和关系
- 清除所有属性标签
- 删除所有索引和约束
- 显示详细的数据库统计信息（节点、关系、标签、属性键等）
- 安全确认机制，防止意外清除数据

## 环境要求

- Python 3.6+
- neo4j-driver
- python-dotenv

## 配置

使用与 `save_to_neo4j.py` 相同的环境变量配置：

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j
```

## 使用方法

### 显示数据库统计信息

```bash
python clear_neo4j.py --stats
```

这将显示数据库中的节点数量、关系数量、标签、关系类型和属性键，但不会清除任何数据。

### 清除节点和关系

```bash
python clear_neo4j.py --confirm
```

这将清除数据库中的所有节点和关系，但不会清除属性标签、索引和约束。

### 清除属性标签

```bash
python clear_neo4j.py --clear-properties --confirm
```

这将清除数据库中的所有属性标签，但不会清除节点和关系。

### 清除所有数据

```bash
python clear_neo4j.py --clear-all --confirm
```

这将清除数据库中的所有数据，包括节点、关系、属性标签、索引和约束。

### 查看帮助信息

```bash
python clear_neo4j.py --help
```

**注意：** 必须使用 `--confirm` 参数才能执行清除操作，这是为了防止意外清除数据。

## 注意事项

- 清除操作是不可逆的，请确保在执行清除操作前已备份重要数据
- `--confirm` 参数是必需的，这是为了防止意外清除数据
- `--clear-all` 参数会删除数据库中的所有数据，包括节点、关系、属性标签、索引和约束
- `--clear-properties` 参数会清除所有属性标签，但不会删除节点和关系
- 属性键（Property Keys）是Neo4j的元数据，即使清除了所有属性值，属性键仍然存在于数据库中
- 要完全删除属性键，需要重新启动Neo4j数据库
- 确保Neo4j数据库已启动并可访问
- 确保环境变量中包含正确的Neo4j连接信息

## 示例输出

### 显示统计信息

```
2023-05-08 18:00:00,000 - __main__ - INFO - 成功连接到Neo4j数据库: bolt://localhost:7687
2023-05-08 18:00:00,100 - __main__ - INFO - 数据库中有 1000 个节点和 2000 个关系
2023-05-08 18:00:00,110 - __main__ - INFO - 数据库中有 5 个标签: Actor, Event, Tool, IoC, Entity
2023-05-08 18:00:00,120 - __main__ - INFO - 数据库中有 8 个关系类型: INVOLVE, TARGET, ACTOR_USE, BELONG_TO, GENERATE, EXPLOIT
2023-05-08 18:00:00,130 - __main__ - INFO - 数据库中有 15 个属性键: name, id, type, subtype, u4id, source_file, location, date, detection_rate, affiliation, owner, host
2023-05-08 18:00:00,140 - __main__ - INFO - 仅显示统计信息，不清除数据
2023-05-08 18:00:00,150 - __main__ - INFO - Neo4j连接已关闭
```

### 清除所有数据

```
2023-05-08 18:01:00,000 - __main__ - INFO - 成功连接到Neo4j数据库: bolt://localhost:7687
2023-05-08 18:01:00,100 - __main__ - INFO - 数据库中有 1000 个节点和 2000 个关系
2023-05-08 18:01:00,110 - __main__ - INFO - 数据库中有 5 个标签: Actor, Event, Tool, IoC, Entity
2023-05-08 18:01:00,120 - __main__ - INFO - 数据库中有 8 个关系类型: INVOLVE, TARGET, ACTOR_USE, BELONG_TO, GENERATE, EXPLOIT
2023-05-08 18:01:00,130 - __main__ - INFO - 数据库中有 15 个属性键: name, id, type, subtype, u4id, source_file, location, date, detection_rate, affiliation, owner, host
2023-05-08 18:01:00,200 - __main__ - INFO - 清除所有数据，包括节点、关系、属性标签、索引和约束
2023-05-08 18:01:00,300 - __main__ - INFO - 已清除 1000 个节点和 2000 个关系
2023-05-08 18:01:00,400 - __main__ - INFO - 发现 15 个属性键: name, id, type, subtype, u4id, source_file, location, date, detection_rate, affiliation, owner, host
2023-05-08 18:01:00,500 - __main__ - INFO - 已清除节点属性: name
2023-05-08 18:01:00,510 - __main__ - INFO - 已清除关系属性: name
2023-05-08 18:01:00,520 - __main__ - INFO - 已清除节点属性: id
2023-05-08 18:01:00,530 - __main__ - INFO - 已清除关系属性: id
...
2023-05-08 18:01:01,000 - __main__ - INFO - 属性标签清除完成
2023-05-08 18:01:01,100 - __main__ - INFO - 所有数据已清除
2023-05-08 18:01:01,200 - __main__ - INFO - 数据库中有 0 个节点和 0 个关系
2023-05-08 18:01:01,210 - __main__ - INFO - 数据库中有 0 个标签: 无
2023-05-08 18:01:01,220 - __main__ - INFO - 数据库中有 0 个关系类型: 无
2023-05-08 18:01:01,230 - __main__ - INFO - 数据库中有 0 个属性键: 无
2023-05-08 18:01:01,300 - __main__ - INFO - Neo4j连接已关闭
```

## 根本删除方法
找到安装目录(如F:\neo4j\data):

```bash
rm -rf databases/neo4j

rm -rf transactions/neo4j
```