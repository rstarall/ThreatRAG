"""
Neo4j 客户端（裸驱动）

只负责连接和 read/write 原语。
所有业务层 Cypher 写逻辑在 graph_store.py，读逻辑在 graph_search.py。
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from neo4j import GraphDatabase, Driver, Session

from ...utils.logging_config import logger


class Neo4jClient:
    """Neo4j 数据库裸客户端，只负责连接和 read/write 原语。"""

    def __init__(
        self,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: str = "neo4j",
    ) -> None:
        self.uri = uri or "bolt://localhost:7687"
        self.username = username or "neo4j"
        self.password = password or "12345678"
        self.database = database
        self.driver: Optional[Driver] = None
        self.is_connected: bool = False
        self._connect()

    def _connect(self) -> None:
        """建立连接并验证连通性。"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, auth=(self.username, self.password),
            )
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            self.is_connected = True
            logger.info(
                f"Neo4j connected at {self.uri} (database={self.database})"
            )
        except Exception as exc:
            logger.error(f"Neo4j connection failed: {exc}")
            self.is_connected = False
            raise

    def close(self) -> None:
        """关闭驱动。"""
        if self.driver:
            self.driver.close()
            self.is_connected = False
            logger.info("Neo4j connection closed")

    def _session(self) -> Session:
        if not self.is_connected:
            raise ConnectionError("Not connected to Neo4j")
        return self.driver.session(database=self.database)  # type: ignore[return-value]

    def read(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> list[Dict[str, Any]]:
        """执行只读查询。"""
        params = params or {}
        with self._session() as sess:
            result = sess.run(query, params)
            return [dict(record) for record in result]

    def write(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行写查询，返回统计信息。"""
        params = params or {}
        with self._session() as sess:
            result = sess.run(query, params)
            counters = result.consume().counters
            return {
                "nodes_created": counters.nodes_created,
                "relationships_created": counters.relationships_created,
                "nodes_deleted": counters.nodes_deleted,
                "relationships_deleted": counters.relationships_deleted,
                "properties_set": counters.properties_set,
            }


__all__ = ["Neo4jClient"]
