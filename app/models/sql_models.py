from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from typing import Union
from datetime import datetime

class SQLQueryItem(BaseModel):
    question: str 
    query: str 
    relevance: float 
    is_time_based: bool 
    chart_type: str 
    
    @field_validator('relevance')
    def relevance_must_be_between_0_and_1(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Relevance must be between 0.0 and 1.0')
        return round(v, 2)
    
    @field_validator('chart_type')
    def chart_type_must_be_valid(cls, v):
        valid_chart_types = ["Bar", "Line", "Area", "Pie", "Donut", "Scatter"]
        if v.lower() == "scatterplot":
            return "Scatter"
        if v not in valid_chart_types:
            raise ValueError(f'Chart type must be one of: {", ".join(valid_chart_types)}')
        return v

class SQLQueryResponse(BaseModel):
    queries: List[SQLQueryItem] 

class PreprocessingData(BaseModel):
    db_schema: str 
    db_type: str 
    role: str 
    domain: str 
    min_max_dates: List[str] 
    
    @field_validator('db_type')
    def validate_db_type(cls, v):
        valid_types = ["mysql", "postgres", "sqlite"]
        if v.lower() not in valid_types:
            raise ValueError(f"Database type must be one of: {', '.join(valid_types)}")
        return v.lower()

class QueryGenerationRequest(BaseModel):
    api_key: str 
    preprocessing_data: PreprocessingData 

class QueryForExecutor(BaseModel):
    query: str 
    explanation: str 
    relevance: float 
    is_time_based: bool 
    chart_type: str 

class QueriesForExecutorResponse(BaseModel):
    queries: List[QueryForExecutor] 

class PostprocessingRequest(BaseModel):
    queries: List[QueryForExecutor] 
    endpoint: str 
    

class QueryRequest(BaseModel):
    # db_schema: Dict[str, Any]
    db_schema:str
    db_type: str
    role: str
    domain: str
    min_date: Optional[Union[datetime, str]] = None
    max_date: Optional[Union[datetime, str]] = None
    api_key: Optional[str] = None
    
class NLQResponse(BaseModel):
    sql_query: str
    explanation: str
    chart_type:str
    
class NLQRequest(BaseModel):
    nl_query: str
    db_schema: str
    db_type: str
    api_key: Optional[str] = None
    
class QueryWithId(BaseModel):
    query_id: str = Field
    query: str = Field
    explanation: str

    
class BatchQueryDateUpdateRequest(BaseModel):
    api_key: Optional[str] = None
    queries: List[QueryWithId]
    min_date: str
    max_date: str
    db_type: str

class QueryDateUpdateResponse(BaseModel):
    query_id: str 
    original_query: str 
    updated_query: str 
    success: bool 
    error: Optional[str]

class TimeBasedQueriesUpdateRequest(BaseModel):
    db_type:str
    queries: List[QueryWithId] 
    min_date: str 
    max_date: str 
    api_key:Optional[str] = None


class TimeBasedQueriesUpdateResponse(BaseModel):
    updated_queries: List[QueryDateUpdateResponse]