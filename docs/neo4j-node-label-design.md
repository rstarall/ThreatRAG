# Neo4j 节点标签设计方案对比

> 生成时间：2026-03-23
> 状态：待回退

## 背景

ThreatRAG 知识图谱中，节点需要区分类型（attacker / victim / event / asset / vul / ioc / tool / file / env）。设计上有两种主流方案：

- **方案 A（当前实现的版本）**：节点标签 = entityType + Entity 双标签，标签作为类型区分的核心手段
- **方案 B（原始方案）**：节点标签统一为 `:Entity`，`entityType` 作为节点属性存储

## 方案对比

### 方案 A：类型标签 + Entity 基础标签

```cypher
MERGE (n:Entity:attacker {entityName: "NCPH", entityType: "attacker", ...})
```

#### 优势
- Cypher 查询可按标签筛选：`(n:attacker)`
- 节点类型一目了然（Neo4j Browser 中图标不同）

#### 劣势
- **需要 APOC 插件**：因为 MERGE 只能基于属性匹配，标签不可作为匹配键，动态设置标签需要 `apoc.create.addLabels`
- **无 APOC 时需 Python 循环降级**：批量写入性能下降
- **MERGE 逻辑复杂**：先 `MERGE (n {entityName: ...})`，再 `SET n:Entity:{entity_type}`，分支逻辑多
- **标签重叠风险**：同一 `entityName` 改了 `entityType` 后 MERGE 找不到旧标签（因为 MERGE 只按属性匹配）
- **约束/索引管理开销**：虽然可以用 `FOR (n) ON EACH [...]` 建泛型索引，但实操中容易出现类型遗漏

### 方案 B：统一 Entity 标签（原始方案）

```cypher
MERGE (n:Entity {entityName: "NCPH", entityType: "attacker", ...})
```

#### 优势
- **MERGE 简单干净**：直接 `MERGE (n:Entity {entityName: $name})`，无 APOC 依赖
- **社区版友好**：不需要任何插件
- **无标签重叠风险**：所有节点统一 `:Entity` 标签
- **约束/索引一套搞定**：唯一约束、全文索引、向量索引都建在 `:Entity` 上，所有类型自动继承
- **向后兼容**：与原始代码完全兼容，无破坏性变更
- **代码量更少**：不需要 `_upsert_entities_batch_apoc` / `_upsert_entities_batch_apoc` 等 APOC 分支

#### 劣势（伪命题）
- `MATCH (n:Entity) WHERE n.entityType = "attacker"` vs `MATCH (n:attacker)` 写法稍长 —— **在 ThreatRAG 的实际查询场景中影响可忽略**

## ThreatRAG 实际查询场景分析

| 查询场景 | 方案 A | 方案 B | 差异 |
|---|---|---|---|
| 按名称精确查节点 | `MATCH (n {entityName: "NCPH"})` | `MATCH (n:Entity {entityName: "NCPH"})` | 方案 B 多一个 `:Entity`，但可命中索引，性能等价 |
| BFS 子图遍历 | `(n {entityName: "NCPH"})-[r*1..3]-(m)` | 同左 | 完全一致 |
| 按 entityType 过滤结果 | `WHERE n.entityType IN $types` | 同左 | 完全一致 |
| 关系类型过滤 | `WHERE type(r) IN $types` | 同左 | 完全一致 |
| 向量相似度搜索 | `WHERE n.entityEmbedding IS NOT NULL` | 同左 | 完全一致 |
| 全库节点统计 | `MATCH (n:Entity) RETURN count(n)` | 同左 | 完全一致 |
| 按类型统计节点数 | `MATCH (n:Entity) RETURN n.entityType, count(n)` | 同左 | 完全一致 |

**结论**：在 ThreatRAG 的所有核心查询路径中，方案 B 与方案 A 在功能和性能上完全等价，方案 A 的"标签筛选"优势从未被真正利用。

## 最终结论

**推荐方案 B（原始方案）**，理由：

1. **功能等价**：所有查询场景两种方案效果一致，方案 A 的标签优势从未被实际使用
2. **实现更简单**：无需 APOC、MERGE 逻辑干净、无标签重叠风险
3. **维护成本低**：约束/索引一套搞定，代码量更少
4. **向后兼容**：与原始代码完全兼容，不破坏已有调用方

## 回退操作

将 `neo4j_client.py` 和 `graph_store.py` 中所有涉及 `SET n:Entity:\`${entity_type}\`` / `apoc.create.addLabels` 的逻辑改回：

```cypher
MERGE (n:Entity {entityName: $entity_name})
SET
    n.entityId = $entity_id,
    n.entityType = $entity_type,
    ...
```

`graph_store.py` 中 `upsert_relationships` 的 `entity_name_to_type` 参数可保留（用于将来扩展），不影响核心逻辑。
