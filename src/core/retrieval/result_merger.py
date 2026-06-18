"""
结果合并器
合并不同来源的检索结果
"""

from typing import List, Dict, Any, Optional
from ...utils.logging_config import logger


class ResultMerger:
    """检索结果合并器"""
    
    def __init__(self):
        """初始化结果合并器"""
        pass
    
    def merge_knowledge_results(self, kb_results: List[Dict[str, Any]],
                               graph_results: Dict[str, Any],
                               weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """合并知识库和图谱的检索结果

        Args:
            kb_results: 知识库结果
            graph_results: 图谱结果，格式为 {"nodes": [...], "edges": [...]}，与 graph_model.SubGraph 一致
            weights: 权重配置

        Returns:
            List[Dict[str, Any]]: 合并后的结果
        """
        weights = weights or {"knowledge_base": 0.7, "graph": 0.3}

        merged_results = []

        # 添加知识库结果
        for result in kb_results:
            merged_result = {
                "source": "knowledge_base",
                "content": result.get("entity", {}).get("text", ""),
                "score": result.get("distance", 0.0) * weights["knowledge_base"],
                "metadata": {
                    "id": result.get("id", ""),
                    "filename": result.get("entity", {}).get("metadata", {}).get("filename", ""),
                    "original_score": result.get("distance", 0.0),
                    "rerank_score": result.get("rerank_score")
                }
            }
            merged_results.append(merged_result)

        # 添加图谱节点结果，使用 graph_model.Entity 标准字段
        nodes = graph_results.get("nodes", []) if isinstance(graph_results, dict) else []
        for node in nodes:
            merged_result = {
                "source": "graph",
                "content": f"实体: {node.get('entity_name', '')}",
                "score": weights["graph"],
                "metadata": {
                    "entity_id": node.get("entity_id", ""),
                    "entity_name": node.get("entity_name", ""),
                    "entity_type": node.get("entity_type", ""),
                    "entity_sub_type": node.get("entity_sub_type", ""),
                    "labels": node.get("labels", []),
                    "times": node.get("times", []),
                    "entity_variant_names": node.get("entity_variant_names", []),
                    "properties": node.get("properties", {}),
                }
            }
            merged_results.append(merged_result)

        # 按分数排序
        merged_results.sort(key=lambda x: x["score"], reverse=True)

        return merged_results
    
    def deduplicate_results(self, results: List[Dict[str, Any]], 
                           similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
        """去重检索结果
        
        Args:
            results: 原始结果
            similarity_threshold: 相似度阈值
            
        Returns:
            List[Dict[str, Any]]: 去重后的结果
        """
        if not results:
            return results
        
        deduplicated = []
        
        for result in results:
            is_duplicate = False
            result_content = result.get("content", "")
            
            for existing in deduplicated:
                existing_content = existing.get("content", "")
                
                # 简单的文本相似度判断
                similarity = self._calculate_text_similarity(result_content, existing_content)
                
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    # 保留分数更高的结果
                    if result.get("score", 0) > existing.get("score", 0):
                        deduplicated.remove(existing)
                        deduplicated.append(result)
                    break
            
            if not is_duplicate:
                deduplicated.append(result)
        
        return deduplicated
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版本）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            float: 相似度分数 (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符重叠相似度
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def rank_results_by_relevance(self, results: List[Dict[str, Any]], 
                                 query: str) -> List[Dict[str, Any]]:
        """根据查询相关性重新排序结果
        
        Args:
            results: 结果列表
            query: 查询文本
            
        Returns:
            List[Dict[str, Any]]: 重新排序的结果
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        for result in results:
            content = result.get("content", "").lower()
            content_terms = set(content.split())
            
            # 计算查询词汇覆盖度
            term_overlap = len(query_terms.intersection(content_terms))
            total_query_terms = len(query_terms)
            
            if total_query_terms > 0:
                relevance_boost = term_overlap / total_query_terms
            else:
                relevance_boost = 0.0
            
            # 调整分数
            original_score = result.get("score", 0.0)
            result["score"] = original_score * (1 + relevance_boost * 0.2)  # 最多提升20%
            result["relevance_boost"] = relevance_boost
        
        # 重新排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results
    
    def format_results_for_display(self, results: List[Dict[str, Any]], 
                                  max_results: int = 10) -> List[Dict[str, Any]]:
        """格式化结果用于显示
        
        Args:
            results: 原始结果
            max_results: 最大结果数量
            
        Returns:
            List[Dict[str, Any]]: 格式化的结果
        """
        formatted = []
        
        for i, result in enumerate(results[:max_results]):
            formatted_result = {
                "rank": i + 1,
                "source": result.get("source", "unknown"),
                "content": result.get("content", "")[:500] + ("..." if len(result.get("content", "")) > 500 else ""),
                "score": round(result.get("score", 0.0), 4),
                "metadata": result.get("metadata", {})
            }
            
            # 添加来源特定信息
            if result.get("source") == "knowledge_base":
                formatted_result["filename"] = result.get("metadata", {}).get("filename", "")
                formatted_result["doc_id"] = result.get("metadata", {}).get("id", "")
            elif result.get("source") == "graph":
                # 使用 graph_model.Entity 标准字段
                metadata = result.get("metadata", {})
                formatted_result["entity_name"] = metadata.get("entity_name", "")
                formatted_result["entity_type"] = metadata.get("entity_type", "")
                formatted_result["entity_sub_type"] = metadata.get("entity_sub_type", "")
                formatted_result["labels"] = metadata.get("labels", [])
                formatted_result["times"] = metadata.get("times", [])
            
            formatted.append(formatted_result)
        
        return formatted
    
    def create_result_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建结果摘要
        
        Args:
            results: 检索结果
            
        Returns:
            Dict[str, Any]: 结果摘要
        """
        if not results:
            return {
                "total_results": 0,
                "sources": {},
                "average_score": 0.0,
                "top_score": 0.0
            }
        
        source_counts = {}
        scores = []
        
        for result in results:
            source = result.get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
            scores.append(result.get("score", 0.0))
        
        return {
            "total_results": len(results),
            "sources": source_counts,
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "top_score": max(scores) if scores else 0.0,
            "score_distribution": {
                "high": len([s for s in scores if s >= 0.8]),
                "medium": len([s for s in scores if 0.5 <= s < 0.8]),
                "low": len([s for s in scores if s < 0.5])
            }
        }


__all__ = ["ResultMerger"]
