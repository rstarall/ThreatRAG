"""
统一检索器
整合packages/core/retriever.py的核心功能
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple

from ...config import get_config
from ...utils.logging_config import logger
from ...models.chat_model import select_model
from ..knowledge.knowledge_base import KnowledgeBase
from ..graph.graph_store import GraphStore
from ..graph.graph_search import GraphSearcher


class Retriever:
    """统一检索器类"""

    def __init__(self):
        """初始化检索器"""
        self.knowledge_base = None
        self.graph_searcher = None
        self._graph_store = None
        
        cfg = get_config()
        
        # 初始化知识库
        if cfg.enable_knowledge_base:
            try:
                self.knowledge_base = KnowledgeBase()
                logger.info("Knowledge base initialized")
            except Exception as e:
                logger.error(f"Failed to initialize knowledge base: {e}")

        # 初始化图搜索
        if cfg.enable_knowledge_graph:
            try:
                self._graph_store = GraphStore()
                self.graph_searcher = GraphSearcher(
                    self._graph_store if self._graph_store.is_running() else None
                )
                logger.info("Graph searcher initialized")
            except Exception as e:
                logger.error(f"Failed to initialize graph searcher: {e}")
    
    async def retrieve(self, query: str, history: List[Dict[str, str]], 
                      meta: Dict[str, Any]) -> Dict[str, Any]:
        """执行检索
        
        Args:
            query: 查询文本
            history: 对话历史
            meta: 元数据参数
            
        Returns:
            Dict[str, Any]: 检索结果
        """
        refs = {
            "query": query,
            "history": history,
            "meta": meta,
            "model_name": get_config().model_name
        }
        
        # 并发执行各种检索
        tasks = []
        
        # 实体识别
        if meta.get("use_graph"):
            tasks.append(self._extract_entities(query, history, refs))
        else:
            tasks.append(asyncio.create_task(self._return_empty_entities()))
        
        # 知识库检索
        if meta.get("db_id") and self.knowledge_base:
            tasks.append(self._query_knowledge_base(query, history, refs))
        else:
            tasks.append(asyncio.create_task(self._return_empty_kb_results()))
        
        # 图谱检索
        if meta.get("use_graph") and self.graph_searcher:
            tasks.append(self._query_graph(query, history, refs))
        else:
            tasks.append(asyncio.create_task(self._return_empty_graph_results()))
        
        # 等待所有任务完成
        entities, kb_results, graph_results = await asyncio.gather(*tasks)
        
        refs.update({
            "entities": entities,
            "knowledge_base": kb_results,
            "graph_base": graph_results
        })
        
        return refs
    
    async def _extract_entities(self, query: str, history: List[Dict[str, str]], 
                               refs: Dict[str, Any]) -> List[str]:
        """提取实体
        
        Args:
            query: 查询文本
            history: 对话历史
            refs: 引用信息
            
        Returns:
            List[str]: 实体列表
        """
        try:
            model = select_model()
            
            entity_prompt = f"""这是一个知识图谱实体抽取任务，从查询中提取实体名称，返回实体名称列表，用"<->"分隔，不要有多余的文本。

查询：{query}

实体："""
            
            # 使用异步线程执行同步调用
            response = await asyncio.to_thread(model.predict, entity_prompt)
            entities = response.content.split("<->")
            
            # 清理和过滤实体
            clean_entities = [entity.strip() for entity in entities if entity.strip()]
            
            logger.debug(f"Extracted entities: {clean_entities}")
            return clean_entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []
    
    async def _query_knowledge_base(self, query: str, history: List[Dict[str, str]], 
                                   refs: Dict[str, Any]) -> Dict[str, Any]:
        """查询知识库
        
        Args:
            query: 查询文本
            history: 对话历史
            refs: 引用信息
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            meta = refs["meta"]
            db_id = meta.get("db_id")
            
            if not db_id or not self.knowledge_base:
                return {"results": [], "all_results": [], "message": "Knowledge base not available"}
            
            # 重写查询（可选）
            rewritten_query = await self._rewrite_query(query, history, refs)
            
            # 执行查询
            result = await asyncio.to_thread(
                self.knowledge_base.query,
                query=rewritten_query,
                db_id=db_id,
                distance_threshold=meta.get("distanceThreshold", 0.5),
                rerank_threshold=meta.get("rerankThreshold", 0.1),
                max_query_count=meta.get("maxQueryCount", 20),
                top_k=meta.get("topK", 10)
            )
            
            result["rw_query"] = rewritten_query
            return result
            
        except Exception as e:
            logger.error(f"Knowledge base query failed: {e}")
            return {"results": [], "all_results": [], "message": str(e)}
    
    async def _query_graph(self, query: str, history: List[Dict[str, str]],
                          refs: Dict[str, Any]) -> Dict[str, Any]:
        """查询知识图谱

        Args:
            query: 查询文本
            history: 对话历史
            refs: 引用信息

        Returns:
            Dict[str, Any]: 查询结果
        """
        try:
            if not self.graph_searcher or not self.graph_searcher.is_running:
                return {"results": {}}

            # 获取实体
            entities = refs.get("entities", [])
            if not entities:
                return {"results": {}}

            # 查询每个实体
            all_subgraphs = []
            for entity in entities:
                if entity.strip():
                    subgraph = await asyncio.to_thread(
                        self.graph_searcher.query_node, entity
                    )
                    all_subgraphs.append(subgraph)

            # 合并子图
            if all_subgraphs:
                # 收集所有节点和关系，使用 graph_model.Entity/Relationship 标准字段
                nodes_dict: Dict[str, Any] = {}
                edges: List[Dict[str, Any]] = []
                for sg in all_subgraphs:
                    for e in sg.entities:
                        if e.entity_name not in nodes_dict:
                            nodes_dict[e.entity_name] = {
                                "entity_id": e.entity_id,
                                "entity_name": e.entity_name,
                                "entity_type": e.entity_type,
                                "entity_sub_type": e.entity_sub_type,
                                "labels": e.labels,
                                "times": e.times,
                                "entity_variant_names": e.entity_variant_names,
                                "properties": e.properties,
                            }
                    for r in sg.relationships:
                        edges.append({
                            "relationship_id": r.relationship_id,
                            "relationship_type": r.relationship_type,
                            "source": r.source,
                            "target": r.target,
                            "source_id": r.source_id,
                            "target_id": r.target_id,
                        })
                return {"results": {"nodes": list(nodes_dict.values()), "edges": edges}}
            else:
                return {"results": {"nodes": [], "edges": []}}
                
        except Exception as e:
            logger.error(f"Graph query failed: {e}")
            return {"results": {}}
    
    async def _rewrite_query(self, query: str, history: List[Dict[str, str]], 
                            refs: Dict[str, Any]) -> str:
        """重写查询
        
        Args:
            query: 原始查询
            history: 对话历史  
            refs: 引用信息
            
        Returns:
            str: 重写后的查询
        """
        try:
            use_rewrite = refs["meta"].get("use_rewrite_query", get_config().use_rewrite_query)
            
            if use_rewrite == "off":
                return query
            
            model = select_model()
            
            # 构建历史上下文
            history_context = ""
            if history:
                history_texts = [msg["content"] for msg in history if msg["role"] == "user"]
                history_context = " ".join(history_texts[-3:])  # 使用最近3轮对话
            
            rewrite_prompt = f"""请根据对话历史，重写用户的查询以提高搜索准确性：

对话历史：{history_context}

当前查询：{query}

重写后的查询："""
            
            response = await asyncio.to_thread(model.predict, rewrite_prompt)
            rewritten_query = response.content.strip()
            
            logger.debug(f"Query rewritten from '{query}' to '{rewritten_query}'")
            return rewritten_query if rewritten_query else query
            
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            return query
    
    async def _return_empty_entities(self) -> List[str]:
        """返回空实体列表"""
        return []
    
    async def _return_empty_kb_results(self) -> Dict[str, Any]:
        """返回空知识库结果"""
        return {"results": [], "all_results": [], "message": "Knowledge base not enabled"}
    
    async def _return_empty_graph_results(self) -> Dict[str, Any]:
        """返回空图谱结果"""
        return {"results": {}}
    
    async def construct_query(self, query: str, refs: Dict[str, Any], 
                             meta: Dict[str, Any]) -> str:
        """构建增强查询
        
        Args:
            query: 原始查询
            refs: 检索结果
            meta: 元数据
            
        Returns:
            str: 增强后的查询
        """
        try:
            external_parts = []
            
            # 处理知识库结果
            kb_results = refs.get("knowledge_base", {}).get("results", [])
            if kb_results:
                kb_texts = []
                for result in kb_results[:5]:  # 限制数量
                    if "entity" in result and "text" in result["entity"]:
                        text = result["entity"]["text"]
                        if len(text) > 200:
                            text = text[:200] + "..."
                        kb_texts.append(f"{result.get('id', '')}: {text}")
                
                if kb_texts:
                    external_parts.extend(["知识库信息:", "\n".join(kb_texts)])
            
            # 处理图谱结果
            graph_results = refs.get("graph_base", {}).get("results", {})
            if graph_results.get("edges"):
                graph_texts = []
                for edge in graph_results["edges"][:5]:  # 限制数量
                    graph_texts.append(
                        f"{edge.get('source', '')}和{edge.get('target', '')}的关系是{edge.get('relationship_type', '')}"
                    )

                if graph_texts:
                    external_parts.extend(["图数据库信息:", "\n".join(graph_texts)])
            
            # 构建最终查询
            if external_parts:
                external_context = "\n\n".join(external_parts)
                enhanced_query = f"""请根据以下信息回答问题：

{external_context}

问题：{query}

请基于上述信息给出准确的回答。如果信息不足，请说明。"""
                
                return enhanced_query
            
            return query
            
        except Exception as e:
            logger.error(f"Query construction failed: {e}")
            return query
    
    async def __call__(self, query: str, history: List[Dict[str, str]], 
                      meta: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """调用接口
        
        Args:
            query: 查询文本
            history: 对话历史
            meta: 元数据
            
        Returns:
            Tuple[str, Dict[str, Any]]: (增强查询, 检索结果)
        """
        # 执行检索
        refs = await self.retrieve(query, history, meta)
        
        # 构建增强查询
        enhanced_query = await self.construct_query(query, refs, meta)
        
        return enhanced_query, refs


__all__ = ["Retriever"]
