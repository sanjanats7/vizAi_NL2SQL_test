from fastapi import APIRouter, HTTPException
from app.models.sql_models import TimeBasedQueriesUpdateResponse, BatchQueryDateUpdateRequest,TimeBasedQueriesUpdateRequest
from app.services.time_based import update_query_date_range,update_time_based_queries
from app.config import GOOGLE_API_KEY
import json
router = APIRouter()


@router.post("/", response_model=TimeBasedQueriesUpdateResponse)
async def update_queries(request_data: BatchQueryDateUpdateRequest):
    try:
        time_based_request = TimeBasedQueriesUpdateRequest(
            queries=request_data.queries,
            min_date=request_data.min_date,
            max_date=request_data.max_date,
            db_type=request_data.db_type
        )
        
        response = await update_time_based_queries(
            api_key=request_data.api_key or GOOGLE_API_KEY,
            query_request=time_based_request
        )
        
        # response = await update_time_based_queries(
        #     api_key=request_data.api_key or GOOGLE_API_KEY,
        #     query_request=request_data 
        # )
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing batch update: {str(e)}")
