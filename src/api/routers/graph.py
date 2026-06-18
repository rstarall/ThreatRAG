"""
知识图谱API路由
重构rag/api/routers/graph_api.py
"""

from fastapi import APIRouter, Body, HTTPException, Query
from typing import Optional, List, Dict, Any

from ...services.graph_service import GraphService


# 创建路由
graph_router = APIRouter(prefix="/graph", tags=["graph"])

# 初始化图谱服务
graph_service = GraphService()


@graph_router.get("/")
async def get_graph_info():
    """获取图数据库信息"""
    try:
        result = graph_service.get_graph_info()
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("message", "图数据库获取出错"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图数据库信息失败: {str(e)}")


@graph_router.get("/node")
async def get_graph_node(entity_name: str = Query(..., description="实体名称")):
    """获取图节点信息"""
    try:
        result = graph_service.get_graph_node(entity_name)
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图节点失败: {str(e)}")


@graph_router.get("/nodes")
async def get_graph_nodes(num: int = Query(50, description="节点数量限制")):
    """获取图节点列表"""
    try:
        result = graph_service.get_graph_nodes(num)
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图节点列表失败: {str(e)}")


@graph_router.get("/stats")
async def get_graph_stats():
    """获取图数据库统计信息"""
    try:
        # 复用get_graph_info的逻辑
        result = graph_service.get_graph_info()
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("message"))
        
        # 提取统计信息
        stats = {
            "node_count": result.get("node_count", 0),
            "relationship_count": result.get("relationship_count", 0),
            "label_counts": result.get("label_counts", {}),
            "status": result.get("status", "unknown")
        }
        
        return {"status": "success", "stats": stats}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取图统计信息失败: {str(e)}")


@graph_router.post("/query")
async def query_graph(
    entities: List[str] = Body(..., description="实体列表")
):
    """查询图谱实体"""
    try:
        if not entities:
            raise HTTPException(status_code=400, detail="实体列表不能为空")
        
        # 查询每个实体
        all_results = {"nodes": [], "edges": []}
        
        for entity in entities:
            result = graph_service.get_graph_node(entity)
            
            if result.get("status") == "success":
                # 合并结果
                entity_data = result
                if "nodes" in entity_data:
                    all_results["nodes"].extend(entity_data["nodes"])
                if "edges" in entity_data:
                    all_results["edges"].extend(entity_data["edges"])
        
        # 去重处理（简单去重，基于ID）
        seen_nodes = set()
        seen_edges = set()
        
        unique_nodes = []
        for node in all_results["nodes"]:
            if node["id"] not in seen_nodes:
                unique_nodes.append(node)
                seen_nodes.add(node["id"])
        
        unique_edges = []
        for edge in all_results["edges"]:
            edge_key = f"{edge['source']}-{edge['target']}-{edge['type']}"
            if edge_key not in seen_edges:
                unique_edges.append(edge)
                seen_edges.add(edge_key)
        
        return {
            "status": "success",
            "nodes": unique_nodes,
            "edges": unique_edges,
            "stats": {
                "node_count": len(unique_nodes),
                "edge_count": len(unique_edges)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图谱查询失败: {str(e)}")


@graph_router.post("/extract")
async def extract_entities(
    text: str = Body(..., description="输入情报文本"),
    source: Optional[str] = Body(None, description="文本来源"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="额外元数据")
):
    """同步抽取实体关系（直接返回抽取结果，不存储到图数据库）"""
    try:
        result = graph_service.extract_entities(text=text, source=source, metadata=metadata)
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("message", "实体抽取失败"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"实体抽取失败: {str(e)}")


@graph_router.post("/extract-and-save", status_code=202)
async def extract_and_save(
    text: str = Body(..., description="输入情报文本"),
    source: Optional[str] = Body(None, description="文本来源"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="额外元数据")
):
    """异步抽取实体关系并存储到图数据库（仅提交后台任务，不等待执行完成）"""
    try:
        result = graph_service.submit_extract_and_save(text=text, source=source, metadata=metadata)
        
        if result.get("status") == "failed":
            raise HTTPException(status_code=500, detail=result.get("message", "抽取并存储失败"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"抽取并存储失败: {str(e)}")


__all__ = ["graph_router"]
