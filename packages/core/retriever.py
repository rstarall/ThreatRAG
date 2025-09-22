import traceback

from .. import config
from .knowledgebase import KnowledgeBase
from .graphbase import GraphDatabase
from ..models.rerank_model import get_reranker
from ..utils.logging_config import logger
from ..models import select_model
from .operators import HyDEOperator
from ..utils.web_search import WebSearcher
from ..utils.prompts import knowbase_qa_template
from ..utils.prompts import rewritten_query_prompt_template
from ..utils.prompts import entity_extraction_prompt_template as entity_template
from ..utils.prompts import keywords_prompt_template as entity_template


class Retriever:

    def __init__(self):
        self.knowledge_base = KnowledgeBase()
        self.graph_base = GraphDatabase()
        self._load_models()

    def _load_models(self):
        if config.enable_reranker:
            self.reranker = get_reranker(config)

        if config.enable_web_search:
            self.web_searcher = WebSearcher()

    def retrieval(self, query, history, meta):
        refs = {"query": query, "history": history, "meta": meta}
        refs["model_name"] = config.model_name
        refs["entities"] = self.reco_entities(query, history, refs)
        refs["knowledge_base"] = self.query_knowledgebase(query, history, refs)
        refs["graph_base"] = self.query_graph(query, history, refs)
        refs["web_search"] = self.query_web(query, history, refs)

        return refs

    def restart(self):
        """所有需要重启的模型"""
        self._load_models()

    def construct_query(self, query, refs, meta):
        logger.debug(f"{refs=}")
        if not refs or len(refs) == 0:
            return query

        # 检查是否显示检索结果信息
        show_retrieval_info = meta.get("show_retrieval_info", True)  # 默认为True，总是传递检索结果
        
        if not show_retrieval_info:
            # 如果不显示检索结果信息，直接返回原始查询
            return query

        external_parts = []

        # 解析知识库的结果
        kb_res = refs.get("knowledge_base", {}).get("results", [])
        if kb_res:
            kb_text = "\n".join(f"{r['id']}: {r['entity']['text']}" for r in kb_res)
            external_parts.extend(["知识库信息:", kb_text])

        # 解析图数据库的结果
        db_res = refs.get("graph_base", {}).get("results", {})
        logger.debug(f"图数据库结果类型: {type(db_res)}, 内容: {db_res}")
        
        # 处理不同的返回格式
        if isinstance(db_res, dict) and db_res.get("nodes") and len(db_res["nodes"]) > 0:
            db_text = "\n".join(
                [f"{edge['source_name']}和{edge['target_name']}的关系是{edge['type']}" for edge in db_res.get("edges", [])]
            )
            external_parts.extend(["图数据库信息:", db_text])
        elif isinstance(db_res, list) and len(db_res) > 0:
            # 如果返回的是列表格式，直接处理
            db_text = "\n".join(
                [f"{item.get('source_name', '')}和{item.get('target_name', '')}的关系是{item.get('type', '')}" 
                 for item in db_res if isinstance(item, dict)]
            )
            if db_text.strip():
                external_parts.extend(["图数据库信息:", db_text])

        # 解析网络搜索的结果
        web_res = refs.get("web_search", {}).get("results", [])
        if web_res:
            web_text = "\n".join(f"{r['title']}: {r['content']}" for r in web_res)
            external_parts.extend(["网络搜索信息:", web_text])

        # 构造查询
        if external_parts and len(external_parts) > 0:
            external = "\n\n".join(external_parts)
            query = knowbase_qa_template.format(external=external, query=query)

        return query

    def query_classification(self, query):
        """判断是否需要查询
        - 对于完全基于用户给定信息的任务，称之为"足够""sufficient"，不需要检索；
        - 否则，称之为"不足""insufficient"，可能需要检索，
        """
        raise NotImplementedError

    def query_graph(self, query, history, refs):
        """增强的图检索方法，支持多模式搜索"""
        results = []
        if not refs["meta"].get("use_graph") or not config.enable_knowledge_base:
            return {"results": []}
        
        # 获取搜索模式配置
        search_mode = refs["meta"].get("search_mode", "hybrid")  # local, global, hybrid
        top_k = refs["meta"].get("top_k", 10)
        threshold = refs["meta"].get("threshold", 0.7)
        
        # 提取关键词
        entities = refs.get("entities", [])
        keywords = [entity for entity in entities if entity.strip()]
        
        if not keywords:
            return {"results": []}
        
        # 根据模式选择搜索策略
        if search_mode == "local":
            # 基于实体的局部搜索
            results = self._search_entities_and_relations(keywords, top_k, threshold)
        elif search_mode == "global":
            # 基于关系关键词的全局搜索
            results = self._search_relations_and_entities(keywords, top_k, threshold)
        else:  # hybrid
            # 混合搜索：结合实体和关系
            entity_results = self._search_entities_and_relations(keywords, top_k, threshold)
            relation_results = self._search_relations_and_entities(keywords, top_k, threshold)
            results = self._merge_search_results(entity_results, relation_results)
        
        return {"results": self.graph_base.format_query_result_to_graph(results)}

    def _search_entities_and_relations(self, keywords, top_k, threshold):
        """基于实体搜索相关关系"""
        try:
            # 使用批量搜索提高效率
            all_results = self.graph_base.query_nodes_batch(
                keywords, 
                threshold=threshold, 
                max_entities=top_k
            )
        except Exception as e:
            logger.warning(f"批量实体搜索失败: {e}")
            # 回退到单个搜索
            all_results = []
            for keyword in keywords:
                try:
                    entity_results = self.graph_base.query_node(
                        keyword, 
                        threshold=threshold, 
                        max_entities=top_k
                    )
                    all_results.extend(entity_results)
                except Exception as e:
                    logger.warning(f"实体搜索失败 {keyword}: {e}")
                    continue
        
        # 去重并限制结果数量
        seen = set()
        unique_results = []
        for result in all_results:
            # 处理Neo4j原始结果格式
            if isinstance(result, (list, tuple)) and len(result) >= 3:
                # Neo4j原始格式: [node1, relationships, node2]
                result_key = (str(result[0]), str(result[2]), str(result[1]))
            elif isinstance(result, dict):
                # 字典格式: {'h': ..., 't': ..., 'r': ...}
                result_key = (result.get('h'), result.get('t'), result.get('r'))
            else:
                # 其他格式，跳过
                continue
                
            if result_key not in seen:
                seen.add(result_key)
                unique_results.append(result)
                if len(unique_results) >= top_k:
                    break
        
        return unique_results

    def _search_relations_and_entities(self, keywords, top_k, threshold):
        """基于关系关键词搜索相关实体"""
        all_results = []
        
        for keyword in keywords:
            try:
                # 搜索包含关键词的关系
                relation_results = self.graph_base.query_by_relationship_type(
                    keyword, 
                    hops=2
                )
                all_results.extend(relation_results)
            except Exception as e:
                logger.warning(f"关系搜索失败 {keyword}: {e}")
                continue
        
        # 去重并限制结果数量
        seen = set()
        unique_results = []
        for result in all_results:
            # 处理Neo4j原始结果格式
            if isinstance(result, (list, tuple)) and len(result) >= 3:
                # Neo4j原始格式: [node1, relationships, node2]
                result_key = (str(result[0]), str(result[2]), str(result[1]))
            elif isinstance(result, dict):
                # 字典格式: {'h': ..., 't': ..., 'r': ...}
                result_key = (result.get('h'), result.get('t'), result.get('r'))
            else:
                # 其他格式，跳过
                continue
                
            if result_key not in seen:
                seen.add(result_key)
                unique_results.append(result)
                if len(unique_results) >= top_k:
                    break
        
        return unique_results

    def _merge_search_results(self, entity_results, relation_results):
        """合并实体和关系搜索结果，使用轮询策略"""
        merged_results = []
        seen = set()
        
        # 轮询合并：交替从两个结果集中取结果
        max_len = max(len(entity_results), len(relation_results))
        for i in range(max_len):
            # 先取实体结果
            if i < len(entity_results):
                result = entity_results[i]
                # 处理Neo4j原始结果格式
                if isinstance(result, (list, tuple)) and len(result) >= 3:
                    result_key = (str(result[0]), str(result[2]), str(result[1]))
                elif isinstance(result, dict):
                    result_key = (result.get('h'), result.get('t'), result.get('r'))
                else:
                    continue
                    
                if result_key not in seen:
                    seen.add(result_key)
                    merged_results.append(result)
            
            # 再取关系结果
            if i < len(relation_results):
                result = relation_results[i]
                # 处理Neo4j原始结果格式
                if isinstance(result, (list, tuple)) and len(result) >= 3:
                    result_key = (str(result[0]), str(result[2]), str(result[1]))
                elif isinstance(result, dict):
                    result_key = (result.get('h'), result.get('t'), result.get('r'))
                else:
                    continue
                    
                if result_key not in seen:
                    seen.add(result_key)
                    merged_results.append(result)
        
        return merged_results

    def query_knowledgebase(self, query, history, refs):
        """查询知识库"""

        response = {
            "results": [],
            "all_results": [],
            "rw_query": query,
            "message": "",
        }

        meta = refs["meta"]

        db_id = meta.get("db_id")
        if not db_id or not config.enable_knowledge_base:
            response["message"] = "知识库未启用、或未指定知识库、或知识库不存在"
            return response

        rw_query = self.rewrite_query(query, history, refs)

        logger.debug(f"{meta=}")
        query_result = self.knowledge_base.query(query=rw_query,
                                            db_id=db_id,
                                            distance_threshold=meta.get("distanceThreshold", 0.5),
                                            rerank_threshold=meta.get("rerankThreshold", 0.1),
                                            max_query_count=meta.get("maxQueryCount", 20),
                                            top_k=meta.get("topK", 10))

        response["results"] = query_result["results"]
        response["all_results"] = query_result["all_results"]
        response["rw_query"] = rw_query
        response["message"] = query_result["message"]

        return response

    def query_web(self, query, history, refs):
        """查询网络"""

        if not refs["meta"].get("use_web") or not config.enable_web_search:
            return {"results": [], "message": "Web search is disabled"}

        if not hasattr(self, 'web_searcher'):
            logger.warning("Web searcher not initialized")
            return {"results": [], "message": "Web searcher not initialized"}

        try:
            search_results = self.web_searcher.search(query, max_results=5)
            return {"results": search_results}
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            return {"results": [], "message": f"Web search error: {str(e)}"}

    def rewrite_query(self, query, history, refs):
        """重写查询"""
        model_provider = config.model_provider
        model_name = config.model_name
        model = select_model(model_provider=model_provider, model_name=model_name)
        if refs["meta"].get("mode") == "search":  # 如果是搜索模式，就使用 meta 的配置，否则就使用全局的配置
            rewrite_query_span = refs["meta"].get("use_rewrite_query", "off")
        else:
            rewrite_query_span = config.use_rewrite_query

        if rewrite_query_span == "off":
            rewritten_query = query
        else:
            history_query = [entry["content"] for entry in history if entry["role"] == "user"] if history else ""
            rewritten_query_prompt = rewritten_query_prompt_template.format(history=history_query, query=query)
            rewritten_query = model.predict(rewritten_query_prompt).content

        if rewrite_query_span == "hyde":
            res = HyDEOperator.call(model_callable=model.predict, query=query, context_str=history_query)
            rewritten_query = res.content

        return rewritten_query

    def reco_entities(self, query, history, refs):
        """识别句子中的实体"""
        query = refs.get("rewritten_query", query)
        model_provider = config.model_provider
        model_name = config.model_name
        model = select_model(model_provider=model_provider, model_name=model_name)

        entities = []
        if refs["meta"].get("use_graph"):
            entity_extraction_prompt = entity_template.format(text=query)
            entities = model.predict(entity_extraction_prompt).content.split("<->")
            #entities = [entity for entity in entities if all(char.isalnum() or char in "汉字" for char in entity)]

        return entities

    def __call__(self, query, history, meta):
        refs = self.retrieval(query, history, meta)
        query = self.construct_query(query, refs, meta)
        return query, refs
