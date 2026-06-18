"""
图谱业务服务
整合rag/service/graph_service.py的业务逻辑
包含实体关系抽取、知识图谱存储等核心功能
查询功能委托给 GraphSearcher，存储功能使用 GraphStore。
"""

import traceback
import uuid
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor

from ..core.graph.graph_store import GraphStore
from ..core.graph.graph_search import GraphSearcher
from ..core.graph.graph_extract import (
    GraphExtractor, ExtractionResult,
    extract_graph_from_text, get_graph_extractor,
)
from ..utils.logging_config import logger
from ..config import config
from ..models.graph_model import KnowledgeGraph


class GraphService:
    """图谱业务服务类"""

    def __init__(self):
        """初始化图谱服务"""
        self.graph_store = GraphStore()
        self.graph_searcher = GraphSearcher(
            self.graph_store if self.graph_store.is_running() else None
        )
        self._extractor: Optional[GraphExtractor] = None
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="graph_task_")

    @property
    def extractor(self) -> GraphExtractor:
        """获取抽取器实例"""
        if self._extractor is None:
            self._extractor = GraphExtractor()
        return self._extractor

    def get_graph_info(self) -> Dict[str, Any]:
        """获取图数据库信息

        Returns:
            Dict[str, Any]: 图数据库信息
        """
        try:
            graph_info = self.graph_searcher.get_stats()

            if "error" in graph_info or graph_info.get("status") == "error":
                return {"message": "图数据库获取出错", "status": "failed", **graph_info}

            return {"status": "success", **graph_info}

        except Exception as e:
            logger.error(f"获取图数据库信息失败: {e}\n{traceback.format_exc()}")
            return {"message": f"获取图数据库信息失败: {e}", "status": "failed"}

    def get_graph_node(self, entity_name: str) -> Dict[str, Any]:
        """获取图节点信息

        Args:
            entity_name: 实体名称

        Returns:
            Dict[str, Any]: 节点信息
        """
        if not self.graph_searcher.is_running:
            return {"message": "图数据库未启动", "status": "failed"}

        try:
            subgraph = self.graph_searcher.query_node(entity_name)

            if subgraph.entities:
                nodes = []
                for e in subgraph.entities:
                    nodes.append({
                        "id": e.entity_id,
                        "name": e.entity_name,
                        "label": e.entity_type,
                        "labels": [e.entity_type],
                        "properties": e.properties,
                    })
                edges = []
                for r in subgraph.relationships:
                    edges.append({
                        "id": r.relationship_id,
                        "source": r.source,
                        "target": r.target,
                        "source_name": r.source,
                        "target_name": r.target,
                        "type": r.relationship_type,
                        "properties": {},
                    })
                return {
                    "status": "success",
                    "nodes": nodes,
                    "edges": edges,
                    "stats": {
                        "node_count": len(nodes),
                        "edge_count": len(edges)
                    }
                }
            else:
                return {"status": "success", "nodes": [], "edges": [], "message": "未找到相关节点"}

        except Exception as e:
            logger.error(f"获取图节点失败: {e}\n{traceback.format_exc()}")
            return {"message": f"获取图节点失败: {e}", "status": "failed"}

    def get_graph_nodes(self, num: int = 50) -> Dict[str, Any]:
        """获取图节点列表

        Args:
            num: 节点数量限制

        Returns:
            Dict[str, Any]: 节点列表
        """
        if not self.graph_searcher.is_running:
            return {"message": "图数据库未启动", "status": "failed"}

        try:
            return self.graph_searcher.get_graph_nodes(num)

        except Exception as e:
            logger.error(f"获取图节点列表失败: {e}\n{traceback.format_exc()}")
            return {"message": f"获取图节点列表失败: {e}", "status": "failed"}

    def _generate_task_id(self) -> str:
        """生成任务 ID

        Returns:
            str: 任务 ID
        """
        return f"task_{uuid.uuid4().hex[:8]}"

    def _save_extraction_to_graph(self, result: ExtractionResult) -> bool:
        """将抽取结果保存到图数据库

        Args:
            result: 抽取结果（内含 Entity / Relationship 列表）

        Returns:
            bool: 是否成功
        """
        if not result.success or not result.entities:
            return False

        try:
            kg = KnowledgeGraph(
                entities=result.entities,
                relationships=result.relationships,
            )
            stats = self.graph_store.save_knowledge_graph(kg)
            logger.info(f"Saved knowledge graph to Neo4j: {stats}")
            return True

        except Exception as exc:
            logger.error(f"Failed to save extraction to graph: {exc}")
            return False

    def extract_entities(self, text: str, source: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """同步抽取实体关系（直接返回结果）

        服务层创建 task_id 并传入底层。

        Args:
            text: 输入情报文本
            source: 文本来源
            metadata: 额外元数据

        Returns:
            Dict[str, Any]: 抽取结果
        """
        task_id = self._generate_task_id()

        try:
            result = extract_graph_from_text(
                text=text,
                task_id=task_id,
                source=source,
                metadata=metadata,
            )

            if result.success:
                response = {
                    "status": "success",
                    "task_id": result.task_id,
                    "entity_count": len(result.entities),
                    "relationship_count": len(result.relationships),
                    "entities": [e.to_dict() for e in result.entities],
                    "relationships": [r.to_dict() for r in result.relationships],
                    "raw_xml": result.raw_xml,
                    "processing_time_ms": result.processing_time_ms,
                    "errors": result.errors,
                }
            else:
                response = {
                    "status": "failed",
                    "task_id": result.task_id,
                    "errors": result.errors,
                }

            return response

        except Exception as e:
            logger.error(f"实体关系抽取失败: {e}\n{traceback.format_exc()}")
            return {"message": f"实体关系抽取失败: {e}", "status": "failed"}

    def extract_entities_async(self, text: str, source: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None,
                             callback: Optional[Callable[[Dict[str, Any]], None]] = None,
                             save_to_graph: bool = False) -> str:
        """异步抽取实体关系（后台线程运行，立即返回任务 ID）

        任务在后台线程中运行，完成后执行回调（可选）。
        可选地自动将结果保存到图数据库。

        Args:
            text: 输入情报文本
            source: 文本来源
            metadata: 额外元数据
            callback: 完成回调函数 (result: Dict)
            save_to_graph: 是否自动保存到图数据库

        Returns:
            str: 任务 ID
        """
        task_id = self._generate_task_id()

        def run_extraction():
            result = self.extractor.extract(
                text=text,
                task_id=task_id,
                source=source,
                metadata=metadata,
            )

            response = {
                "task_id": task_id,
                "success": result.success,
            }

            if result.success:
                response.update({
                    "entity_count": len(result.entities),
                    "relationship_count": len(result.relationships),
                    "entities": [e.to_dict() for e in result.entities],
                    "relationships": [r.to_dict() for r in result.relationships],
                    "raw_xml": result.raw_xml,
                    "processing_time_ms": result.processing_time_ms,
                    "errors": result.errors,
                })
                if save_to_graph and self.graph_store.is_running():
                    self._save_extraction_to_graph(result)
            else:
                response["errors"] = result.errors

            if callback:
                try:
                    callback(response)
                except Exception as cb_err:
                    logger.error(f"Callback error: {cb_err}")

            logger.info(f"[{task_id}] Async extraction completed")
            return response

        self._executor.submit(run_extraction)
        logger.info(f"[{task_id}] Extraction task submitted (async)")
        return task_id

    def submit_extract_and_save(
        self,
        text: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """提交“先抽取后存储”的后台任务，并立即返回任务接收结果。"""
        task_id = self._generate_task_id()

        def run_extract_and_save():
            try:
                result = self.extractor.extract(
                    text=text,
                    task_id=task_id,
                    source=source,
                    metadata=metadata,
                )

                if not result.success:
                    logger.error(f"[{task_id}] 实体抽取失败: {result.errors}")
                    return

                if not self.graph_store.is_running():
                    logger.warning(f"[{task_id}] 图数据库未启动，跳过存储")
                    return

                saved = self._save_extraction_to_graph(result)
                if not saved:
                    logger.error(f"[{task_id}] 抽取完成但存储失败")
                else:
                    logger.info(f"[{task_id}] 抽取并存储完成")

            except Exception as exc:
                logger.error(f"[{task_id}] 后台抽取并存储失败: {exc}\n{traceback.format_exc()}")

        try:
            self._executor.submit(run_extract_and_save)
        except Exception as exc:
            logger.error(f"[{task_id}] 提交后台任务失败: {exc}\n{traceback.format_exc()}")
            return {
                "status": "failed",
                "task_id": task_id,
                "message": f"任务提交失败: {exc}",
            }

        return {
            "status": "success",
            "task_id": task_id,
            "message": "任务已接收，正在后台执行抽取并存储",
        }

    def shutdown(self):
        """关闭服务，清理资源"""
        if self._executor:
            self._executor.shutdown(wait=True)
        logger.info("GraphService shutdown")


_graph_service: Optional[GraphService] = None


def get_graph_service() -> GraphService:
    """获取全局图谱服务实例

    Returns:
        GraphService: 图谱服务实例
    """
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service


__all__ = ["GraphService", "get_graph_service"]
