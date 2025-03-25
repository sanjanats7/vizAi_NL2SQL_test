import re
import logging
import traceback
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import PydanticOutputParser

from app.models.sql_models import SQLQueryItem, SQLQueryResponse, QueryRequest

logger = logging.getLogger("query_generator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
class QueryGenerator: 
    def __init__(self, schema: str, api_key: str, db_type: str, model: str = "gemini-1.5-pro"):
        self.schema = schema
        self.db_type = db_type.lower()
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model=model, 
            google_api_key=api_key
        )
        self.parser = PydanticOutputParser(pydantic_object=SQLQueryResponse)
        
        sql_syntax_instruction = {
            "mysql": "Write queries ONLY using syntax compatible with MySQL database.",
            "postgres": "Write queries ONLY using syntax compatible with PostgreSQL database.",
            "sqlite": "Write queries ONLY using syntax compatible with SQLite database."
        }.get(self.db_type, "Write queries using standard SQL syntax.")
        
        logger.info(f"Initialized QueryGenerator | DB Type: {self.db_type}")

        self.draft_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert SQL query generator specialising in creating high value, schema restricted SQL queries tailored to specific business needs.

                Your Task
                - Given a database schema, user role, and business domain, generate exactly 30 SQL queries for analytics.
                - STRICT RULE: Only use tables and columns from the provided schema. Do not reference any table or field not explicitly listed.
                - Each query should directly support decision-making for a {role} in the {domain} domain.
                
                Database Schema(Strictly enforced):
                {schema}
    
                User Role: {role}
                Business Domain: {domain}
    
                Instructions:
                - {sql_syntax_instruction}
                - Carefully analyze the schema to identify relevant tables and relationships for the given domain
                - Generate exactly 30 insightful UNIQUE queries:
                  * 15 should analyze time-based trends (monthly, quarterly, year-over-year)
                  * 15 should provide non-time-based insights (distributions, ratios, aggregations)
                - Each query should directly support decision-making for a {role} in the {domain} context
                - Use appropriate SQL techniques based on the schema structure
                - Assign a relevance score (0.0-1.0) indicating how valuable each query is for the role
                - IMPORTANT: For time-based queries, use placeholders '[MIN_DATE]' and '[MAX_DATE]' instead of actual dates.
                    These will be replaced with real dates later.
                - For each query, recommend ONE of the following chart types that would best visualize the results:
                    * Bar: For comparing values across categories
                    * Line: For showing trends over time or continuous data
                    * Area: For emphasizing the magnitude of trends over time
                    * Pie: For showing proportions of a whole
                    * Donut: For showing proportions with a focus on a central value
                    * Scatter: For showing correlation between two variables
                - Try to use a variety of chart types across your recommendations, including Radian and Scatterplot where appropriate.
    
                {format_instructions}"""),
            ("human", "Generate SQL queries for the {role} role in the {domain} domain using the database schema provided.")
        ])
        self.draft_prompt = self.draft_prompt.partial(format_instructions=self.parser.get_format_instructions(), sql_syntax_instruction=sql_syntax_instruction)

    def clean_sql(self, sql_query: str) -> str:
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        sql_query = sql_query.replace("''", "'")  # Fix double quotes
        return sql_query
    

    def is_time_based_query(self, query: str) -> bool:

        time_patterns = [
            r'DATE_FORMAT', r'YEAR\s*\(', r'MONTH\s*\(', r'DAY\s*\(', 
            r'QUARTER\s*\(', r'WEEK\s*\(', r'DATE_SUB', r'DATE_ADD',
            r'DATE_DIFF', r'BETWEEN.*AND', r'>\s*\d{4}-\d{2}-\d{2}',
            r'<\s*\d{4}-\d{2}-\d{2}', r'GROUP BY.*year', r'GROUP BY.*month',
            r'GROUP BY.*quarter', r'GROUP BY.*date', r'\[MIN_DATE\]', r'\[MAX_DATE\]'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def refine_time_based_query(self, query: str, min_date: str, max_date: str) -> str:

        if not self.is_time_based_query(query):
            return query

        if not min_date or not max_date:
            return query

        query = query.replace("[MIN_DATE]", min_date).replace("[MAX_DATE]", max_date)
        
        query = query.replace("''", "'")
        logger.info(f"Refined Time-Based Query: {query}")

        print(query)

        return query

    def extract_sql_from_response(self, response: str) -> str:
        """
        Extract SQL query from a response that might contain markdown formatting.
        """
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
            
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
            
        return response.strip()

    def generate_queries(self, role: str, domain: str, min_max_dates: List[str] = []) -> SQLQueryResponse:
        try:
            logger.info(f"Generating Queries | Role: {role} | Domain: {domain}")
            logger.debug(f"Schema (truncated): {self.schema[:500]}...")  # Log first 500 chars of schema
            draft_chain = self.draft_prompt | self.llm | self.parser
            draft_result = draft_chain.invoke({
                "schema": self.schema,
                "role": role,
                "domain": domain
            })
            
            refined_queries = []
            min_date = max_date = None
            
            if len(min_max_dates) == 2:
                min_date, max_date = min_max_dates[0], min_max_dates[1]
            
            for item in draft_result.queries:
                if item.is_time_based and min_date and max_date:
                    refined_query = self.refine_time_based_query(item.query, min_date, max_date)
                    refined_explanation = self.refine_time_based_query(item.question,min_date,max_date)
                    refined_queries.append(SQLQueryItem(
                        question=refined_explanation,
                        query=refined_query,
                        relevance=item.relevance,
                        is_time_based=True,
                        chart_type=item.chart_type
                    ))
                else:
                    refined_queries.append(item)
                    
            logger.info(f"Generated {len(refined_queries)} SQL Queries Successfully.")
            return SQLQueryResponse(queries=refined_queries)
        
        except Exception as e:
            logger.error(f"Error generating queries: {str(e)}\n{traceback.format_exc()}")
            return SQLQueryResponse(queries=[
                SQLQueryItem(
                    question="Error generating queries",
                    query=f"-- Error: {str(e)}",
                    relevance=0.0,
                    is_time_based=False,
                    chart_type="Line"
                )
            ])
    
    def get_queries_for_executor(self, role: str, domain: str, min_max_dates: List[str] = []) -> List[Dict[str, Any]]:
        response = self.generate_queries(role=role, domain=domain, min_max_dates=min_max_dates)

        queries_list = [
            {
                "query": item.query,
                "explanation": item.question,
                "relevance": item.relevance,
                "is_time_based": item.is_time_based,
                "chart_type": item.chart_type
            }
            for item in response.queries
        ]
        logger.info(f"Returning {len(queries_list)} Queries for Execution.")
        return queries_list