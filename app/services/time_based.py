from typing import List, Dict, Any, Optional
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
import re
import json
from app.models.sql_models import TimeBasedQueriesUpdateRequest

async def update_time_based_queries(
    api_key: str,
    query_request: dict,
    model: str = "gemini-1.5-flash"
) -> dict:
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key
    )

    
    date_update_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert SQL query modifier specializing in updating time-based filters while preserving their original intent.

    Task: Modify SQL Queries with New Date Ranges
    Database Type: {db_type}
    Original SQL Query:
    {original_query}

    New Date Constraints:
    - Min Date: {min_date}
    - Max Date: {max_date}
    
    Explanation:
    {original_explanation}

    Guidelines for Query Modification:

    1. Identify all date-related conditions in the query, including:
        - Direct date comparisons (e.g., WHERE order_date = 'YYYY-MM-DD')
        - BETWEEN clauses
        - Date functions:
            - MySQL: DATE_SUB, DATE_ADD, INTERVAL, EXTRACT, UNIX_TIMESTAMP
            - PostgreSQL: AGE, DATE_TRUNC, NOW(), INTERVAL, EXTRACT, CURRENT_DATE
        - Relative date filters:
            - MySQL: Uses DATE_SUB with INTERVAL
            - PostgreSQL: Uses CURRENT_DATE with INTERVAL

    2. Preserve relative date logic:
        - Adjust base reference dates while maintaining interval logic.
        - Ensure date manipulation functions align with the specified `{db_type}`.

    3. Update static date literals:
        - Replace earliest dates with `{min_date}`.
        - Replace latest dates with `{max_date}`.
        - Ensure all date-related expressions retain their original meaning.

    4. Modify BETWEEN clauses correctly to reflect the new date range.

    5. DO NOT modify any other parts of the query:
        - Table structure, column names, joins, and logic must remain unchanged.
        - Preserve SQL syntax, formatting, and comments exactly as in the original query.
    3. Modify explanations accordingly:
        - Ensure explanations correctly reference the updated date range.
        - Maintain clarity and conciseness.
    **Expected Output Format (Strictly Follow This)**:
    ```
    ```sql
    UPDATED_SQL_QUERY_HERE
    ```
    
    ```text
    UPDATED_EXPLANATION_HERE
    ```
    ```
    Ensure that the SQL query remains valid and the explanation correctly reflects the changes made.
    
    """),
    ("human", "{original_query}\n {original_explanation}")
])
# Expected Output:
#     - Return only the updated SQL query followed by the updated explanation.
#     - Maintain indentation and code style exactly as in the input query.

    update_chain = date_update_prompt | llm
    
    updated_queries = []
    
    if isinstance(query_request, dict):
        query_request = TimeBasedQueriesUpdateRequest(**query_request)
        
    for query_item in query_request.queries:
        # query_dict = query_item.model_dump()  # Convert Pydantic model to dict
        try:
            result = update_chain.invoke({
                "original_query": query_item.query,
                "original_explanation":query_item.explanation,
                "min_date": query_request.min_date,
                "max_date": query_request.max_date,
                "db_type":  query_request.db_type

            })
            
            updated_query, updated_explanation = extract_sql_and_explanation(result.content)
            
            updated_queries.append({
                "query_id": query_item.query_id,
                "original_query": query_item.query,
                "original_explanation":query_item.explanation,
                "updated_query": updated_query,
                "updated_explanation":updated_explanation,
                "success": True,
                "error": None
            })
            
        except Exception as e:
            updated_queries.append({
                "query_id": query_item["query_id"],
                "original_query": query_item["query"],
                "updated_query": query_item["query"],  # Return original on failure
                "success": False,
                "error": str(e)
            })
    
    return {"updated_queries": updated_queries}

def extract_sql_from_response(response: str) -> str:
    sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
        
    code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
        
    return response.strip()

def extract_sql_and_explanation(response: str) -> tuple:
    sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
    explanation_match = re.search(r'```text\s*(.*?)\s*```', response, re.DOTALL)

    sql_query = sql_match.group(1).strip() if sql_match else "No valid SQL found."
    explanation = explanation_match.group(1).strip() if explanation_match else "No explanation provided."

    return sql_query, explanation



def update_query_date_range(
    api_key: str,
    query_id: str,
    query: str,
    explanation:str,
    min_date: str,
    max_date: str,
    db_type:str,
    model: str = "gemini-1.5-flash"
) -> dict:
    try:
        request = {
            "queries": [{"query_id": query_id, "query": query,"explanation":explanation}],
            "min_date": min_date,
            "max_date": max_date,
            "db_type": str(db_type)
        }
        
        response = update_time_based_queries(
            api_key=api_key,
            query_request=request,
            model=model
        )
        
        return response["updated_queries"][0]
        
    except Exception as e:
        return {
            "query_id": query_id,
            "original_query": query,
            "updated_query": query,
            "success": False,
            "error": str(e)
        }