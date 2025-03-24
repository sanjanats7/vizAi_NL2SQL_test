import re
from typing import Dict, Any
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import PydanticOutputParser
from app.models.sql_models import NLQResponse

class NLQToSQLGenerator:
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model=model, 
            google_api_key=api_key
        )
        self.parser = PydanticOutputParser(pydantic_object=NLQResponse)

    def get_sql_syntax_instruction(self, db_type: str) -> str:
        """Returns database-specific SQL syntax instructions."""
        db_type = db_type.lower()
        return {
            "mysql": "Write queries ONLY using syntax compatible with MySQL database.",
            "postgres": "Write queries ONLY using syntax compatible with PostgreSQL database.",
        }.get(db_type, "Write queries using standard SQL syntax.")

    def extract_sql_from_response(self, response: str) -> str:
        """Extracts SQL query from the model response."""
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL)
        if sql_match:
            return sql_match.group(1).strip()
        
        code_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        
        return response.strip()
    
    def convert_nlq_to_sql(self, nl_query: str, db_schema: str, db_type: str) -> NLQResponse:
        try:
            query_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert SQL query generator capable of converting natural language questions into optimized SQL queries.
                    
                    Given a database schema and a user question, generate a single SQL query that retrieves the relevant data.
                    
                    Database Schema:
                    {db_schema}
                    
                    Strict Rules:
                    -Use ONLY tables and columns explicitly listed in {db_schema}.
                    -DO NOT assume or invent any tables, columns, or relationships.
                    -Verify all table joins based on actual foreign key relationships in {db_schema}.
                    -Avoid unnecessary joins or complex subqueries unless absolutely necessary.
                    -Prioritize indexed columns for filtering (`WHERE`) and sorting (`ORDER BY`).
                    - If the schema does not support the query request, return:
                    "Error: Required data not found in schema."
                    
                    Instructions:
                    - {sql_syntax_instructions}
                    - Understand the question intent and map it to relevant tables and columns.
                    - Generate an optimized SQL query ensuring accuracy and efficiency.
                    - Avoid unnecessary joins or complex subqueries unless required.
                    - Ensure the SQL adheres to best practices for the {db_type} database.
                    - Provide a short, clear explanation of the query’s purpose within 255 characters.
                    - Use ONLY the tables and columns provided in {db_schema}.
                    - Do NOT assume or invent tables, columns, or relationships.
                    - Ensure that all joins are valid based on {db_schema}.
                    - Use `GROUP BY` and `ORDER BY` correctly when retrieving aggregated data.
                    - Prioritize primary keys and indexed columns for efficiency.
                    - After generating the query, verify its correctness against "{nl_query}".
                    - If the schema does not support the request, return: "Error: Required data not found in schema."
                    - For each query, recommend ONE of the following chart types that would best visualize the results:
                        * Bar: For comparing values across categories
                        * Line: For showing trends over time or continuous data
                        * Area: For emphasizing the magnitude of trends over time
                        * Pie: For showing proportions of a whole
                        * Donut: For showing proportions with a focus on a central value
                        * Scatterplot: For showing correlation between two variables
                    - Try to use a variety of chart types across your recommendations, including Scatterplot where appropriate.
                    
                    {format_instructions}"""),
                ("human", "Convert the following natural language question into an SQL query: {nl_query}")
            ])


            query_prompt = query_prompt.partial(
                format_instructions=self.parser.get_format_instructions(), 
                sql_syntax_instructions=self.get_sql_syntax_instruction(db_type),
                db_type=db_type
            )

            query_chain = query_prompt | self.llm | self.parser
            response = query_chain.invoke({
                "db_schema": db_schema,
                "nl_query": nl_query,
            })
            
            sql_query = self.extract_sql_from_response(response.sql_query)
            return NLQResponse(
                sql_query=sql_query,
                explanation=response.explanation,
                chart_type=response.chart_type
            )
        except Exception as e:
            return NLQResponse(
                sql_query=f"-- Error: {str(e)}",
                explanation="Error generating SQL query from natural language.",
                chart_type="None"
            )
