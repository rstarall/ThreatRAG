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
from ..utils.prompts import keywords_prompt_template as keywords_template
from .entity_extractor import EntityExtractor


class Retriever:

    def __init__(self):
        self.knowledge_base = KnowledgeBase()
        self.graph_base = GraphDatabase()
        self.entity_extractor = EntityExtractor()
        self._load_models()

    def _load_models(self):
        if config.enable_reranker:
            self.reranker = get_reranker(config)

        if config.enable_web_search:
            self.web_searcher = WebSearcher()

    def retrieval(self, query, history, meta):
        refs = {"query": query, "history": history, "meta": meta}
        refs["model_name"] = config.model_name
        
        # 检查是否启用四阶段检索
        if meta.get("use_hybrid_retrieval", False):
            refs.update(self.hybrid_retrieval(query, history, meta))
        else:
            # 原有的检索方式
            refs["entities"] = self.reco_entities(query, history, refs)
            refs["knowledge_base"] = self.query_knowledgebase(query, history, refs)
            refs["graph_base"] = self.query_graph(query, history, refs)
            refs["web_search"] = self.query_web(query, history, refs)

        return refs

    def restart(self):
        """所有需要重启的模型"""
        self._load_models()

    def hybrid_retrieval(self, query, history, meta):
        """四阶段混合检索：向量检索 -> 实体链接 -> 图检索 -> 上下文融合"""
        logger.info("开始四阶段混合检索")
        
        # 阶段1：向量检索 - 广泛的语义召回
        vector_results = self._vector_retrieval_stage(query, history, meta)
        
        # 阶段2：实体链接 - 从文本片段中提取实体
        seed_entities = self._entity_linking_stage(vector_results, query, meta)
        
        # 阶段3：图检索 - 基于种子节点的深度挖掘
        graph_results = self._graph_retrieval_stage(seed_entities, query, meta)
        
        # 阶段4：上下文融合 - 整合向量和图检索结果
        fused_context = self._context_fusion_stage(vector_results, graph_results, query)
        
        return {
            "entities": seed_entities,
            "knowledge_base": vector_results,
            "graph_base": graph_results,
            "fused_context": fused_context,
            "web_search": self.query_web(query, history, {"meta": meta})
        }

    def _vector_retrieval_stage(self, query, history, meta):
        """阶段1：向量检索 - 进行广泛的语义召回"""
        logger.debug("阶段1：向量检索")
        
        db_id = meta.get("db_id")
        if not db_id or not config.enable_knowledge_base:
            return {"results": [], "message": "知识库未启用或未指定"}
        
        # 重写查询以获得更好的语义匹配
        rw_query = self.rewrite_query(query, history, {"meta": meta})
        
        # 使用更大的top_k进行广泛召回
        top_k = meta.get("vector_top_k", 20)  # 默认20个结果
        distance_threshold = meta.get("vector_distance_threshold", 0.7)  # 更宽松的阈值
        
        query_result = self.knowledge_base.query(
            query=rw_query,
            db_id=db_id,
            distance_threshold=distance_threshold,
            rerank_threshold=meta.get("rerankThreshold", 0.1),
            max_query_count=meta.get("maxQueryCount", 20),
            top_k=top_k
        )
        
        logger.debug(f"向量检索返回 {len(query_result['results'])} 个结果")
        return query_result

    def _entity_linking_stage(self, vector_results, query, meta):
        """阶段2：实体链接 - 从文本片段中提取实体"""
        logger.debug("阶段2：实体链接")
        
        if not vector_results.get("results"):
            return []
        
        # 合并所有检索到的文本片段
        text_chunks = []
        for result in vector_results["results"]:
            if isinstance(result, dict) and "entity" in result:
                text_chunks.append(result["entity"]["text"])
        
        combined_text = "\n".join(text_chunks)
        
        # 使用实体提取器从文本中提取实体
        try:
            # 提取STIX实体 - 正确处理异步调用
            import asyncio
            import concurrent.futures
            
            # 在新的事件循环中运行异步方法
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(self.entity_extractor.extract_entities(
                        text=combined_text,
                        language="chinese"
                    ))
                )
                stix_entities = future.result()
            
            # 提取关键词实体（用于图检索）
            keywords = self._extract_keywords_from_text(combined_text, query)
            
            # 合并两种实体
            all_entities = []
            
            # 从STIX实体中提取实体名称
            for entity in stix_entities:
                if isinstance(entity, dict) and "name" in entity:
                    all_entities.append(entity["name"])
            
            # 添加关键词
            all_entities.extend(keywords)
            
            # 去重并过滤
            unique_entities = list(set([e.strip() for e in all_entities if e.strip()]))
            
            logger.debug(f"实体链接提取到 {len(unique_entities)} 个实体: {unique_entities[:5]}...")
            return unique_entities
            
        except Exception as e:
            logger.error(f"实体链接失败: {e}")
            # 回退到简单的关键词提取
            return self._extract_keywords_from_text(combined_text, query)

    def _extract_keywords_from_text(self, text, query):
        """从文本中提取关键词"""
        try:
            model_provider = config.model_provider
            model_name = config.model_name
            model = select_model(model_provider=model_provider, model_name=model_name)
            
            # 使用关键词提取模板
            keyword_prompt = keywords_template.format(text=text, query=query)
            keywords_response = model.predict(keyword_prompt).content
            
            # 解析关键词
            keywords = [kw.strip() for kw in keywords_response.split("<->") if kw.strip()]
            return keywords
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []

    def _graph_retrieval_stage(self, seed_entities, query, meta):
        """阶段3：图检索 - 基于LLM生成Cypher并执行"""
        logger.debug("阶段3：图检索 (Cypher生成)")
        
        if not seed_entities:
            return {"results": []}
        
        try:
            # 新增：让LLM根据上下文和实体生成Cypher查询
            # self.graph_base需要实现generate_cypher_query方法
            cypher_query = self.graph_base.generate_cypher_query(
                query=query,
                entities=seed_entities,
                graph_schema=self.graph_base.get_schema_str()
            )

            if not cypher_query:
                logger.warning("LLM未能生成有效的Cypher查询，图检索被跳过。")
                return {"results": []}
            
            logger.info(f"由LLM生成的Cypher查询: {cypher_query}")

            # 直接执行生成的Cypher查询
            query_results = self.graph_base.query(cypher_query)
        
        # 去重和格式化结果
            unique_results = self._deduplicate_graph_results(query_results)
        formatted_results = self.graph_base.format_query_result_to_graph(unique_results)
        
            logger.debug(f"图检索返回 {len(formatted_results)} 个格式化结果")
        return {"results": formatted_results}

        except Exception as e:
            logger.error(f"图检索阶段失败: {e}, {traceback.format_exc()}")
            return {"results": []}

    def _deduplicate_graph_results(self, results):
        """对图检索结果进行去重"""
        seen = set()
        unique_results = []
        
        for result in results:
            # 处理不同的结果格式
            if isinstance(result, (list, tuple)) and len(result) >= 3:
                result_key = (str(result[0]), str(result[2]), str(result[1]))
            elif isinstance(result, dict):
                result_key = (result.get('h'), result.get('t'), result.get('r'))
            else:
                continue
                
            if result_key not in seen:
                seen.add(result_key)
                unique_results.append(result)
        
        return unique_results

    def _context_fusion_stage(self, vector_results, graph_results, query):
        """阶段4：上下文融合 - 整合向量和图检索结果"""
        logger.debug("阶段4：上下文融合")
        
        # 构建向量检索的上下文
        vector_context = []
        if vector_results.get("results"):
            for i, result in enumerate(vector_results["results"][:10]):  # 限制前10个
                if isinstance(result, dict) and "entity" in result:
                    vector_context.append(f"[文档{i+1}] {result['entity']['text']}")
        
        # 构建图检索的上下文
        graph_context = []
        if graph_results.get("results"):
            if isinstance(graph_results["results"], dict) and graph_results["results"].get("edges"):
                for edge in graph_results["results"]["edges"][:10]:  # 限制前10个
                    graph_context.append(f"{edge['source_name']} -> {edge['target_name']}: {edge['type']}")
            elif isinstance(graph_results["results"], list):
                for i, item in enumerate(graph_results["results"][:10]):
                    if isinstance(item, dict):
                        source = item.get('source_name', '')
                        target = item.get('target_name', '')
                        rel_type = item.get('type', '')
                        if source and target and rel_type:
                            graph_context.append(f"{source} -> {target}: {rel_type}")
        
        # 融合上下文
        fused_context = {
            "vector_context": "\n".join(vector_context),
            "graph_context": "\n".join(graph_context),
            "query": query,
            "summary": f"基于查询'{query}'，检索到{len(vector_context)}个相关文档片段和{len(graph_context)}个图关系"
        }
        
        logger.debug(f"上下文融合完成: {fused_context['summary']}")
        return fused_context

    def construct_query(self, query, refs, meta):
        logger.debug(f"{refs=}")
        if not refs or len(refs) == 0:
            return query

        # 检查是否显示检索结果信息
        show_retrieval_info = meta.get("show_retrieval_info", True)  # 默认为True，总是传递检索结果
        
        if not show_retrieval_info:
            # 如果不显示检索结果信息，直接返回原始查询
            return query

        # 检查是否使用了四阶段检索
        if refs.get("fused_context"):
            return self._construct_hybrid_query(query, refs, meta)
        else:
            return self._construct_traditional_query(query, refs, meta)

    def _construct_hybrid_query(self, query, refs, meta):
        """构造四阶段检索的查询"""
        fused_context = refs.get("fused_context", {})
        external_parts = []
        
        # 添加向量检索的上下文
        vector_context = fused_context.get("vector_context", "")
        if vector_context:
            external_parts.extend(["相关文档信息:", vector_context])
        
        # 添加图检索的上下文
        graph_context = fused_context.get("graph_context", "")
        if graph_context:
            external_parts.extend(["知识图谱关系:", graph_context])
        
        # 添加网络搜索的结果
        web_res = refs.get("web_search", {}).get("results", [])
        if web_res:
            web_text = "\n".join(f"{r['title']}: {r['content']}" for r in web_res)
            external_parts.extend(["网络搜索信息:", web_text])
        
        # 构造查询
        if external_parts:
            external = "\n\n".join(external_parts)
            query = knowbase_qa_template.format(external=external, query=query)
        
        return query

    def _construct_traditional_query(self, query, refs, meta):
        """构造传统检索的查询"""
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
