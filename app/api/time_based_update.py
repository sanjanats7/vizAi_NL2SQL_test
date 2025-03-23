from fastapi import APIRouter, HTTPException
from app.models.sql_models import TimeBasedQueriesUpdateResponse, TimeBasedQueriesUpdateRequest
from app.services.time_based import update_time_based_queries
from app.config import GOOGLE_API_KEY
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/")
async def update_queries(request_data: TimeBasedQueriesUpdateRequest):
    try:
        # ✅ Log the incoming request payload
        logger.info(f"📤 LLM Request Payload: {request_data.model_dump_json(indent=2)}")

        # ✅ Pass the parsed Pydantic model directly
        response = await update_time_based_queries(
            api_key=request_data.api_key or GOOGLE_API_KEY,
            query_request=request_data
        )

        # ✅ Log the LLM service response
        logger.info(f"📥 LLM Response: {json.dumps(response, indent=2)}")
        
        return response

    except Exception as e:
        logger.error(f"❌ Error processing batch update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing batch update: {str(e)}")
