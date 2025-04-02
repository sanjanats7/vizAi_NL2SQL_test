import logging
import json
import traceback
from fastapi import APIRouter, HTTPException
from app.models.sql_models import NLQResponse, NLQRequest
from app.services.NL2SQL import NLQToSQLGenerator
from app.config import GOOGLE_API_KEY

logger = logging.getLogger("api")

router = APIRouter()

@router.post("/convert_nl_to_sql", response_model=NLQResponse)
async def convert_nlq_to_sql(request_data: NLQRequest):
    try:
        logger.info(f"Received NLQ request: {request_data.nl_query}")

        api_key = request_data.api_key or GOOGLE_API_KEY
        sql_generator = NLQToSQLGenerator(api_key)

        logger.info(f"Using database type: {request_data.db_type}")

        logger.info(f"DB Schema: {request_data.db_schema}")
        
        result = sql_generator.convert_nlq_to_sql(
            nl_query=request_data.nl_query,
            db_schema=request_data.db_schema,
            db_type=request_data.db_type
        )
        
        if result.chart_type.lower() == 'scatterplot':
            logger.debug("Chart type corrected from 'scatterplot' to 'scatter'")
            result.chart_type = "scatter"

        logger.info("SQL query generated successfully")
        return result
    
    except Exception as e:
        logger.error(f"Error generating SQL: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generating SQL: {str(e)}")
