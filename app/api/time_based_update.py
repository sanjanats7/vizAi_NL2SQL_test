import logging
import json
import traceback
from fastapi import APIRouter, HTTPException
from app.models.sql_models import TimeBasedQueriesUpdateResponse, TimeBasedQueriesUpdateRequest
from app.services.time_based import update_time_based_queries
from app.config import GOOGLE_API_KEY

router = APIRouter()

logger = logging.getLogger("api")

@router.post("/")
async def update_queries(request_data: TimeBasedQueriesUpdateRequest):
    try:
        logger.info(f"Received request to update time-based queries:\n{request_data.model_dump_json(indent=2)}")

        response = await update_time_based_queries(
            api_key=request_data.api_key or GOOGLE_API_KEY,
            query_request=request_data
        )

        logger.info(f"Time-based query update successful:\n{json.dumps(response, indent=2)}")
        
        return response

    except Exception as e:
        logger.error(f"Error processing batch update: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing batch update: {str(e)}")
