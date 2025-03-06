import traceback
from pprint import pprint
from config import (
    CONNECTION_STRING, 
    GOOGLE_API_KEY, 
    LLM_MODEL, 
    DEFAULT_NUM_QUERIES
)
from db_extract import DatabaseSchemaExtractor
from query_generator import FinanceQueryGenerator
from query_exec import DatabaseQueryExecutor

def main():
    try:
        
        schema_extractor = DatabaseSchemaExtractor(CONNECTION_STRING)
        schema = schema_extractor.get_schema()
        print("Schema extracted successfully")
        
        query_generator = FinanceQueryGenerator(
            schema=schema,
            api_key=GOOGLE_API_KEY,
            model=LLM_MODEL
        )
        finance_queries = query_generator.generate_finance_queries(
            num_queries=DEFAULT_NUM_QUERIES
        )
        print(f"Generated {len(finance_queries)} finance queries")
        
        query_executor = DatabaseQueryExecutor(CONNECTION_STRING)
        query_results = query_executor.execute_queries(finance_queries)
        
        print("=== Finance Manager Query Analysis ===")
        for i, result in enumerate(query_results, 1):
            print(f"\n--- Query {i} ---")
            print(f"SQL Query:\n{result['query']}")
            print(f"\nExplanation:\n{result.get('explanation', 'No explanation provided')}")
            
            if 'results' in result:
                print("\n--- Results ---")
                pprint(result['results'])  
            elif 'error' in result:
                print(f"\n--- Error ---\n{result['error']}")
            
            print("-" * 50)
    
    except Exception as e:
        print(f"An error occurred: {e}")
        print(traceback.format_exc())  

if __name__ == "__main__":
    main()