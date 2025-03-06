from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

class DatabaseQueryExecutor:
    def __init__(self, connection_string: str):
        """
        Initialize database connection for query execution
        
        :param connection_string: SQLAlchemy database connection string
        """
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
    
    def execute_queries(self, queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Execute multiple SQL queries and return results
        
        :param queries: List of query dictionaries with 'query' and 'explanation' keys
        :return: List of query results with query and corresponding data
        """
        results = []
        with self.Session() as session:
            for query_info in queries:
                query = query_info['query']
                try:
                    print(f"\nExecuting Query:\n{query}")
                    result = session.execute(text(query))
                    print(f"Raw result:{result}")
                    query_results = []
                    for row in result:
                      print(f"Row Object: {row}")  
                      try:
                          row_dict = dict(row)
                          query_results.append(row_dict)
                      except Exception as e:
                        print(f"Error converting row to dictionary: {e}")
                        print(f"Row Data: {row}")
                        query_results.append({"error": str(e), "row_data": str(row)})
                    results.append({
                        "query": query,
                        "results": query_results
                    })
                except Exception as e:
                  results.append({
                    "query": query,
                    "error": str(e)
                })
        
        return results