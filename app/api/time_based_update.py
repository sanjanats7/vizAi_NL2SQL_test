from fastapi import APIRouter, HTTPException
from app.models.sql_models import QueryDateUpdateResponse,QueryDateUpdateRequest
from app.services.time_based import update_query_date_range,update_time_based_queries
from app.config import GOOGLE_API_KEY
import json


router = APIRouter()
@router.post("/", response_model=QueryDateUpdateResponse)
async def update_queries(request_data:QueryDateUpdateRequest):
    try:
        response = update_query_date_range(
            api_key=request_data.api_key,
            query_id=request_data.query_id,
            query=request_data.query,
            min_date=request_data.min_date,
            max_date=request_data.max_date
        )  
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
