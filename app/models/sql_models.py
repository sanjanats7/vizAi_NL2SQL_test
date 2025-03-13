from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class SQLQueryItem(BaseModel):
    question: str = Field(..., description="Business question this query answers")
    query: str = Field(..., description="SQL query that answers the business question")
    relevance: float = Field(..., ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0")
    is_time_based: bool = Field(..., description="Whether this query analyzes time-based trends")
    chart_type: str = Field(..., description="Recommended chart type for visualization of query")
    
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

class PreprocessingData(BaseModel):
    db_schema: str = Field(..., description="Database schema as a string")
    db_type: str = Field(..., description="Database type (mysql, postgres, sqlite)")
    role: str = Field(default="Finance Manager", description="User role for query context")
    domain: str = Field(default="finance", description="Business domain for query context")
    min_max_dates: List[str] = Field(default=[], description="Array of min and max dates. If empty, generate non-time-based queries")
    
    @field_validator('db_type')
    def validate_db_type(cls, v):
        valid_types = ["mysql", "postgres", "sqlite"]
        if v.lower() not in valid_types:
            raise ValueError(f"Database type must be one of: {', '.join(valid_types)}")
        return v.lower()

class QueryGenerationRequest(BaseModel):
    api_key: str = Field(..., description="Google API key for Gemini")
    preprocessing_data: PreprocessingData = Field(..., description="Data from preprocessing service")

class QueryForExecutor(BaseModel):
    query: str = Field(..., description="SQL query to execute")
    explanation: str = Field(..., description="Explanation of what the query does")
    relevance: float = Field(..., description="Relevance score from 0.0 to 1.0")
    is_time_based: bool = Field(..., description="Whether this query analyzes time-based trends")
    chart_type: str = Field(..., description="Recommended chart type for visualization")

class QueriesForExecutorResponse(BaseModel):
    queries: List[QueryForExecutor] = Field(..., description="List of queries ready for execution")

class PostprocessingRequest(BaseModel):
    queries: List[QueryForExecutor] = Field(..., description="List of queries to send to postprocessing")
    endpoint: str = Field(..., description="Endpoint URL for the postprocessing service")
    

class QueryRequest(BaseModel):
    # db_schema: Dict[str, Any]
    db_schema:str
    db_type: str
    role: str
    domain: str
    min_date: str = None
    max_date: str = None
    api_key: str = None
    