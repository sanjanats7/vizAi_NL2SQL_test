from typing import List, Dict, Any
import google.generativeai as genai
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

class FinanceQueryGenerator:
    def __init__(self, schema: str, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize AI-powered query generator
        
        :param schema: Database schema description
        :param api_key: Google API key
        :param model: LLM model to use
        """
        self.schema = schema
        
        
        self.llm = ChatGoogleGenerativeAI(
            model=model, 
            google_api_key=api_key
        )
        
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert financial data analyst. 
            Generate SQL queries that provide meaningful insights for a finance manager.
            
            Database Schema:
            {schema}
            
            Context: Finance Manager's analytical needs
            
            Guidelines:
            - Focus on financial performance metrics
            - Provide queries that offer strategic insights
            - Ensure queries are concise and meaningful
            - Use aggregations, grouping, and analytical functions
            - Consider business performance, revenue trends, and financial health
            - Make queries based on different metrics
            
            Generate a unique, insightful SQL query that can be directly executed on the database.
            
            Format your response as:
            ```sql
            [SQL QUERY HERE]
            ```
            EXPLANATION: [Brief explanation of the query]"""),
            ("human", "Generate a finance-focused SQL query")
        ])
        
        self.chain = self.prompt | self.llm

    def clean_sql(self, sql_query: str) -> str:
        """
        Remove markdown formatting (backticks) from SQL queries.
        """
        return sql_query.replace("```sql", "").replace("```", "").strip()

    def generate_finance_queries(self, num_queries: int = 3) -> List[Dict[str, str]]:
        """
        Generate multiple finance-focused SQL queries
        
        :param num_queries: Number of queries to generate
        :return: List of generated SQL queries with explanations
        """
        queries = []
        
        for _ in range(num_queries):
            try:
                query_response = self.chain.invoke({
                    "schema": self.schema,
                })
                
                content = query_response.content
                
                if "EXPLANATION:" in content:
                    sql_query, explanation = content.split("EXPLANATION:", 1)
                    sql_query = self.clean_sql(sql_query)
                    explanation = explanation.strip()
                else:
                    sql_query = self.clean_sql(content)
                    explanation = "No explanation provided."
                
                queries.append({
                    "query": sql_query,
                    "explanation": explanation
                })
                
            except Exception as e:
                print(f"Error generating query: {e}")
                
                queries.append({
                    "query": "-- Error generating query",
                    "explanation": str(e)
                })
        
        return queries