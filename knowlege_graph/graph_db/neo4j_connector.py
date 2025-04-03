# neo4j connector

from neo4j import GraphDatabase

class Neo4jConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_knowledge_graph(self):
        pass

    def add_node(self, node_type, node_id, node_properties):
        pass

    def add_edge(self, edge_type, source_id, target_id, edge_properties):
        pass
    
    
