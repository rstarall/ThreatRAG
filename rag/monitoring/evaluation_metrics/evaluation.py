import pandas as pd

class EvaluationMetrics:
    def __init__(self):
        pass

    def evaluate(self, query, response):
        pass

    # 测试脚本示例：对比纯文本RAG vs 知识图谱增强RAG
    def run_evaluation_comparison(self, test_queries, mode='text_only'):
        results = []
        for query in test_queries:
            if mode == 'text_only':
                context = text_retriever(query)
            else:
                context = graph_enhanced_retriever(query)
                
            report = generator(query, context)
            results.append(calculate_metrics(report))
        return pd.DataFrame(results)

    def run_all_metrics(self, params: dict):
        # 执行对比测试
        baseline_df = self.run_evaluation_comparison(params['test_queries'], 'text_only')
        enhanced_df = self.run_evaluation_comparison(params['test_queries'], 'graph_enhanced')


