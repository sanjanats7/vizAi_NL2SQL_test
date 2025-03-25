import logging
import json
import traceback
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from app.models.sql_models import QueriesForExecutorResponse, QueryRequest
from app.services.query_generator import QueryGenerator
from app.config import GOOGLE_API_KEY

logger = logging.getLogger("api")

router = APIRouter()

@router.post("/", response_model=QueriesForExecutorResponse)
async def get_queries(request_data: QueryRequest):
    try:
        logger.info(f"Received request: {request_data}")

        min_max_dates = []
        if request_data.min_date and request_data.max_date:
            min_date = request_data.min_date
            max_date = request_data.max_date
            
            if isinstance(min_date, datetime):
                min_date = min_date.strftime("%Y-%m-%d")
            elif isinstance(min_date, str):
                min_date = min_date.split("T")[0] if "T" in min_date else min_date
                
            if isinstance(max_date, datetime):
                max_date = max_date.strftime("%Y-%m-%d")
            elif isinstance(max_date, str):
                max_date = max_date.split("T")[0] if "T" in max_date else max_date
                
            min_max_dates = [min_date, max_date]
            logger.info(f"Processed date range: {min_date} to {max_date}")
        
        api_key = request_data.api_key or GOOGLE_API_KEY
        
        schema_str = ""
        if isinstance(request_data.db_schema, str):
            try:
                schema_obj = json.loads(request_data.db_schema)
                schema_str = json.dumps(schema_obj, indent=2)
            except json.JSONDecodeError:
                schema_str = request_data.db_schema
        else:
            schema_str = json.dumps(request_data.db_schema, indent=2)
        
        logger.info(f"Using database type: {request_data.db_type}")
        
        generator = QueryGenerator(
            schema=schema_str,
            api_key=api_key,
            db_type=request_data.db_type
        )
        
        queries = generator.get_queries_for_executor(
            role=request_data.role,
            domain=request_data.domain,
            min_max_dates=min_max_dates
        )
        
        logger.info(f"Generated {len(queries)} queries successfully")
        return QueriesForExecutorResponse(queries=queries)
    
    except Exception as e:
        logger.error(f"Error in get_queries: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.post("/raw")
async def process_raw_request(request: Request):
    """Debug endpoint to see raw request data"""
    try:
        body = await request.body()
        json_body = await request.json()
        
        logger.debug(f"Raw request received: {body.decode('utf-8')}")
        return {
            "message": "Raw request received",
            "raw_body": str(body),
            "json_body": json_body
        }
    except Exception as e:
        logger.error(f"Error processing raw request: {str(e)}\n{traceback.format_exc()}")
        return {"error": str(e)}
