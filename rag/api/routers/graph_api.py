import os
import asyncio
import json
import traceback
from typing import List, Optional, Dict, Any, Union, Literal
from fastapi import APIRouter, Body, HTTPException, File, UploadFile, Form

from packages.utils import logger, hashstr
from packages import config
from packages import executor, retriever, knowledge_base, graph_base
from packages.core.graph_indexer import graph_indexer
from packages.core.kb_entity_service import kb_entity_service
from packages.core.entity_extractor import entity_extractor
from packages.core.constant import STIX_ENTITY_TYPES


graph = APIRouter(prefix="/graph")




@graph.post("/start-indexer")
async def start_graph_indexer(interval: Optional[int] = Body(3600), 
                             batch_size: Optional[int] = Body(100),
                             kgdb_name: Optional[str] = Body("neo4j")):
    """启动图数据库索引器"""
    if not config.enable_knowledge_graph:
        return {"message": "知识图谱未启用", "status": "failed"}
    
    if not graph_base.is_running():
        return {"message": "图数据库未启动", "status": "failed"}
    
    # 更新索引器配置
    graph_indexer.interval = interval
    graph_indexer.batch_size = batch_size
    graph_indexer.kgdb_name = kgdb_name
    
    # 启动索引器
    success = graph_indexer.start()
    if success:
        return {"message": f"图数据库索引器已启动，扫描间隔: {interval}秒", "status": "success"}
    else:
        return {"message": "图数据库索引器启动失败", "status": "failed"}

@graph.post("/stop-indexer")
async def stop_graph_indexer():
    """停止图数据库索引器"""
    graph_indexer.stop()
    return {"message": "图数据库索引器已停止", "status": "success"}

@graph.get("/indexer-status")
async def get_graph_indexer_status():
    """获取图数据库索引器状态"""
    return graph_indexer.get_status()

@graph.post("/run-indexer-now")
async def run_graph_indexer_now(batch_size: Optional[int] = Body(None), 
                               kgdb_name: Optional[str] = Body(None)):
    """立即运行一次索引"""
    if not config.enable_knowledge_graph:
        return {"message": "知识图谱未启用", "status": "failed"}
    
    if not graph_base.is_running():
        return {"message": "图数据库未启动", "status": "failed"}
    
    # 临时更新批处理大小和数据库名称（如果提供）
    original_batch_size = graph_indexer.batch_size
    original_kgdb_name = graph_indexer.kgdb_name
    
    if batch_size is not None:
        graph_indexer.batch_size = batch_size
    if kgdb_name is not None:
        graph_indexer.kgdb_name = kgdb_name
    
    try:
        # 运行索引
        indexed_count = graph_indexer._index_nodes()
        return {
            "message": f"索引完成，共为 {indexed_count} 个节点添加了嵌入向量", 
            "status": "success",
            "indexed_count": indexed_count
        }
    finally:
        # 恢复原始配置
        graph_indexer.batch_size = original_batch_size
        graph_indexer.kgdb_name = original_kgdb_name


@graph.get("/info")
async def get_graph_info():
    graph_info = graph_base.get_graph_info()
    if graph_info is None:
        raise HTTPException(status_code=400, detail="图数据库获取出错")
    return graph_info

@graph.post("/index-nodes")
async def index_nodes(data: dict = Body(default={})):
    if not graph_base.is_running():
        raise HTTPException(status_code=400, detail="图数据库未启动")

    # 获取参数或使用默认值
    kgdb_name = data.get('kgdb_name', 'neo4j')

    # 调用GraphDatabase的add_embedding_to_nodes方法
    count = graph_base.add_embedding_to_nodes(kgdb_name=kgdb_name)

    return {"status": "success", "message": f"已成功为{count}个节点添加嵌入向量", "indexed_count": count}

@graph.get("/node")
async def get_graph_node(entity_name: str):
    result = graph_base.query_node(entity_name=entity_name)
    return {"result": graph_base.format_query_result_to_graph(result), "message": "success"}

@graph.get("/nodes")
async def get_graph_nodes(kgdb_name: str, num: int):
    if not config.enable_knowledge_graph:
        raise HTTPException(status_code=400, detail="Knowledge graph is not enabled")

    logger.debug(f"Get graph nodes in {kgdb_name} with {num} nodes")
    result = graph_base.get_sample_nodes(kgdb_name, num)
    return {"result": graph_base.format_general_results(result), "message": "success"}

@graph.post("/add-by-jsonl")
async def add_graph_entity(file_path: str = Body(...), kgdb_name: Optional[str] = Body(None)):
    if not config.enable_knowledge_graph:
        return {"message": "知识图谱未启用", "status": "failed"}

    if not file_path.endswith('.jsonl'):
        return {"message": "文件格式错误，请上传jsonl文件", "status": "failed"}

    try:
        await graph_base.jsonl_file_add_entity(file_path, kgdb_name)
        return {"message": "实体添加成功", "status": "success"}
    except Exception as e:
        logger.error(f"添加实体失败: {e}, {traceback.format_exc()}")
        return {"message": f"添加实体失败: {e}", "status": "failed"}

@graph.post("/extract-entities-from-file")
async def extract_entities_from_file(
    file: UploadFile = File(...),
    language: str = Form("chinese"),
    entity_types: Optional[str] = Form(None),  # 逗号分隔或JSON数组字符串，为空则提取所有STIX类型
    kgdb_name: str = Form("neo4j")
):
    """接收前端上传的文件，分块-实体提取-保存到Neo4j的流水线接口"""
    try:
        # 1) 保存临时文件
        basename, ext = os.path.splitext(file.filename or "uploaded.txt")
        tmp_dir = os.path.join(config.save_dir, "data", "tmp_uploads")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, f"{basename}{ext}")
        with open(tmp_path, "wb") as f_out:
            f_out.write(await file.read())

        # 2) 分块（复用知识库的分块逻辑，但不入库）
        chunks_info = knowledge_base.file_to_chunk([tmp_path])
        # 取第一项
        first_key = next(iter(chunks_info.keys()))
        nodes = chunks_info[first_key]["nodes"]
        combined_text = " ".join([n["text"] for n in nodes]).strip()

        # 3) 解析实体类型参数
        types_list: Optional[List[str]] = None
        if entity_types and entity_types.strip():
            try:
                # 兼容JSON数组字符串
                parsed = json.loads(entity_types)
                if isinstance(parsed, list):
                    types_list = [str(t) for t in parsed]
            except Exception:
                # 兼容逗号分隔
                types_list = [t.strip() for t in entity_types.split(",") if t.strip()]
        
        # 如果没有指定实体类型，使用所有可用的STIX实体类型
        if not types_list:
            types_list = list(STIX_ENTITY_TYPES.keys())

        # 4) 实体提取
        extract_res = await entity_extractor.extract_entities(
            text=combined_text,
            language=language,
            entity_types=types_list
        )
        if extract_res.get("status") != "success":
            return {"message": extract_res.get("message", "实体提取失败"), "status": "failed"}

        entities = extract_res.get("entities", [])
        relationships = extract_res.get("relationships", [])

        # 5) 保存到Neo4j
        if not config.enable_knowledge_graph:
            return {"message": "知识图谱未启用", "status": "failed"}
        if not graph_base.is_running():
            return {"message": "图数据库未启动，无法保存实体", "status": "failed"}

        await graph_base.add_entities_and_relationships(
            entities=entities,
            relationships=relationships,
            kgdb_name=kgdb_name
        )

        # 6) 清理临时文件
        try:
            os.remove(tmp_path)
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"实体提取完成并保存到Neo4j ({kgdb_name})",
            "entities_count": len(entities),
            "relationships_count": len(relationships)
        }
    except Exception as e:
        logger.error(f"实体提取失败: {e}, {traceback.format_exc()}")
        return {"message": f"实体提取失败: {e}", "status": "failed"}