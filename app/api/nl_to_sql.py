from fastapi import APIRouter, HTTPException
from app.models.sql_models import NLQResponse,NLQRequest
from app.services.NL2SQL import NLQToSQLGenerator
from app.config import GOOGLE_API_KEY
import json

router = APIRouter()
@router.post("/convert_nl_to_sql", response_model=NLQResponse)
async def convert_nlq_to_sql(request_data: NLQRequest):
    try:
        api_key = request_data.api_key or GOOGLE_API_KEY 
        sql_generator = NLQToSQLGenerator(api_key)
        result = sql_generator.convert_nlq_to_sql(
            nl_query=request_data.nl_query,
            db_schema=request_data.db_schema,
            db_type=request_data.db_type
        )
        if result.chart_type.lower() == 'scatterplot':
            result.chart_type = "scatter"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating SQL: {str(e)}")