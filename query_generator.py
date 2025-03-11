from typing import List, Dict, Any
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field, field_validator
from langchain_core.output_parsers import PydanticOutputParser
from sqlalchemy import create_engine, text
import re

class SQLQueryItem(BaseModel):
    question: str = Field(..., description="Business question this query answers")
    query: str = Field(..., description="SQL query that answers the business question")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0")
    is_time_based: bool = Field(..., description="Whether this query analyzes time-based trends")
    
    @field_validator('relevance')
    def relevance_must_be_between_0_and_1(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Relevance must be between 0.0 and 1.0')
        return round(v, 2)

class SQLQueryResponse(BaseModel):
    queries: List[SQLQueryItem] = Field(..., description="List of generated SQL queries")

class FinanceQueryGenerator: 
    def __init__(self, schema: str, api_key: str, db_url: str,db_type:str, model: str = "gemini-1.5-pro"):
        """
        Initialize AI-powered query generator
        
        :param schema: Database schema description
        :param api_key: Google API key
        :param db_url: Database connection URL
        :param model: LLM model to use
        """
        self.schema = schema
        self.db_url = db_url
        self.db_type = db_type.lower()
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
                - Generate exactly 10 insightful queries:
                  * 5 should analyze time-based trends (monthly, quarterly, year-over-year)
                  * 5 should provide non-time-based insights (distributions, ratios, aggregations)
                - Each query should directly support decision-making for a {role} in the {domain} context
                - Use appropriate SQL techniques based on the schema structure
                - Assign a relevance score (0.0-1.0) indicating how valuable each query is for the role
                - IMPORTANT: For time-based queries, use placeholders '[MIN_DATE]' and '[MAX_DATE]' instead of actual dates.
                    These will be replaced with real dates later.
    
                {format_instructions}"""),
            ("human", "Generate SQL queries for the {role} role in the {domain} domain using the database schema provided.")
        ])
        self.draft_prompt = self.draft_prompt.partial(format_instructions=self.parser.get_format_instructions(),sql_syntax_instructions=sql_syntax_instruction )
        
        self.refine_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert SQL query modifier. You need to update a query to use specific date ranges.

                Original query:
                {original_query}
                
                Date range to use:
                Min date: {min_date}
                Max date: {max_date}
                
                Instructions:
                - Modify the query to use the provided min and max dates
                - Replace any current date functions or placeholders with actual date literals
                - Keep all other parts of the query identical
                - The query needs to return actual data, so ensure the time ranges are realistic
            """),
            ("human", "Please modify the query to use the actual date range.")
        ])

    def clean_sql(self, sql_query: str) -> str:
        """
        Remove markdown formatting (backticks) from SQL queries.
        """
        return sql_query.replace("```sql", "").replace("```", "").strip()

    def fetch_relevant_min_max_dates(self, query: str) -> tuple:
        """
        Fetch the min and max timestamps for the tables referenced in the given SQL query.
        
        :param query: The SQL query for which we need the relevant date range
        :return: Tuple (min_date, max_date) for the relevant tables
        """
        engine = create_engine(self.db_url)
        with engine.connect() as connection:
            table_names_query = text("""
                WITH tables_in_query AS (
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() 
                        AND LOCATE(TABLE_NAME, :query) > 0
                )
                SELECT 
                    GROUP_CONCAT(
                        CONCAT('SELECT MIN(', COLUMN_NAME, ') AS min_date, MAX(', COLUMN_NAME, ') AS max_date FROM ', TABLE_NAME)
                        SEPARA TOR ' UNION ALL '
                    ) AS query_string
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME IN (SELECT TABLE_NAME FROM tables_in_query)
                    AND DATA_TYPE IN ('date', 'datetime', 'timestamp', 'time');
            """)
            
            result = connection.execute(table_names_query, {"query": query})
            query_string = result.fetchone()[0]

            if not query_string:
                return None, None 

            final_result = connection.execute(text(query_string)).fetchall()

            min_date = min(row.min_date for row in final_result if row.min_date is not None)
            max_date = max(row.max_date for row in final_result if row.max_date is not None)
            print(f"Fetched min_date: {min_date}, max_date: {max_date} for query: {query}")

            return min_date, max_date

    def is_time_based_query(self, query: str) -> bool:
        """
        Determine if a query is time-based by looking for date functions and operations.
        
        :param query: The SQL query to analyze
        :return: True if the query appears to be time-based
        """
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

    def refine_time_based_query(self, query: str) -> str:
        """
        Replace [MIN_DATE] and [MAX_DATE] placeholders with actual date values.
        """
        if not self.is_time_based_query(query):
            return query

        try:
            min_date, max_date = self.fetch_relevant_min_max_dates(query)

            if not min_date or not max_date:
                print(f"Warning: No valid date range found for query:\n{query}")
                return query  

            refined_query = query.replace("[MIN_DATE]", f"{min_date}").replace("[MAX_DATE]", f"{max_date}")

            # print(f"Refined Query:\n{refined_query}") 

            return refined_query

        except Exception as e:
            print(f"Error refining query: {e}")
            return query
    
    def extract_sql_from_response(self, response: str) -> str:
        """
        Extract SQL code from an LLM response.
        
        :param response: LLM response text
        :return: Extracted SQL or None
        """
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
            
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
            
        return response.strip()

    def generate_queries(self, role: str="Finance Manager", domain: str = "finance") -> SQLQueryResponse:
        """
        Generate SQL queries tailored to a specific role and domain
        
        :param role: User role (e.g., "Finance Manager", "CFO", "Financial Analyst")
        :param domain: Business domain (e.g., "finance", "retail", "healthcare")
        :return: Structured response with generated SQL queries
        """
        try:
            draft_chain = self.draft_prompt | self.llm | self.parser
            draft_result = draft_chain.invoke({
                "schema": self.schema,
                "role": role,
                "domain": domain
            })
            
            refined_queries = []
            for item in draft_result.queries:
                if item.is_time_based:
                    refined_query = self.refine_time_based_query(item.query)
                    refined_queries.append(SQLQueryItem(
                        question=item.question,
                        query=refined_query,
                        relevance=item.relevance,
                        is_time_based=True
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
                    is_time_based=False
                )
            ])
    
    def get_queries_for_executor(self, role: str="Finance Manager", domain: str="finance") -> List[Dict[str, str]]:
        """
        Get a list of queries formatted for execution
        
        :param role: User role
        :param domain: Business domain
        :return: List of formatted query dictionaries
        """
        response = self.generate_queries(role=role, domain=domain)

        return [
            {
                "query": item.query,
                "explanation": item.question,
                "relevance": item.relevance,
                "is_time_based": item.is_time_based
            }
            for item in response.queries
        ]