"""
BM25检索算法实现
结合向量检索和BM25算法进行混合检索
"""
from typing import List, Dict, Any
import numpy as np
from ..utils import logger
from ..utils.bm25 import create_bm25, AbstractBM25


class HybridRetriever:
    """混合检索器：结合向量检索和BM25"""
    
    def __init__(self, vector_weight: float = 0.7, bm25_weight: float = 0.3, language: str = 'chinese'):
        """
        初始化混合检索器
        
        Args:
            vector_weight: 向量检索权重
            bm25_weight: BM25检索权重
            language: BM25 使用的语言 ('chinese' 或 'english')
        """
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.language = language
        self.bm25: AbstractBM25 = None
        self.doc_id_map: Dict[int, str] = {}
        self.is_trained = False
        
        # 确保权重和为1
        total_weight = vector_weight + bm25_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"权重总和不为1，将进行归一化: {vector_weight} + {bm25_weight}")
            self.vector_weight = vector_weight / total_weight
            self.bm25_weight = bm25_weight / total_weight
    
    def fit_bm25(self, documents: List[str], document_ids: List[str]):
        """
        训练BM25模型
        
        Args:
            documents: 文档列表
            document_ids: 文档ID列表 (与 documents 一一对应)
        """
        if not documents or not document_ids or len(documents) != len(document_ids):
             logger.warning("BM25训练失败：文档或文档ID为空，或数量不匹配。")
             self.is_trained = False
             return

        self.bm25 = create_bm25(documents, language=self.language)
        self.doc_id_map = {i: doc_id for i, doc_id in enumerate(document_ids)}
        self.is_trained = True
        logger.info(f"BM25模型训练完成 ({self.language}), 文档数量: {len(documents)}")
    
    def hybrid_search(self, query: str, vector_results: List[Dict], vector_scores: List[float], top_k: int = 10) -> List[Dict]:
        """
        执行混合检索
        
        Args:
            query: 查询文本
            vector_results: 向量检索结果
            vector_scores: 向量检索分数
            top_k: 返回结果数量
            
        Returns:
            混合检索结果
        """
        if not self.is_trained or self.bm25 is None:
            logger.warning("BM25模型未训练，仅使用向量检索")
            # 仅做归一化和排序
            for i, result in enumerate(vector_results):
                result['hybrid_score'] = vector_scores[i] if i < len(vector_scores) else 0.0
            vector_results.sort(key=lambda x: x.get('hybrid_score', 0.0), reverse=True)
            return vector_results[:top_k]
        
        # 获取BM25检索结果
        # BM25 search返回的是 [(doc_index, score), ...]
        bm25_results_indexed = self.bm25.search(query, top_k=len(self.bm25.corpus))
        
        # 将BM25分数转换为 {doc_id: score} 的字典
        bm25_scores_dict = {
            self.doc_id_map.get(doc_index): score 
            for doc_index, score in bm25_results_indexed 
            if doc_index in self.doc_id_map
        }
        
        # 标准化BM25分数 (e.g., Min-Max scaling)
        max_bm25_score = max(bm25_scores_dict.values()) if bm25_scores_dict else 1.0
        if max_bm25_score > 0:
            for doc_id in bm25_scores_dict:
                bm25_scores_dict[doc_id] /= max_bm25_score

        # 创建结果映射并计算混合分数
        hybrid_results = []
        for i, result in enumerate(vector_results):
            # 确保 entity 和 file_id 存在
            if "entity" not in result or "file_id" not in result["entity"]:
                continue
            doc_id = result["entity"]["file_id"]
            
            vector_score = vector_scores[i] if i < len(vector_scores) else 0.0
            bm25_score = bm25_scores_dict.get(doc_id, 0.0)

            # 计算混合分数
            hybrid_score = (self.vector_weight * vector_score + 
                          self.bm25_weight * bm25_score)
            
            res_copy = result.copy()
            res_copy["hybrid_score"] = hybrid_score
            res_copy["vector_score"] = vector_score
            res_copy["bm25_score"] = bm25_score
            
            hybrid_results.append(res_copy)
        
        # 按混合分数排序
        hybrid_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        
        logger.info(f"混合检索完成，向量权重: {self.vector_weight:.2f}, BM25权重: {self.bm25_weight:.2f}")
        return hybrid_results[:top_k]
    
    def get_config(self) -> Dict[str, Any]:
        """获取检索器配置"""
        return {
            "vector_weight": self.vector_weight,
            "bm25_weight": self.bm25_weight,
            "language": self.language,
            "is_trained": self.is_trained,
            "document_count": self.bm25.doc_count if self.is_trained and self.bm25 else 0
        }
