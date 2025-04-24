#向量检索

class VectorRetriever:
    def __init__(self,vector_database:any):
        self.vector_database = vector_database

    def retrieve(self, query: str) -> list[str]:
        pass

