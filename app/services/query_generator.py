import re
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import PydanticOutputParser

from app.models.sql_models import SQLQueryItem, SQLQueryResponse,QueryRequest


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
        
        self.draft_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert SQL query generator who creates insightful analytics queries tailored to specific business needs.

                Given a database schema, user role, and business domain, generate 10 high-value SQL queries that would provide meaningful insights.

                Database Schema:
                {schema}
    
                User Role: {role}
                Business Domain: {domain}
    
                Instructions:
                -{sql_syntax_instructions}
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
                    * Pie: For showing proportions of a whole***
                    * Donut: For showing proportions with a focus on a central value
                    * Scatter: For showing correlation between two variables
                - Try to use a variety of chart types across your recommendations, including Radian and Scatterplot where appropriate.

    
                {format_instructions}"""),
            ("human", "Generate SQL queries for the {role} role in the {domain} domain using the database schema provided.")
        ])
        self.draft_prompt = self.draft_prompt.partial(format_instructions=self.parser.get_format_instructions(), sql_syntax_instructions=sql_syntax_instruction)

    def clean_sql(self, sql_query: str) -> str:
        """
        Remove markdown formatting (backticks) from SQL queries.
        """
        return sql_query.replace("```sql", "").replace("```", "").strip()

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
        """
        Replace date placeholders with actual min and max dates
        """
        if not self.is_time_based_query(query):
            return query

        if not min_date or not max_date:
            return query

        refined_query = query.replace("[MIN_DATE]", f"'{min_date}'").replace("[MAX_DATE]", f"'{max_date}'")
        return refined_query

    def extract_sql_from_response(self, response: str) -> str:
        """
        Extract SQL code from an LLM response.
        """
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
            
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
            
        return response.strip()

    def generate_queries(self, role: str, domain: str , min_max_dates: List[str] = []) -> SQLQueryResponse:
        try:
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
                    refined_queries.append(SQLQueryItem(
                        question=item.question,
                        query=refined_query,
                        relevance=item.relevance,
                        is_time_based=True,
                        chart_type=item.chart_type
                    ))
                else:
                    refined_queries.append(item)
            
            return SQLQueryResponse(queries=refined_queries)
        
        except Exception as e:
            print(f"Error generating queries: {e}")
            return SQLQueryResponse(queries=[
                SQLQueryItem(
                    question="Error generating queries",
                    query=f"-- Error: {str(e)}",
                    relevance=0.0,
                    is_time_based=False,
                    chart_type="Line"
                )
            ])
    
    def get_queries_for_executor(self, role: str , domain: str , min_max_dates: List[str] = []) -> List[Dict[str, Any]]:

        response = self.generate_queries(role=role, domain=domain, min_max_dates=min_max_dates)

        return [
            {
                "query": item.query,
                "explanation": item.question,
                "relevance": item.relevance,
                "is_time_based": item.is_time_based,
                "chart_type": item.chart_type
            }
            for item in response.queries
        ]