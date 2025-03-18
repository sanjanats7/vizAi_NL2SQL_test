from typing import List, Dict, Any, Optional
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
import re
from app.models.sql_models import TimeBasedQueriesUpdateRequest,TimeBasedQueriesUpdateResponse,QueryDateUpdateResponse,QueryWithId

def update_time_based_queries(
    api_key: str,
    query_request: TimeBasedQueriesUpdateRequest,
    model: str = "gemini-1.5-pro"
) -> TimeBasedQueriesUpdateResponse:
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key
    )
    
    date_update_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a SQL expert specializing in modifying date ranges in SQL queries.

            Original SQL query:
            {original_query}
            
            New date range to use:
            - Min date: {min_date}
            - Max date: {max_date}
            
            Instructions:
            1. Analyze the original query and identify ALL date filters, constraints, and comparisons
            2. If [MIN_DATE] or [MAX_DATE] placeholders exist, replace them with the actual dates
            3. If the query has actual date literals (like '2023-01-01'), update them as follows:
              - Replace the earliest/minimum dates with the new min_date
              - Replace the latest/maximum dates with the new max_date
              - Maintain appropriate relative time spans for dates in between
            4. Update any date ranges in BETWEEN clauses (e.g., BETWEEN '2023-01-01' AND '2023-12-31')
            5. Modify any date-related functions (DATE_SUB, DATE_ADD, etc.) to align with the new range
            6. For relative time expressions (e.g., INTERVAL statements), adjust them proportionally
            7. DO NOT change the query logic, table structure, columns, or any non-date-related parts
            8. Return ONLY the modified SQL query with no additional explanation
            9. Maintain the exact format and style of the original query (indentation, comments, etc.)
            10. Do not add triple backticks or other formatting around the SQL
            11. Do not add any explanations or comments unless they were in the original query
            
            The goal is to make the query work with the new date range while preserving its original analytical intent and time window relationships.
            
            Output the complete SQL query with updated date ranges.
        """),
        ("human", "Here's the SQL query that needs date range updates.")
    ])
    
    update_chain = date_update_prompt | llm
    
    updated_queries = []
    
    for query_item in query_request.queries:
        try:
            result = update_chain.invoke({
                "original_query": query_item.query,
                "min_date": query_request.min_date,
                "max_date": query_request.max_date
            })
            
            updated_query = extract_sql_from_response(result.content)
            
            updated_queries.append(
                QueryDateUpdateResponse(
                    query_id=query_item.query_id,
                    original_query=query_item.query,
                    updated_query=updated_query,
                    success=True,
                    error=None
                )
            )
            
        except Exception as e:
            updated_queries.append(
                QueryDateUpdateResponse(
                    query_id=query_item.query_id,
                    original_query=query_item.query,
                    updated_query=query_item.query,  # Return original on failure
                    success=False,
                    error=str(e)
                )
            )
    
    return TimeBasedQueriesUpdateResponse(updated_queries=updated_queries)

def extract_sql_from_response(response: str) -> str:

    sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
    if sql_match:
        return sql_match.group(1).strip()
        
    code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
        
    return response.strip()

def update_query_date_range(
    api_key: str,
    query_id: str,
    query: str,
    min_date: str,
    max_date: str,
    model: str = "gemini-1.5-pro"
) -> QueryDateUpdateResponse:
    """
    Update a single time-based SQL query with new date range.
    
    Args:
        api_key: Google API key for Gemini model
        query_id: Unique identifier for the query
        query: SQL query to update
        min_date: New minimum date in YYYY-MM-DD format
        max_date: New maximum date in YYYY-MM-DD format
        model: Model name to use (default: gemini-1.5-pro)
        
    Returns:
        QueryDateUpdateResponse with original and updated query
    """
    try:
        request = TimeBasedQueriesUpdateRequest(
            queries=[
                QueryWithId(
                    query_id=query_id,
                    query=query
                )
            ],
            min_date=min_date,
            max_date=max_date
        )
        
        response = update_time_based_queries(
            api_key=api_key,
            query_request=request,
            model=model
        )
        
        return response.updated_queries[0]
        
    except Exception as e:
        return QueryDateUpdateResponse(
            query_id=query_id,
            original_query=query,
            updated_query=query,
            success=False,
            error=str(e)
        )