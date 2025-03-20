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
    chart_type: str= Field(..., desctiption="Recommeneded chart type for visualisation of query")
    
    @field_validator('relevance')
    def relevance_must_be_between_0_and_1(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Relevance must be between 0.0 and 1.0')
        return round(v, 2)
    @field_validator('chart_type')
    def chart_type_must_be_valid(cls, v):
        valid_chart_types = ["Bar", "Line", "Area", "Pie", "Donut", "Radian", "Scatterplot"]
        if v not in valid_chart_types:
            raise ValueError(f'Chart type must be one of: {", ".join(valid_chart_types)}')
        return v

class SQLQueryResponse(BaseModel):
    queries: List[SQLQueryItem] = Field(..., description="List of generated SQL queries")

class QueryGenerator: 
    def __init__(self, schema: str, api_key: str, db_url: str,db_type:str, model: str = "gemini-1.5-pro"):
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

                Given a database schema, user role, and business domain, generate 30 high-value SQL queries that would provide meaningful insights.

                Database Schema:
                {schema}
    
                User Role: {role}
                Business Domain: {domain}
    
                Instructions:
                -{sql_syntax_instructions}
                - Carefully analyze the schema to identify relevant tables and relationships for the given domain
                - Generate exactly 30 insightful queries:
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
                    * Radian: For visualizing circular relationships or cyclical data
                    * Scatterplot: For showing correlation between two variables
                - Try to use a variety of chart types across your recommendations, including Radian and Scatterplot where appropriate.

    
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
        default_min_date = "2020-01-01"
        default_max_date = "2023-12-31"

        try:
            engine = create_engine(self.db_url)
            table_names_query = None
            with engine.connect() as connection:
                if self.db_type == "mysql":
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
                                SEPARATOR ' UNION ALL '
                            ) AS query_string
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_NAME IN (SELECT TABLE_NAME FROM tables_in_query)
                            AND DATA_TYPE IN ('date', 'datetime', 'timestamp', 'time');
                    """)

                elif self.db_type == "postgres":
                    table_names_query = text("""
                        WITH tables_in_query AS (
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_catalog = current_database() 
                                AND POSITION(table_name IN :query) > 0
                        )
                        SELECT 
                            STRING_AGG(
                                'SELECT MIN(' || column_name || ') AS min_date, MAX(' || column_name || ') AS max_date FROM ' || table_name, 
                                ' UNION ALL '
                            ) AS query_string
                        FROM information_schema.columns
                        WHERE table_name IN (SELECT table_name FROM tables_in_query)
                            AND data_type IN ('date', 'timestamp');
                    """)

                elif self.db_type == "sqlite":
                    table_names_query = text("""
                        SELECT name AS table_name 
                        FROM sqlite_master 
                        WHERE type='table' AND name LIKE :query;
                    """)

                if table_names_query is None:
                    print(f"Using default date range for unsupported db_type: {self.db_type}")
                    return default_min_date, default_max_date

                result = connection.execute(table_names_query, {"query": query})
                row = result.fetchone()

                if not row or not row[0]:
                    print(f"No date columns found in tables for query. Using default date range.")
                    return default_min_date, default_max_date

                query_string = row[0]

                try:
                    final_result = connection.execute(text(query_string)).fetchall()

                    valid_dates = [(row.min_date, row.max_date) for row in final_result 
                    if row.min_date is not None and row.max_date is not None]

                    if not valid_dates:
                        print(f"No valid dates found in tables. Using default date range.")
                        return default_min_date, default_max_date

                    min_date = min(date[0] for date in valid_dates)
                    max_date = max(date[1] for date in valid_dates)

                    print(f"Fetched min_date: {min_date}, max_date: {max_date} for query: {query}")
                    return min_date, max_date

                except Exception as inner_e:
                    print(f"Error executing date query: {inner_e}. Using default date range.")
                    return default_min_date, default_max_date

        except Exception as e:
            print(f"Error fetching date range: {e}. Using default date range.")
            return default_min_date, default_max_date

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

    def refine_time_based_query(self, query: str) -> str:
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
                        is_time_based=True,
                        chart_type = item.chart_type
                        
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
                    chart_type="line"
                    
                )
            ])
    
    def get_queries_for_executor(self, role: str="Finance Manager", domain: str="finance") -> List[Dict[str, str]]:
        response = self.generate_queries(role=role, domain=domain)

        return [
            {
                "query": item.query,
                "explanation": item.question,
                "relevance": item.relevance,
                "is_time_based": item.is_time_based,
                "chart_type":item.chart_type
            }
            for item in response.queries
        ]