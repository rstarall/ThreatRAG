"""
查询处理器
处理查询相关的辅助功能
"""

from typing import List, Dict, Any, Optional
from ...models.chat_model import select_model
from ...utils.logging_config import logger


class QueryProcessor:
    """查询处理器"""
    
    def __init__(self):
        """初始化查询处理器"""
        pass
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            List[str]: 关键词列表
        """
        try:
            # 简单的关键词提取（可以替换为更复杂的NLP方法）
            import re
            
            # 去除标点符号，分词
            words = re.findall(r'\b\w+\b', text.lower())
            
            # 过滤停用词（简化版本）
            stop_words = {'的', '了', '在', '是', '我', '你', '他', '她', '它', '和', '与', '或', '但', '然而', '因此', '所以'}
            keywords = [word for word in words if word not in stop_words and len(word) > 1]
            
            return keywords[:10]  # 限制关键词数量
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
    
    def clean_query(self, query: str) -> str:
        """清理查询文本
        
        Args:
            query: 原始查询
            
        Returns:
            str: 清理后的查询
        """
        # 去除多余空格
        query = ' '.join(query.split())
        
        # 去除特殊字符（保留中英文、数字、基本标点）
        import re
        query = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:]', '', query)
        
        return query.strip()
    
    def expand_query(self, query: str, expansion_terms: List[str]) -> str:
        """扩展查询
        
        Args:
            query: 原始查询
            expansion_terms: 扩展词汇
            
        Returns:
            str: 扩展后的查询
        """
        if not expansion_terms:
            return query
            
        # 将扩展词汇添加到查询中
        expanded_query = f"{query} {' '.join(expansion_terms[:3])}"  # 限制扩展词数量
        
        return expanded_query
    
    def analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """分析查询意图
        
        Args:
            query: 查询文本
            
        Returns:
            Dict[str, Any]: 意图分析结果
        """
        intent_info = {
            "query_type": "general",  # general, factual, procedural, comparative
            "entity_focus": False,
            "temporal_focus": False,
            "requires_reasoning": False
        }
        
        # 简单的规则判断
        query_lower = query.lower()
        
        # 判断查询类型
        if any(word in query_lower for word in ['什么是', '什么叫', 'what is', 'define']):
            intent_info["query_type"] = "factual"
        elif any(word in query_lower for word in ['如何', '怎么', 'how to', '怎样']):
            intent_info["query_type"] = "procedural"
        elif any(word in query_lower for word in ['比较', '对比', 'compare', 'versus']):
            intent_info["query_type"] = "comparative"
        
        # 判断是否关注实体
        if any(word in query_lower for word in ['公司', '人员', '机构', '组织', '地区']):
            intent_info["entity_focus"] = True
        
        # 判断是否有时间关注
        if any(word in query_lower for word in ['时间', '日期', '年', '月', '日', '什么时候', 'when']):
            intent_info["temporal_focus"] = True
        
        # 判断是否需要推理
        if any(word in query_lower for word in ['为什么', '原因', '影响', '结果', 'why', 'because']):
            intent_info["requires_reasoning"] = True
        
        return intent_info


__all__ = ["QueryProcessor"]
