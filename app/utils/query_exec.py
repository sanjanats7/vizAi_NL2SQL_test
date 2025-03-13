from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

class DatabaseQueryExecutor:
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
    
    def execute_queries(self, queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        results = []

        with self.Session() as session:
            for query_info in queries:
                query = query_info['query']
                # print(f"Executing Query:\n{query}")
                try:
                    with self.engine.connect() as conn:
                        with conn.begin():
                            result = session.execute(text(query))

                            column_names = result.keys() if hasattr(result, 'keys') else None

                            query_results = []
                            for row in result:
                                try:
                                    if column_names:
                                        row_dict = {col: row[idx] for idx, col in enumerate(column_names)}
                                    else:
                                        row_dict = {f'column_{i}': val for i, val in enumerate(row)}

                                    query_results.append(row_dict)
                                except Exception as row_error:
                                    query_results.append({
                                        'error': str(row_error),
                                        'row_data': str(row)
                                    })

                            results.append({
                                "query": query,
                                "explanation": query_info.get('explanation', 'No explanation provided'),
                                "relevance": query_info.get('relevance', 0.0),
                                "chart_type": query_info.get('chart_type', 'Not specified'),
                                "results": query_results
                            })

                except Exception as e:
                    results.append({
                        "query": query,
                        "explanation": query_info.get('explanation', 'No explanation provided'),
                        "relevance": query_info.get('relevance', 0.0),
                        "chart_type": query_info.get('chart_type', 'Not specified'),
                        "error": str(e)
                    })
        
        return results
